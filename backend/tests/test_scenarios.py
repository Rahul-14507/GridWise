"""Tests for Scenario repository and predefined scenarios."""

import pytest
from app.simulation.scenarios import ScenarioManager, Scenario


def test_scenario_manager_get_all_scenarios():
    """Verify all 8 expected scenarios are present in repository."""
    scenarios = ScenarioManager.get_all_scenarios()
    expected = [
        "NORMAL_DAY",
        "SOLAR_SURPLUS",
        "CLOUD_EVENT",
        "RAIN_EVENT",
        "EVENING_PEAK",
        "HIGH_EV_DEMAND",
        "HOT_DAY",
        "COMBINED_STRESS",
    ]
    for name in expected:
        assert name in scenarios
        scenario = scenarios[name]
        assert isinstance(scenario, Scenario)
        assert scenario.name == name
        assert len(scenario.description) > 0
        assert isinstance(scenario.evs, list)
        assert scenario.battery.capacity_kwh > 0
        assert scenario.parking.total_slots >= len(scenario.evs)


def test_scenario_manager_get_single_scenario():
    """Verify fetching an individual scenario by name."""
    scenario = ScenarioManager.get_scenario("hot_day")
    assert scenario.name == "HOT_DAY"
    assert scenario.temperature_c == 43.5


def test_scenario_manager_unknown_scenario_raises():
    """Verify unknown scenario name raises descriptive ValueError."""
    with pytest.raises(ValueError) as exc_info:
        ScenarioManager.get_scenario("UNKNOWN_SCENARIO")
    assert "Unknown scenario" in str(exc_info.value)
