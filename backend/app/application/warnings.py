"""Warning evaluation service for Smart EV Charging Management System."""

from typing import List, Optional
from app.application.models import SystemWarning
from app.domain.models.simulation import ThermalStatus
from app.domain.models.system import SystemState
from app.infrastructure.hardware.telemetry_service import HardwareStatusSummary
from app.optimizer.models import DeadlineStatus, OptimizationDecision


class WarningService:
    """Evaluates factual conditions from system state, optimizer decisions, and hardware health."""

    @staticmethod
    def evaluate_warnings(
        system_state: SystemState,
        latest_decision: Optional[OptimizationDecision] = None,
        hardware_status: Optional[HardwareStatusSummary] = None,
        data_source: str = "simulation",
    ) -> List[SystemWarning]:
        """Generate structured warnings from current factual state without duplicating domain logic."""
        warnings: List[SystemWarning] = []

        # 1. Hardware health warnings
        if hardware_status is not None:
            if hardware_status.stale_devices > 0:
                warnings.append(
                    SystemWarning(
                        code="HARDWARE_TELEMETRY_STALE",
                        severity="warning",
                        message=f"{hardware_status.stale_devices} hardware telemetry device(s) report stale data (> {hardware_status.timeout_seconds:.0f}s old)",
                    )
                )
            if data_source == "hardware" and hardware_status.active_devices == 0:
                warnings.append(
                    SystemWarning(
                        code="NO_HARDWARE_TELEMETRY",
                        severity="critical",
                        message="Active data source is set to hardware, but no online telemetry devices are reporting",
                    )
                )

        # 2. Thermal Derating warnings
        if system_state.thermal.thermal_status != ThermalStatus.NORMAL:
            severity = "critical" if system_state.thermal.thermal_status == ThermalStatus.CRITICAL else "warning"
            warnings.append(
                SystemWarning(
                    code="THERMAL_DERATING_ACTIVE",
                    severity=severity,
                    message=(
                        f"Grid capacity is thermally derated to {system_state.thermal.effective_capacity_kw:.1f} kW "
                        f"(nominal {system_state.thermal.base_capacity_kw:.1f} kW) due to ambient temperature of "
                        f"{system_state.environment.temperature_c:.1f}°C"
                    ),
                )
            )

        # 3. Available charging power warnings
        if system_state.energy.available_ev_charging_capacity_kw <= 0.0:
            warnings.append(
                SystemWarning(
                    code="ZERO_EV_CHARGING_CAPACITY",
                    severity="warning",
                    message="Zero net capacity available for EV charging under current grid and building demand constraints",
                )
            )

        # 4. Battery low reserve warning
        if system_state.battery.soc_percent <= system_state.battery.minimum_soc_percent:
            warnings.append(
                SystemWarning(
                    code="BATTERY_LOW_RESERVE",
                    severity="info",
                    message=f"Stationary battery at or below reserve floor ({system_state.battery.soc_percent:.1f}% <= {system_state.battery.minimum_soc_percent:.1f}%)",
                )
            )

        # 5. Optimizer-derived warnings (EV deadline risks)
        if latest_decision is not None:
            for alloc in latest_decision.allocations:
                if alloc.deadline_status == DeadlineStatus.AT_RISK:
                    warnings.append(
                        SystemWarning(
                            code="EV_DEADLINE_AT_RISK",
                            severity="warning",
                            message=f"EV '{alloc.ev_id}' is at risk of missing target SoC before scheduled departure (requires {alloc.required_average_power_kw:.1f} kW avg)",
                        )
                    )

        # 6. Infrastructure utilization warnings
        effective_cap = system_state.energy.grid.effective_capacity_kw
        total_ev_alloc = sum(ev.allocated_power_kw for ev in system_state.evs)
        total_load = system_state.energy.grid.building_demand_kw + total_ev_alloc - system_state.energy.solar.estimated_generation_kw
        if effective_cap > 0 and (total_load / effective_cap) >= 0.90:
            warnings.append(
                SystemWarning(
                    code="HIGH_INFRASTRUCTURE_UTILIZATION",
                    severity="warning",
                    message=f"Net infrastructure loading is at {(total_load / effective_cap) * 100:.1f}% of effective capacity ({total_load:.1f} / {effective_cap:.1f} kW)",
                )
            )

        return warnings
