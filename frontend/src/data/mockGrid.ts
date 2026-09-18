/**
 * Mock grid topology + deterministic telemetry generator.
 *
 * Used when the FastAPI backend is unreachable (demo / offline mode)
 * and as the visual backbone for the interactive Grid Map.
 *
 * Coordinates are in a 100 x 62 viewBox space so the SVG scales
 * responsively without extra math.
 */

export type GridNodeStatus = 'online' | 'stable' | 'warning' | 'offline' | 'maintenance';
export type GridNodeKind =
  | 'substation'
  | 'transformer'
  | 'feeder'
  | 'solar'
  | 'battery'
  | 'ev-bay'
  | 'load';

export interface GridNode {
  id: string;
  label: string;
  kind: GridNodeKind;
  /** 0 to 100 x, 0 to 62 y */
  x: number;
  y: number;
  status: GridNodeStatus;
  loadKw: number;
  capacityKw: number;
  voltageKv: number;
  /** Short operator note shown in tooltip / side panel */
  note: string;
}

export interface GridEdge {
  id: string;
  from: string;
  to: string;
  /** Current flow on this segment */
  flowKw: number;
  /** Whether power is actively flowing (animates) */
  energized: boolean;
}

/** Canonical demo topology: mirrors a small campus / depot microgrid. */
export const MOCK_NODES: GridNode[] = [
  { id: 'SUB-01', label: 'Main Substation', kind: 'substation', x: 8, y: 31, status: 'online', loadKw: 184, capacityKw: 250, voltageKv: 11, note: 'Grid import . 2 feeders' },
  { id: 'TR-01', label: 'Transformer T1', kind: 'transformer', x: 24, y: 16, status: 'stable', loadKw: 92, capacityKw: 120, voltageKv: 0.415, note: 'Feeds North bus . 77% loaded' },
  { id: 'TR-02', label: 'Transformer T2', kind: 'transformer', x: 24, y: 46, status: 'warning', loadKw: 108, capacityKw: 120, voltageKv: 0.415, note: 'Thermal derate 8% . watch temp' },
  { id: 'FEED-A', label: 'Feeder A . North', kind: 'feeder', x: 40, y: 16, status: 'stable', loadKw: 64, capacityKw: 90, voltageKv: 0.415, note: 'EV bays 1 to 2 + offices' },
  { id: 'FEED-B', label: 'Feeder B . South', kind: 'feeder', x: 40, y: 46, status: 'warning', loadKw: 78, capacityKw: 90, voltageKv: 0.415, note: 'EV bays 3 to 4 . near limit' },
  { id: 'PV-01', label: 'Solar PV Array', kind: 'solar', x: 58, y: 6, status: 'online', loadKw: -42, capacityKw: 60, voltageKv: 0.415, note: 'Generating 42 kW . clear sky proxy' },
  { id: 'BESS-01', label: 'BESS Battery', kind: 'battery', x: 58, y: 56, status: 'stable', loadKw: -12, capacityKw: 100, voltageKv: 0.415, note: 'SoC 68% . discharging 12 kW' },
  { id: 'BAY-01', label: 'EV Bay 01', kind: 'ev-bay', x: 74, y: 12, status: 'online', loadKw: 22, capacityKw: 30, voltageKv: 0.415, note: 'Charging . 22 kW . SoC 61%' },
  { id: 'BAY-02', label: 'EV Bay 02', kind: 'ev-bay', x: 74, y: 24, status: 'online', loadKw: 18, capacityKw: 30, voltageKv: 0.415, note: 'Charging . 18 kW . SoC 74%' },
  { id: 'BAY-03', label: 'EV Bay 03', kind: 'ev-bay', x: 74, y: 38, status: 'warning', loadKw: 7, capacityKw: 30, voltageKv: 0.415, note: 'At-risk deadline . throttled' },
  { id: 'BAY-04', label: 'EV Bay 04', kind: 'ev-bay', x: 74, y: 50, status: 'offline', loadKw: 0, capacityKw: 30, voltageKv: 0, note: 'Outage . contactor fault . crew dispatched' },
  { id: 'HQ-LOAD', label: 'Building Load', kind: 'load', x: 90, y: 31, status: 'stable', loadKw: 56, capacityKw: 80, voltageKv: 0.415, note: 'HVAC + lighting baseload' },
];

export const MOCK_EDGES: GridEdge[] = [
  { id: 'e1', from: 'SUB-01', to: 'TR-01', flowKw: 92, energized: true },
  { id: 'e2', from: 'SUB-01', to: 'TR-02', flowKw: 108, energized: true },
  { id: 'e3', from: 'TR-01', to: 'FEED-A', flowKw: 64, energized: true },
  { id: 'e4', from: 'TR-02', to: 'FEED-B', flowKw: 78, energized: true },
  { id: 'e5', from: 'PV-01', to: 'FEED-A', flowKw: 42, energized: true },
  { id: 'e6', from: 'BESS-01', to: 'FEED-B', flowKw: 12, energized: true },
  { id: 'e7', from: 'FEED-A', to: 'BAY-01', flowKw: 22, energized: true },
  { id: 'e8', from: 'FEED-A', to: 'BAY-02', flowKw: 18, energized: true },
  { id: 'e9', from: 'FEED-B', to: 'BAY-03', flowKw: 7, energized: true },
  { id: 'e10', from: 'FEED-B', to: 'BAY-04', flowKw: 0, energized: false },
  { id: 'e11', from: 'FEED-A', to: 'HQ-LOAD', flowKw: 28, energized: true },
  { id: 'e12', from: 'FEED-B', to: 'HQ-LOAD', flowKw: 28, energized: true },
];

/** Status to dot colour (slate base, emerald stable, amber warning). */
export const STATUS_COLOR: Record<GridNodeStatus, string> = {
  online: '#10b981', // emerald-500
  stable: '#34d399', // emerald-400
  warning: '#f59e0b', // amber-500
  offline: '#ef4444', // red-500
  maintenance: '#94a3b8', // slate-400
};

export interface TelemetryPoint {
  t: string; // HH:MM label
  demandKw: number;
  solarKw: number;
  evKw: number;
  stability: number; // 0 to 100
}

/**
 * Deterministic pseudo-random generator (mulberry32) so mock charts
 * are stable across renders but still look organic.
 */
function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Generate 48 mock telemetry points (15-min cadence, 12h window). */
export function generateMockTelemetry(seed = 42, points = 48): TelemetryPoint[] {
  const rand = mulberry32(seed);
  const out: TelemetryPoint[] = [];
  for (let i = 0; i < points; i++) {
    const hour = 6 + (i * 0.25); // 06:00 to 18:00 solar curve
    const solarPeak = Math.max(0, Math.sin(((hour - 6) / 12) * Math.PI));
    const solarKw = +(solarPeak * 58 + rand() * 4).toFixed(1);
    const base = 120 + Math.sin((i / points) * Math.PI * 2) * 28;
    const evKw = +(18 + Math.sin(i * 0.55) * 9 + rand() * 6).toFixed(1);
    const demandKw = +(base + evKw - solarKw * 0.35 + rand() * 5).toFixed(1);
    const stability = Math.round(
      Math.min(99, Math.max(52, 92 - (demandKw - 120) * 0.28 - evKw * 0.12 + solarKw * 0.08 + (rand() - 0.5) * 6)),
    );
    const hh = String(Math.floor(hour)).padStart(2, '0');
    const mm = hour % 1 === 0 ? '00' : hour % 1 === 0.25 ? '15' : hour % 1 === 0.5 ? '30' : '45';
    out.push({ t: `${hh}:${mm}`, demandKw, solarKw, evKw, stability });
  }
  return out;
}
