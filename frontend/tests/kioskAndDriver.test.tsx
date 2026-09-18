import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KioskQRStationPage } from '../src/pages/kiosk/KioskQRStationPage';
import { DriverLiveStatusPage } from '../src/pages/driver/DriverLiveStatusPage';
import { api } from '../src/services/api';

describe('KioskQRStationPage Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders unique QR code and scan instructions', async () => {
    const mockSession = {
      session_id: 'QR-TEST1234',
      bay_id: 'BAY-04',
      created_at: '2026-09-19T00:00:00Z',
      status: 'active' as const,
    };

    vi.spyOn(api, 'createQRSession').mockResolvedValue(mockSession);
    vi.spyOn(api, 'getQRSession').mockResolvedValue(mockSession);
    vi.spyOn(api, 'getNetworkInfo').mockResolvedValue({
      host_ip: '172.16.12.85',
      frontend_port: 3000,
      backend_port: 8000,
      driver_base_url: 'http://172.16.12.85:3000/?view=driver',
    });

    render(<KioskQRStationPage />);

    expect(await screen.findByText('GRIDWISE ONBOARDING KIOSK')).toBeInTheDocument();
    const tokenElements = await screen.findAllByText(/QR-TEST1234/i);
    expect(tokenElements.length).toBeGreaterThan(0);
    expect(screen.getByText(/Scan to track charging status & register vehicle/i)).toBeInTheDocument();
  });
});

describe('DriverLiveStatusPage Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders check-in form when vehicle is not yet registered', async () => {
    const mockSession = {
      session_id: 'QR-NEW5678',
      bay_id: 'BAY-02',
      created_at: '2026-09-19T00:00:00Z',
      status: 'active' as const,
      ev_id: null,
    };

    vi.spyOn(api, 'claimQRSession').mockResolvedValue(mockSession);

    render(<DriverLiveStatusPage sessionId="QR-NEW5678" />);

    expect(await screen.findByText('EV Driver Check-in')).toBeInTheDocument();
    expect(screen.getByText(/Start Charging & Track Live/i)).toBeInTheDocument();
  });

  it('renders live battery SoC and ready by time when vehicle is actively charging', async () => {
    const mockSession = {
      session_id: 'QR-ACTIVE99',
      bay_id: 'BAY-01',
      created_at: '2026-09-19T00:00:00Z',
      status: 'registered' as const,
      ev_id: 'EV-001',
    };

    const mockEv = {
      id: 'EV-001',
      slot_id: 'BAY-01',
      status: 'charging',
      battery_capacity_kwh: 75,
      soc_percent: 54,
      target_soc_percent: 85,
      max_charging_power_kw: 11,
      allocated_power_kw: 7.0,
      arrival_time: '2026-09-19T00:00:00Z',
      departure_time: '2026-09-19T03:00:00Z',
      energy_required_kwh: 23.25,
      remaining_time_minutes: 180,
      required_average_power_kw: 7.75,
      priority_score: 2.1,
      deadline_status: 'feasible',
      reason: 'Optimized allocation',
    };

    vi.spyOn(api, 'claimQRSession').mockResolvedValue(mockSession);
    vi.spyOn(api, 'getEVById').mockResolvedValue(mockEv as any);

    render(<DriverLiveStatusPage sessionId="QR-ACTIVE99" />);

    expect(await screen.findByText('Charging: EV-001')).toBeInTheDocument();
    expect(await screen.findByText('54')).toBeInTheDocument();
    expect(await screen.findByText(/7.0 kW/i)).toBeInTheDocument();
    expect(screen.getByText(/RETURN BY:/i)).toBeInTheDocument();
  });
});
