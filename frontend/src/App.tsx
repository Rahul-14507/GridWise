/**
 * GridWise Ops Console: SCADA & EV Energy Management Platform Entrypoint.
 * Stack: React 18 + TypeScript + Vite + Tailwind CSS.
 * 7 Tabs: Overview | Analytics | Node Management | EV Fleet | Alerts | Reports | System Settings.
 * Live data via useSystemState (FastAPI /api/v1) with mock fallback.
 */
import React, { useMemo, useState } from 'react';
import { AlertOctagon, RefreshCw } from 'lucide-react';
import { AppShell, type GridTab } from './components/layout/AppShell';
import { Overview } from './pages/Overview';
import { Analytics } from './pages/Analytics';
import { NodeManagement } from './pages/NodeManagement';
import { EVFleetPage } from './pages/EVFleetPage';
import { AlertsPage } from './pages/AlertsPage';
import { ReportsPage } from './pages/ReportsPage';
import { SystemSettings } from './pages/SystemSettings';
import { useSystemState } from './hooks/useSystemState';
import { getBaseUrl } from './services/api';
import { generateMockTelemetry } from './data/mockGrid';
import { FALLBACK_METRICS, computeHeroMetrics } from './utils/metrics';
import type { ChartPoint } from './components/dashboard/TelemetryChart';
import type { GridNode } from './data/mockGrid';

export const App: React.FC = () => {
  // -- Tab + polling state --
  const [tab, setTab] = useState<GridTab>('overview');
  const [pollMs, setPollMs] = useState(3000);

  const {
    summary,
    status,
    energy,
    evs,
    optimization,
    history,
    lastUpdated,
    isStale,
    isLoading,
    error,
    isOptimizing,
    isApplying,
    isTicking,
    refresh,
    runOptimization,
    applyOptimization,
    triggerTick,
  } = useSystemState(pollMs);

  // -- Derived hero metrics --
  const metrics = useMemo(() => {
    if (!energy && !summary) return FALLBACK_METRICS;
    try {
      return computeHeroMetrics(energy, summary, evs);
    } catch {
      return FALLBACK_METRICS;
    }
  }, [energy, summary, evs]);

  // -- Chart points --
  const mockPoints: ChartPoint[] = useMemo(() => generateMockTelemetry(42, 48), []);
  const chartPoints: ChartPoint[] = useMemo(() => {
    if (history.length >= 3) {
      return history.map((h) => ({
        t: h.timeLabel,
        demandKw: h.totalDemandKw,
        solarKw: h.solarGenerationKw,
        evKw: h.evFleetPowerKw,
      }));
    }
    return mockPoints;
  }, [history, mockPoints]);

  // -- Live Status mapping --
  const liveStatus = useMemo(() => {
    const out: Record<string, GridNode['status']> = {};
    for (const ev of evs) {
      const slot = (ev.slot_id ?? '').toUpperCase().replace('_', '-');
      const key = slot.startsWith('BAY') ? slot.replace('BAY-', 'BAY-0').slice(0, 6) : null;
      const norm = slot.replace(/^BAY-0*(\d+)$/, (_, d) => `BAY-${String(d).padStart(2, '0')}`);
      const target = key ? norm : null;
      if (!target) continue;
      const st = String(ev.status).toLowerCase();
      const dl = String(ev.deadline_status ?? '').toLowerCase();
      if (st === 'disconnected' || dl === 'expired') out[target] = 'offline';
      else if (dl === 'at_risk' || st === 'paused') out[target] = 'warning';
      else if (st === 'charging' || st === 'waiting') out[target] = 'online';
    }
    for (const item of metrics.outageItems) {
      const m = item.match(/BAY-0?\d/i);
      if (m) out[m[0].toUpperCase().replace(/^BAY-0*(\d+)$/, (_, d) => `BAY-${String(d).padStart(2, '0')}`)] = 'offline';
    }
    return out;
  }, [evs, metrics.outageItems]);

  const warnings = useMemo(
    () => summary?.warnings ?? status?.warnings ?? [],
    [summary, status],
  );
  const systemStatus = summary?.system_status ?? status?.status ?? (error && !summary ? 'degraded' : 'operational');
  const dataSource = summary?.data_source ?? status?.data_source ?? 'simulation';
  const dataSourceLabel = `${dataSource}${history.length >= 3 ? '' : ' | mock fallback'}`;

  // -- Loading Screen --
  if (isLoading && !summary && !error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-[#F4F5F7] text-slate-900 font-sans">
        <div className="loading-spinner" aria-hidden />
        <h2 className="text-base font-extrabold text-slate-900">Establishing SCADA Session...</h2>
        <p className="text-xs text-slate-500">Connecting to GridWise backend API endpoint /api/v1...</p>
      </div>
    );
  }

  const backendDown = error !== null && summary === null;

  return (
    <AppShell
      active={tab}
      onChange={setTab}
      systemStatus={systemStatus}
      dataSource={dataSource}
      isStale={backendDown ? true : isStale}
      lastUpdated={lastUpdated}
      isLoading={isLoading}
      onRefresh={refresh}
      onOptimize={runOptimization}
      isOptimizing={isOptimizing}
      onTick={triggerTick}
      isTicking={isTicking}
    >
      {backendDown && (
        <div className="flex items-center gap-3 rounded-md border border-red-300 bg-red-50 p-3" role="alert">
          <AlertOctagon size={22} className="shrink-0 text-red-600" />
          <div className="flex-1 text-xs">
            <p className="font-extrabold text-red-900">Backend Unreachable: Operating in Offline Mock Telemetry Mode</p>
            <p className="text-slate-600">
              Tried endpoint <code className="font-mono font-bold text-red-800">{getBaseUrl()}</code> | {error}
            </p>
          </div>
          <button onClick={refresh} className="flex items-center gap-1 rounded bg-red-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-red-700">
            <RefreshCw size={13} /> Retry Connection
          </button>
        </div>
      )}

      {tab === 'overview' && (
        <Overview
          metrics={metrics}
          chartPoints={chartPoints}
          warnings={warnings}
          liveStatus={liveStatus}
          dataSourceLabel={dataSourceLabel}
        />
      )}

      {tab === 'analytics' && (
        <Analytics
          history={history}
          fallbackPoints={mockPoints}
          energy={energy}
          summary={summary}
          evs={evs}
          optimization={optimization}
        />
      )}

      {tab === 'nodes' && (
        <NodeManagement energy={energy} energySummary={summary?.energy ?? null} evs={evs} />
      )}

      {tab === 'ev-fleet' && <EVFleetPage evs={evs} />}

      {tab === 'alerts' && <AlertsPage warnings={warnings} />}

      {tab === 'reports' && <ReportsPage summary={summary} energy={energy} />}

      {tab === 'settings' && (
        <SystemSettings
          pollMs={pollMs}
          onPollChange={setPollMs}
          dataSource={dataSource}
          onTick={triggerTick}
          isTicking={isTicking}
          onOptimize={runOptimization}
          isOptimizing={isOptimizing}
          onApply={applyOptimization}
          isApplying={isApplying}
        />
      )}
    </AppShell>
  );
};

export default App;

