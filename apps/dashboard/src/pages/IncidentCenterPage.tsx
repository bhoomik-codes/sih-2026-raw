import React, { useState, useMemo } from 'react';
import { AlertTriangle, Filter, Search, RefreshCw } from 'lucide-react';
import { Incident } from '../types/incident';
import { Camera } from '../types/camera';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { LoadingState } from '../components/common/LoadingState';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';

interface IncidentCenterPageProps {
  incidents: Incident[];
  cameras: Camera[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onSelectIncident: (incident: Incident) => void;
}

export const IncidentCenterPage: React.FC<IncidentCenterPageProps> = ({
  incidents,
  cameras,
  isLoading,
  error,
  onRefresh,
  onSelectIncident,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedCameraId, setSelectedCameraId] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');

  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      if (selectedSeverity !== 'all' && inc.severity !== selectedSeverity) return false;
      if (selectedCameraId !== 'all' && (inc.camera_id !== selectedCameraId && inc.camera_name !== selectedCameraId)) return false;
      if (selectedStatus !== 'all' && inc.status !== selectedStatus) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesId = inc.incident_id.toLowerCase().includes(q);
        const matchesDesc = (inc.description || '').toLowerCase().includes(q);
        const matchesTrack = inc.track_id.toString().includes(q);
        if (!matchesId && !matchesDesc && !matchesTrack) return false;
      }
      return true;
    });
  }, [incidents, selectedSeverity, selectedCameraId, selectedStatus, searchQuery]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-4 space-y-3">
      {/* Top Filter Bar */}
      <div className="bg-slate-900 p-3.5 rounded-lg border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <span className="font-bold text-slate-100 uppercase tracking-wider">
            Incident Center
          </span>
          <span className="text-slate-500 font-mono">({filteredIncidents.length} of {incidents.length})</span>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-500" />
            <input
              type="text"
              placeholder="Search ID, track, rule..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded pl-8 pr-3 py-1 text-slate-100 font-mono focus:outline-none focus:border-blue-500 w-44"
            />
          </div>

          {/* Severity Filter */}
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-mono focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Camera Filter */}
          <select
            value={selectedCameraId}
            onChange={(e) => setSelectedCameraId(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200 font-mono focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Cameras</option>
            {cameras.map((c) => (
              <option key={c.camera_id} value={c.camera_id}>
                {c.name || c.camera_id}
              </option>
            ))}
          </select>

          {/* Refresh */}
          <button
            onClick={onRefresh}
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            title="Refresh Incidents"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Incident List Table */}
      <div className="flex-1 bg-slate-900 rounded-lg border border-slate-800 overflow-hidden flex flex-col">
        {isLoading && incidents.length === 0 ? (
          <LoadingState message="Loading incidents..." className="flex-1" />
        ) : error && incidents.length === 0 ? (
          <ErrorState message={error} onRetry={onRefresh} className="m-4" />
        ) : filteredIncidents.length === 0 ? (
          <EmptyState
            title="No incidents found"
            message={
              incidents.length > 0
                ? 'No incidents match the active filters'
                : 'No incidents recorded by backend incident engine'
            }
            className="flex-1"
          />
        ) : (
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left font-mono text-xs">
              <thead className="text-[10px] text-slate-400 uppercase tracking-wider border-b border-slate-800 bg-slate-950/60 sticky top-0">
                <tr>
                  <th className="p-3">Incident ID</th>
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Severity</th>
                  <th className="p-3">Risk Score</th>
                  <th className="p-3">Track</th>
                  <th className="p-3">Camera</th>
                  <th className="p-3">Description / Triggers</th>
                  <th className="p-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {filteredIncidents.map((inc) => (
                  <tr
                    key={inc.incident_id}
                    onClick={() => onSelectIncident(inc)}
                    className="hover:bg-slate-850/60 cursor-pointer transition"
                  >
                    <td className="p-3 font-bold text-slate-100">#{inc.incident_id}</td>
                    <td className="p-3 text-slate-400">
                      {new Date(
                        inc.timestamp * (inc.timestamp < 1e11 ? 1000 : 1)
                      ).toLocaleString()}
                    </td>
                    <td className="p-3">
                      <SeverityBadge severity={inc.severity} />
                    </td>
                    <td className="p-3 font-bold text-rose-400">{inc.risk_score}</td>
                    <td className="p-3 text-blue-400">#{inc.track_id}</td>
                    <td className="p-3 text-slate-200">{inc.camera_name || inc.camera_id || '—'}</td>
                    <td className="p-3 text-slate-300 truncate max-w-sm">
                      <div className="flex flex-col gap-1">
                        <span>{inc.description || `${inc.triggering_events?.length || 0} event(s)`}</span>
                        {inc.blockchain_tx_hash && (
                          <div
                            className="inline-flex items-center gap-1 text-[9px] font-bold tracking-wider text-emerald-400 bg-emerald-950/40 border border-emerald-900/50 px-1.5 py-0.5 rounded-full w-max"
                            title={`Evidence Hash: ${inc.evidence_hash}\nTxHash: ${inc.blockchain_tx_hash}`}
                          >
                            🛡️ BLOCKCHAIN VERIFIED
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="p-3 text-right uppercase text-[10px] font-semibold">
                      <span
                        className={
                          inc.status === 'acknowledged'
                            ? 'text-blue-400'
                            : inc.status === 'resolved'
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }
                      >
                        {inc.status || 'ACTIVE'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
