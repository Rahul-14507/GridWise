/**
 * Analytics tab: Deep telemetry: live rolling history (backend) with
 * mock fallback, plus energy-flow and optimization context.
 */
import React, { useMemo } from 'react';
import { BatteryStatus } from '../components/battery/BatteryStatus';
import { EnergyFlow } from '../components/energy/EnergyFlow';
import { OptimizationStatus } from '../components/optimization/OptimizationStatus';
import { RealtimeCharts } from '../components/charts/RealtimeCharts';
import { SolarSubsystem } from '../components/energy/SolarSubsystem';
import { TelemetryChart, type ChartPoint } from '../components/dashboard/TelemetryChart';
import type {
  EnergyDetailResponse,
  EVDetailResponse,
  OptimizationDecision,
  SystemSummaryResponse,
  TimeSeriesPoint,
} from '../types/api';

interface AnalyticsProps {
  history: TimeSeriesPoint[];
  fallbackPoints: ChartPoint[];
  energy: EnergyDetailResponse | null;
  summary: SystemSummaryResponse | null;
  evs: EVDetailResponse[];
  optimization: OptimizationDecision | null;
}

export const Analytics: React.FC<AnalyticsProps> = ({
  history,
  fallbackPoints,
  energy,
  summary,
  evs,
  optimization,
}) => {
  // Normalize live history -> chart points; fall back to mock when empty.
  const livePoints: ChartPoint[] = useMemo(
    () =>
      history.map((h) => ({
        t: h.timeLabel,
        demandKw: h.totalDemandKw,
        solarKw: h.solarGenerationKw,
        evKw: h.evFleetPowerKw,
        stability: undefined,
      })),
    [history],
  );
  const points = livePoints.length >= 3 ? livePoints : fallbackPoints;
  const source = livePoints.length >= 3 ? 'Live backend telemetry stream' : 'Mock fallback stream';

  return (
    <div className="space-y-4">
      <TelemetryChart
        points={points}
        height={240}
        title="Load & Generation Historical Telemetry Analytics"
        subtitle={`${points.length} telemetry points collected | Source: ${source}`}
      />

      {/* Existing deep-dive charts (live rolling window) */}
      <RealtimeCharts history={history} />

      <div className="grid gap-4 lg:grid-cols-2">
        <EnergyFlow energy={energy} evs={evs} />
        <OptimizationStatus optimization={optimization} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SolarSubsystem energy={energy} rainDetected={false} rainIntensity={0} />
        <BatteryStatus battery={summary?.battery ?? null} energy={energy} />
      </div>
    </div>
  );
};

