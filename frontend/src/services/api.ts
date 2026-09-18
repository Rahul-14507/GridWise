/** Centralized API client for GridWise Backend. */

import {
  EnergyDetailResponse,
  EVDetailResponse,
  EVRegistrationRequest,
  HardwareStatusSummary,
  HardwareTelemetry,
  NetworkInfoResponse,
  OptimizationApplyResponse,
  OptimizationDecision,
  QRSession,
  SystemStatusResponse,
  SystemSummaryResponse,
} from '../types/api';

export const getBaseUrl = (): string => {
  const envUrl = import.meta.env?.VITE_API_BASE_URL;
  if (envUrl) {
    let url = envUrl;
    if (url.endsWith('/')) url = url.slice(0, -1);
    if (!url.endsWith('/api/v1') && url !== '') url = `${url}/api/v1`;
    return url;
  }

  if (typeof window !== 'undefined') {
    return '/api/v1';
  }

  return 'http://localhost:8000/api/v1';
};

export const API_BASE_URL = getBaseUrl();

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    let errorDetail = `API error (${response.status} ${response.statusText})`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }
  return response.json() as Promise<T>;
};

export const fetchSystemSummary = async (): Promise<SystemSummaryResponse> => {
  const res = await fetch(`${getBaseUrl()}/system/summary`);
  return handleResponse<SystemSummaryResponse>(res);
};

export const fetchSystemStatus = async (): Promise<SystemStatusResponse> => {
  const res = await fetch(`${getBaseUrl()}/system/status`);
  return handleResponse<SystemStatusResponse>(res);
};

export const fetchSystemState = async (): Promise<any> => {
  const res = await fetch(`${getBaseUrl()}/system/state`);
  return handleResponse<any>(res);
};

export const fetchEnergy = async (): Promise<EnergyDetailResponse> => {
  const res = await fetch(`${getBaseUrl()}/energy`);
  return handleResponse<EnergyDetailResponse>(res);
};

export const fetchEVs = async (): Promise<EVDetailResponse[]> => {
  const res = await fetch(`${getBaseUrl()}/evs`);
  return handleResponse<EVDetailResponse[]>(res);
};

export const fetchEVById = async (evId: string): Promise<EVDetailResponse> => {
  const res = await fetch(`${getBaseUrl()}/evs/${encodeURIComponent(evId)}`);
  return handleResponse<EVDetailResponse>(res);
};

export const fetchCurrentOptimization = async (): Promise<OptimizationDecision | null> => {
  try {
    const res = await fetch(`${getBaseUrl()}/optimization/current`);
    if (res.status === 404) {
      return null;
    }
    return handleResponse<OptimizationDecision>(res);
  } catch (err: any) {
    if (err.message && err.message.includes('404')) {
      return null;
    }
    throw err;
  }
};

export const runOptimization = async (): Promise<OptimizationDecision> => {
  const res = await fetch(`${getBaseUrl()}/optimization/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<OptimizationDecision>(res);
};

export const applyOptimization = async (): Promise<OptimizationApplyResponse> => {
  const res = await fetch(`${getBaseUrl()}/optimization/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<OptimizationApplyResponse>(res);
};

export const fetchHardwareStatus = async (): Promise<HardwareStatusSummary> => {
  const res = await fetch(`${getBaseUrl()}/hardware/status`);
  return handleResponse<HardwareStatusSummary>(res);
};

export const fetchLatestHardwareTelemetry = async (deviceId?: string): Promise<HardwareTelemetry> => {
  const query = deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : '';
  const res = await fetch(`${getBaseUrl()}/hardware/telemetry/latest${query}`);
  return handleResponse<HardwareTelemetry>(res);
};

export const postHardwareTelemetry = async (payload: any): Promise<any> => {
  const res = await fetch(`${getBaseUrl()}/hardware/telemetry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<any>(res);
};

export const triggerTick = async (seconds: number = 60): Promise<any> => {
  const res = await fetch(`${getBaseUrl()}/simulation/tick?interval_seconds=${seconds}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<any>(res);
};

export const stepSimulation = async (seconds: number = 60): Promise<any> => {
  return triggerTick(seconds);
};

export const resetSimulation = async (): Promise<any> => {
  const res = await fetch(`${getBaseUrl()}/simulation/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<any>(res);
};

export const toggleHardwareMode = async (enable: boolean): Promise<any> => {
  const res = await fetch(`${getBaseUrl()}/hardware/toggle-mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enable_hardware_mode: enable }),
  });
  return handleResponse<any>(res);
};

export const createQRSession = async (bayId?: string): Promise<QRSession> => {
  const url = bayId ? `${getBaseUrl()}/evs/qr-session?bay_id=${encodeURIComponent(bayId)}` : `${getBaseUrl()}/evs/qr-session`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<QRSession>(res);
};

export const getQRSession = async (sessionId: string): Promise<QRSession> => {
  const res = await fetch(`${getBaseUrl()}/evs/qr-session/${encodeURIComponent(sessionId)}`);
  return handleResponse<QRSession>(res);
};

export const claimQRSession = async (sessionId: string): Promise<QRSession> => {
  const res = await fetch(`${getBaseUrl()}/evs/qr-session/${encodeURIComponent(sessionId)}/claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<QRSession>(res);
};

export const registerDriverEV = async (payload: EVRegistrationRequest): Promise<EVDetailResponse> => {
  const res = await fetch(`${getBaseUrl()}/evs/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<EVDetailResponse>(res);
};

export const fetchNetworkInfo = async (): Promise<NetworkInfoResponse> => {
  const res = await fetch(`${getBaseUrl()}/system/network-info`);
  return handleResponse<NetworkInfoResponse>(res);
};

export const api = {
  getSystemSummary: fetchSystemSummary,
  getSystemStatus: fetchSystemStatus,
  getSystemState: fetchSystemState,
  getEnergyState: fetchEnergy,
  getEVs: fetchEVs,
  getEVById: fetchEVById,
  getOptimization: fetchCurrentOptimization,
  runOptimization,
  applyOptimization,
  getHardwareStatus: fetchHardwareStatus,
  getLatestHardwareTelemetry: fetchLatestHardwareTelemetry,
  postHardwareTelemetry,
  createQRSession,
  getQRSession,
  claimQRSession,
  registerDriverEV,
  getNetworkInfo: fetchNetworkInfo,
  triggerTick,
  stepSimulation,
  resetSimulation,
  toggleHardwareMode,
};

