import React, { useEffect, useRef } from 'react';
import { MapPin, AlertCircle } from 'lucide-react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Camera } from '../types/camera';
import { Incident } from '../types/incident';
import { EmptyState } from '../components/common/EmptyState';

interface MapViewPageProps {
  cameras: Camera[];
  incidents: Incident[];
  onSelectCamera?: (id: string) => void;
}

export const MapViewPage: React.FC<MapViewPageProps> = ({
  cameras,
  incidents,
  onSelectCamera,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Filter cameras that actually have real lat/lng coordinates
  const geolocatedCameras = cameras.filter(
    (c) => c.location && c.location.lat !== null && c.location.lng !== null
  );

  useEffect(() => {
    if (geolocatedCameras.length === 0 || !mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const firstCam = geolocatedCameras[0];
      const initialLat = firstCam.location!.lat!;
      const initialLng = firstCam.location!.lng!;

      const map = L.map(mapContainerRef.current, {
        attributionControl: false,
      }).setView([initialLat, initialLng], 14);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
      }).addTo(map);

      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear previous markers
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker || layer instanceof L.CircleMarker) {
        map.removeLayer(layer);
      }
    });

    // Add camera markers
    geolocatedCameras.forEach((cam) => {
      const lat = cam.location!.lat!;
      const lng = cam.location!.lng!;
      const isOnline = cam.status === 'ONLINE';

      const hasAlert = incidents.some(
        (i) => i.camera_id === cam.camera_id && i.status === 'active'
      );

      const color = hasAlert ? '#ef4444' : isOnline ? '#10b981' : '#64748b';

      const marker = L.circleMarker([lat, lng], {
        radius: 8,
        fillColor: color,
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9,
      }).addTo(map);

      marker.bindPopup(`
        <div style="font-family: sans-serif; font-size: 12px;">
          <strong>${cam.name || cam.camera_id}</strong><br/>
          <span>ID: ${cam.camera_id}</span><br/>
          <span>Status: ${cam.status}</span><br/>
          <span>GPS: ${lat.toFixed(5)}, ${lng.toFixed(5)}</span>
        </div>
      `);
    });
  }, [geolocatedCameras, incidents]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-4 space-y-3">
      {/* Header */}
      <div className="bg-slate-900 p-3.5 rounded-lg border border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <MapPin className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-bold text-slate-100 uppercase tracking-wider">
            Tactical Map View
          </span>
          <span className="text-xs font-mono text-slate-400">
            ({geolocatedCameras.length} Geolocated Cameras)
          </span>
        </div>

        <div className="text-[11px] font-mono text-slate-400">
          Source: Real GPS Coordinates from Registered Cameras
        </div>
      </div>

      {/* Map Content */}
      <div className="flex-1 bg-slate-900 rounded-lg border border-slate-800 overflow-hidden relative">
        {geolocatedCameras.length === 0 ? (
          <EmptyState
            title="No camera locations available"
            message="No registered cameras have GPS coordinates configured in their metadata."
            className="h-full"
          />
        ) : (
          <div ref={mapContainerRef} className="w-full h-full" />
        )}
      </div>
    </div>
  );
};
