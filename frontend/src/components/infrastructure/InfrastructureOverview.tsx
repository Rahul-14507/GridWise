import React from 'react';
import { Zap, ShieldCheck, Gauge, ArrowDownUp } from 'lucide-react';
import { EnergyDetailResponse, EnergySummary } from '../../types/api';

interface InfrastructureOverviewProps {
  energy: EnergyDetailResponse | null;
  summary: EnergySummary | null;
}

export const InfrastructureOverview: React.FC<InfrastructureOverviewProps> = ({ energy, summary }) => {
  const totalDemand = energy ? energy.infrastructure_load_kw : summary ? summary.building_demand_kw + summary.available_ev_power_kw : 0;
  const effectiveCapacity = energy ? energy.effective_grid_capacity_kw : summary ? summary.effective_capacity_kw : 25.0;
  const availableEvPower = energy ? energy.available_ev_charging_power_kw : summary ? summary.available_ev_power_kw : 0;
  const baseCapacity = energy ? energy.base_grid_capacity_kw : summary ? summary.grid_capacity_kw : 25.0;

  const utilization = effectiveCapacity > 0 ? (totalDemand / effectiveCapacity) * 100 : 0;

  const getUtilizationColor = (util: number) => {
    if (util >= 90) return 'text-danger bg-danger-subtle';
    if (util >= 75) return 'text-warning bg-warning-subtle';
    return 'text-success bg-success-subtle';
  };

  const getProgressColor = (util: number) => {
    if (util >= 90) return 'progress-danger';
    if (util >= 75) return 'progress-warning';
    return 'progress-success';
  };

  return (
    <div className="section-card">
      <div className="section-header">
        <h2 className="section-title">
          <Gauge size={18} className="text-primary" />
          Infrastructure & Power Headroom
        </h2>
        <span className="text-xs text-muted">Authoritative Grid Interconnection</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-3">
        {/* Card 1: Total Demand */}
        <div className="kpi-card">
          <div className="kpi-icon bg-primary-subtle text-primary">
            <Zap size={20} />
          </div>
          <div>
            <span className="kpi-label">Total Facility Load</span>
            <div className="kpi-value">{totalDemand.toFixed(1)} <span className="kpi-unit">kW</span></div>
            <span className="kpi-subtext">Building + Active EV Fleet</span>
          </div>
        </div>

        {/* Card 2: Effective Capacity */}
        <div className="kpi-card">
          <div className="kpi-icon bg-info-subtle text-info">
            <ShieldCheck size={20} />
          </div>
          <div>
            <span className="kpi-label">Effective Grid Capacity</span>
            <div className="kpi-value">{effectiveCapacity.toFixed(1)} <span className="kpi-unit">kW</span></div>
            <span className="kpi-subtext">
              {effectiveCapacity < baseCapacity ? `Derated from ${baseCapacity.toFixed(1)} kW` : `Nominal 100% capacity`}
            </span>
          </div>
        </div>

        {/* Card 3: Available EV Power */}
        <div className="kpi-card">
          <div className="kpi-icon bg-success-subtle text-success">
            <ArrowDownUp size={20} />
          </div>
          <div>
            <span className="kpi-label">Available EV Power</span>
            <div className="kpi-value text-success">{availableEvPower.toFixed(1)} <span className="kpi-unit">kW</span></div>
            <span className="kpi-subtext">Net Headroom for Charging</span>
          </div>
        </div>

        {/* Card 4: Infrastructure Utilization */}
        <div className="kpi-card">
          <div className={`kpi-icon ${getUtilizationColor(utilization)}`}>
            <Gauge size={20} />
          </div>
          <div className="w-full">
            <div className="flex justify-between items-baseline">
              <span className="kpi-label">Infrastructure Load</span>
              <span className="kpi-percentage">{utilization.toFixed(1)}%</span>
            </div>
            <div className="progress-bar-bg mt-1">
              <div
                className={`progress-bar-fill ${getProgressColor(utilization)}`}
                style={{ width: `${Math.min(100, Math.max(0, utilization))}%` }}
              />
            </div>
            <span className="kpi-subtext mt-1 block">
              {utilization >= 90 ? 'High Utilization / Near Constraint' : 'Operating within safe limits'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
