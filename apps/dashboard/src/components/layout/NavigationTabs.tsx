import React from 'react';
import {
  LayoutDashboard,
  Cctv,
  Maximize2,
  AlertTriangle,
  MapPin,
  Activity,
  UserCheck,
} from 'lucide-react';

export type DashboardPage =
  | 'command_center'
  | 'camera_management'
  | 'camera_detail'
  | 'incident_center'
  | 'map_view'
  | 'system_health'
  | 'face_registry';

interface NavigationTabsProps {
  currentPage: DashboardPage;
  onSelectPage: (page: DashboardPage) => void;
  activeIncidentCount?: number;
}

export const NavigationTabs: React.FC<NavigationTabsProps> = ({
  currentPage,
  onSelectPage,
  activeIncidentCount = 0,
}) => {
  const tabs: { id: DashboardPage; label: string; icon: React.ElementType; badge?: number }[] = [
    { id: 'command_center', label: 'Command', icon: LayoutDashboard },
    { id: 'camera_management', label: 'Cameras', icon: Cctv },
    { id: 'camera_detail', label: 'Zones', icon: Maximize2 },
    {
      id: 'incident_center',
      label: 'Incidents',
      icon: AlertTriangle,
      badge: activeIncidentCount > 0 ? activeIncidentCount : undefined,
    },
    { id: 'map_view', label: 'Map', icon: MapPin },
    { id: 'system_health', label: 'Health', icon: Activity },
    { id: 'face_registry', label: 'Faces', icon: UserCheck },
  ];

  return (
    <nav className="flex items-center gap-0.5 select-none">
      {tabs.map((tab, i) => {
        const Icon = tab.icon;
        const isActive = currentPage === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onSelectPage(tab.id)}
            className={`
              relative flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-[11px] font-mono tracking-wider
              transition-all duration-200 ease-out
              animate-fade-in
              ${isActive ? 'nav-tab-active' : 'text-[rgba(0,212,255,0.45)] hover:text-[rgba(0,212,255,0.85)] hover:bg-[rgba(0,212,255,0.05)]'}
            `}
            style={{ animationDelay: `${i * 30}ms` }}
          >
            <Icon className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="uppercase hidden xl:inline">{tab.label}</span>

            {/* Incident count badge */}
            {tab.badge !== undefined && (
              <span className="relative flex items-center justify-center ml-0.5">
                {/* Ping ring */}
                <span
                  className="absolute inline-flex h-4 w-4 rounded-full opacity-60 animate-ping-slow"
                  style={{ background: 'rgba(255,50,50,0.4)' }}
                />
                <span
                  className="relative z-10 flex items-center justify-center h-4 min-w-[16px] px-1 rounded-sm text-[9px] font-bold font-mono text-white"
                  style={{ background: '#e02020', boxShadow: '0 0 8px rgba(255,50,50,0.7)' }}
                >
                  {tab.badge}
                </span>
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
};
