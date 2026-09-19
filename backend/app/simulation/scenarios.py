"""Simulation Scenarios repository and definitions.

Defines deterministic test scenarios reproducing distinct operational conditions:
- NORMAL_DAY
- SOLAR_SURPLUS
- CLOUD_EVENT
- RAIN_EVENT
- EVENING_PEAK
- HIGH_EV_DEMAND
- HOT_DAY
- COMBINED_STRESS
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.battery import VirtualBattery
from app.domain.models.ev import EV, EVStatus
from app.domain.models.parking import ParkingSlot, ParkingState


class Scenario(BaseModel):
    """Configuration and initial state for a simulation scenario."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Unique uppercase scenario identifier.")
    description: str = Field(..., description="Human-readable description of scenario conditions.")
    initial_time: datetime = Field(..., description="Starting simulation timestamp.")
    battery: VirtualBattery = Field(..., description="Initial Virtual Battery state.")
    evs: List[EV] = Field(default_factory=list, description="Initial fleet of EVs.")
    parking: ParkingState = Field(..., description="Initial parking state.")

    # Environmental / Grid Overrides (Optional)
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    rain_detected: Optional[bool] = None
    rain_intensity: Optional[float] = None
    solar_voltage_v: Optional[float] = None
    building_demand_kw: Optional[float] = None


def _create_default_parking(slots_count: int = 4) -> ParkingState:
    slots = [ParkingSlot(id=f"SLOT-{i+1:02d}", occupied=False) for i in range(slots_count)]
    return ParkingState(total_slots=slots_count, slots=slots)


def _create_standard_battery(soc_percent: float = 60.0) -> VirtualBattery:
    return VirtualBattery(
        capacity_kwh=50.0,
        soc_percent=soc_percent,
        max_charge_power_kw=10.0,
        max_discharge_power_kw=10.0,
        efficiency_percent=95.0,
        minimum_soc_percent=20.0,
    )


def _create_standard_fleet(base_time: datetime) -> List[EV]:
    return []


def _create_mock_fleet(base_time: datetime) -> List[EV]:
    return [
        EV(
            id="EV-001",
            slot_id="SLOT-01",
            battery_capacity_kwh=60.0,
            soc_percent=22.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=base_time - timedelta(minutes=30),
            departure_time=base_time + timedelta(hours=2),
            allocated_power_kw=0.0,
            status=EVStatus.WAITING,
        ),
        EV(
            id="EV-002",
            slot_id="SLOT-02",
            battery_capacity_kwh=75.0,
            soc_percent=61.0,
            target_soc_percent=90.0,
            max_charging_power_kw=11.0,
            arrival_time=base_time - timedelta(minutes=15),
            departure_time=base_time + timedelta(hours=4),
            allocated_power_kw=0.0,
            status=EVStatus.WAITING,
        ),
        EV(
            id="EV-003",
            slot_id="SLOT-03",
            battery_capacity_kwh=50.0,
            soc_percent=34.0,
            target_soc_percent=90.0,
            max_charging_power_kw=7.4,
            arrival_time=base_time - timedelta(minutes=5),
            departure_time=base_time + timedelta(hours=1, minutes=30),
            allocated_power_kw=0.0,
            status=EVStatus.WAITING,
        ),
        EV(
            id="EV-004",
            slot_id="SLOT-04",
            battery_capacity_kwh=100.0,
            soc_percent=82.0,
            target_soc_percent=90.0,
            max_charging_power_kw=22.0,
            arrival_time=base_time - timedelta(hours=1),
            departure_time=base_time + timedelta(hours=6),
            allocated_power_kw=0.0,
            status=EVStatus.WAITING,
        ),
    ]


class ScenarioManager:
    """Registry and factory for simulation scenarios."""

    @staticmethod
    def get_all_scenarios(base_time: Optional[datetime] = None) -> Dict[str, Scenario]:
        """Generate all predefined simulation scenarios."""
        t0 = base_time or datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)

        # 1. NORMAL_DAY
        normal_day = Scenario(
            name="NORMAL_DAY",
            description="Standard daytime operations with normal solar irradiance and moderate building demand.",
            initial_time=t0,
            battery=_create_standard_battery(soc_percent=60.0),
            evs=_create_standard_fleet(t0),
            parking=_create_default_parking(4),
            temperature_c=28.0,
            humidity_percent=55.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=2.20,
            building_demand_kw=8.0,
        )

        # 2. SOLAR_SURPLUS
        solar_surplus = Scenario(
            name="SOLAR_SURPLUS",
            description="Peak solar irradiance conditions with high solar generation and low building demand.",
            initial_time=t0,
            battery=_create_standard_battery(soc_percent=40.0),
            evs=_create_standard_fleet(t0),
            parking=_create_default_parking(4),
            temperature_c=31.0,
            humidity_percent=45.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=2.85,
            building_demand_kw=5.0,
        )

        # 3. CLOUD_EVENT
        cloud_event = Scenario(
            name="CLOUD_EVENT",
            description="Sudden cloud cover reduces solar panel voltage significantly during peak hours.",
            initial_time=t0,
            battery=_create_standard_battery(soc_percent=65.0),
            evs=_create_standard_fleet(t0),
            parking=_create_default_parking(4),
            temperature_c=26.0,
            humidity_percent=65.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=0.60,
            building_demand_kw=8.5,
        )

        # 4. RAIN_EVENT
        rain_event = Scenario(
            name="RAIN_EVENT",
            description="Precipitation onset with overcast skies, higher humidity, and active rain detection.",
            initial_time=t0,
            battery=_create_standard_battery(soc_percent=50.0),
            evs=_create_standard_fleet(t0),
            parking=_create_default_parking(4),
            temperature_c=23.5,
            humidity_percent=88.0,
            rain_detected=True,
            rain_intensity=12.5,
            solar_voltage_v=0.45,
            building_demand_kw=9.0,
        )

        # 5. EVENING_PEAK
        t_evening = t0.replace(hour=18, minute=30)
        evening_peak = Scenario(
            name="EVENING_PEAK",
            description="Evening facility peak power consumption coinciding with negligible solar availability.",
            initial_time=t_evening,
            battery=_create_standard_battery(soc_percent=80.0),
            evs=_create_standard_fleet(t_evening),
            parking=_create_default_parking(4),
            temperature_c=27.0,
            humidity_percent=60.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=0.10,
            building_demand_kw=15.5,
        )

        # 6. HIGH_EV_DEMAND
        high_fleet = [
            EV(
                id="EV-001",
                slot_id="SLOT-01",
                battery_capacity_kwh=80.0,
                soc_percent=15.0,
                target_soc_percent=90.0,
                max_charging_power_kw=11.0,
                arrival_time=t0 - timedelta(minutes=10),
                departure_time=t0 + timedelta(hours=2),
                allocated_power_kw=0.0,
                status=EVStatus.WAITING,
            ),
            EV(
                id="EV-002",
                slot_id="SLOT-02",
                battery_capacity_kwh=64.0,
                soc_percent=20.0,
                target_soc_percent=85.0,
                max_charging_power_kw=7.4,
                arrival_time=t0 - timedelta(minutes=20),
                departure_time=t0 + timedelta(hours=3),
                allocated_power_kw=0.0,
                status=EVStatus.WAITING,
            ),
        ]
        high_ev_demand = Scenario(
            name="HIGH_EV_DEMAND",
            description="Multiple Electric Vehicles connected concurrently with large energy deficits.",
            initial_time=t0,
            battery=_create_standard_battery(soc_percent=75.0),
            evs=high_fleet,
            parking=_create_default_parking(6),
            temperature_c=29.0,
            humidity_percent=52.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=2.10,
            building_demand_kw=9.0,
        )

        # 7. HOT_DAY
        hot_day = Scenario(
            name="HOT_DAY",
            description="Extreme ambient temperature exceeding 42°C triggering thermal capacity derating.",
            initial_time=t0,
            battery=_create_standard_battery(soc_percent=55.0),
            evs=_create_standard_fleet(t0),
            parking=_create_default_parking(4),
            temperature_c=43.5,
            humidity_percent=30.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=2.70,
            building_demand_kw=11.0,
        )

        # 8. COMBINED_STRESS
        combined_stress = Scenario(
            name="COMBINED_STRESS",
            description="High ambient temperature, high facility demand, depressed solar output, and full EV cluster.",
            initial_time=t0,
            battery=_create_standard_battery(soc_percent=30.0),
            evs=high_fleet,
            parking=_create_default_parking(6),
            temperature_c=45.0,
            humidity_percent=35.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=0.50,
            building_demand_kw=14.0,
        )

        # 9. MOCK_FLEET (for unit testing multi-EV optimization)
        mock_fleet = Scenario(
            name="MOCK_FLEET",
            description="Pre-populated 4-EV test fleet for unit tests and multi-EV test verification.",
            initial_time=t0,
            battery=_create_standard_battery(soc_percent=60.0),
            evs=_create_mock_fleet(t0),
            parking=_create_default_parking(4),
            temperature_c=28.0,
            humidity_percent=55.0,
            rain_detected=False,
            rain_intensity=0.0,
            solar_voltage_v=2.20,
            building_demand_kw=8.0,
        )

        return {
            "NORMAL_DAY": normal_day,
            "SOLAR_SURPLUS": solar_surplus,
            "CLOUD_EVENT": cloud_event,
            "RAIN_EVENT": rain_event,
            "EVENING_PEAK": evening_peak,
            "HIGH_EV_DEMAND": high_ev_demand,
            "HOT_DAY": hot_day,
            "COMBINED_STRESS": combined_stress,
            "MOCK_FLEET": mock_fleet,
        }

    @classmethod
    def get_scenario(cls, scenario_name: str, base_time: Optional[datetime] = None) -> Scenario:
        """Fetch a specific scenario by uppercase name."""
        scenarios = cls.get_all_scenarios(base_time)
        upper_name = scenario_name.strip().upper()
        if upper_name not in scenarios:
            available = ", ".join(scenarios.keys())
            raise ValueError(f"Unknown scenario '{scenario_name}'. Available scenarios: {available}")
        return scenarios[upper_name]
