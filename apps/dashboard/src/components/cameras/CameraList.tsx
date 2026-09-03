import React from 'react';
import { Cctv, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { Camera } from '../../types/camera';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';

interface CameraListProps {
  cameras: Camera[];
  selectedCameraId: string | null;
  onSelectCamera: (id: string) => void;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const CameraList: React.FC<CameraListProps> = ({
  cameras,
  selectedCameraId,
  onSelectCamera,
  isLoading,
  error,
  onRefresh,
}) => {
  const getStatusDot = (status: Camera['status']) => {
    switch (status) {
      case 'ONLINE':     return { bg: '#00ff88', shadow: '0 0 6px #00ff88', anim: 'animate-pulse-glow' };
      case 'CONNECTING': return { bg: '#00d4ff', shadow: '0 0 6px #00d4ff', anim: 'animate-pulse' };
      case 'ERROR':      return { bg: '#ff3232', shadow: '0 0 6px #ff3232', anim: '' };
      default:           return { bg: 'rgba(0,212,255,0.2)', shadow: 'none', anim: '' };
    }
  };

  const onlineCount = cameras.filter(c => c.status === 'ONLINE').length;

  return (
    <div
      className="flex flex-col h-full overflow-hidden animate-fade-in"
      style={{
        background: 'rgba(2,8,20,0.92)',
        border: '1px solid rgba(0,212,255,0.15)',
        borderRadius: '4px',
        boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
      }}
    >
      {/* Header */}
      <div
        className="px-3 py-2 flex items-center justify-between flex-shrink-0"
        style={{
          background: 'rgba(0,8,20,0.85)',
          borderBottom: '1px solid rgba(0,212,255,0.12)',
        }}
      >
        <div className="flex items-center gap-2">
          <Cctv className="w-3.5 h-3.5" style={{ color: 'rgba(0,212,255,0.6)' }} />
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.18em]" style={{ color: 'rgba(0,212,255,0.75)' }}>
            NODES
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[9px]" style={{ color: 'rgba(0,255,136,0.6)' }}>
            {onlineCount}/{cameras.length}
          </span>
          <button
            onClick={onRefresh}
            className="p-1 rounded-sm transition-all"
            title="Refresh Cameras"
            style={{ color: 'rgba(0,212,255,0.4)' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#00d4ff')}
            onMouseLeave={e => (e.currentTarget.style.color = 'rgba(0,212,255,0.4)')}
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
        {isLoading && cameras.length === 0 ? (
          <LoadingState message="Scanning network..." className="py-6" />
        ) : error && cameras.length === 0 ? (
          <ErrorState message={error} onRetry={onRefresh} className="p-3" />
        ) : cameras.length === 0 ? (
          <EmptyState title="No cameras" message="No video sources configured" className="py-6" />
        ) : (
          cameras.map((cam) => {
            const isSelected = cam.camera_id === selectedCameraId;
            const dot = getStatusDot(cam.status);
            return (
              <button
                key={cam.camera_id}
                onClick={() => onSelectCamera(cam.camera_id)}
                className="w-full text-left p-2 rounded-sm transition-all duration-150 flex items-center justify-between group"
                style={{
                  background: isSelected ? 'rgba(0,212,255,0.08)' : 'rgba(0,8,20,0.5)',
                  border: isSelected
                    ? '1px solid rgba(0,212,255,0.45)'
                    : '1px solid rgba(0,212,255,0.06)',
                  boxShadow: isSelected ? '0 0 10px rgba(0,212,255,0.1)' : 'none',
                }}
              >
                <div className="flex items-center gap-2 overflow-hidden">
                  <span
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot.anim}`}
                    style={{ background: dot.bg, boxShadow: dot.shadow }}
                  />
                  <div className="truncate">
                    <div className="text-[11px] font-semibold truncate" style={{ color: isSelected ? '#00d4ff' : '#c8d6f0' }}>
                      {cam.name || cam.camera_id}
                    </div>
                    <div className="text-[9px] font-mono truncate" style={{ color: 'rgba(0,212,255,0.35)' }}>
                      {cam.camera_id}
                    </div>
                  </div>
                </div>
                <span
                  className="text-[9px] font-mono font-bold uppercase ml-1 flex-shrink-0 tracking-wider"
                  style={{
                    color: cam.status === 'ONLINE'
                      ? 'rgba(0,255,136,0.7)'
                      : cam.status === 'CONNECTING'
                        ? 'rgba(0,212,255,0.6)'
                        : 'rgba(255,50,50,0.6)',
                  }}
                >
                  {cam.status === 'ONLINE' ? 'ON' : cam.status === 'CONNECTING' ? '...' : 'OFF'}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
