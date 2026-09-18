"""Mandatory Critical Infrastructure Safety Test.

Verifies the hard constraint:
    effective capacity = 22 kW
    building demand = 12 kW
    solar generation = 3 kW
    battery discharge = 0 kW
    available EV power = 13 kW
    EV demand = 20 kW

The optimizer MUST NOT allocate more than 13 kW total across all EVs.
"""

from datetime import datetime, timezone, timedelta
from app.domain.models.hardware import HardwareTelemetry
from app.domain.models.energy import GridState, SolarState, EnergyState
from app.domain.models.battery import VirtualBattery
from app.domain.models.ev import EV, EVStatus
from app.domain.models.parking import ParkingSlot, ParkingState
from app.domain.models.simulation import ThermalState, ThermalStatus
from app.domain.models.system import SystemState
from app.optimizer.optimizer import ChargingOptimizer


def test_mandatory_critical_infrastructure_safety_constraint():
    """Verify optimizer enforces effective grid capacity constraint under excess EV demand."""
    now = datetime(2026, 9, 18, 14, 0, 0, tzinfo=timezone.utc)

    # 1. Setup exact infrastructure conditions
    # Effective capacity = 22.0 kW, building demand = 12.0 kW, solar = 3.0 kW
    grid = GridState(max_capacity_kw=25.0, building_demand_kw=12.0, effective_capacity_kw=22.0)
    solar = SolarState(solar_voltage_v=1.0, availability_percent=30.0, estimated_generation_kw=3.0)
    thermal = ThermalState(
        base_capacity_kw=25.0,
        effective_capacity_kw=22.0,
        derating_factor=0.88,
        thermal_status=ThermalStatus.ELEVATED,
        ambient_temperature_c=38.0,
    )
    energy = EnergyState(grid=grid, solar=solar, available_ev_charging_capacity_kw=13.0)
    battery = VirtualBattery(
        capacity_kwh=50.0,
        soc_percent=20.0,  # At minimum SoC -> cannot discharge
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
        minimum_soc_percent=20.0,
    )

    # 2. Setup high EV demand: 3 EVs requesting 7.4 kW each (22.2 kW total demand > 13.0 kW available)
    evs = [
        EV(
            id="EV-001",
            slot_id="SLOT-01",
            battery_capacity_kwh=60.0,
            soc_percent=20.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=now - timedelta(minutes=30),
            departure_time=now + timedelta(hours=2),
            status=EVStatus.WAITING,
        ),
        EV(
            id="EV-002",
            slot_id="SLOT-02",
            battery_capacity_kwh=75.0,
            soc_percent=30.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=now - timedelta(minutes=20),
            departure_time=now + timedelta(hours=3),
            status=EVStatus.WAITING,
        ),
        EV(
            id="EV-003",
            slot_id="SLOT-03",
            battery_capacity_kwh=60.0,
            soc_percent=40.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=now - timedelta(minutes=10),
            departure_time=now + timedelta(hours=4),
            status=EVStatus.WAITING,
        ),
    ]

    parking = ParkingState(
        total_slots=3,
        slots=[ParkingSlot(id=f"SLOT-0{i+1}", occupied=True, ev_id=f"EV-00{i+1}") for i in range(3)],
    )

    environment = HardwareTelemetry(
        device_id="ESP32-001",
        timestamp=now,
        temperature_c=38.0,
        humidity_percent=40.0,
        rain_detected=False,
        rain_intensity=0.0,
        solar_voltage_v=1.0,
    )

    system_state = SystemState(
        timestamp=now,
        environment=environment,
        energy=energy,
        thermal=thermal,
        battery=battery,
        evs=evs,
        parking=parking,
    )

    # 3. Execute Optimizer
    optimizer = ChargingOptimizer()
    decision = optimizer.optimize(system_state, simulation_interval_seconds=60.0)

    # 4. Mandatory Verifications
    # Total EV power <= Available EV power (13.0 kW)
    assert decision.total_allocated_power_kw <= 13.0 + 0.001
    assert decision.available_ev_power_kw == 13.0

    # Net infrastructure load <= Effective grid capacity (22.0 kW)
    # Net load = Building Demand (12 kW) + Total EV Allocation (<= 13 kW) - Solar (3 kW) - Battery (0 kW) <= 22 kW
    net_load = 12.0 + decision.total_allocated_power_kw - 3.0 - 0.0
    assert net_load <= 22.0 + 0.001
    assert decision.infrastructure_load_kw <= 22.0 + 0.001

    # Individual charger limit respected
    for alloc in decision.allocations:
        assert alloc.allocated_power_kw <= 7.4
        assert alloc.allocated_power_kw >= 0.0
