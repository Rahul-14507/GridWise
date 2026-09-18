import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AdminDashboard } from '../src/pages/AdminDashboard';
import { api } from '../src/services/api';

describe('AdminDashboard Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the complete admin dashboard when backend data is available', async () => {
    const mockSummary = {
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

    const mockEnergy = {
      timestamp: '2026-09-18T12:00:00Z',
      base_grid_capacity_kw: 100,
      effective_grid_capacity_kw: 100,
      building_demand_kw: 25,
      solar_voltage_v: 4.2,
      solar_availability_percent: 85,
      estimated_solar_generation_kw: 12.5,
      battery_discharge_kw: 0,
      battery_charge_kw: 0,
      available_ev_charging_power_kw: 87.5,
      total_ev_allocated_power_kw: 11,
      infrastructure_load_kw: 36,
    };

    const mockEVs = [
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
    ];

    vi.spyOn(api, 'getSystemSummary').mockResolvedValue(mockSummary as any);
    vi.spyOn(api, 'getSystemStatus').mockResolvedValue({
      status: 'operational',
      data_source: 'simulation',
      simulation_running: true,
      hardware_devices_online: 1,
      last_state_update: '2026-09-18T12:00:00Z',
      warnings: [],
    });
    vi.spyOn(api, 'getEnergyState').mockResolvedValue(mockEnergy as any);
    vi.spyOn(api, 'getEVs').mockResolvedValue(mockEVs as any);
    vi.spyOn(api, 'getOptimization').mockResolvedValue(null);
    vi.spyOn(api, 'getHardwareStatus').mockResolvedValue({
      mode: 'simulation',
      online: true,
      total_devices: 1,
      online_devices: 1,
      stale_devices: 0,
      last_received: '2026-09-18T12:00:00Z',
      devices: [],
    });

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('SMART EV CHARGING')).toBeInTheDocument();
    });

    expect(screen.getByText('GRID / INFRASTRUCTURE')).toBeInTheDocument();
    expect(screen.getByText('ENERGY MIX')).toBeInTheDocument();
    expect(screen.getByText('ACTIVE VEHICLES')).toBeInTheDocument();
    expect(screen.getByText('SYSTEM / TRANSFORMER')).toBeInTheDocument();
  });

  it('renders error state when backend is unreachable', async () => {
    vi.spyOn(api, 'getSystemSummary').mockRejectedValue(new Error('Connection refused'));
    vi.spyOn(api, 'getSystemStatus').mockRejectedValue(new Error('Connection refused'));
    vi.spyOn(api, 'getEnergyState').mockRejectedValue(new Error('Connection refused'));
    vi.spyOn(api, 'getEVs').mockRejectedValue(new Error('Connection refused'));
    vi.spyOn(api, 'getOptimization').mockRejectedValue(new Error('Connection refused'));
    vi.spyOn(api, 'getHardwareStatus').mockRejectedValue(new Error('Connection refused'));

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('SCADA CONNECTION ERROR')).toBeInTheDocument();
    });
    expect(screen.getByText('Retry Connection')).toBeInTheDocument();
  });
});
