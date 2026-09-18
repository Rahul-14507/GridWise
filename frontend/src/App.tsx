import React, { useEffect, useState } from 'react';
import { AdminDashboard } from './pages/AdminDashboard';
import { LiveMQTTMonitorPage } from './pages/LiveMQTTMonitorPage';
import { KioskQRStationPage } from './pages/kiosk/KioskQRStationPage';
import { DriverLiveStatusPage } from './pages/driver/DriverLiveStatusPage';
import { LayoutDashboard, QrCode, Radio, Zap } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'mqtt' | 'kiosk'>('dashboard');
  const [isDriverPortal, setIsDriverPortal] = useState<boolean>(false);
  const [activeSessionId, setActiveSessionId] = useState<string>('');

  // Check URL query parameters on load (e.g. ?view=driver&session=QR-XXXX from mobile scan)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const viewParam = params.get('view');
    const sessionParam = params.get('session');

    if (sessionParam) {
      setActiveSessionId(sessionParam);
    }

    if (viewParam === 'driver') {
      setIsDriverPortal(true);
    } else if (viewParam === 'kiosk') {
      setActiveTab('kiosk');
    } else if (viewParam === 'mqtt') {
      setActiveTab('mqtt');
    }
  }, []);

  const handleOpenDriverView = (sessionId: string) => {
    setActiveSessionId(sessionId);
    setIsDriverPortal(true);
  };

  // 1. ISOLATED MOBILE DRIVER VIEW: No admin navbar, no access to other portals
  if (isDriverPortal) {
    return (
      <div style={{ minHeight: '100vh', background: '#090d16', display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '0.75rem' }}>
        <DriverLiveStatusPage sessionId={activeSessionId} />
      </div>
    );
  }

  // 2. ADMIN & KIOSK PORTAL VIEW
  return (
    <div className="dashboard-container">
      {/* Top Global Navigation Bar for Admins & Operators */}
      <nav className="top-navbar">
        <div className="flex items-center gap-2">
          <div className="logo-icon">
            <Zap size={18} className="text-primary" />
          </div>
          <span className="nav-brand-tag">GridWise Control Hub</span>
        </div>

        <div className="nav-tabs">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`nav-tab ${activeTab === 'dashboard' ? 'nav-tab-active' : ''}`}
          >
            <LayoutDashboard size={14} />
            <span>Admin Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab('mqtt')}
            className={`nav-tab nav-tab-mqtt ${activeTab === 'mqtt' ? 'nav-tab-active' : ''}`}
          >
            <Radio size={14} className={activeTab === 'mqtt' ? 'animate-pulse text-cyan-300' : ''} />
            <span>Live ESP32 MQTT</span>
          </button>

          <button
            onClick={() => setActiveTab('kiosk')}
            className={`nav-tab ${activeTab === 'kiosk' ? 'nav-tab-active' : ''}`}
          >
            <QrCode size={14} style={{ color: activeTab === 'kiosk' ? '#ffffff' : '#38bdf8' }} />
            <span>Driver QR Station</span>
          </button>
        </div>
      </nav>

      {/* Main Tab Content */}
      <main className="dashboard-main">
        {activeTab === 'dashboard' && (
          <AdminDashboard onNavigateToMQTT={() => setActiveTab('mqtt')} />
        )}

        {activeTab === 'mqtt' && (
          <LiveMQTTMonitorPage onNavigateToDashboard={() => setActiveTab('dashboard')} />
        )}

        {activeTab === 'kiosk' && (
          <KioskQRStationPage
            onOpenDriverView={handleOpenDriverView}
            onNavigateToDashboard={() => setActiveTab('dashboard')}
          />
        )}
      </main>
    </div>
  );
};

export default App;



