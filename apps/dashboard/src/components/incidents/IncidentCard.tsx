import React from 'react';
import { Clock } from 'lucide-react';
import { Incident } from '../../types/incident';
import { SeverityBadge } from '../common/SeverityBadge';

interface IncidentCardProps {
  incident: Incident;
  onSelect: (incident: Incident) => void;
}

export const IncidentCard: React.FC<IncidentCardProps> = ({ incident, onSelect }) => {
  const sev = (incident.severity || 'low').toLowerCase();
  const severityClass =
    sev === 'critical'
      ? 'severity-critical'
      : sev === 'high'
      ? 'severity-high'
      : sev === 'medium'
      ? 'severity-medium'
      : 'severity-low';

  return (
    <div
      onClick={() => onSelect(incident)}
      className={`p-2.5 rounded-sm border border-[#232a36] cursor-pointer transition space-y-1.5 ${severityClass} hover:bg-[#19202b]`}
    >
      {/* Top Row: ID, Severity, Risk */}
      <div className="flex items-center justify-between gap-1.5">
        <div className="flex items-center space-x-1.5">
          <span className="font-mono font-bold text-xs text-[#dce2f3]">
            #{incident.incident_id}
          </span>
          <SeverityBadge severity={incident.severity} />
          {incident.status === 'acknowledged' && (
            <span className="px-1 py-0.2 rounded-sm text-[9px] font-mono font-bold uppercase bg-blue-500/15 text-blue-400 border border-blue-500/30">
              ACK
            </span>
          )}
        </div>

        <div>
          <span className="text-xs font-mono font-bold text-rose-400">
            RISK: {incident.risk_score}
          </span>
        </div>
      </div>

      {/* Description / Rule Summary */}
      <div className="text-xs font-semibold text-[#dce2f3] line-clamp-1 font-sans">
        {incident.description || `Track #${incident.track_id} Alert`}
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[10px] text-[#8f9195] font-mono pt-1 border-t border-[#232a36]">
        <div>
          NODE: {incident.camera_name || incident.camera_id || '—'}
        </div>
        <div className="flex items-center space-x-1">
          <Clock className="w-2.5 h-2.5 text-[#8f9195]" />
          <span>
            {new Date(incident.timestamp * (incident.timestamp < 1e11 ? 1000 : 1)).toLocaleTimeString('en-US', {
              hour12: false,
            })}
          </span>
        </div>
      </div>
    </div>
  );
};
