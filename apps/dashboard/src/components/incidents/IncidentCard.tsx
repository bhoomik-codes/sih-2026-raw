import React from 'react';
import { Clock, AlertTriangle, CheckCircle } from 'lucide-react';
import { Incident } from '../../types/incident';
import { SeverityBadge } from '../common/SeverityBadge';

interface IncidentCardProps {
  incident: Incident;
  onSelect: (incident: Incident) => void;
}

function getDisplayCode(incident: Incident): string {
  return incident.incident_code
    || (incident.id ? `INC-${incident.id.slice(-6).toUpperCase()}` : null)
    || incident.incident_id
    || '—';
}

function getDisplayTime(incident: Incident): string {
  try {
    if (incident.created_at) {
      return new Date(incident.created_at).toLocaleTimeString('en-GB', { hour12: false });
    }
    if (incident.timestamp) {
      return new Date(
        incident.timestamp < 1e11 ? incident.timestamp * 1000 : incident.timestamp
      ).toLocaleTimeString('en-GB', { hour12: false });
    }
  } catch {}
  return '—';
}

export const IncidentCard: React.FC<IncidentCardProps> = ({ incident, onSelect }) => {
  const sev = (incident.severity || 'low').toLowerCase();
  const severityClass =
    sev === 'critical' ? 'severity-critical' :
    sev === 'high'     ? 'severity-high' :
    sev === 'medium'   ? 'severity-medium' :
                         'severity-low';

  const isAcknowledged =
    incident.status === 'ACKNOWLEDGED' || incident.status === 'acknowledged';

  const displayCode = getDisplayCode(incident);
  const displayTitle = incident.title || incident.description || `Track #${incident.track_id} Alert`;
  const eventCount = incident.incident_events?.length
    || incident.triggering_events?.length
    || 0;

  return (
    <div
      onClick={() => onSelect(incident)}
      className={`p-2.5 rounded border border-[#232a36] cursor-pointer transition-all duration-150 space-y-1.5 ${severityClass} hover:bg-[#19202b] hover:border-[#374151] active:scale-[0.99]`}
    >
      {/* Top Row: Code, Severity, Ack status, Risk */}
      <div className="flex items-center justify-between gap-1.5">
        <div className="flex items-center space-x-1.5 min-w-0">
          {/* Pulsing dot for unacknowledged */}
          {!isAcknowledged && (
            <span
              className={`w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse ${
                sev === 'critical' ? 'bg-rose-500' :
                sev === 'high'     ? 'bg-orange-500' :
                sev === 'medium'   ? 'bg-amber-400' :
                                     'bg-cyan-400'
              }`}
            />
          )}
          {isAcknowledged && <CheckCircle className="w-3 h-3 text-blue-400 flex-shrink-0" />}
          <span className="font-mono font-bold text-xs text-[#dce2f3] truncate">
            {displayCode}
          </span>
          <SeverityBadge severity={incident.severity} />
          {isAcknowledged && (
            <span className="px-1 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-blue-500/15 text-blue-400 border border-blue-500/30 flex-shrink-0">
              ACK
            </span>
          )}
        </div>

        <div className="flex-shrink-0">
          <span className="text-xs font-mono font-bold text-rose-400">
            {incident.risk_score}
          </span>
        </div>
      </div>

      {/* Title / Description */}
      <div className="text-xs font-semibold text-[#dce2f3] line-clamp-1 font-sans">
        {displayTitle}
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[10px] text-[#8f9195] font-mono pt-1 border-t border-[#232a36]">
        <div className="flex items-center space-x-1.5 min-w-0">
          <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0" />
          <span className="truncate">
            {incident.camera_id || incident.camera_name || '—'}
          </span>
          {eventCount > 0 && (
            <span className="text-[#45474a]">• {eventCount} events</span>
          )}
        </div>
        <div className="flex items-center space-x-1 flex-shrink-0">
          <Clock className="w-2.5 h-2.5" />
          <span>{getDisplayTime(incident)}</span>
        </div>
      </div>
    </div>
  );
};
