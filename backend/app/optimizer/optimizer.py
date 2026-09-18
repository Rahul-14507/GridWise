"""Central Charging Optimization Engine.

Coordinates EV urgency analysis, deadline risk evaluation, priority scoring, battery dispatch strategy,
and constrained power allocation to produce validated, explainable OptimizationDecision payloads.
"""

from typing import List, Optional
from app.config.settings import Settings, get_settings
from app.domain.models.system import SystemState
from app.domain.models.ev import EV, EVStatus
from app.domain.services.energy_service import EnergyService
from app.optimizer.models import (
    BatteryAction,
    DeadlineStatus,
    EVAllocationDecision,
    OptimizationDecision,
)
from app.optimizer.urgency import UrgencyCalculator
from app.optimizer.deadline import DeadlineAnalyzer
from app.optimizer.priority import PriorityScorer
from app.optimizer.battery_strategy import BatteryStrategy
from app.optimizer.allocator import PowerAllocator
from app.optimizer.constraints import ConstraintValidator


class ChargingOptimizer:
    """Intelligent EV charging priority and power allocation optimizer."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize ChargingOptimizer with application settings."""
        self.settings = settings or get_settings()

    def optimize(
        self,
        system_state: SystemState,
        simulation_interval_seconds: Optional[float] = None,
    ) -> OptimizationDecision:
        """Execute one complete optimization cycle for the given SystemState.

        Args:
            system_state: Current snapshot of facility environment, grid, battery, EVs, and parking.
            simulation_interval_seconds: Step interval duration in seconds. Defaults to settings config.

        Returns:
            Validated, explainable OptimizationDecision domain model.
        """
        dt_seconds = simulation_interval_seconds or self.settings.simulation_interval_seconds
        current_time = system_state.timestamp

        # 1. Evaluate Urgency, Deadlines, and Priority for all EVs
        analyzed_evs = []
        total_eligible_demand_kw = 0.0

        for ev in system_state.evs:
            rem_hours = ev.remaining_time_hours(current_time)
            energy_req = ev.energy_required_kwh

            # Urgency components
            soc_urg = UrgencyCalculator.calculate_soc_urgency(ev.soc_percent, ev.target_soc_percent)
            dep_urg = UrgencyCalculator.calculate_departure_urgency(
                remaining_time_hours=rem_hours,
                horizon_hours=self.settings.departure_urgency_horizon_hours,
                critical_horizon_hours=self.settings.departure_critical_horizon_hours,
            )
            def_score = UrgencyCalculator.calculate_energy_deficit_score(energy_req, ev.battery_capacity_kwh)

            waiting_mins = max(0.0, (current_time - ev.arrival_time).total_seconds() / 60.0)
            wait_score = UrgencyCalculator.calculate_waiting_score(
                waiting_minutes=waiting_mins,
                reference_minutes=self.settings.waiting_reference_minutes,
            )

            # Deadline analysis
            deadline_status, req_avg_power = DeadlineAnalyzer.analyze_deadline(
                energy_required_kwh=energy_req,
                remaining_time_hours=rem_hours,
                max_charging_power_kw=ev.max_charging_power_kw,
            )

            # Priority score
            priority = PriorityScorer.calculate_priority(
                soc_urgency=soc_urg,
                departure_urgency=dep_urg,
                energy_deficit_score=def_score,
                waiting_score=wait_score,
                w_soc=self.settings.priority_weight_soc,
                w_departure=self.settings.priority_weight_departure,
                w_deficit=self.settings.priority_weight_deficit,
                w_waiting=self.settings.priority_weight_waiting,
            )

            analyzed_evs.append({
                "ev": ev,
                "soc_urgency": soc_urg,
                "departure_urgency": dep_urg,
                "energy_deficit_score": def_score,
                "waiting_score": wait_score,
                "deadline_status": deadline_status,
                "required_average_power_kw": req_avg_power,
                "priority_score": priority,
            })

            if ev.status != EVStatus.DISCONNECTED and ev.soc_percent < ev.target_soc_percent and energy_req > 0:
                duration_hours = dt_seconds / 3600.0
                power_for_target = energy_req / duration_hours if duration_hours > 0 else 0.0
                total_eligible_demand_kw += min(ev.max_charging_power_kw, power_for_target)

        # 2. Calculate Base Available EV Power (without battery)
        effective_grid_kw = system_state.thermal.effective_capacity_kw
        building_demand_kw = system_state.energy.grid.building_demand_kw
        solar_gen_kw = system_state.energy.solar.estimated_generation_kw

        base_available_ev_power = EnergyService.calculate_available_ev_power(
            grid_capacity_kw=effective_grid_kw,
            building_demand_kw=building_demand_kw,
            solar_generation_kw=solar_gen_kw,
            battery_discharge_kw=0.0,
        )

        # 3. Determine Battery Strategy
        unmet_demand_kw = max(0.0, total_eligible_demand_kw - base_available_ev_power)
        battery_action, battery_power_kw = BatteryStrategy.evaluate_battery_dispatch(
            battery=system_state.battery,
            unmet_ev_demand_kw=unmet_demand_kw,
            simulation_interval_seconds=dt_seconds,
            enable_battery_support=self.settings.enable_battery_support_in_optimizer,
        )

        # 4. Total Available EV Power including Battery Contribution
        battery_discharge_contribution = battery_power_kw if battery_action == BatteryAction.DISCHARGE else 0.0
        total_available_ev_power = EnergyService.calculate_available_ev_power(
            grid_capacity_kw=effective_grid_kw,
            building_demand_kw=building_demand_kw,
            solar_generation_kw=solar_gen_kw,
            battery_discharge_kw=battery_discharge_contribution,
        )

        # 5. Execute Constrained Power Allocation
        ev_items_for_allocator = [
            (item["ev"], item["priority_score"], item["deadline_status"])
            for item in analyzed_evs
        ]
        allocations_map = PowerAllocator.allocate_power(
            ev_items=ev_items_for_allocator,
            available_power_kw=total_available_ev_power,
            simulation_interval_seconds=dt_seconds,
        )

        # 6. Generate Explainability Reasons & Build Allocation Decisions
        ev_decisions: List[EVAllocationDecision] = []
        warnings: List[str] = []

        for item in analyzed_evs:
            ev = item["ev"]
            allocated_power = allocations_map.get(ev.id, 0.0)
            status = item["deadline_status"]

            # Reason synthesis
            if ev.status == EVStatus.DISCONNECTED:
                reason = "Disconnected: Vehicle is not connected"
            elif ev.soc_percent >= ev.target_soc_percent:
                reason = f"Completed: Target SoC of {ev.target_soc_percent:.0f}% reached"
            elif status == DeadlineStatus.EXPIRED:
                reason = "Expired: Departure time passed; charging paused"
            elif allocated_power >= ev.max_charging_power_kw - 0.01:
                if status == DeadlineStatus.AT_RISK:
                    reason = f"At Risk: Allocated maximum charging rate ({ev.max_charging_power_kw:.1f} kW) to minimize departure deficit"
                    warnings.append(f"EV '{ev.id}' cannot reach target {ev.target_soc_percent:.0f}% by scheduled departure")
                else:
                    reason = f"High Priority: Full maximum charging rate ({ev.max_charging_power_kw:.1f} kW) allocated"
            elif allocated_power > 0.0:
                reason = f"Partial Allocation: Granted {allocated_power:.2f} kW constrained by available capacity"
            else:
                if status == DeadlineStatus.AT_RISK:
                    reason = "At Risk: Insufficient capacity available despite critical deadline"
                    warnings.append(f"EV '{ev.id}' received 0 kW due to capacity deficit")
                else:
                    reason = "Paused/Waiting: Lower priority rank under constrained infrastructure headroom"

            ev_decisions.append(
                EVAllocationDecision(
                    ev_id=ev.id,
                    allocated_power_kw=allocated_power,
                    priority_score=item["priority_score"],
                    soc_urgency=item["soc_urgency"],
                    departure_urgency=item["departure_urgency"],
                    energy_deficit_score=item["energy_deficit_score"],
                    waiting_score=item["waiting_score"],
                    required_average_power_kw=item["required_average_power_kw"],
                    deadline_status=status,
                    reason=reason,
                )
            )

        total_allocated_power = sum(allocations_map.values())
        net_infrastructure_load = building_demand_kw + total_allocated_power - solar_gen_kw - battery_discharge_contribution
        net_infrastructure_load = max(0.0, net_infrastructure_load)

        if system_state.thermal.derating_factor < 1.0:
            warnings.append(
                f"Thermal Derating Active: Grid capacity reduced by {(1.0 - system_state.thermal.derating_factor)*100:.0f}% "
                f"({effective_grid_kw:.1f} kW effective limit)"
            )

        # 7. Independent Hard Safety Validation
        ConstraintValidator.validate_allocations(
            system_state=system_state,
            ev_allocations=allocations_map,
            battery_discharge_kw=battery_discharge_contribution,
            battery_charge_kw=0.0,
            simulation_interval_seconds=dt_seconds,
        )

        return OptimizationDecision(
            timestamp=current_time,
            available_ev_power_kw=round(total_available_ev_power, 4),
            total_allocated_power_kw=round(total_allocated_power, 4),
            allocations=ev_decisions,
            battery_action=battery_action,
            battery_power_kw=round(battery_power_kw, 4),
            infrastructure_load_kw=round(net_infrastructure_load, 4),
            effective_capacity_kw=round(effective_grid_kw, 4),
            warnings=warnings,
        )
