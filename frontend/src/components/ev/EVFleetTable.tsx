import React from 'react';
import { Car, Clock, Zap, CheckCircle2, PauseCircle } from 'lucide-react';
import { EVDetailResponse } from '../../types/api';

interface EVFleetTableProps {
  evs: EVDetailResponse[];
}

export const EVFleetTable: React.FC<EVFleetTableProps> = ({ evs }) => {
  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'charging':
        return <span className="badge badge-success"><Zap size={12} className="mr-1" /> CHARGING</span>;
      case 'waiting':
        return <span className="badge badge-warning"><Clock size={12} className="mr-1" /> WAITING</span>;
      case 'paused':
        return <span className="badge badge-neutral"><PauseCircle size={12} className="mr-1" /> PAUSED</span>;
      case 'completed':
        return <span className="badge badge-info"><CheckCircle2 size={12} className="mr-1" /> COMPLETED</span>;
      default:
        return <span className="badge badge-neutral">{status.toUpperCase()}</span>;
    }
  };

  const getDeadlineBadge = (deadline: string | null) => {
    if (!deadline) return <span className="text-muted text-xs">N/A</span>;
    switch (deadline.toLowerCase()) {
      case 'feasible':
        return <span className="badge badge-success text-xs">FEASIBLE</span>;
      case 'at_risk':
        return <span className="badge badge-danger text-xs">AT RISK</span>;
      case 'expired':
        return <span className="badge badge-danger text-xs">EXPIRED</span>;
      case 'complete':
        return <span className="badge badge-info text-xs">COMPLETE</span>;
      default:
        return <span className="badge badge-neutral text-xs">{deadline}</span>;
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const formatRemainingMinutes = (mins: number) => {
    if (mins <= 0) return 'Past departure';
    const hours = Math.floor(mins / 60);
    const remainder = Math.floor(mins % 60);
    if (hours === 0) return `${remainder}m remaining`;
    return `${hours}h ${remainder}m remaining`;
  };

  return (
    <div className="section-card">
      <div className="section-header">
        <h2 className="section-title">
          <Car size={18} className="text-primary" />
          Connected EV Fleet & Priority Charging Allocations
        </h2>
        <span className="text-xs text-muted">
          {evs.filter((e) => e.status.toLowerCase() === 'charging').length} of {evs.length} actively charging
        </span>
      </div>

      {evs.length === 0 ? (
        <div className="empty-state">
          <Car size={32} className="text-muted mb-2" />
          <p>No electric vehicles connected to charging bays.</p>
        </div>
      ) : (
        <div className="table-responsive mt-3">
          <table className="data-table">
            <thead>
              <tr>
                <th>Vehicle & Bay</th>
                <th>Status</th>
                <th>State of Charge (Current to Target)</th>
                <th>Charging Rate</th>
                <th>Departure & Time</th>
                <th>Required Avg Power</th>
                <th>Priority Score</th>
                <th>Deadline Status</th>
              </tr>
            </thead>
            <tbody>
              {evs.map((ev) => {
                const isCharging = ev.status.toLowerCase() === 'charging' && ev.allocated_power_kw > 0;
                return (
                  <tr key={ev.id} className={ev.deadline_status === 'at_risk' ? 'row-warning' : ''}>
                    {/* Vehicle & Bay */}
                    <td>
                      <div className="font-semibold text-sm">{ev.id}</div>
                      <div className="text-xs text-muted">{ev.slot_id || 'Unassigned Slot'}</div>
                    </td>

                    {/* Status */}
                    <td>{getStatusBadge(ev.status)}</td>

                    {/* SoC with Target Pin */}
                    <td className="min-w-[160px]">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-semibold">{ev.soc_percent.toFixed(0)}%</span>
                        <span className="text-muted">Target: {ev.target_soc_percent.toFixed(0)}%</span>
                      </div>
                      <div className="relative progress-bar-bg h-2">
                        {/* Current SoC fill */}
                        <div
                          className="progress-bar-fill progress-primary h-full rounded"
                          style={{ width: `${Math.min(100, Math.max(0, ev.soc_percent))}%` }}
                        />
                        {/* Target pin marker */}
                        <div
                          className="absolute top-0 bottom-0 w-1 bg-amber-500 z-10"
                          style={{ left: `${Math.min(99, Math.max(0, ev.target_soc_percent))}%` }}
                          title={`Target SoC: ${ev.target_soc_percent}%`}
                        />
                      </div>
                      <div className="text-[10px] text-muted mt-0.5">
                        Deficit: {ev.energy_required_kwh.toFixed(1)} kWh
                      </div>
                    </td>

                    {/* Charging Rate */}
                    <td>
                      <div className={`rate-badge ${isCharging ? 'rate-active' : 'rate-inactive'}`}>
                        <Zap size={13} className="mr-1 inline" />
                        <span className="font-bold text-sm">{ev.allocated_power_kw.toFixed(1)}</span>
                        <span className="text-xs font-normal"> / {ev.max_charging_power_kw.toFixed(1)} kW</span>
                      </div>
                    </td>

                    {/* Departure & Time */}
                    <td>
                      <div className="text-xs font-medium">{formatTime(ev.departure_time)}</div>
                      <div className="text-[11px] text-muted">{formatRemainingMinutes(ev.remaining_time_minutes)}</div>
                    </td>

                    {/* Required Avg Power */}
                    <td>
                      <div className="text-xs font-semibold">{ev.required_average_power_kw.toFixed(1)} kW</div>
                      <div className="text-[10px] text-muted">to meet departure</div>
                    </td>

                    {/* Priority Score */}
                    <td>
                      {ev.priority_score !== null ? (
                        <div>
                          <span className="priority-val font-mono font-semibold text-xs">
                            {ev.priority_score.toFixed(2)}
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted text-xs">N/A</span>
                      )}
                    </td>

                    {/* Deadline Status */}
                    <td>
                      {getDeadlineBadge(ev.deadline_status)}
                      {ev.reason && (
                        <div className="text-[10px] text-muted truncate max-w-[140px]" title={ev.reason}>
                          {ev.reason}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
