import React from 'react';
import { Camera } from '../types/camera';
import { Incident } from '../types/incident';
import { SurveillanceEvent } from '../types/event';
import { SystemMetrics } from '../types/metrics';
import { CameraList } from '../components/cameras/CameraList';
import { CameraGrid } from '../components/cameras/CameraGrid';
import { ActiveIncidentsList } from '../components/incidents/ActiveIncidentsList';
import { EventTimeline } from '../components/events/EventTimeline';
import { SystemHealthBar } from '../components/health/SystemHealthBar';

interface CommandCenterPageProps {
  cameras: Camera[];
  selectedCamera: Camera | null;
  selectedCameraId: string | null;
  onSelectCamera: (id: string) => void;
  camerasLoading: boolean;
  camerasError: string | null;
  onRefreshCameras: () => void;

  incidents: Incident[];
  onSelectIncident: (incident: Incident) => void;
  incidentsLoading: boolean;
  incidentsError: string | null;
  onRefreshIncidents: () => void;

  events: SurveillanceEvent[];
  eventsLoading: boolean;
  eventsError: string | null;
  onRefreshEvents: () => void;

  metrics: SystemMetrics | null;
  metricsLoading: boolean;
  metricsError: string | null;
}

export const CommandCenterPage: React.FC<CommandCenterPageProps> = ({
  cameras,
  selectedCamera,
  selectedCameraId,
  onSelectCamera,
  camerasLoading,
  camerasError,
  onRefreshCameras,

  incidents,
  onSelectIncident,
  incidentsLoading,
  incidentsError,
  onRefreshIncidents,

  events,
  eventsLoading,
  eventsError,
  onRefreshEvents,

  metrics,
  metricsLoading,
  metricsError,
}) => {
  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-2.5 gap-2.5">
      {/* ── Upper 3-Column Surveillance Matrix ─────────────────────────────── */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-2.5 min-h-0">

        {/* Left Column: Camera Node List (2 cols) */}
        <div className="md:col-span-2 h-full min-h-[220px]">
          <CameraList
            cameras={cameras}
            selectedCameraId={selectedCameraId}
            onSelectCamera={onSelectCamera}
            isLoading={camerasLoading}
            error={camerasError}
            onRefresh={onRefreshCameras}
          />
        </div>

        {/* Center Column: Multi-Camera Mosaic (7 cols) */}
        <div className="md:col-span-7 h-full min-h-[300px]">
          <CameraGrid
            cameras={cameras}
            selectedCameraId={selectedCameraId}
            onSelectCamera={onSelectCamera}
            isLoading={camerasLoading}
            error={camerasError}
          />
        </div>

        {/* Right Column: Active Incidents (3 cols) */}
        <div className="md:col-span-3 h-full min-h-[220px]">
          <ActiveIncidentsList
            incidents={incidents}
            onSelectIncident={onSelectIncident}
            isLoading={incidentsLoading}
            error={incidentsError}
            onRefresh={onRefreshIncidents}
          />
        </div>
      </div>

      {/* ── Lower Section: Event Timeline ───────────────────────────────────── */}
      <div className="h-40 flex-shrink-0">
        <EventTimeline
          events={events}
          isLoading={eventsLoading}
          error={eventsError}
          onRefresh={onRefreshEvents}
        />
      </div>

      {/* ── Bottom: System Health Bar ───────────────────────────────────────── */}
      <div className="flex-shrink-0">
        <SystemHealthBar
          metrics={metrics}
          isLoading={metricsLoading}
          error={metricsError}
        />
      </div>
    </div>
  );
};
