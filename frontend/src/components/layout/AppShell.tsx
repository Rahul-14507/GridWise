/**
 * AppShell: Enterprise SCADA & EV Energy Management Console Frame.
 * Crisp industrial light palette (#F4F5F7 canvas, #FFFFFF cards, #E2E8F0 borders).
 * 7 Primary Navigation Tabs: Overview, Analytics, Node Management, EV Fleet, Alerts, Reports, System Settings.
 */
import React, { useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  Car,
  Clock,
  Download,
  FileText,
  LayoutDashboard,
  Network,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sliders,
  Zap,
} from 'lucide-react';

export type GridTab = 'overview' | 'analytics' | 'nodes' | 'ev-fleet' | 'alerts' | 'reports' | 'settings';

export const TABS: { id: GridTab; label: string; icon: React.ElementType; hint: string }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, hint: 'SCADA Topology & Live KPIs' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, hint: 'Telemetry Deep-Dive & Load Trends' },
  { id: 'nodes', label: 'Node Management', icon: Network, hint: 'Substations, Feeders & Breakers' },
  { id: 'ev-fleet', label: 'EV Fleet', icon: Car, hint: 'Priority Allocation & Charger Control' },
  { id: 'alerts', label: 'Alerts', icon: AlertTriangle, hint: 'Operational Fault Log & Constraints' },
  { id: 'reports', label: 'Reports', icon: FileText, hint: 'PDF / CSV / Excel Export Center' },
  { id: 'settings', label: 'System Settings', icon: Settings, hint: 'SCADA Config & Thresholds' },
];

interface AppShellProps {
  active: GridTab;
  onChange: (t: GridTab) => void;
  systemStatus: string;
  dataSource: string;
  isStale: boolean;
  lastUpdated: Date | null;
  isLoading: boolean;
  onRefresh: () => void;
  onOptimize: () => void;
  isOptimizing: boolean;
  onTick?: (seconds?: number) => void;
  isTicking?: boolean;
  children: React.ReactNode;
}

function formatUtcTime(d: Date | null): string {
  if (!d) return '14:32:05 UTC';
  return d.toUTCString().split(' ')[4] + ' UTC';
}

export const AppShell: React.FC<AppShellProps> = ({
  active,
  onChange,
  systemStatus,
  dataSource,
  isStale,
  lastUpdated,
  isLoading,
  onRefresh,
  onOptimize,
  isOptimizing,
  onTick,
  isTicking,
  children,
}) => {
  const [selectedZone, setSelectedZone] = useState('Zone 4 - North Substation');

  const statusBadge =
    systemStatus === 'operational' ? (
      <span className="inline-flex items-center gap-1 rounded border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-700">
        <ShieldCheck size={13} /> GRID STATUS: NOMINAL (99.8% STABILITY)
      </span>
    ) : systemStatus === 'warning' ? (
      <span className="inline-flex items-center gap-1 rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700">
        <AlertTriangle size={13} /> GRID STATUS: CONSTRAINED
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 rounded border border-red-300 bg-red-50 px-2 py-0.5 text-xs font-bold text-red-700">
        <AlertTriangle size={13} /> GRID STATUS: DEGRADED
      </span>
    );

  return (
    <div className="min-h-screen bg-[#F4F5F7] text-slate-900 font-sans">
      {/* Top Header Bar */}
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white shadow-xs">
        <div className="mx-auto flex max-w-[1536px] flex-wrap items-center justify-between gap-3 px-4 py-2.5">
          {/* Brand & Substation Switcher */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded border border-blue-600 bg-blue-50 text-blue-600">
              <Zap size={20} className="fill-blue-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-extrabold tracking-tight text-slate-900">
                  GRIDWISE <span className="text-xs font-normal text-slate-500">| Enterprise SCADA & EV Energy Management</span>
                </h1>
                <span className="rounded bg-slate-900 px-1.5 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider">
                  SCADA v4.2
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <label className="flex items-center gap-1 font-semibold text-slate-700">
                  Substation:
                  <select
                    value={selectedZone}
                    onChange={(e) => setSelectedZone(e.target.value)}
                    className="rounded border border-slate-300 bg-slate-50 px-2 py-0.5 text-xs font-bold text-slate-800 focus:border-blue-600 focus:outline-none"
                  >
                    <option value="Zone 4 - North Substation">Zone 4 - North Substation</option>
                    <option value="Zone 1 - Main Grid Substation">Zone 1 - Main Grid Substation</option>
                    <option value="Zone 2 - Commercial Park Substation">Zone 2 - Commercial Park Substation</option>
                    <option value="Zone 3 - Solar PV Array Microgrid">Zone 3 - Solar PV Array Microgrid</option>
                  </select>
                </label>
              </div>
            </div>
          </div>

          {/* Operational Status & Sync Telemetry */}
          <div className="hidden items-center gap-3 lg:flex">
            {statusBadge}

            <div className="flex items-center gap-1.5 rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-mono text-slate-600">
              <span className={`h-2 w-2 rounded-full ${isStale ? 'bg-red-500' : 'bg-emerald-500'}`} />
              <span className="font-bold text-slate-700">{isStale ? 'STALE' : 'LIVE'}</span>
              <span className="text-slate-400">| Last Sync: {formatUtcTime(lastUpdated)}</span>
            </div>
          </div>

          {/* Header Action Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="flex items-center gap-1.5 rounded border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              title="Refresh telemetry"
            >
              <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} /> Refresh Data
            </button>

            {onTick && (
              <button
                onClick={() => onTick(60)}
                disabled={isTicking}
                className="hidden items-center gap-1.5 rounded border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 sm:flex"
                title="Advance simulation by 60s"
              >
                <Clock size={13} className={isTicking ? 'animate-spin' : ''} /> Step +60s
              </button>
            )}

            <button
              onClick={onOptimize}
              disabled={isOptimizing}
              className="flex items-center gap-1.5 rounded bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50"
              title="Run ChargingOptimizer dispatch cycle"
            >
              <Sliders size={13} className={isOptimizing ? 'animate-spin' : ''} /> {isOptimizing ? 'Optimizing...' : 'Optimize'}
            </button>

            <button
              onClick={() => onChange('reports')}
              className="hidden items-center gap-1.5 rounded border border-slate-300 bg-slate-800 px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-700 md:flex"
              title="Export grid report"
            >
              <Download size={13} /> Export Report
            </button>
          </div>
        </div>

        {/* 7 Primary Navigation Tabs */}
        <nav className="border-t border-slate-200 bg-slate-50 px-4" aria-label="Primary SCADA Navigation">
          <div className="mx-auto flex max-w-[1536px] overflow-x-auto slim-scroll">
            {TABS.map((t) => {
              const Icon = t.icon;
              const selected = active === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => onChange(t.id)}
                  aria-current={selected ? 'page' : undefined}
                  title={t.hint}
                  className={`tab-btn flex shrink-0 items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-bold transition-colors ${
                    selected
                      ? 'border-blue-600 bg-white text-blue-700'
                      : 'border-transparent text-slate-600 hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <Icon size={15} />
                  {t.label}
                </button>
              );
            })}
          </div>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto w-full max-w-[1536px] space-y-4 px-4 py-4 pb-12">{children}</main>

      {/* Enterprise Footer */}
      <footer className="border-t border-slate-200 bg-white px-4 py-3 text-center text-xs text-slate-500">
        <div className="mx-auto flex max-w-[1536px] flex-wrap items-center justify-between gap-2">
          <span>GRIDWISE Enterprise Electric Grid & EV Infrastructure Platform | IEC 61850 / SCADA Compliant</span>
          <span className="font-mono text-[11px]">Source: {dataSource.toUpperCase()} | Polling endpoint: /api/v1</span>
        </div>
      </footer>
    </div>
  );
};

