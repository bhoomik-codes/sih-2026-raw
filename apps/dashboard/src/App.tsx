import React, { useState } from 'react';
import { useCameras } from './hooks/useCameras';
import { useIncidents } from './hooks/useIncidents';
import { useEvents } from './hooks/useEvents';
import { useMetrics } from './hooks/useMetrics';
import { useHealth } from './hooks/useHealth';
import { useWebSocket } from './websocket/useWebSocket';

import { Header } from './components/layout/Header';
import { DashboardPage, NavigationTabs } from './components/layout/NavigationTabs';
import { MobileAwarenessView } from './components/layout/MobileAwarenessView';
import { IncidentDetailModal } from './components/incidents/IncidentDetailModal';

import { CommandCenterPage } from './pages/CommandCenterPage';
import { CameraManagementPage } from './pages/CameraManagementPage';
import { CameraDetailPage } from './pages/CameraDetailPage';
import { IncidentCenterPage } from './pages/IncidentCenterPage';
import { MapViewPage } from './pages/MapViewPage';
import { SystemHealthPage } from './pages/SystemHealthPage';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<DashboardPage>('command_center');

  // Server Data Hooks
  const {
    cameras,
    selectedCamera,
    selectedCameraId,
    setSelectedCameraId,
    isLoading: camerasLoading,
    error: camerasError,
    refresh: refreshCameras,
  } = useCameras();

  const {
    incidents,
    activeIncidents,
    selectedIncident,
    setSelectedIncident,
    isLoading: incidentsLoading,
    error: incidentsError,
    refresh: refreshIncidents,
    handleNewIncident,
    acknowledge,
  } = useIncidents();

  const {
    events,
    isLoading: eventsLoading,
    error: eventsError,
    refresh: refreshEvents,
    handleNewEvent,
  } = useEvents();

  const {
    metrics,
    isLoading: metricsLoading,
    error: metricsError,
    refresh: refreshMetrics,
    handleNewMetrics,
  } = useMetrics();

  // Real WebSocket Hook
  const { isConnected: isWsConnected } = useWebSocket({
    onEvent: handleNewEvent,
    onIncident: handleNewIncident,
    onMetrics: handleNewMetrics,
  });

  // Health Monitoring
  const {
    healthStatus,
    activeCameraCount,
    uptimeSeconds,
    refreshHealth,
  } = useHealth(isWsConnected);

  const handleRefreshAll = () => {
    refreshCameras();
    refreshIncidents();
    refreshEvents();
    refreshMetrics();
    refreshHealth();
  };

  const renderActivePage = () => {
    switch (currentPage) {
      case 'command_center':
        return (
          <CommandCenterPage
            cameras={cameras}
            selectedCamera={selectedCamera}
            selectedCameraId={selectedCameraId}
            onSelectCamera={setSelectedCameraId}
            camerasLoading={camerasLoading}
            camerasError={camerasError}
            onRefreshCameras={refreshCameras}
            incidents={activeIncidents}
            onSelectIncident={setSelectedIncident}
            incidentsLoading={incidentsLoading}
            incidentsError={incidentsError}
            onRefreshIncidents={refreshIncidents}
            events={events}
            eventsLoading={eventsLoading}
            eventsError={eventsError}
            onRefreshEvents={refreshEvents}
            metrics={metrics}
            metricsLoading={metricsLoading}
            metricsError={metricsError}
          />
        );
      case 'camera_management':
        return (
          <CameraManagementPage
            cameras={cameras}
            isLoading={camerasLoading}
            error={camerasError}
            onRefresh={refreshCameras}
          />
        );
      case 'camera_detail':
        return (
          <CameraDetailPage
            cameras={cameras}
            selectedCamera={selectedCamera}
            selectedCameraId={selectedCameraId}
            onSelectCamera={setSelectedCameraId}
            onRefresh={refreshCameras}
          />
        );
      case 'incident_center':
        return (
          <IncidentCenterPage
            incidents={incidents}
            cameras={cameras}
            isLoading={incidentsLoading}
            error={incidentsError}
            onRefresh={refreshIncidents}
            onSelectIncident={setSelectedIncident}
          />
        );
      case 'map_view':
        return (
          <MapViewPage
            cameras={cameras}
            incidents={activeIncidents}
            onSelectCamera={setSelectedCameraId}
          />
        );
      case 'system_health':
        return (
          <SystemHealthPage
            metrics={metrics}
            healthStatus={healthStatus}
            activeCameraCount={activeCameraCount}
            uptimeSeconds={uptimeSeconds}
            isLoading={metricsLoading}
            error={metricsError}
            onRefresh={refreshMetrics}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans select-none">
      {/* Top Application Header */}
      <Header
        healthStatus={healthStatus}
        currentPage={currentPage}
        onSelectPage={setCurrentPage}
        activeIncidentCount={activeIncidents.length}
      />

      {/* Mobile Navigation Bar (Visible only on small screens) */}
      <div className="lg:hidden bg-slate-900 border-b border-slate-800 px-3 py-1.5 flex-shrink-0">
        <NavigationTabs
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          activeIncidentCount={activeIncidents.length}
        />
      </div>

      {/* Main Page Area */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {renderActivePage()}
      </main>

      {/* Incident Detail / Explainability Modal */}
      {selectedIncident && (
        <IncidentDetailModal
          incident={selectedIncident}
          onClose={() => setSelectedIncident(null)}
          onAcknowledge={acknowledge}
        />
      )}
    </div>
  );
};

export default App;
