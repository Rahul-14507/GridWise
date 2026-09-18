"""Command-line runner for interactive simulation demonstration.

Usage:
    python -m app.simulation --scenario NORMAL_DAY --ticks 5 --interval 60 --optimize
"""

import argparse
import sys
from typing import Optional
from app.domain.models.simulation import SimulationControlInput
from app.optimizer.optimizer import ChargingOptimizer
from app.optimizer.models import OptimizationDecision
from app.simulation.engine import SimulationEngine
from app.simulation.scenarios import ScenarioManager


def format_system_state_table(
    engine: SimulationEngine,
    tick_index: int,
    decision: Optional[OptimizationDecision] = None,
) -> str:
    """Format SystemState and optional OptimizationDecision into a clean terminal table."""
    state = engine.get_state()
    time_str = state.timestamp.strftime("%H:%M:%S UTC")

    lines = [
        "=" * 78,
        f"  SMART EV CHARGING SIMULATION - TICK {tick_index:03d} [{time_str}]",
        f"  Scenario: {engine.current_scenario_name}" + (" (OPTIMIZED)" if decision else " (MANUAL ALLOC)"),
        "=" * 78,
        "",
        "  [ ENVIRONMENT (ESP32 Telemetry) ]",
        f"    Temperature:       {state.environment.temperature_c:.1f} °C",
        f"    Humidity:          {state.environment.humidity_percent:.1f} %",
        f"    Rain Detected:     {'YES (' + str(state.environment.rain_intensity) + ' mm/h)' if state.environment.rain_detected else 'NO'}",
        f"    Solar Voltage:     {state.environment.solar_voltage_v:.3f} V  (Raw Sensor Proxy)",
        f"    Solar Availability:{state.energy.solar.availability_percent:.1f} %",
        "",
        "  [ FACILITY POWER & GRID BALANCE ]",
        f"    Base Grid Limit:   {state.energy.grid.max_capacity_kw:.2f} kW",
        f"    Effective Grid:    {state.energy.grid.effective_capacity_kw:.2f} kW (Status: {state.thermal.thermal_status.value.upper()}, Factor: {state.thermal.derating_factor:.2f})",
        f"    Building Demand:   {state.energy.grid.building_demand_kw:.2f} kW",
        f"    Solar Generation:  {state.energy.solar.estimated_generation_kw:.2f} kW (Estimated)",
        f"    Virtual BESS SoC:  {state.battery.soc_percent:.1f} % (Min: {state.battery.minimum_soc_percent:.0f}%, Cap: {state.battery.capacity_kwh:.0f} kWh)",
        f"    -> AVAILABLE EV:   {state.available_ev_charging_capacity_kw:.2f} kW",
        "",
        "  [ EV FLEET ALLOCATION & PRIORITY BREAKDOWN ]",
        f"    Parking Bays:      {state.occupied_parking_slots} occupied / {state.available_parking_slots} available (Total: {state.parking.total_slots})",
        f"    Active Charging:   {state.active_charging_ev_count} EVs ({state.total_ev_allocated_power_kw:.2f} kW total)",
        "",
        f"    {'ID':<8} {'SOC':<7} {'TARGET':<8} {'STATUS':<11} {'PRIORITY':<10} {'DEADLINE':<10} {'ALLOC (kW)':<11} {'REASON'}",
        f"    {'-'*74}",
    ]

    reason_map = {a.ev_id: a for a in decision.allocations} if decision else {}

    for ev in state.evs:
        dec = reason_map.get(ev.id)
        prio_str = f"{dec.priority_score:.2f}" if dec else "N/A"
        dead_str = dec.deadline_status.value.upper() if dec else "N/A"
        reason_str = dec.reason if dec else "Manual/Default allocation"

        lines.append(
            f"    {ev.id:<8} {ev.soc_percent:>5.1f}% {ev.target_soc_percent:>5.1f}%  "
            f"{ev.status.value:<11} {prio_str:<10} {dead_str:<10} {ev.allocated_power_kw:>8.2f}    {reason_str}"
        )

    if decision and decision.warnings:
        lines.append("")
        lines.append("  [ WARNINGS & ALERTS ]")
        for w in decision.warnings:
            lines.append(f"    ! {w}")

    lines.append("=" * 78)
    return "\n".join(lines)


def run_cli() -> None:
    """CLI execution entrypoint."""
    parser = argparse.ArgumentParser(description="GridWise Smart EV Charging Simulation Engine")
    parser.add_argument(
        "--scenario",
        type=str,
        default="NORMAL_DAY",
        help="Predefined scenario name (e.g. NORMAL_DAY, SOLAR_SURPLUS, HOT_DAY, COMBINED_STRESS)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of simulation ticks to execute (default: 5)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Simulation interval in seconds per tick (default: 60.0)",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Run ChargingOptimizer dynamically to allocate power on each tick",
    )

    args = parser.parse_args()

    try:
        engine = SimulationEngine(scenario_name=args.scenario)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    optimizer = ChargingOptimizer() if args.optimize else None

    print(format_system_state_table(engine, 0))

    # Static default allocations if --optimize is not set
    manual_allocations = {
        "EV-001": 7.4,
        "EV-002": 5.5,
        "EV-003": 0.0,
        "EV-004": 3.7,
    }

    for tick in range(1, args.ticks + 1):
        if optimizer:
            current_state = engine.get_state()
            decision = optimizer.optimize(current_state, simulation_interval_seconds=args.interval)
            control_input = decision.to_control_input()
            engine.tick(control_input=control_input, interval_seconds=args.interval)
            print(format_system_state_table(engine, tick, decision=decision))
        else:
            control_input = SimulationControlInput(ev_allocations=manual_allocations)
            engine.tick(control_input=control_input, interval_seconds=args.interval)
            print(format_system_state_table(engine, tick))


if __name__ == "__main__":
    run_cli()
