import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchSystemSummary,
  fetchSystemStatus,
  fetchEnergy,
  fetchEVs,
  fetchEVById,
  fetchCurrentOptimization,
  runOptimization,
  applyOptimization,
  getBaseUrl,
} from '../src/services/api';

describe('API Service Client', () => {
  const baseUrl = getBaseUrl();

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchSystemSummary fetches /system/summary', async () => {
    const mockData = {
      timestamp: '2026-09-18T10:00:00Z',
      system_status: 'operational',
      data_source: 'simulation',
      energy: {
        grid_capacity_kw: 100,
        effective_capacity_kw: 100,
        building_demand_kw: 25,
        solar_generation_kw: 10,
        available_ev_power_kw: 85,
      },
      battery: {
        soc_percent: 80,
        current_energy_kwh: 40,
        capacity_kwh: 50,
        action: 'idle',
      },
      evs: { total: 2, charging: 1, waiting: 1, paused: 0, completed: 0, disconnected: 0 },
      parking: { total_slots: 4, occupied_slots: 2, available_slots: 2 },
      hardware: { status: 'online', devices_online: 1, devices_stale: 0 },
      warnings: [],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await fetchSystemSummary();
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(`${baseUrl}/system/summary`);
  });

  it('fetchSystemStatus fetches /system/status', async () => {
    const mockData = {
      status: 'operational',
      data_source: 'simulation',
      simulation_running: true,
      hardware_devices_online: 1,
      last_state_update: '2026-09-18T10:00:00Z',
      warnings: [],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await fetchSystemStatus();
    expect(result.status).toBe('operational');
    expect(global.fetch).toHaveBeenCalledWith(`${baseUrl}/system/status`);
  });

  it('fetchEnergy fetches /energy', async () => {
    const mockData = {
      timestamp: '2026-09-18T10:00:00Z',
      base_grid_capacity_kw: 100,
      effective_grid_capacity_kw: 100,
      building_demand_kw: 25,
      solar_voltage_v: 4.2,
      solar_availability_percent: 85,
      estimated_solar_generation_kw: 12,
      battery_discharge_kw: 0,
      battery_charge_kw: 0,
      available_ev_charging_power_kw: 87,
      total_ev_allocated_power_kw: 22,
      infrastructure_load_kw: 47,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await fetchEnergy();
    expect(result.effective_grid_capacity_kw).toBe(100);
    expect(global.fetch).toHaveBeenCalledWith(`${baseUrl}/energy`);
  });

  it('fetchEVs and fetchEVById fetch EV endpoints', async () => {
    const mockEVs = [
      {
        id: 'EV-001',
        slot_id: 'BAY-1',
        status: 'charging',
        battery_capacity_kwh: 60,
        soc_percent: 50,
        target_soc_percent: 80,
        max_charging_power_kw: 22,
        allocated_power_kw: 11,
        arrival_time: '2026-09-18T09:00:00Z',
        departure_time: '2026-09-18T12:00:00Z',
        energy_required_kwh: 18,
        remaining_time_minutes: 180,
        required_average_power_kw: 6,
        priority_score: 1.5,
        deadline_status: 'feasible',
        reason: 'Optimal',
      },
    ];

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockEVs,
    } as Response);

    const list = await fetchEVs();
    expect(list.length).toBe(1);

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockEVs[0],
    } as Response);

    const single = await fetchEVById('EV-001');
    expect(single.id).toBe('EV-001');
  });

  it('fetchCurrentOptimization handles 404 cleanly by returning null', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'No optimization calculated yet' }),
    } as Response);

    const result = await fetchCurrentOptimization();
    expect(result).toBeNull();
  });

  it('runOptimization posts to /optimization/run', async () => {
    const mockDecision = {
      timestamp: '2026-09-18T10:00:00Z',
      available_power_kw: 85,
      allocated_power_kw: 22,
      unallocated_power_kw: 63,
      bess_action: {
        mode: 'idle',
        target_power_kw: 0,
        projected_soc_percent: 80,
        reason: 'Adequate solar & grid',
      },
      allocations: [],
      warnings: [],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockDecision,
    } as Response);

    const result = await runOptimization();
    expect(result.allocated_power_kw).toBe(22);
    expect(global.fetch).toHaveBeenCalledWith(`${baseUrl}/optimization/run`, expect.objectContaining({ method: 'POST' }));
  });

  it('applyOptimization posts to /optimization/apply', async () => {
    const mockApply = {
      applied: true,
      timestamp: '2026-09-18T10:00:00Z',
      evs_updated: 2,
      battery_mode: 'idle',
      message: 'Applied allocations successfully',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockApply,
    } as Response);

    const result = await applyOptimization();
    expect(result.applied).toBe(true);
  });

  it('handles and parses API errors with status text', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({ detail: 'Simulation crash' }),
    } as Response);

    await expect(fetchSystemSummary()).rejects.toThrow('Simulation crash');
  });
});
