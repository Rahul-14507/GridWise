/**
 * Grid health math: single source of truth for the three hero metrics:
 * Power Consumption, Grid Stability Index, Active Outages.
 *
 * When live backend data exists we derive from it; otherwise callers
 * fall back to mock constants so the UI never renders empty.
 */
import type { EnergyDetailResponse, EVDetailResponse, SystemSummaryResponse } from '../types/api';

export interface HeroMetrics {
  /** Total facility draw in kW */
  powerKw: number;
  /** Share of effective capacity currently used (0 to 1+) */
  utilization: number;
  /** Effective headroom in kW */
  headroomKw: number;
  /** 0 to 100 stability score */
  stabilityIndex: number;
  stabilityGrade: 'Stable' | 'Watch' | 'Strained' | 'Critical';
  /** Outage-class incidents (offline bays, critical warnings, expired EVs) */
  activeOutages: number;
  outageItems: string[];
}

export function stabilityGradeFor(score: number): HeroMetrics['stabilityGrade'] {
  if (score >= 85) return 'Stable';
  if (score >= 65) return 'Watch';
  if (score >= 40) return 'Strained';
  return 'Critical';
}

/**
 * Compute hero metrics from live state. Pure + unit-testable.
 * Formula: start at 100, subtract utilization / derate / warning penalties.
 */
export function computeHeroMetrics(
  energy: EnergyDetailResponse | null,
  summary: SystemSummaryResponse | null,
  evs: EVDetailResponse[],
): HeroMetrics {
  const powerKw = energy?.infrastructure_load_kw
    ?? (summary ? summary.energy.building_demand_kw + 0 : 0);
  const effective = energy?.effective_grid_capacity_kw ?? summary?.energy.effective_capacity_kw ?? 250;
  const base = energy?.base_grid_capacity_kw ?? summary?.energy.grid_capacity_kw ?? 250;
  const utilization = effective > 0 ? powerKw / effective : 0;
  const headroomKw = Math.max(0, effective - powerKw);

  // Penalties
  let score = 100;
  if (utilization > 0.9) score -= 28;
  else if (utilization > 0.8) score -= 16;
  else if (utilization > 0.7) score -= 7;

  const derateRatio = base > 0 ? 1 - effective / base : 0;
  score -= Math.min(20, derateRatio * 120); // e.g. 10% derate ~ -12 pts

  const warnings = summary?.warnings ?? [];
  const critical = warnings.filter((w) => String(w.severity).toLowerCase() === 'critical').length;
  const warn = warnings.filter((w) => String(w.severity).toLowerCase() === 'warning').length;
  score -= critical * 15 + warn * 5;

  const expiredEvs = evs.filter((e) => String(e.deadline_status ?? '').toLowerCase() === 'expired').length;
  score -= Math.min(12, expiredEvs * 4);

  // Solar + battery resilience bonus (small, capped)
  const solarKw = energy?.estimated_solar_generation_kw ?? summary?.energy.solar_generation_kw ?? 0;
  if (solarKw > 20) score += 3;
  const soc = summary?.battery.soc_percent ?? 50;
  if (soc > 60) score += 2;

  const stabilityIndex = Math.round(Math.max(0, Math.min(100, score)));

  // Outages: critical warnings + offline EV bays + expired deadlines.
  // EV "disconnected" is treated as an outage-class item for operators.
  const outageItems: string[] = [];
  warnings
    .filter((w) => String(w.severity).toLowerCase() === 'critical')
    .forEach((w) => outageItems.push(`${w.code}: ${w.message}`));
  evs
    .filter((e) => ['disconnected'].includes(String(e.status).toLowerCase()) || String(e.deadline_status ?? '').toLowerCase() === 'expired')
    .forEach((e) => outageItems.push(`${e.id}: ${e.status} / deadline ${e.deadline_status ?? 'unknown'}`));

  return {
    powerKw: +powerKw.toFixed(1),
    utilization,
    headroomKw: +headroomKw.toFixed(1),
    stabilityIndex,
    stabilityGrade: stabilityGradeFor(stabilityIndex),
    activeOutages: outageItems.length,
    outageItems,
  };
}

/** Demo fallback shown before first poll resolves or when backend is down. */
export const FALLBACK_METRICS: HeroMetrics = {
  powerKw: 196.4,
  utilization: 0.82,
  headroomKw: 43.6,
  stabilityIndex: 78,
  stabilityGrade: 'Watch',
  activeOutages: 1,
  outageItems: ['BAY-04: contactor fault . crew dispatched'],
};

export const formatKw = (v: number, digits = 1): string => `${v.toFixed(digits)} kW`;
export const formatPct = (v: number): string => `${Math.round(v * 100)}%`;
