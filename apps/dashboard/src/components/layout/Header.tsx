import React, { useState, useEffect } from 'react';
import { Shield } from 'lucide-react';
import { HealthStatusLevel } from '../../types/health';
import { ConnectionBadge } from '../common/ConnectionBadge';
import { NavigationTabs, DashboardPage } from './NavigationTabs';

interface HeaderProps {
  healthStatus: HealthStatusLevel;
  currentPage: DashboardPage;
  onSelectPage: (page: DashboardPage) => void;
  activeIncidentCount?: number;
}

export const Header: React.FC<HeaderProps> = ({
  healthStatus,
  currentPage,
  onSelectPage,
  activeIncidentCount = 0,
}) => {
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const update = () => {
      setCurrentTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-12 bg-[#0c141f] border-b border-[#232a36] flex items-center justify-between px-4 z-40 select-none flex-shrink-0">
      {/* Brand: Stitch Tactical Oversight ID */}
      <div className="flex items-center space-x-3">
        <div className="w-6 h-6 rounded-sm bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
          <Shield className="w-3.5 h-3.5" />
        </div>
        <div className="flex items-center space-x-2">
          <span className="font-mono font-bold text-xs text-[#dce2f3] tracking-widest uppercase">
            IBVAP // SOC
          </span>
          <span className="text-[#374151] hidden sm:inline">|</span>
          <span className="text-[11px] font-mono text-[#8f9195] hidden sm:inline uppercase">
            SSB SECTOR 4
          </span>
        </div>
      </div>

      {/* Center Tabs Navigation */}
      <div className="hidden lg:block">
        <NavigationTabs
          currentPage={currentPage}
          onSelectPage={onSelectPage}
          activeIncidentCount={activeIncidentCount}
        />
      </div>

      {/* Right Status */}
      <div className="flex items-center space-x-3">
        <ConnectionBadge status={healthStatus} />
        <div className="hidden sm:block pl-2.5 border-l border-[#232a36] text-[11px] font-mono text-[#8f9195]">
          UTC_{currentTime}
        </div>
      </div>
    </header>
  );
};
