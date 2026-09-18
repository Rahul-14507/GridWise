import React from 'react';
import { Thermometer } from 'lucide-react';
import { EnergyDetailResponse } from '../../types/api';

interface TransformerSafetyProps {
  energy: EnergyDetailResponse | null;
  ambientTempC?: number;
  thermalStatus?: string;
}

export const TransformerSafety: React.FC<TransformerSafetyProps> = ({
  energy,
  ambientTempC = 25.0,
  thermalStatus = 'NORMAL',
}) => {
  const baseCap = energy?.base_grid_capacity_kw || 25.0;
  const effCap = energy?.effective_grid_capacity_kw || 25.0;
  const isDerated = effCap < baseCap;
  const deratedKw = Math.max(0, baseCap - effCap);

  return (
    <div className="subcard">
      <div className="flex justify-between items-center mb-2">
        <h3 className="subcard-title flex items-center gap-1.5">
          <Thermometer size={16} className="text-warning" />
          Thermal & Interconnection Safety
        </h3>
        <span className={`status-pill ${thermalStatus === 'CRITICAL' ? 'status-pill-danger' : thermalStatus === 'ELEVATED' ? 'status-pill-warning' : 'status-pill-success'}`}>
          {thermalStatus.toUpperCase()}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="stat-box">
          <span className="stat-label">Ambient Temperature</span>
          <span className="stat-val">{ambientTempC.toFixed(1)} °C</span>
        </div>

        <div className="stat-box">
          <span className="stat-label">Thermal Derating</span>
          <span className={`stat-val ${isDerated ? 'text-warning font-semibold' : 'text-success'}`}>
            {isDerated ? `-${deratedKw.toFixed(1)} kW` : 'None (Active)'}
          </span>
        </div>
      </div>

      <p className="micro-note mt-2">
        * Modelled transformer capacity constraint calculated dynamically from ambient ambient temperature and thermal dissipation limits.
      </p>
    </div>
  );
};
