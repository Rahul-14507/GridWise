import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useSystemState } from '../src/hooks/useSystemState';
import { api } from '../src/services/api';

describe('useSystemState Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes and polls system state successfully', async () => {
    const mockSummary = {
      timestamp: '2026-09-18T10:00:00Z',
      system_status: 'operational',
      data_source: 'simulation',
      energy: {
        grid_capacity_kw: 100,
        effective_capacity_kw: 100,
        building_demand_kw: 20,
        solar_generation_kw: 10,
        available_ev_power_kw: 90,
      },
      battery: { soc_percent: 80, current_energy_kwh: 40, capacity_kwh: 50, action: 'idle' },
      evs: { total: 1, charging: 1, waiting: 0, paused: 0, completed: 0, disconnected: 0 },
      parking: { total_slots: 4, occupied_slots: 1, available_slots: 3 },
      hardware: { status: 'online', devices_online: 1, devices_stale: 0 },
      warnings: [],
    };

    const mockEnergy = {
      timestamp: '2026-09-18T10:00:00Z',
      base_grid_capacity_kw: 100,
      effective_grid_capacity_kw: 100,
      building_demand_kw: 20,
      solar_voltage_v: 4.0,
      solar_availability_percent: 80,
      estimated_solar_generation_kw: 10,
      battery_discharge_kw: 0,
      battery_charge_kw: 0,
      available_ev_charging_power_kw: 90,
      total_ev_allocated_power_kw: 11,
      infrastructure_load_kw: 31,
    };

    vi.spyOn(api, 'getSystemSummary').mockResolvedValue(mockSummary as any);
    vi.spyOn(api, 'getSystemStatus').mockResolvedValue({
      status: 'operational',
      data_source: 'simulation',
      simulation_running: true,
      hardware_devices_online: 1,
      last_state_update: '2026-09-18T10:00:00Z',
      warnings: [],
    });
    vi.spyOn(api, 'getEnergyState').mockResolvedValue(mockEnergy as any);
    vi.spyOn(api, 'getEVs').mockResolvedValue([]);
    vi.spyOn(api, 'getOptimization').mockResolvedValue(null);
    vi.spyOn(api, 'getHardwareStatus').mockResolvedValue({
      mode: 'simulation',
      online: true,
      total_devices: 1,
      online_devices: 1,
      stale_devices: 0,
      last_received: '2026-09-18T10:00:00Z',
      devices: [],
    });

    const { result, unmount } = renderHook(() => useSystemState(10000));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.summary?.system_status).toBe('operational');
    expect(result.current.energy?.effective_grid_capacity_kw).toBe(100);
    expect(result.current.history.length).toBe(1);
    expect(result.current.isStale).toBe(false);

    unmount();
  });

  it('handles optimization triggers correctly', async () => {
    const mockOptDecision = {
      timestamp: '2026-09-18T10:00:00Z',
      available_power_kw: 90,
      allocated_power_kw: 11,
      unallocated_power_kw: 79,
      bess_action: { mode: 'idle', target_power_kw: 0, projected_soc_percent: 80, reason: 'Ok' },
      allocations: [],
      warnings: [],
    };

    vi.spyOn(api, 'getSystemSummary').mockResolvedValue({} as any);
    vi.spyOn(api, 'getSystemStatus').mockResolvedValue({} as any);
    vi.spyOn(api, 'getEnergyState').mockResolvedValue({} as any);
    vi.spyOn(api, 'getEVs').mockResolvedValue([]);
    vi.spyOn(api, 'getOptimization').mockResolvedValue(null);
    vi.spyOn(api, 'getHardwareStatus').mockResolvedValue({} as any);

    const runOptSpy = vi.spyOn(api, 'runOptimization').mockResolvedValue(mockOptDecision as any);
    const applyOptSpy = vi.spyOn(api, 'applyOptimization').mockResolvedValue({
      applied: true,
      timestamp: '2026-09-18T10:00:00Z',
      evs_updated: 1,
      battery_mode: 'idle',
      message: 'Success',
    });

    const { result, unmount } = renderHook(() => useSystemState(10000));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.runOptimization();
    });

    expect(runOptSpy).toHaveBeenCalledTimes(1);
    expect(result.current.optimization?.allocated_power_kw).toBe(11);

    await act(async () => {
      await result.current.applyOptimization();
    });

    expect(applyOptSpy).toHaveBeenCalledTimes(1);

    unmount();
  });
});
