import React from 'react';
import { HealthStatusLevel } from '../../types/health';

export const ConnectionBadge: React.FC<{ status: HealthStatusLevel }> = ({ status }) => {
  switch (status) {
    case 'ONLINE':
      return (
        <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded-sm bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[11px] font-mono font-bold tracking-wider uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>SYS_ONLINE</span>
        </div>
      );
    case 'CONNECTING':
      return (
        <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded-sm bg-blue-500/10 text-blue-400 border border-blue-500/30 text-[11px] font-mono font-bold tracking-wider uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
          <span>CONNECTING</span>
        </div>
      );
    case 'DEGRADED':
      return (
        <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded-sm bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[11px] font-mono font-bold tracking-wider uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          <span>SYS_DEGRADED</span>
        </div>
      );
    default:
      return (
        <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded-sm bg-rose-500/10 text-rose-400 border border-rose-500/30 text-[11px] font-mono font-bold tracking-wider uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
          <span>BACKEND_OFFLINE</span>
        </div>
      );
  }
};
