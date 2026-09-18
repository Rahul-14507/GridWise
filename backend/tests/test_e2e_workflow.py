"""End-to-end integration test covering the complete Phase 5 workflow:

Start simulation -> Get SystemState -> Run optimizer -> Get decision ->
Apply decision -> Tick simulation -> Verify updated SoC & constraint satisfaction.
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.application.state_service import get_app_state_service
from app.simulation.engine import get_simulation_engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    engine = get_simulation_engine()
    engine.load_scenario("NORMAL_DAY")
    service = get_app_state_service()
    service.reset_decision()
    yield
    service.reset_decision()


def test_complete_simulation_optimization_loop():
    # 1. Start simulation
    start_res = client.post("/api/v1/simulation/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "running"

    # 2. Get initial system state
    state_0_res = client.get("/api/v1/system/state")
    assert state_0_res.status_code == 200
    state_0 = state_0_res.json()
    ev1_initial_soc = state_0["evs"][0]["soc_percent"]
    assert state_0["evs"][0]["allocated_power_kw"] == 0.0

    # 3. Run optimizer on current system state
    opt_res = client.post("/api/v1/optimization/run")
    assert opt_res.status_code == 200
    decision = opt_res.json()
    assert decision["total_allocated_power_kw"] > 0.0

    # 4. Get current decision via GET /optimization/current
    cur_dec_res = client.get("/api/v1/optimization/current")
    assert cur_dec_res.status_code == 200
    assert cur_dec_res.json()["timestamp"] == decision["timestamp"]

    # 5. Apply optimization decision to simulation
    apply_res = client.post("/api/v1/optimization/apply")
    assert apply_res.status_code == 200
    assert apply_res.json()["status"] == "applied"

    # Verify allocations are now reflected on the EV fleet
    evs_res = client.get("/api/v1/evs")
    assert evs_res.status_code == 200
    assert evs_res.json()[0]["allocated_power_kw"] > 0.0

    # 6. Advance simulation by ticking (60 seconds)
    tick_res = client.post("/api/v1/simulation/tick?interval_seconds=60")
    assert tick_res.status_code == 200

    # 7. Get updated system state
    state_1_res = client.get("/api/v1/system/state")
    assert state_1_res.status_code == 200
    state_1 = state_1_res.json()

    # 8. Verify EV charged and SoC increased
    ev1_new_soc = state_1["evs"][0]["soc_percent"]
    assert ev1_new_soc > ev1_initial_soc

    # 9. Verify hard safety constraints remain satisfied
    effective_capacity = state_1["thermal"]["effective_capacity_kw"]
    building_demand = state_1["energy"]["grid"]["building_demand_kw"]
    solar_gen = state_1["energy"]["solar"]["estimated_generation_kw"]
    total_ev_alloc = sum(ev["allocated_power_kw"] for ev in state_1["evs"])

    battery_discharge = decision.get("battery_power_kw", 0.0) if decision.get("battery_action") == "discharge" else 0.0
    net_grid_load = building_demand + total_ev_alloc - solar_gen - battery_discharge
    assert net_grid_load <= effective_capacity + 0.01  # Tolerance

    # 10. Run second optimization cycle on updated state
    opt_res_2 = client.post("/api/v1/optimization/run")
    assert opt_res_2.status_code == 200
    decision_2 = opt_res_2.json()
    assert decision_2["total_allocated_power_kw"] >= 0.0
