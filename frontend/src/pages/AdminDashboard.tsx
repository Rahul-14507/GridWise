import React from 'react';
import { useSystemState } from '../hooks/useSystemState';
import { Header } from '../components/layout/Header';
import { InfrastructureOverview } from '../components/infrastructure/InfrastructureOverview';
import { TransformerSafety } from '../components/infrastructure/TransformerSafety';
import { SolarSubsystem } from '../components/energy/SolarSubsystem';
import { EnergyFlow } from '../components/energy/EnergyFlow';
import { BatteryStatus } from '../components/battery/BatteryStatus';
import { EVFleetTable } from '../components/ev/EVFleetTable';
import { ParkingOverview } from '../components/parking/ParkingOverview';
import { OptimizationStatus } from '../components/optimization/OptimizationStatus';
import { WarningsPanel } from '../components/warnings/WarningsPanel';
import { RealtimeCharts } from '../components/charts/RealtimeCharts';
import { AlertOctagon, RefreshCw } from 'lucide-react';

export const AdminDashboard: React.FC = () => {
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
  } = useSystemState(3000);

  // Initial loading state
  if (isLoading && !summary) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <h2 className="text-lg font-semibold text-foreground">Loading GridWise Telemetry...</h2>
        <p className="text-sm text-muted">Establishing live session with backend API...</p>
      </div>
    );
  }

  // Disconnected / Unreachable Error banner
  const hasError = error !== null && summary === null;

  if (hasError) {
    return (
      <div className="dashboard-container">
        <Header
          summary={summary}
          status={status}
          lastUpdated={lastUpdated}
          isStale={true}
          isLoading={isLoading}
          isOptimizing={isOptimizing}
          isApplying={isApplying}
          isTicking={isTicking}
          onRefresh={refresh}
          onRunOptimization={runOptimization}
          onApplyOptimization={applyOptimization}
          onTriggerTick={triggerTick}
        />
        <div className="error-banner">
          <AlertOctagon size={28} className="text-danger flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-bold text-base">Backend Connection Unavailable</h3>
            <p className="text-sm text-muted mt-0.5">
              Unable to reach the GridWise backend at <code>{import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}</code>.
            </p>
            <p className="text-xs text-muted mt-1">Error: {error}</p>
          </div>
          <button onClick={refresh} className="btn btn-primary btn-sm">
            <RefreshCw size={14} /> Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const warnings = summary?.warnings || status?.warnings || [];

  return (
    <div className="dashboard-container">
      {/* Header Bar */}
      <Header
        summary={summary}
        status={status}
        lastUpdated={lastUpdated}
        isStale={isStale}
        isLoading={isLoading}
        isOptimizing={isOptimizing}
        isApplying={isApplying}
        isTicking={isTicking}
        onRefresh={refresh}
        onRunOptimization={runOptimization}
        onApplyOptimization={applyOptimization}
        onTriggerTick={triggerTick}
      />

      {/* Main Content Layout */}
      <main className="dashboard-main space-y-4">
        {/* Top: Warnings / System Alerts */}
        <WarningsPanel warnings={warnings} />

        {/* Primary Row 1: Infrastructure Overview KPIs */}
        <InfrastructureOverview energy={energy} summary={summary?.energy || null} />

        {/* Primary Row 2: Active EV Fleet Table & Allocations */}
        <EVFleetTable evs={evs} />

        {/* Primary Row 3: Energy Intelligence & Solar & Safety */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1">
            <SolarSubsystem
              energy={energy}
              rainDetected={false}
              rainIntensity={0.0}
            />
          </div>
          <div className="lg:col-span-1">
            <TransformerSafety
              energy={energy}
              ambientTempC={25.0}
              thermalStatus="NORMAL"
            />
          </div>
          <div className="lg:col-span-1">
            <ParkingOverview parking={summary?.parking || null} />
          </div>
        </div>

        {/* Primary Row 4: Energy Flow & Battery Status */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <EnergyFlow energy={energy} evs={evs} />
          <OptimizationStatus optimization={optimization} />
        </div>

        {/* Primary Row 5: Battery Subsystem */}
        <BatteryStatus battery={summary?.battery || null} energy={energy} />

        {/* Primary Row 6: Real-Time Telemetry Charts */}
        <RealtimeCharts history={history} />
      </main>

      {/* Footer */}
      <footer className="dashboard-footer">
        <p>GridWise Smart EV Charging Management System — Real-Time Admin Telemetry & Optimization Dashboard</p>
      </footer>
    </div>
  );
};
