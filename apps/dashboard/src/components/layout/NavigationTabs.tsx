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
    { id: 'command_center', label: 'Command Center', icon: LayoutDashboard },
    { id: 'camera_management', label: 'Cameras', icon: Cctv },
    { id: 'camera_detail', label: 'Zones & Fences', icon: Maximize2 },
    {
      id: 'incident_center',
      label: 'Incident Center',
      icon: AlertTriangle,
      badge: activeIncidentCount > 0 ? activeIncidentCount : undefined,
    },
    { id: 'map_view', label: 'Tactical Map', icon: MapPin },
    { id: 'system_health', label: 'Observability', icon: Activity },
    { id: 'face_registry', label: 'Face Registry', icon: UserCheck },
  ];

  return (
    <nav className="flex items-center space-x-1 select-none">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = currentPage === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onSelectPage(tab.id)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-sm text-xs font-mono tracking-wider transition ${
              isActive
                ? 'bg-[#232a36] text-[#dce2f3] border-b-2 border-blue-400 font-bold'
                : 'text-[#8f9195] hover:text-[#dce2f3] hover:bg-[#19202b] border-b-2 border-transparent'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="uppercase text-[11px]">{tab.label}</span>
            {tab.badge !== undefined && (
              <span className="px-1.5 py-0.2 rounded-sm text-[10px] font-bold bg-rose-600 text-white font-mono">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
};
