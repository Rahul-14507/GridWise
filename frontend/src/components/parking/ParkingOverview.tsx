import React from 'react';
import { SquareParking } from 'lucide-react';
import { ParkingSummary } from '../../types/api';

interface ParkingOverviewProps {
  parking: ParkingSummary | null;
}

export const ParkingOverview: React.FC<ParkingOverviewProps> = ({ parking }) => {
  const total = parking?.total_slots ?? 4;
  const occupied = parking?.occupied_slots ?? 0;
  const available = parking?.available_slots ?? total - occupied;
  const occupancyPercent = total > 0 ? (occupied / total) * 100 : 0;

  return (
    <div className="subcard">
      <div className="flex justify-between items-center mb-2">
        <h3 className="subcard-title flex items-center gap-1.5">
          <SquareParking size={16} className="text-primary" />
          Charging Bay Occupancy
        </h3>
        <span className="text-xs text-muted">Simulated Status</span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="stat-box">
          <span className="stat-label">Total Bays</span>
          <span className="stat-val">{total}</span>
        </div>

        <div className="stat-box">
          <span className="stat-label">Occupied</span>
          <span className="stat-val font-semibold text-primary">{occupied}</span>
        </div>

        <div className="stat-box">
          <span className="stat-label">Available</span>
          <span className="stat-val text-success font-semibold">{available}</span>
        </div>
      </div>

      <div className="progress-bar-bg mt-2.5">
        <div
          className="progress-bar-fill progress-primary"
          style={{ width: `${occupancyPercent}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-muted mt-1">
        <span>{occupancyPercent.toFixed(0)}% Occupancy</span>
        <span>{available} Bays Vacant</span>
      </div>
    </div>
  );
};
