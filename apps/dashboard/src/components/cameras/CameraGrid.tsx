import React from 'react';
import { Camera } from '../../types/camera';
import { LiveStream } from './LiveStream';
import { EmptyState } from '../common/EmptyState';
import { LoadingState } from '../common/LoadingState';

interface CameraGridProps {
  camera: Camera | null;
  isLoading: boolean;
  error: string | null;
}

export const CameraGrid: React.FC<CameraGridProps> = ({
  camera,
  isLoading,
  error,
}) => {
  return (
    <div className="bg-[#151c27] rounded-sm border border-[#232a36] flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-3.5 py-2 bg-[#19202b] border-b border-[#232a36] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-mono font-bold text-[#dce2f3] uppercase tracking-wider">
            PRIMARY_FEED_SURVEILLANCE
          </span>
          {camera && (
            <span className="text-[11px] font-mono text-[#8f9195]">
              // {camera.name || camera.camera_id}
            </span>
          )}
        </div>

        {camera && (
          <div className="flex items-center space-x-2 text-[10px] font-mono">
            <span className="text-[#8f9195]">STATUS:</span>
            <span
              className={`font-bold uppercase ${
                camera.status === 'ONLINE' ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {camera.status}
            </span>
          </div>
        )}
      </div>

      {/* Main View Area */}
      <div className="flex-1 p-2 bg-[#070e19] flex flex-col min-h-0">
        {isLoading && !camera ? (
          <LoadingState message="Connecting to camera feed..." className="flex-1" />
        ) : error && !camera ? (
          <EmptyState title="Stream unavailable" message={error} className="flex-1" />
        ) : !camera ? (
          <EmptyState title="No camera selected" message="Select a camera to view live annotated stream" className="flex-1" />
        ) : (
          <LiveStream camera={camera} className="flex-1" />
        )}
      </div>
    </div>
  );
};
