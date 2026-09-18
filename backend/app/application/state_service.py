"""Application State Coordinator.

Centralizes access to the live SystemState, latest OptimizationDecision,
and simulation/hardware execution bridges.
"""

import socket
import threading
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict, List, Optional

from app.application.models import (
    BatterySummary,
    EnergyDetailResponse,
    EnergySummary,
    EVDetailResponse,
    EVSummary,
    HardwareSummary,
    NetworkInfoResponse,
    OptimizationApplyResponse,
    ParkingSummary,
    SystemStatusResponse,
    SystemSummaryResponse,
)
from app.application.warnings import WarningService
from app.config.settings import Settings, get_settings
from app.domain.models.ev import EV, EVStatus
from app.domain.models.qr_session import EVRegistrationRequest, QRSession, QRSessionStatus
from app.domain.models.simulation import SimulationRunStatus
from app.domain.models.system import SystemState
from app.infrastructure.hardware.telemetry_service import (
    HardwareTelemetryService,
    get_hardware_telemetry_service,
)
from app.optimizer.models import OptimizationDecision
from app.optimizer.optimizer import ChargingOptimizer
from app.simulation.engine import SimulationEngine, get_simulation_engine


class AppStateService:
    """In-memory coordinator bridging domain, simulation, hardware, and optimizer layers."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        sim_engine: Optional[SimulationEngine] = None,
        hw_service: Optional[HardwareTelemetryService] = None,
        optimizer: Optional[ChargingOptimizer] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._sim_engine = sim_engine or get_simulation_engine()
        self._hw_service = hw_service or get_hardware_telemetry_service()
        self._optimizer = optimizer or ChargingOptimizer(settings=self._settings)
        self._latest_decision: Optional[OptimizationDecision] = None
        self._qr_sessions: Dict[str, QRSession] = {}
        self._lock = threading.Lock()

    def get_current_state(self) -> SystemState:
        """Retrieve the authoritative SystemState snapshot according to configured data source."""
        with self._lock:
            hw_summary = self._hw_service.get_status_summary()
            if self._settings.telemetry_data_source == "hardware" or hw_summary.active_devices > 0 or self._hw_service.get_latest_telemetry() is not None:
                sim_state = self._sim_engine.get_state()
                try:
                    return self._hw_service.build_hardware_system_state(
                        building_demand_kw=sim_state.energy.grid.building_demand_kw,
                        battery=sim_state.battery,
                        evs=sim_state.evs,
                        parking=sim_state.parking,
                        settings=self._settings,
                    )
                except ValueError:
                    return sim_state
            return self._sim_engine.get_state()

    def get_latest_decision(self) -> Optional[OptimizationDecision]:
        """Retrieve the most recent optimization decision, or None if none computed."""
        with self._lock:
            return self._latest_decision

    def set_latest_decision(self, decision: OptimizationDecision) -> None:
        """Store an externally generated optimization decision."""
        with self._lock:
            self._latest_decision = decision

    def run_optimization(self) -> OptimizationDecision:
        """Run ChargingOptimizer on current SystemState, cache, and return the decision."""
        current_state = self.get_current_state()
        decision = self._optimizer.optimize(
            system_state=current_state,
            simulation_interval_seconds=float(self._settings.simulation_interval_seconds),
        )
        with self._lock:
            self._latest_decision = decision
        return decision

    def apply_optimization_to_simulation(self) -> OptimizationApplyResponse:
        """Apply the latest computed optimization decision to the simulation engine.

        Raises:
            ValueError: If in hardware mode or if no decision is available.
        """
        with self._lock:
            if self._settings.telemetry_data_source == "hardware":
                raise ValueError("Optimization decisions cannot be applied directly to physical hardware in hardware mode")

            if self._latest_decision is None:
                raise ValueError("No optimization decision available to apply. Run /api/v1/optimization/run first")

            decision = self._latest_decision
            alloc_dict = decision.get_allocations_dict()

            # Update simulated EVs with allocated power and active charging status
            updated_evs: List[EV] = []
            for ev in self._sim_engine.ev_sim.evs:
                alloc_kw = alloc_dict.get(ev.id, 0.0)
                new_status = ev.status
                if ev.status not in (EVStatus.COMPLETED, EVStatus.DISCONNECTED):
                    if alloc_kw > 0.0:
                        new_status = EVStatus.CHARGING
                    elif ev.status == EVStatus.CHARGING:
                        new_status = EVStatus.PAUSED
                updated_ev = ev.model_copy(update={"allocated_power_kw": alloc_kw, "status": new_status})
                updated_evs.append(updated_ev)

            self._sim_engine.ev_sim.set_evs(updated_evs)
            self._sim_engine.parking_sim.sync_with_evs(updated_evs)

            return OptimizationApplyResponse(
                status="applied",
                decision_timestamp=decision.timestamp,
                total_allocated_kw=decision.total_allocated_power_kw,
                ev_allocations_count=len(decision.allocations),
                battery_action=decision.battery_action.value,
                battery_power_kw=decision.battery_power_kw,
                message=f"Applied power allocations to {len(decision.allocations)} EVs ({decision.total_allocated_power_kw:.1f} kW total)",
            )

    def get_system_summary(self) -> SystemSummaryResponse:
        """Assemble a presentation-friendly dashboard summary."""
        state = self.get_current_state()
        hw_summary = self._hw_service.get_status_summary(current_time=state.timestamp)
        warnings = WarningService.evaluate_warnings(
            system_state=state,
            latest_decision=self._latest_decision,
            hardware_status=hw_summary,
            data_source=self._settings.telemetry_data_source,
        )

        ev_counts = {"charging": 0, "waiting": 0, "paused": 0, "completed": 0, "disconnected": 0}
        for ev in state.evs:
            status_key = ev.status.value if isinstance(ev.status, EVStatus) else str(ev.status).lower()
            if status_key in ev_counts:
                ev_counts[status_key] += 1

        has_critical = any(w.severity == "critical" for w in warnings)
        has_warning = any(w.severity == "warning" for w in warnings)
        if has_critical:
            system_status = "degraded"
        elif has_warning:
            system_status = "warning"
        else:
            system_status = "operational"

        battery_action = "idle"
        if self._latest_decision is not None:
            battery_action = self._latest_decision.battery_action.value

        return SystemSummaryResponse(
            timestamp=state.timestamp,
            system_status=system_status,
            data_source=self._settings.telemetry_data_source,
            energy=EnergySummary(
                grid_capacity_kw=state.energy.grid.max_capacity_kw,
                effective_capacity_kw=state.energy.grid.effective_capacity_kw,
                building_demand_kw=state.energy.grid.building_demand_kw,
                solar_generation_kw=state.energy.solar.estimated_generation_kw,
                available_ev_power_kw=state.energy.available_ev_charging_capacity_kw,
            ),
            battery=BatterySummary(
                soc_percent=state.battery.soc_percent,
                current_energy_kwh=round(state.battery.capacity_kwh * (state.battery.soc_percent / 100.0), 4),
                capacity_kwh=state.battery.capacity_kwh,
                action=battery_action,
            ),
            evs=EVSummary(
                total=len(state.evs),
                charging=ev_counts["charging"],
                waiting=ev_counts["waiting"],
                paused=ev_counts["paused"],
                completed=ev_counts["completed"],
                disconnected=ev_counts["disconnected"],
            ),
            parking=ParkingSummary(
                total_slots=state.parking.total_slots,
                occupied_slots=state.parking.occupied_slots,
                available_slots=state.parking.available_slots,
            ),
            hardware=HardwareSummary(
                status=hw_summary.status,
                devices_online=hw_summary.active_devices,
                devices_stale=hw_summary.stale_devices,
            ),
            warnings=warnings,
        )

    def get_system_status(self) -> SystemStatusResponse:
        """Assemble operational health and status response."""
        state = self.get_current_state()
        hw_summary = self._hw_service.get_status_summary(current_time=state.timestamp)
        warnings = WarningService.evaluate_warnings(
            system_state=state,
            latest_decision=self._latest_decision,
            hardware_status=hw_summary,
            data_source=self._settings.telemetry_data_source,
        )

        has_critical = any(w.severity == "critical" for w in warnings)
        has_warning = any(w.severity == "warning" for w in warnings)
        if has_critical:
            status = "degraded"
        elif has_warning:
            status = "warning"
        else:
            status = "operational"

        return SystemStatusResponse(
            status=status,
            data_source=self._settings.telemetry_data_source,
            simulation_running=self._sim_engine.status == SimulationRunStatus.RUNNING,
            hardware_devices_online=hw_summary.active_devices,
            last_state_update=state.timestamp,
            warnings=warnings,
        )

    def get_energy_detail(self) -> EnergyDetailResponse:
        """Assemble detailed facility energy breakdown."""
        state = self.get_current_state()
        total_ev_alloc = sum(ev.allocated_power_kw for ev in state.evs)
        infrastructure_load = state.energy.grid.building_demand_kw + total_ev_alloc - state.energy.solar.estimated_generation_kw

        battery_discharge = 0.0
        battery_charge = 0.0
        if self._latest_decision is not None:
            if self._latest_decision.battery_action.value == "discharge":
                battery_discharge = self._latest_decision.battery_power_kw
            elif self._latest_decision.battery_action.value == "charge":
                battery_charge = self._latest_decision.battery_power_kw

        return EnergyDetailResponse(
            timestamp=state.timestamp,
            base_grid_capacity_kw=state.energy.grid.max_capacity_kw,
            effective_grid_capacity_kw=state.energy.grid.effective_capacity_kw,
            building_demand_kw=state.energy.grid.building_demand_kw,
            solar_voltage_v=state.energy.solar.solar_voltage_v,
            solar_availability_percent=state.energy.solar.availability_percent,
            estimated_solar_generation_kw=state.energy.solar.estimated_generation_kw,
            battery_discharge_kw=battery_discharge,
            battery_charge_kw=battery_charge,
            available_ev_charging_power_kw=state.energy.available_ev_charging_capacity_kw,
            total_ev_allocated_power_kw=total_ev_alloc,
            infrastructure_load_kw=max(0.0, infrastructure_load),
        )

    def get_evs_detail(self) -> List[EVDetailResponse]:
        """Assemble enriched status for all connected EVs."""
        state = self.get_current_state()
        now = state.timestamp

        decision_map = {}
        if self._latest_decision is not None:
            for alloc in self._latest_decision.allocations:
                decision_map[alloc.ev_id] = alloc

        details = []
        for ev in state.evs:
            rem_hours = ev.remaining_time_hours(now)
            rem_minutes = max(0.0, rem_hours * 60.0)
            deficit_kwh = ev.energy_required_kwh
            req_power = ev.required_average_power_kw(now)

            alloc_info = decision_map.get(ev.id)
            priority_score = alloc_info.priority_score if alloc_info else None
            deadline_status = alloc_info.deadline_status.value if alloc_info else None
            reason = alloc_info.reason if alloc_info else None

            details.append(
                EVDetailResponse(
                    id=ev.id,
                    slot_id=ev.slot_id,
                    status=ev.status.value if isinstance(ev.status, EVStatus) else str(ev.status),
                    battery_capacity_kwh=ev.battery_capacity_kwh,
                    soc_percent=ev.soc_percent,
                    target_soc_percent=ev.target_soc_percent,
                    max_charging_power_kw=ev.max_charging_power_kw,
                    allocated_power_kw=ev.allocated_power_kw,
                    arrival_time=ev.arrival_time,
                    departure_time=ev.departure_time,
                    energy_required_kwh=deficit_kwh,
                    remaining_time_minutes=rem_minutes,
                    required_average_power_kw=req_power,
                    priority_score=priority_score,
                    deadline_status=deadline_status,
                    reason=reason,
                )
            )
        return details

    def get_ev_detail(self, ev_id: str) -> Optional[EVDetailResponse]:
        """Retrieve enriched details for a single EV, or None if not found."""
        for ev_detail in self.get_evs_detail():
            if ev_detail.id == ev_id:
                return ev_detail
        return None

    def create_qr_session(self, bay_id: Optional[str] = None) -> QRSession:
        """Generate a cryptographically unique single-use QR onboarding session."""
        with self._lock:
            token = f"QR-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now(timezone.utc)
            slot = bay_id or f"BAY-0{len(self._sim_engine.ev_sim.evs) + 1}"
            session = QRSession(
                session_id=token,
                bay_id=slot,
                created_at=now,
                status=QRSessionStatus.ACTIVE,
                expires_at=now + timedelta(minutes=15),
            )
            self._qr_sessions[token] = session
            return session

    def get_qr_session(self, session_id: str) -> Optional[QRSession]:
        """Retrieve a QR onboarding session by session ID."""
        with self._lock:
            return self._qr_sessions.get(session_id)

    def claim_qr_session(self, session_id: str) -> QRSession:
        """Mark a QR session as scanned/claimed so the kiosk expires the token."""
        with self._lock:
            session = self._qr_sessions.get(session_id)
            if session is None:
                raise ValueError(f"QR Session '{session_id}' not found")
            if session.status == QRSessionStatus.EXPIRED:
                raise ValueError(f"QR Session '{session_id}' has expired")
            if session.status == QRSessionStatus.REGISTERED:
                return session

            updated = session.model_copy(update={"status": QRSessionStatus.SCANNED})
            self._qr_sessions[session_id] = updated
            return updated

    def register_driver_ev(self, req: EVRegistrationRequest) -> EVDetailResponse:
        """Register a driver vehicle from a mobile QR scan into the active fleet."""
        with self._lock:
            session = self._qr_sessions.get(req.session_id)
            if session is None:
                raise ValueError(f"Invalid QR session token '{req.session_id}'")
            if session.status == QRSessionStatus.EXPIRED:
                raise ValueError("This QR code has expired. Please scan the current QR code on the kiosk.")
            if session.status == QRSessionStatus.REGISTERED and session.ev_id:
                # Idempotent response if already registered
                existing = self.get_ev_detail(session.ev_id)
                if existing:
                    return existing

            now = datetime.now(timezone.utc)
            assigned_ev_id = req.ev_id or f"EV-{len(self._sim_engine.ev_sim.evs) + 1:03d}"
            assigned_slot = req.slot_id or session.bay_id or f"BAY-{len(self._sim_engine.ev_sim.evs) + 1:02d}"
            departure = now + timedelta(hours=max(0.5, req.departure_in_hours))

            new_ev = EV(
                id=assigned_ev_id,
                slot_id=assigned_slot,
                battery_capacity_kwh=req.battery_capacity_kwh,
                soc_percent=req.soc_percent,
                target_soc_percent=req.target_soc_percent,
                max_charging_power_kw=req.max_charging_power_kw,
                allocated_power_kw=0.0,
                arrival_time=now,
                departure_time=departure,
                status=EVStatus.WAITING,
            )

            # Add to simulation fleet
            existing_evs = [ev for ev in self._sim_engine.ev_sim.evs if ev.id != assigned_ev_id]
            updated_fleet = [*existing_evs, new_ev]
            self._sim_engine.ev_sim.set_evs(updated_fleet)
            self._sim_engine.parking_sim.sync_with_evs(updated_fleet)

            # Update QR session state
            self._qr_sessions[req.session_id] = session.model_copy(
                update={"status": QRSessionStatus.REGISTERED, "ev_id": assigned_ev_id}
            )

        # Run optimizer immediately so power is allocated
        self.run_optimization()
        self.apply_optimization_to_simulation()

        detail = self.get_ev_detail(assigned_ev_id)
        if detail is None:
            raise RuntimeError(f"Failed to retrieve registered EV '{assigned_ev_id}'")
        return detail

    def get_network_info(self) -> NetworkInfoResponse:
        """Discover the host machine's active local LAN IPv4 address."""
        host_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                host_ip = s.getsockname()[0]
            finally:
                s.close()
        except Exception:
            host_ip = "127.0.0.1"

        return NetworkInfoResponse(
            host_ip=host_ip,
            frontend_port=3000,
            backend_port=8000,
            driver_base_url=f"http://{host_ip}:3000/?view=driver",
        )

    def reset_decision(self) -> None:
        """Clear cached optimization decision (for testing)."""
        with self._lock:
            self._latest_decision = None


@lru_cache()
def get_app_state_service() -> AppStateService:
    """Retrieve singleton AppStateService instance."""
    return AppStateService()

