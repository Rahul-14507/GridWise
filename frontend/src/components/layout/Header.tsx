import React from 'react';
import {
  Zap,
  Activity,
  AlertTriangle,
  RefreshCw,
  Play,
  CheckCircle,
  Sliders,
  Cpu,
  Clock,
} from 'lucide-react';
import { SystemStatusResponse, SystemSummaryResponse } from '../../types/api';

interface HeaderProps {
  summary: SystemSummaryResponse | null;
  status: SystemStatusResponse | null;
  lastUpdated: Date | null;
  isStale: boolean;
  isLoading: boolean;
  isOptimizing: boolean;
  isApplying: boolean;
  isTicking: boolean;
  onRefresh: () => void;
  onRunOptimization: () => void;
  onApplyOptimization: () => void;
  onTriggerTick: (seconds?: number) => void;
}

export const Header: React.FC<HeaderProps> = ({
  summary,
  status,
  lastUpdated,
  isStale,
  isLoading,
  isOptimizing,
  isApplying,
  isTicking,
  onRefresh,
  onRunOptimization,
  onApplyOptimization,
  onTriggerTick,
}) => {
  const dataSource = summary?.data_source || status?.data_source || 'simulation';
  const systemStatus = summary?.system_status || status?.status || 'operational';

  const formatRelativeTime = (date: Date | null): string => {
    if (!date) return 'Never';
    const seconds = Math.max(0, Math.floor((new Date().getTime() - date.getTime()) / 1000));
    if (seconds < 5) return 'just now';
    if (seconds < 60) return `${seconds}s ago`;
    const mins = Math.floor(seconds / 60);
    return `${mins}m ${seconds % 60}s ago`;
  };

  const getStatusBadge = () => {
    switch (systemStatus) {
      case 'operational':
        return (
          <span className="badge badge-success">
            <CheckCircle size={14} className="mr-1" /> OPERATIONAL
          </span>
        );
      case 'warning':
        return (
          <span className="badge badge-warning">
            <AlertTriangle size={14} className="mr-1" /> WARNING
          </span>
        );
      case 'degraded':
        return (
          <span className="badge badge-danger">
            <AlertTriangle size={14} className="mr-1" /> DEGRADED
          </span>
        );
      default:
        return (
          <span className="badge badge-neutral">
            <Activity size={14} className="mr-1" /> NO DATA
          </span>
        );
    }
  };

  return (
    <header className="header-container">
      <div className="header-brand">
        <div className="logo-icon">
          <Zap size={22} className="text-primary" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="header-title">GRIDWISE</h1>
            <span className="admin-tag">ADMIN</span>
          </div>
          <p className="header-subtitle">Smart EV Charging Management System</p>
        </div>
      </div>

      <div className="header-meta">
        {/* Operating Mode */}
        <div className="meta-card">
          <span className="meta-label">Operating Mode</span>
          <span className={`mode-badge ${dataSource === 'hardware' ? 'mode-hardware' : 'mode-simulation'}`}>
            <Cpu size={13} className="mr-1" />
            {dataSource.toUpperCase()}
          </span>
        </div>

        {/* System Health */}
        <div className="meta-card">
          <span className="meta-label">System Health</span>
          {getStatusBadge()}
        </div>

        {/* Data Stream Freshness */}
        <div className="meta-card">
          <span className="meta-label">Telemetry Stream</span>
          <div className="flex items-center gap-1.5">
            <span className={`pulse-dot ${isStale ? 'pulse-stale' : 'pulse-live'}`} />
            <span className="stream-text">{isStale ? 'STALE' : 'LIVE'}</span>
            <span className="timestamp-text">({formatRelativeTime(lastUpdated)})</span>
          </div>
        </div>
      </div>

      {/* Action Controls */}
      <div className="header-actions">
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="btn btn-secondary btn-sm"
          title="Manual refresh"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>

        {dataSource === 'simulation' && (
          <>
            <button
              onClick={() => onTriggerTick(60)}
              disabled={isTicking}
              className="btn btn-secondary btn-sm"
              title="Advance simulation by 60 seconds"
            >
              <Clock size={14} className={isTicking ? 'animate-spin' : ''} />
              <span>Step +60s</span>
            </button>

            <button
              onClick={onRunOptimization}
              disabled={isOptimizing}
              className="btn btn-primary btn-sm"
              title="Run ChargingOptimizer decision cycle"
            >
              <Sliders size={14} className={isOptimizing ? 'animate-spin' : ''} />
              <span>{isOptimizing ? 'Optimizing...' : 'Optimize'}</span>
            </button>

            <button
              onClick={onApplyOptimization}
              disabled={isApplying}
              className="btn btn-accent btn-sm"
              title="Apply computed allocations to simulation"
            >
              <Play size={14} className={isApplying ? 'animate-spin' : ''} />
              <span>{isApplying ? 'Applying...' : 'Apply Allocations'}</span>
            </button>
          </>
        )}
      </div>
    </header>
  );
};
