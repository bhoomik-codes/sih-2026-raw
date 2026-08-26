import React from 'react';
import { Shield, AlertTriangle, Check, VideoOff } from 'lucide-react';
import { Camera } from '../../types/camera';
import { Incident } from '../../types/incident';
import { HealthStatusLevel } from '../../types/health';
import { ConnectionBadge } from '../common/ConnectionBadge';
import { SeverityBadge } from '../common/SeverityBadge';
import { LiveStream } from '../cameras/LiveStream';

interface MobileAwarenessViewProps {
  cameras: Camera[];
  selectedCamera: Camera | null;
  selectedCameraId: string | null;
  onSelectCamera: (id: string) => void;
  incidents: Incident[];
  onSelectIncident: (incident: Incident) => void;
  onAcknowledge: (id: string) => Promise<any>;
  healthStatus: HealthStatusLevel;
}

export const MobileAwarenessView: React.FC<MobileAwarenessViewProps> = ({
  cameras,
  selectedCamera,
  selectedCameraId,
  onSelectCamera,
  incidents,
  onSelectIncident,
  onAcknowledge,
  healthStatus,
}) => {
  const activeIncidents = incidents.filter((i) => i.status !== 'resolved' && i.status !== 'false_alarm');

  return (
    <div className="flex flex-col h-full bg-slate-950 p-3 space-y-3 overflow-y-auto font-sans">
      {/* Top Mobile Bar */}
      <div className="flex items-center justify-between bg-slate-900 p-3 rounded-lg border border-slate-800">
        <div className="flex items-center space-x-2">
          <Shield className="w-4 h-4 text-blue-400" />
          <span className="font-bold text-xs text-slate-100">IBVAP Mobile C2</span>
        </div>
        <ConnectionBadge status={healthStatus} />
      </div>

      {/* Camera Selector */}
      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
        <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
          Select Active Stream:
        </label>
        <select
          value={selectedCameraId || ''}
          onChange={(e) => onSelectCamera(e.target.value)}
          className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
        >
          {cameras.length === 0 ? (
            <option value="">No cameras available</option>
          ) : (
            cameras.map((c) => (
              <option key={c.camera_id} value={c.camera_id}>
                {c.name || c.camera_id} ({c.status})
              </option>
            ))
          )}
        </select>
      </div>

      {/* Single Live Camera Stream */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden h-64">
        {selectedCamera ? (
          <LiveStream camera={selectedCamera} className="h-full" />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs">
            <VideoOff className="w-6 h-6 mb-1 text-slate-600" />
            <span>No stream selected</span>
          </div>
        )}
      </div>

      {/* Active Incidents List with 1-Click Acknowledge */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-3 space-y-2">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center space-x-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-bold text-slate-100 uppercase tracking-wider">
              Active Alerts ({activeIncidents.length})
            </span>
          </div>
        </div>

        {activeIncidents.length === 0 ? (
          <div className="text-center py-4 text-slate-500 text-xs">
            Perimeter clear • No active incidents
          </div>
        ) : (
          <div className="space-y-2">
            {activeIncidents.map((inc) => (
              <div
                key={inc.incident_id}
                className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-xs text-slate-200">
                      #{inc.incident_id}
                    </span>
                    <SeverityBadge severity={inc.severity} />
                  </div>
                  <span className="text-xs font-mono font-bold text-rose-400">
                    Risk: {inc.risk_score}
                  </span>
                </div>

                <div className="text-xs text-slate-300 font-medium">
                  {inc.description || `Track #${inc.track_id} Alert`}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                  <span className="text-[10px] font-mono text-slate-400">
                    Cam: {inc.camera_name || inc.camera_id || '—'}
                  </span>

                  {inc.status !== 'acknowledged' && (
                    <button
                      onClick={() => onAcknowledge(inc.incident_id)}
                      className="flex items-center space-x-1 px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-semibold"
                    >
                      <Check className="w-3 h-3" />
                      <span>Acknowledge</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
