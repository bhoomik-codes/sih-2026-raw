import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Incident } from '../../types/incident';
import { IncidentCard } from './IncidentCard';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';

interface ActiveIncidentsListProps {
  incidents: Incident[];
  onSelectIncident: (incident: Incident) => void;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const ActiveIncidentsList: React.FC<ActiveIncidentsListProps> = ({
  incidents,
  onSelectIncident,
  isLoading,
  error,
  onRefresh,
}) => {
  return (
    <div className="bg-[#151c27] rounded-sm border border-[#232a36] flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 bg-[#19202b] border-b border-[#232a36] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-[11px] font-mono font-bold text-[#dce2f3] uppercase tracking-wider">
            ACTIVE_ALERTS
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[10px] font-mono text-[#8f9195] font-semibold">
            [{incidents.length} ESCALATED]
          </span>
          <button
            onClick={onRefresh}
            className="p-1 rounded-sm text-[#8f9195] hover:text-[#dce2f3] hover:bg-[#232a36] transition"
            title="Refresh Incidents"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1.5">
        {isLoading && incidents.length === 0 ? (
          <LoadingState message="Loading incidents..." className="py-6" />
        ) : error && incidents.length === 0 ? (
          <ErrorState message={error} onRetry={onRefresh} className="p-3" />
        ) : incidents.length === 0 ? (
          <EmptyState
            title="No active incidents"
            message="No security threshold violations reported by edge engine"
            className="py-6"
          />
        ) : (
          incidents.map((incident) => (
            <IncidentCard
              key={incident.id || incident.incident_id}
              incident={incident}
              onSelect={onSelectIncident}
            />
          ))
        )}
      </div>
    </div>
  );
};
