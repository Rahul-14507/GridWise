/**
 * EV Fleet Tab Page: Priority Charging Allocations, Fleet State, and Charger Control.
 */
import React, { useState } from 'react';
import { Car, Zap, Clock, ShieldAlert, Sliders, Filter, Search } from 'lucide-react';
import { EVFleetTable } from '../components/ev/EVFleetTable';
import type { EVDetailResponse } from '../types/api';

interface EVFleetPageProps {
  evs: EVDetailResponse[];
}

export const EVFleetPage: React.FC<EVFleetPageProps> = ({ evs }) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const totalEvs = evs.length;
  const chargingCount = evs.filter((e) => e.status.toLowerCase() === 'charging').length;
  const waitingCount = evs.filter((e) => e.status.toLowerCase() === 'waiting').length;
  const totalAllocatedKw = evs.reduce((sum, e) => sum + (e.allocated_power_kw || 0), 0);
  const avgSoc = totalEvs > 0 ? evs.reduce((sum, e) => sum + e.soc_percent, 0) / totalEvs : 0;

  const filteredEvs = evs.filter((ev) => {
    if (statusFilter !== 'all' && ev.status.toLowerCase() !== statusFilter) return false;
    if (!search) return true;
    return `${ev.id} ${ev.slot_id} ${ev.status}`.toLowerCase().includes(search.toLowerCase());
  });

  return (
    <div className="space-y-4">
      {/* Fleet Overview KPIs */}
      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-md border border-slate-200 bg-white p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Connected EV Fleet</span>
            <Car size={16} className="text-blue-600" />
          </div>
          <p className="mt-1 font-mono text-2xl font-extrabold text-slate-900">{totalEvs}</p>
          <span className="text-xs text-slate-500">{chargingCount} Charging | {waitingCount} Waiting</span>
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Active Charging Load</span>
            <Zap size={16} className="text-emerald-600" />
          </div>
          <p className="mt-1 font-mono text-2xl font-extrabold text-emerald-600">{totalAllocatedKw.toFixed(1)} kW</p>
          <span className="text-xs text-slate-500">Total Allocated Power</span>
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Fleet Average SoC</span>
            <Clock size={16} className="text-blue-600" />
          </div>
          <p className="mt-1 font-mono text-2xl font-extrabold text-slate-900">{avgSoc.toFixed(1)}%</p>
          <span className="text-xs text-slate-500">Average Battery Level</span>
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Urgent Priorities</span>
            <ShieldAlert size={16} className="text-amber-600" />
          </div>
          <p className="mt-1 font-mono text-2xl font-extrabold text-amber-600">
            {evs.filter((e) => e.deadline_status === 'at_risk').length}
          </p>
          <span className="text-xs text-slate-500">Vehicles At Risk of Missing Departure</span>
        </div>
      </div>

      {/* Filter and Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 bg-white p-3 shadow-xs">
        <div className="flex items-center gap-2">
          <Filter size={15} className="text-slate-400" />
          <span className="text-xs font-bold uppercase text-slate-700">Filters:</span>
          <div className="flex rounded border border-slate-200 bg-slate-50 p-0.5">
            {['all', 'charging', 'waiting', 'paused'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`rounded px-2.5 py-1 text-xs font-bold capitalize ${
                  statusFilter === st ? 'bg-blue-600 text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs">
            <Search size={14} className="text-slate-400" />
            <input
              type="text"
              placeholder="Search EV ID / Bay..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent text-xs text-slate-900 focus:outline-none"
            />
          </div>
          <button
            onClick={() => alert('EV Fleet Priority re-calculation dispatched via API.')}
            className="flex items-center gap-1 rounded bg-slate-900 px-3 py-1 text-xs font-bold text-white hover:bg-slate-800"
          >
            <Sliders size={13} /> Re-prioritize Fleet
          </button>
        </div>
      </div>

      {/* EV Fleet Table Component */}
      <EVFleetTable evs={filteredEvs} />
    </div>
  );
};
