import React from 'react';
import { History, RefreshCw } from 'lucide-react';
import { SurveillanceEvent } from '../../types/event';
import { SeverityBadge } from '../common/SeverityBadge';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';

interface EventTimelineProps {
  events: SurveillanceEvent[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({
  events,
  isLoading,
  error,
  onRefresh,
}) => {
  return (
    <div className="bg-[#151c27] rounded-sm border border-[#232a36] flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-3 py-1.5 bg-[#19202b] border-b border-[#232a36] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <History className="w-3.5 h-3.5 text-[#8f9195]" />
          <span className="text-[11px] font-mono font-bold text-[#dce2f3] uppercase tracking-wider">
            EVENT_STREAM_TIMELINE
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[10px] font-mono text-[#8f9195] font-medium">
            [{events.length} EVENTS]
          </span>
          <button
            onClick={onRefresh}
            className="p-1 rounded-sm text-[#8f9195] hover:text-[#dce2f3] hover:bg-[#232a36] transition"
            title="Refresh Timeline"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-x-auto overflow-y-auto p-1">
        {isLoading && events.length === 0 ? (
          <LoadingState message="Loading events..." className="py-4" />
        ) : error && events.length === 0 ? (
          <ErrorState message={error} onRetry={onRefresh} className="p-3" />
        ) : events.length === 0 ? (
          <EmptyState
            title="No events received"
            message="Awaiting surveillance events from edge detection engine"
            className="py-4"
          />
        ) : (
          <table className="w-full text-left font-mono text-xs">
            <thead className="text-[10px] text-[#8f9195] uppercase tracking-wider border-b border-[#232a36] bg-[#070e19] sticky top-0">
              <tr>
                <th className="py-1.5 px-2">TIME</th>
                <th className="py-1.5 px-2">EVENT_TYPE</th>
                <th className="py-1.5 px-2">CAMERA_NODE</th>
                <th className="py-1.5 px-2">TRACK_ID</th>
                <th className="py-1.5 px-2">SEVERITY</th>
                <th className="py-1.5 px-2">RULE / TRIGGER</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#232a36] text-[#c5c6cb] text-[11px]">
              {events.map((evt, idx) => {
                const ts = evt.timestamp
                  ? new Date(evt.timestamp * (evt.timestamp < 1e11 ? 1000 : 1)).toLocaleTimeString('en-US', {
                      hour12: false,
                    })
                  : '—';
                return (
                  <tr key={evt.event_id || idx} className="hover:bg-[#19202b]/60">
                    <td className="py-1.5 px-2 text-[#8f9195]">{ts}</td>
                    <td className="py-1.5 px-2 font-bold text-[#dce2f3]">{evt.event_type}</td>
                    <td className="py-1.5 px-2 text-[#c5c6cb]">{evt.camera_name || evt.camera_id || '—'}</td>
                    <td className="py-1.5 px-2 text-blue-400">#{evt.track_id}</td>
                    <td className="py-1.5 px-2">
                      <SeverityBadge severity={evt.severity} />
                    </td>
                    <td className="py-1.5 px-2 text-[#8f9195] truncate max-w-xs">{evt.rule_name || '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
