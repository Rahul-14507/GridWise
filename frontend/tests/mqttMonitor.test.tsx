import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LiveMQTTMonitorPage } from '../src/pages/LiveMQTTMonitorPage';

describe('LiveMQTTMonitorPage Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders hardware telemetry metrics and ESP32 status', async () => {
    const mockStatus = {
      mode: 'hardware',
      online: true,
      total_devices: 1,
      online_devices: 1,
      stale_devices: 0,
      last_received: '2026-09-18T12:30:00Z',
      devices: [],
    };

    const mockTelemetry = {
      device_id: 'ESP32-001',
      timestamp: '2026-09-18T12:30:00Z',
      temperature_c: 35.0,
      humidity_percent: 50.0,
      rain_detected: false,
      rain_intensity: 0.0,
      solar_voltage_v: 2.5,
      rain_raw: 3200,
      rain_status: 'DRY',
      solar_status: 'BRIGHT',
    };

    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = url.toString();
      if (urlStr.includes('/hardware/status')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockStatus),
        } as Response);
      }
      if (urlStr.includes('/hardware/telemetry/latest')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTelemetry),
        } as Response);
      }
      return Promise.reject(new Error('Unknown URL'));
    }) as any;

    render(<LiveMQTTMonitorPage />);

    expect(await screen.findByText(/35.0°C/i)).toBeInTheDocument();
    expect(await screen.findByText(/2.50 V/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/3200/i)).length).toBeGreaterThan(0);
  });

  it('displays critical Overload Alert when temperature exceeds 50 degrees', async () => {
    const mockStatus = {
      mode: 'hardware',
      online: true,
      total_devices: 1,
      online_devices: 1,
      stale_devices: 0,
      last_received: '2026-09-18T12:30:00Z',
      devices: [],
    };

    const mockOverloadTelemetry = {
      device_id: 'ESP32-001',
      timestamp: '2026-09-18T12:30:00Z',
      temperature_c: 54.2,
      humidity_percent: 30.0,
      rain_detected: false,
      rain_intensity: 0.0,
      solar_voltage_v: 2.9,
      rain_raw: 3500,
      rain_status: 'DRY',
      solar_status: 'BRIGHT',
    };

    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = url.toString();
      if (urlStr.includes('/hardware/status')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockStatus),
        } as Response);
      }
      if (urlStr.includes('/hardware/telemetry/latest')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockOverloadTelemetry),
        } as Response);
      }
      return Promise.reject(new Error('Unknown URL'));
    }) as any;

    render(<LiveMQTTMonitorPage />);

    expect(await screen.findByText(/CRITICAL TEMPERATURE EXCEEDED: 54.2°C/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/OVERLOAD ALERT/i)).length).toBeGreaterThan(0);
  });
});
