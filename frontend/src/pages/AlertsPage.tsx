/**
 * Alerts Tab Page: Operational Log & Fault History Console.
 * Filter by Severity (All, Critical, Warning, Info), Substation/Node, and Date Range.
 */
import React, { useState } from 'react';
import { AlertTriangle, OctagonX, CheckCircle2, ShieldAlert, Filter, Search, Eye } from 'lucide-react';
import type { SystemWarning } from '../types/api';

interface AlertsPageProps {
  warnings: SystemWarning[];
}

interface AlertLogEntry {
  id: string;
  timestamp: string;
  node: string;
  substation: string;
  severity: 'critical' | 'warning' | 'info';
  event: string;
  impact: string;
  status: 'Active' | 'Acknowledged' | 'Cleared';
}

const HISTORICAL_ALERTS: AlertLogEntry[] = [
  {
    id: 'ALT-8092',
    timestamp: '2026-09-18 14:28:10',
    node: 'TR-02',
    substation: 'North Substation',
    severity: 'warning',
    event: 'Thermal Derating Warning (Ambient 38.5 C)',
    impact: '-10.0 kW Capacity Reduction',
    status: 'Active',
  },
  {
    id: 'ALT-8089',
    timestamp: '2026-09-18 14:15:22',
    node: 'PV-01',
    substation: 'Solar PV Array',
    severity: 'info',
    event: 'Cloud Cover Overcast Ingress',
    impact: 'Solar generation down to 12.5 kW',
    status: 'Acknowledged',
  },
  {
    id: 'ALT-8085',
    timestamp: '2026-09-18 13:50:00',
    node: 'BAY-02',
    substation: 'EV Hub Alpha',
    severity: 'warning',
    event: 'High Priority Vehicle Arrival (EV-002)',
    impact: 'Re-allocation required for urgent departure',
    status: 'Active',
  },
  {
    id: 'ALT-8071',
    timestamp: '2026-09-18 12:30:15',
    node: 'FDR-04',
    substation: 'North Substation',
    severity: 'critical',
    event: 'Feeder Phase Imbalance Constraint',
    impact: 'Feeder current exceeded 420A limit',
    status: 'Cleared',
  },
  {
    id: 'ALT-8060',
    timestamp: '2026-09-18 11:10:04',
    node: 'BAT-01',
    substation: 'BESS Buffer Substation',
    severity: 'info',
    event: 'BESS Pre-charge Cycle Complete',
    impact: 'Reserve SoC at 75.0%',
    status: 'Cleared',
  },
];

export const AlertsPage: React.FC<AlertsPageProps> = ({ warnings }) => {
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'warning' | 'info'>('all');
  const [query, setQuery] = useState('');
  const [ackedIds, setAckedIds] = useState<Set<string>>(new Set());

  // Merge live warnings with historical alerts
  const liveLogEntries: AlertLogEntry[] = warnings.map((w, idx) => ({
    id: `LIVE-${w.code}-${idx}`,
    timestamp: 'Just now (Live)',
    node: w.code.includes('TRANSFORMER') ? 'TR-02' : w.code.includes('SOLAR') ? 'PV-01' : 'SUB-01',
    substation: 'North Substation',
    severity: (w.severity as 'critical' | 'warning' | 'info') || 'warning',
    event: w.message,
    impact: 'Real-time grid constraint active',
    status: ackedIds.has(`LIVE-${w.code}-${idx}`) ? 'Acknowledged' : 'Active',
  }));

  const allEntries = [...liveLogEntries, ...HISTORICAL_ALERTS];

  const filteredEntries = allEntries.filter((e) => {
    if (severityFilter !== 'all' && e.severity !== severityFilter) return false;
    if (!query) return true;
    return `${e.id} ${e.node} ${e.substation} ${e.event} ${e.impact}`.toLowerCase().includes(query.toLowerCase());
  });

  const toggleAck = (id: string) => {
    setAckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const criticalCount = allEntries.filter((e) => e.severity === 'critical' && e.status === 'Active').length;
  const warningCount = allEntries.filter((e) => e.severity === 'warning' && e.status === 'Active').length;

  return (
    <div className="space-y-4">
      {/* Alert KPI Summary Bar */}
      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-md border border-slate-200 bg-white p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Active Faults & Alerts</span>
            <ShieldAlert size={16} className="text-blue-600" />
          </div>
          <p className="mt-1 font-mono text-2xl font-extrabold text-slate-900">{allEntries.filter((e) => e.status === 'Active').length}</p>
          <span className="text-xs text-slate-500">Requiring Operator Attention</span>
        </div>

        <div className="rounded-md border border-red-200 bg-red-50/50 p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-red-700">Critical Faults</span>
            <OctagonX size={16} className="text-red-600" />
          </div>
          <p className="mt-1 font-mono text-2xl font-extrabold text-red-600">{criticalCount}</p>
          <span className="text-xs text-red-700 font-semibold">Immediate Action Required</span>
        </div>

        <div className="rounded-md border border-amber-200 bg-amber-50/50 p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-800">Warnings</span>
            <AlertTriangle size={16} className="text-amber-600" />
          </div>
          <p className="mt-1 font-mono text-2xl font-extrabold text-amber-700">{warningCount}</p>
          <span className="text-xs text-amber-800 font-semibold">Grid Constraints Active</span>
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Acknowledged</span>
            <CheckCircle2 size={16} className="text-emerald-600" />
          </div>
          <p className="mt-1 font-mono text-2xl font-extrabold text-slate-900">
            {allEntries.filter((e) => e.status === 'Acknowledged').length}
          </p>
          <span className="text-xs text-slate-500">Logged & Monitored</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 bg-white p-3 shadow-xs">
        <div className="flex items-center gap-2">
          <Filter size={15} className="text-slate-400" />
          <span className="text-xs font-bold uppercase text-slate-700">Severity Filter:</span>
          <div className="flex rounded border border-slate-200 bg-slate-50 p-0.5">
            {(['all', 'critical', 'warning', 'info'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`rounded px-2.5 py-1 text-xs font-bold capitalize ${
                  severityFilter === sev
                    ? sev === 'critical'
                      ? 'bg-red-600 text-white'
                      : sev === 'warning'
                      ? 'bg-amber-600 text-white'
                      : 'bg-blue-600 text-white'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs">
            <Search size={14} className="text-slate-400" />
            <input
              type="text"
              placeholder="Search alert ID / node / event..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-48 bg-transparent text-xs text-slate-900 focus:outline-none"
            />
          </div>
          <button
            onClick={() => {
              allEntries.forEach((e) => toggleAck(e.id));
              alert('All active alerts acknowledged.');
            }}
            className="rounded border border-slate-300 bg-white px-3 py-1 text-xs font-bold text-slate-700 hover:bg-slate-50"
          >
            Ack All Active
          </button>
        </div>
      </div>

      {/* Alert & Fault History Table */}
      <div className="rounded-md border border-slate-200 bg-white p-4 shadow-xs">
        <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-900 mb-3">
          <AlertTriangle size={16} className="text-blue-600" /> Operational Alert & Fault History Log ({filteredEntries.length})
        </h3>

        <div className="overflow-x-auto slim-scroll">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-extrabold uppercase text-slate-600">
                <th className="px-3 py-2.5">Timestamp</th>
                <th className="px-3 py-2.5">Alert ID</th>
                <th className="px-3 py-2.5">Asset / Node</th>
                <th className="px-3 py-2.5">Severity</th>
                <th className="px-3 py-2.5">Event Description</th>
                <th className="px-3 py-2.5">Operational Impact</th>
                <th className="px-3 py-2.5">Status</th>
                <th className="px-3 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredEntries.map((e) => {
                const isAcked = e.status === 'Acknowledged' || ackedIds.has(e.id);
                return (
                  <tr
                    key={e.id}
                    className={`border-b border-slate-100 hover:bg-slate-50 ${
                      e.severity === 'critical' ? 'bg-red-50/30' : e.severity === 'warning' ? 'bg-amber-50/20' : ''
                    }`}
                  >
                    <td className="px-3 py-2.5 font-mono text-slate-600">{e.timestamp}</td>
                    <td className="px-3 py-2.5 font-mono font-bold text-slate-900">{e.id}</td>
                    <td className="px-3 py-2.5 font-bold text-slate-800">
                      {e.node} <span className="font-normal text-slate-500">({e.substation})</span>
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] font-extrabold uppercase ${
                          e.severity === 'critical'
                            ? 'border-red-300 bg-red-100 text-red-700'
                            : e.severity === 'warning'
                            ? 'border-amber-300 bg-amber-100 text-amber-800'
                            : 'border-blue-300 bg-blue-50 text-blue-700'
                        }`}
                      >
                        {e.severity === 'critical' ? <OctagonX size={10} /> : <AlertTriangle size={10} />}
                        {e.severity}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 font-semibold text-slate-900">{e.event}</td>
                    <td className="px-3 py-2.5 text-slate-600">{e.impact}</td>
                    <td className="px-3 py-2.5">
                      <span
                        className={`rounded px-2 py-0.5 font-bold ${
                          isAcked
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : e.status === 'Cleared'
                            ? 'bg-slate-100 text-slate-600'
                            : 'bg-amber-100 text-amber-800 border border-amber-300'
                        }`}
                      >
                        {isAcked ? 'Acknowledged' : e.status}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => toggleAck(e.id)}
                          className={`rounded border px-2 py-1 font-bold ${
                            isAcked
                              ? 'border-blue-300 bg-blue-50 text-blue-700'
                              : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                          }`}
                        >
                          <CheckCircle2 size={12} className="inline mr-1" /> {isAcked ? 'Acked' : 'Ack'}
                        </button>
                        <button
                          onClick={() => alert(`Inspecting asset ${e.node} in SCADA topology view.`)}
                          className="rounded border border-slate-300 bg-white px-2 py-1 font-bold text-slate-700 hover:bg-slate-50"
                        >
                          <Eye size={12} className="inline mr-1" /> Inspect
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
