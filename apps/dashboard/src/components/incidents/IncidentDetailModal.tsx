import React, { useState } from 'react';
import { X, Shield, Check } from 'lucide-react';
import { Incident } from '../../types/incident';
import { SeverityBadge } from '../common/SeverityBadge';

interface IncidentDetailModalProps {
  incident: Incident;
  onClose: () => void;
  onAcknowledge: (id: string) => Promise<any>;
}

export const IncidentDetailModal: React.FC<IncidentDetailModalProps> = ({
  incident,
  onClose,
  onAcknowledge,
}) => {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [ackError, setAckError] = useState<string | null>(null);

  const handleAck = async () => {
    setIsSubmitting(true);
    setAckError(null);
    try {
      await onAcknowledge(incident.incident_id);
    } catch (err: any) {
      setAckError(err.message || 'Failed to acknowledge incident');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formattedTime = new Date(
    incident.timestamp * (incident.timestamp < 1e11 ? 1000 : 1)
  ).toLocaleString();

  return (
    <div className="fixed inset-0 z-50 bg-[#070e19]/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#151c27] border border-[#374151] rounded-sm max-w-xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="px-4 py-3 border-b border-[#232a36] flex items-center justify-between bg-[#19202b]">
          <div className="flex items-center space-x-2">
            <span className="font-mono font-bold text-xs text-[#dce2f3] uppercase tracking-wider">
              INCIDENT_REPORT // #{incident.incident_id}
            </span>
            <SeverityBadge severity={incident.severity} />
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-sm text-[#8f9195] hover:text-[#dce2f3] hover:bg-[#232a36] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3.5 overflow-y-auto text-xs">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 bg-[#0c141f] p-3 rounded-sm border border-[#232a36]">
            <div>
              <div className="text-[10px] text-[#8f9195] uppercase font-mono font-semibold">CUMULATIVE_RISK</div>
              <div className="text-xl font-bold font-mono text-rose-400 mt-0.5">
                {incident.risk_score} <span className="text-[10px] text-[#8f9195] font-normal">/ 100</span>
              </div>
            </div>
            <div>
              <div className="text-[10px] text-[#8f9195] uppercase font-mono font-semibold">TARGET_TRACK</div>
              <div className="text-sm font-semibold font-mono text-[#dce2f3] mt-1">
                TRACK #{incident.track_id}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-[#8f9195] uppercase font-mono font-semibold">CAMERA_NODE</div>
              <div className="text-sm font-semibold font-mono text-[#dce2f3] mt-1 truncate">
                {incident.camera_name || incident.camera_id || '—'}
              </div>
            </div>
          </div>

          {/* Description */}
          {incident.description && (
            <div className="space-y-1">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#8f9195]">EVENT_SUMMARY:</span>
              <p className="text-[#c5c6cb] bg-[#0c141f] p-2.5 rounded-sm border border-[#232a36] leading-relaxed">
                {incident.description}
              </p>
            </div>
          )}

          {/* Explainability Breakdown */}
          <div className="space-y-1.5">
            <div className="flex items-center space-x-1.5 text-[#dce2f3] font-mono font-bold text-[11px] uppercase tracking-wider">
              <Shield className="w-3.5 h-3.5 text-blue-400" />
              <span>EXPLAINABILITY_CORRELATION (TRIGGERING EVENTS)</span>
            </div>

            {incident.triggering_events && incident.triggering_events.length > 0 ? (
              <div className="space-y-1">
                {incident.triggering_events.map((evt, idx) => (
                  <div
                    key={idx}
                    className="p-2 bg-[#0c141f] rounded-sm border border-[#232a36] flex items-start justify-between gap-2 font-mono"
                  >
                    <div className="space-y-0.5">
                      <div className="font-bold text-[#dce2f3] flex items-center space-x-1.5">
                        <span className="text-blue-400">›</span>
                        <span>{evt.rule_name || evt.event_type}</span>
                        <SeverityBadge severity={evt.severity} />
                      </div>
                      <div className="text-[10px] text-[#8f9195]">
                        CLASS: {evt.class_name || 'person'} • TRACK #{evt.track_id}
                        {evt.confidence !== undefined && ` • CONF: ${(evt.confidence * 100).toFixed(0)}%`}
                        {evt.location && ` • POS: (${evt.location[0]}, ${evt.location[1]})`}
                      </div>
                    </div>

                    <div className="text-[9px] font-mono text-[#8f9195] flex-shrink-0">
                      {evt.timestamp ? new Date(evt.timestamp * (evt.timestamp < 1e11 ? 1000 : 1)).toLocaleTimeString() : '—'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[#8f9195] text-[11px] bg-[#0c141f] p-2.5 rounded-sm border border-[#232a36]">
                No individual sub-events recorded for this incident.
              </div>
            )}
          </div>

          {/* Three-Clock Latency Timestamp Trace */}
          {incident.triggering_events?.[0]?.capture_ts && (
            <div className="space-y-1 bg-[#0c141f] p-2.5 rounded-sm border border-[#232a36] font-mono text-[10px]">
              <div className="text-[#8f9195] font-bold uppercase tracking-wider">THREE_CLOCK_LATENCY_AUDIT:</div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
                <div className="p-1.5 bg-[#151c27] rounded-sm border border-[#232a36] truncate">
                  <span className="text-[#8f9195] block text-[9px]">1. CAPTURE_TS</span>
                  <span className="text-[#dce2f3]">{incident.triggering_events[0].capture_ts}</span>
                </div>
                <div className="p-1.5 bg-[#151c27] rounded-sm border border-[#232a36] truncate">
                  <span className="text-[#8f9195] block text-[9px]">2. INGEST_TS</span>
                  <span className="text-emerald-400">{incident.triggering_events[0].ingest_ts || '—'}</span>
                </div>
                <div className="p-1.5 bg-[#151c27] rounded-sm border border-[#232a36] truncate">
                  <span className="text-[#8f9195] block text-[9px]">3. DISPLAY_TS</span>
                  <span className="text-blue-400">{incident.triggering_events[0].display_ts || '—'}</span>
                </div>
              </div>
            </div>
          )}

          {/* Error notice if acknowledgement fails */}
          {ackError && (
            <div className="p-2 rounded-sm bg-rose-500/10 border border-rose-500/30 text-rose-400 text-[11px] font-mono">
              ERROR: {ackError}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-[#232a36] bg-[#19202b] flex items-center justify-between font-mono">
          <div className="text-[10px] text-[#8f9195]">
            LOGGED: {formattedTime}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3 py-1 rounded-sm bg-[#232a36] hover:bg-[#2e3541] text-[#c5c6cb] text-xs font-mono uppercase transition"
            >
              CLOSE
            </button>

            {incident.status !== 'acknowledged' && (
              <button
                onClick={handleAck}
                disabled={isSubmitting}
                className="flex items-center space-x-1.5 px-3 py-1 rounded-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-mono font-bold uppercase transition"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{isSubmitting ? 'ACKING...' : 'ACKNOWLEDGE'}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
