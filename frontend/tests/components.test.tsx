import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '../src/components/layout/Header';
import { InfrastructureOverview } from '../src/components/infrastructure/InfrastructureOverview';
import { TransformerSafety } from '../src/components/infrastructure/TransformerSafety';
import { SolarSubsystem } from '../src/components/energy/SolarSubsystem';
import { EnergyFlow } from '../src/components/energy/EnergyFlow';
import { BatteryStatus } from '../src/components/battery/BatteryStatus';
import { EVFleetTable } from '../src/components/ev/EVFleetTable';
import { ParkingOverview } from '../src/components/parking/ParkingOverview';
import { OptimizationStatus } from '../src/components/optimization/OptimizationStatus';
import { WarningsPanel } from '../src/components/warnings/WarningsPanel';
import { RealtimeCharts } from '../src/components/charts/RealtimeCharts';
import { EnergyDetailResponse, EVDetailResponse, OptimizationDecision, SystemSummaryResponse } from '../src/types/api';

describe('Frontend Component Suite', () => {
  const mockSummary: SystemSummaryResponse = {
    timestamp: '2026-09-18T12:00:00Z',
    system_status: 'operational',
    data_source: 'simulation',
    energy: {
      grid_capacity_kw: 100,
      effective_capacity_kw: 100,
      building_demand_kw: 25,
      solar_generation_kw: 12.5,
      available_ev_power_kw: 87.5,
    },
    battery: {
      soc_percent: 75,
      current_energy_kwh: 37.5,
      capacity_kwh: 50,
      action: 'idle',
    },
    evs: { total: 2, charging: 1, waiting: 1, paused: 0, completed: 0, disconnected: 0 },
    parking: { total_slots: 4, occupied_slots: 2, available_slots: 2 },
    hardware: { status: 'online', devices_online: 1, devices_stale: 0 },
    warnings: [],
  };

  const mockEnergy: EnergyDetailResponse = {
    timestamp: '2026-09-18T12:00:00Z',
    base_grid_capacity_kw: 100,
    effective_grid_capacity_kw: 90,
    building_demand_kw: 25,
    solar_voltage_v: 4.1,
    solar_availability_percent: 85,
    estimated_solar_generation_kw: 12.5,
    battery_discharge_kw: 0,
    battery_charge_kw: 0,
    available_ev_charging_power_kw: 77.5,
    total_ev_allocated_power_kw: 22,
    infrastructure_load_kw: 47,
  };

  const mockEVs: EVDetailResponse[] = [
    {
      id: 'EV-001',
      slot_id: 'BAY-1',
      status: 'charging',
      battery_capacity_kwh: 75,
      soc_percent: 45,
      target_soc_percent: 80,
      max_charging_power_kw: 22,
      allocated_power_kw: 11,
      arrival_time: '2026-09-18T10:00:00Z',
      departure_time: '2026-09-18T14:00:00Z',
      energy_required_kwh: 26.25,
      remaining_time_minutes: 120,
      required_average_power_kw: 13.1,
      priority_score: 2.15,
      deadline_status: 'feasible',
      reason: 'Standard charging',
    },
    {
      id: 'EV-002',
      slot_id: 'BAY-2',
      status: 'waiting',
      battery_capacity_kwh: 50,
      soc_percent: 30,
      target_soc_percent: 90,
      max_charging_power_kw: 11,
      allocated_power_kw: 0,
      arrival_time: '2026-09-18T11:00:00Z',
      departure_time: '2026-09-18T12:00:00Z',
      energy_required_kwh: 30,
      remaining_time_minutes: 60,
      required_average_power_kw: 30,
      priority_score: 5.4,
      deadline_status: 'at_risk',
      reason: 'Urgent deadline',
    },
  ];

  it('renders Header with status, mode badge, and action buttons', () => {
    const handleRefresh = vi.fn();
    const handleRunOpt = vi.fn();
    const handleApplyOpt = vi.fn();
    const handleTick = vi.fn();

    render(
      <Header
        summary={mockSummary}
        status={null}
        lastUpdated={new Date()}
        isStale={false}
        isLoading={false}
        isOptimizing={false}
        isApplying={false}
        isTicking={false}
        onRefresh={handleRefresh}
        onRunOptimization={handleRunOpt}
        onApplyOptimization={handleApplyOpt}
        onTriggerTick={handleTick}
      />
    );

    expect(screen.getByText('GRIDWISE')).toBeInTheDocument();
    expect(screen.getByText('SIMULATION')).toBeInTheDocument();
    expect(screen.getByText(/OPERATIONAL/)).toBeInTheDocument();
    expect(screen.getByText('Step +60s')).toBeInTheDocument();
  });

  it('renders InfrastructureOverview with power metrics and utilization bar', () => {
    render(<InfrastructureOverview energy={mockEnergy} summary={mockSummary.energy} />);

    expect(screen.getByText('Infrastructure & Power Headroom')).toBeInTheDocument();
    expect(screen.getByText(/47.0/)).toBeInTheDocument();
    expect(screen.getByText(/90.0/)).toBeInTheDocument();
    expect(screen.getByText(/77.5/)).toBeInTheDocument();
  });

  it('renders EVFleetTable with active EV rows, SoC progress, and deadline badges', () => {
    render(<EVFleetTable evs={mockEVs} />);

    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(/Connected EV Fleet & Priority Charging Allocations/);
    expect(screen.getByText('EV-001')).toBeInTheDocument();
    expect(screen.getByText('EV-002')).toBeInTheDocument();
    expect(screen.getByText('11.0')).toBeInTheDocument();
    expect(screen.getByText(/FEASIBLE/)).toBeInTheDocument();
    expect(screen.getByText(/AT RISK/)).toBeInTheDocument();
  });

  it('renders SolarSubsystem with solar metrics and precipitation indicator', () => {
    render(<SolarSubsystem energy={mockEnergy} rainDetected={false} rainIntensity={0.0} />);

    expect(screen.getByText('Solar PV & Renewable Generation')).toBeInTheDocument();
    expect(screen.getByText('12.5 kW')).toBeInTheDocument();
    expect(screen.getByText('4.10 V')).toBeInTheDocument();
    expect(screen.getByText('Clear / Overcast')).toBeInTheDocument();
  });

  it('renders TransformerSafety with thermal status and derating details', () => {
    render(
      <TransformerSafety
        energy={mockEnergy}
        ambientTempC={38.5}
        thermalStatus="DERATED"
      />
    );

    expect(screen.getByText('Thermal & Interconnection Safety')).toBeInTheDocument();
    expect(screen.getByText('38.5 °C')).toBeInTheDocument();
    expect(screen.getByText('-10.0 kW')).toBeInTheDocument();
  });

  it('renders EnergyFlow power balance breakdown', () => {
    render(<EnergyFlow energy={mockEnergy} evs={mockEVs} />);

    expect(screen.getByText('Real-Time Facility Energy Flow Balance')).toBeInTheDocument();
    expect(screen.getByText(/Solar PV:/)).toBeInTheDocument();
    expect(screen.getByText(/Utility Grid:/)).toBeInTheDocument();
    expect(screen.getByText(/Facility Baseload:/)).toBeInTheDocument();
  });

  it('renders BatteryStatus with BESS SoC and state', () => {
    render(<BatteryStatus battery={mockSummary.battery} energy={mockEnergy} />);

    expect(screen.getByText('Stationary Virtual Battery (BESS)')).toBeInTheDocument();
    expect(screen.getByText('75.0%')).toBeInTheDocument();
    expect(screen.getByText('37.5 / 50 kWh')).toBeInTheDocument();
  });

  it('renders ParkingOverview with occupancy metrics', () => {
    render(<ParkingOverview parking={mockSummary.parking} />);

    expect(screen.getByText('Charging Bay Occupancy')).toBeInTheDocument();
    expect(screen.getByText(/50% Occupancy/)).toBeInTheDocument();
    expect(screen.getByText('Total Bays')).toBeInTheDocument();
  });

  it('renders WarningsPanel correctly for active warnings and empty state', () => {
    const { rerender } = render(<WarningsPanel warnings={[]} />);
    expect(screen.getByText('System Operational: No Active Safety or Constraint Warnings')).toBeInTheDocument();

    const warnings = [
      { code: 'W_SOLAR_LOW', severity: 'warning', message: 'Solar output low due to rain' },
      { code: 'C_TRANSFORMER_HOT', severity: 'critical', message: 'Transformer temperature critical' },
    ];
    rerender(<WarningsPanel warnings={warnings} />);
    expect(screen.getByText(/Active System Alerts/)).toBeInTheDocument();
    expect(screen.getByText('W_SOLAR_LOW')).toBeInTheDocument();
    expect(screen.getByText('C_TRANSFORMER_HOT')).toBeInTheDocument();
  });

  it('renders OptimizationStatus decision details', () => {
    const mockOpt: OptimizationDecision = {
      timestamp: '2026-09-18T12:00:00Z',
      available_power_kw: 85,
      allocated_power_kw: 22,
      unallocated_power_kw: 63,
      bess_action: {
        mode: 'idle',
        target_power_kw: 0,
        projected_soc_percent: 75,
        reason: 'Adequate power',
      },
      allocations: [
        {
          ev_id: 'EV-001',
          allocated_power_kw: 11,
          status: 'charging',
          priority_score: 2.15,
          deadline_status: 'feasible',
          reason: 'Proportional allocation',
        },
      ],
      warnings: [],
    };

    render(<OptimizationStatus optimization={mockOpt} />);
    expect(screen.getByText('Latest Optimization Cycle')).toBeInTheDocument();
    expect(screen.getByText('22.0 / 85.0 kW')).toBeInTheDocument();
  });

  it('renders RealtimeCharts without crashing', () => {
    const history = [
      {
        timestamp: '2026-09-18T12:00:00Z',
        timeLabel: '12:00:00',
        totalDemandKw: 45,
        effectiveCapacityKw: 100,
        solarGenerationKw: 10,
        evFleetPowerKw: 20,
        batterySocPercent: 80,
      },
      {
        timestamp: '2026-09-18T12:01:00Z',
        timeLabel: '12:01:00',
        totalDemandKw: 48,
        effectiveCapacityKw: 100,
        solarGenerationKw: 12,
        evFleetPowerKw: 22,
        batterySocPercent: 80,
      },
    ];

    render(<RealtimeCharts history={history} />);
    expect(screen.getByText('Real-Time Operational Telemetry Charts')).toBeInTheDocument();
  });
});
