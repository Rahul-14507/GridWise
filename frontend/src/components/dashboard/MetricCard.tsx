/**
 * MetricCard: Enterprise SCADA Hero KPI Tile.
 * Restrained industrial design: crisp light surface (#FFFFFF), 1px border (#E2E8F0),
 * flat operational status badges, clear monospaced telemetry values, and trend indicators.
 */
import React from 'react';
import type { LucideIcon } from 'lucide-react';

export type MetricTone = 'emerald' | 'amber' | 'red' | 'blue' | 'slate';

const TONE_STYLES: Record<MetricTone, { border: string; iconBg: string; iconText: string; bar: string; badge: string }> = {
  emerald: {
    border: 'border-slate-200 hover:border-emerald-300',
    iconBg: 'bg-emerald-50 border-emerald-200',
    iconText: 'text-emerald-700',
    bar: 'bg-emerald-600',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-300',
  },
  amber: {
    border: 'border-slate-200 hover:border-amber-300',
    iconBg: 'bg-amber-50 border-amber-200',
    iconText: 'text-amber-700',
    bar: 'bg-amber-600',
    badge: 'bg-amber-50 text-amber-800 border-amber-300',
  },
  red: {
    border: 'border-slate-200 hover:border-red-300',
    iconBg: 'bg-red-50 border-red-200',
    iconText: 'text-red-700',
    bar: 'bg-red-600',
    badge: 'bg-red-50 text-red-700 border-red-300',
  },
  blue: {
    border: 'border-slate-200 hover:border-blue-300',
    iconBg: 'bg-blue-50 border-blue-200',
    iconText: 'text-blue-700',
    bar: 'bg-blue-600',
    badge: 'bg-blue-50 text-blue-700 border-blue-300',
  },
  slate: {
    border: 'border-slate-200',
    iconBg: 'bg-slate-100 border-slate-200',
    iconText: 'text-slate-700',
    bar: 'bg-slate-600',
    badge: 'bg-slate-100 text-slate-700 border-slate-300',
  },
};

interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  subtext?: string;
  icon: LucideIcon;
  tone?: MetricTone;
  /** 0 to 1 progress fill under the value (e.g. utilization) */
  progress?: number;
  /** Small badge text, e.g. "LIVE" or grade */
  badge?: string;
  /** Trend text e.g. "↓ 3.2% vs prev hour" */
  trend?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subtext,
  icon: Icon,
  tone = 'slate',
  progress,
  badge,
  trend,
}) => {
  const s = TONE_STYLES[tone];
  return (
    <section
      aria-label={label}
      className={`rounded-md border bg-white p-3.5 shadow-xs transition-colors ${s.border}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3">
          <span className={`flex h-9 w-9 items-center justify-center rounded border ${s.iconBg}`}>
            <Icon size={18} className={s.iconText} aria-hidden />
          </span>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{label}</p>
            <p className="font-mono text-2xl font-extrabold leading-tight text-slate-900">
              {value}
              {unit && <span className="ml-1 text-xs font-semibold text-slate-500">{unit}</span>}
            </p>
          </div>
        </div>
        {badge && (
          <span className={`rounded border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wide ${s.badge}`}>
            {badge}
          </span>
        )}
      </div>

      {typeof progress === 'number' && (
        <div
          className="mt-2.5 h-1.5 w-full overflow-hidden rounded bg-slate-100"
          role="progressbar"
          aria-valuenow={Math.round(progress * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${label} utilization`}
        >
          <div className={`h-full rounded-xs ${s.bar}`} style={{ width: `${Math.min(100, progress * 100)}%` }} />
        </div>
      )}

      {(subtext || trend) && (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-1 text-xs text-slate-500">
          {subtext && <span>{subtext}</span>}
          {trend && <span className="font-mono font-semibold text-slate-700">{trend}</span>}
        </div>
      )}
    </section>
  );
};

