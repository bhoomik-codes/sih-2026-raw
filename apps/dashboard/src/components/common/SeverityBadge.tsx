import React from 'react';
import { EventSeverity } from '../../types/event';

export const SeverityBadge: React.FC<{ severity?: EventSeverity | string }> = ({ severity }) => {
  const s = (severity || 'low').toLowerCase();

  switch (s) {
    case 'critical':
      return (
        <span className="px-1.5 py-0.5 rounded-sm text-[10px] font-mono font-bold uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/40">
          Critical
        </span>
      );
    case 'high':
      return (
        <span className="px-1.5 py-0.5 rounded-sm text-[10px] font-mono font-bold uppercase tracking-wider bg-orange-500/20 text-orange-300 border border-orange-500/40">
          High
        </span>
      );
    case 'medium':
      return (
        <span className="px-1.5 py-0.5 rounded-sm text-[10px] font-mono font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40">
          Medium
        </span>
      );
    default:
      return (
        <span className="px-1.5 py-0.5 rounded-sm text-[10px] font-mono font-bold uppercase tracking-wider bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
          Low
        </span>
      );
  }
};
