import React, { useState } from 'react';
import { Camera } from '../../types/camera';
import { LiveStream } from './LiveStream';
import { EmptyState } from '../common/EmptyState';
import { LoadingState } from '../common/LoadingState';
import { Grid2x2, Monitor, Grid3x3, LayoutGrid } from 'lucide-react';

interface CameraGridProps {
  cameras: Camera[];
  selectedCameraId: string | null;
  onSelectCamera: (id: string) => void;
  isLoading: boolean;
  error: string | null;
}

type GridLayout = '1x1' | '2x2' | '3x3';

const LAYOUT_CONFIG: Record<GridLayout, { cols: string; max: number; label: string; icon: React.ElementType }> = {
  '1x1': { cols: 'grid-cols-1',                        max: 1,  label: '1×1', icon: Monitor   },
  '2x2': { cols: 'grid-cols-2',                        max: 4,  label: '2×2', icon: Grid2x2   },
  '3x3': { cols: 'grid-cols-3',                        max: 9,  label: '3×3', icon: Grid3x3   },
};

export const CameraGrid: React.FC<CameraGridProps> = ({
  cameras,
  selectedCameraId,
  onSelectCamera,
  isLoading,
  error,
}) => {
  const [layout, setLayout] = useState<GridLayout>('2x2');

  const onlineCameras = cameras.filter(c => c.status !== 'OFFLINE');
  const allCameras = cameras;
  const { cols, max } = LAYOUT_CONFIG[layout];

  // Prioritise selected first, then online, filling up to `max`
  const sorted = [...allCameras].sort((a, b) => {
    if (a.camera_id === selectedCameraId) return -1;
    if (b.camera_id === selectedCameraId) return 1;
    if (a.status === 'ONLINE' && b.status !== 'ONLINE') return -1;
    if (b.status === 'ONLINE' && a.status !== 'ONLINE') return 1;
    return 0;
  });
  const visible = sorted.slice(0, max);

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
      {/* ── Panel Header ──────────────────────────────────────────────────── */}
      <div
        className="px-3 py-2 flex items-center justify-between flex-shrink-0"
        style={{
          background: 'rgba(0,8,20,0.85)',
          borderBottom: '1px solid rgba(0,212,255,0.12)',
        }}
      >
        <div className="flex items-center gap-2">
          <LayoutGrid className="w-3.5 h-3.5" style={{ color: 'rgba(0,212,255,0.7)' }} />
          <span
            className="font-mono text-[11px] font-bold uppercase tracking-[0.18em]"
            style={{ color: 'rgba(0,212,255,0.85)' }}
          >
            SURVEILLANCE MOSAIC
          </span>
          <span
            className="font-mono text-[10px]"
            style={{ color: 'rgba(0,212,255,0.35)' }}
          >
            [{onlineCameras.length}/{cameras.length} ONLINE]
          </span>
        </div>

        {/* Layout picker */}
        <div
          className="flex items-center gap-0.5 p-0.5 rounded-sm"
          style={{ background: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.1)' }}
        >
          {(Object.entries(LAYOUT_CONFIG) as [GridLayout, typeof LAYOUT_CONFIG[GridLayout]][]).map(([key, cfg]) => {
            const Ico = cfg.icon;
            const isActive = layout === key;
            return (
              <button
                key={key}
                onClick={() => setLayout(key)}
                title={cfg.label}
                className="flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono transition-all duration-150"
                style={{
                  background: isActive ? 'rgba(0,212,255,0.18)' : 'transparent',
                  color: isActive ? '#00d4ff' : 'rgba(0,212,255,0.4)',
                  boxShadow: isActive ? '0 0 8px rgba(0,212,255,0.2)' : 'none',
                }}
              >
                <Ico className="w-3 h-3" />
                <span className="hidden sm:inline">{cfg.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Grid Area ─────────────────────────────────────────────────────── */}
      <div className="flex-1 p-2 min-h-0 overflow-auto">
        {isLoading && cameras.length === 0 ? (
          <LoadingState message="Connecting to camera network..." className="flex-1 h-full" />
        ) : error && cameras.length === 0 ? (
          <EmptyState title="Camera network error" message={error} className="flex-1 h-full" />
        ) : cameras.length === 0 ? (
          <EmptyState title="No cameras configured" message="Add cameras in Camera Management" className="flex-1 h-full" />
        ) : (
          <div className={`grid ${cols} gap-2 h-full`}>
            {visible.map((cam) => {
              const isSelected = cam.camera_id === selectedCameraId;
              return (
                <div
                  key={cam.camera_id}
                  onClick={() => onSelectCamera(cam.camera_id)}
                  className="relative rounded-sm overflow-hidden cursor-pointer transition-all duration-200 group"
                  style={{
                    border: isSelected
                      ? '1.5px solid rgba(0,212,255,0.85)'
                      : '1px solid rgba(0,212,255,0.1)',
                    boxShadow: isSelected
                      ? '0 0 16px rgba(0,212,255,0.3), inset 0 0 16px rgba(0,212,255,0.04)'
                      : '0 2px 8px rgba(0,0,0,0.4)',
                    minHeight: layout === '1x1' ? '100%' : layout === '2x2' ? '160px' : '110px',
                  }}
                >
                  {/* Selected indicator corners */}
                  {isSelected && (
                    <>
                      <span className="absolute top-0 left-0 w-3 h-3 border-t-[1.5px] border-l-[1.5px] z-30 pointer-events-none" style={{ borderColor: '#00d4ff' }} />
                      <span className="absolute bottom-0 right-0 w-3 h-3 border-b-[1.5px] border-r-[1.5px] z-30 pointer-events-none" style={{ borderColor: '#00d4ff' }} />
                    </>
                  )}

                  {/* Hover overlay */}
                  <div
                    className="absolute inset-0 z-20 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                    style={{ background: 'rgba(0,212,255,0.03)', border: '1px solid rgba(0,212,255,0.2)' }}
                  />

                  <LiveStream
                    camera={cam}
                    className="w-full h-full"
                    compact={layout === '3x3'}
                  />
                </div>
              );
            })}

            {/* Ghost cells to fill layout grid */}
            {Array.from({ length: Math.max(0, max - visible.length) }).map((_, i) => (
              <div
                key={`ghost-${i}`}
                className="flex items-center justify-center rounded-sm"
                style={{
                  border: '1px dashed rgba(0,212,255,0.08)',
                  background: 'rgba(0,8,20,0.5)',
                  minHeight: layout === '2x2' ? '160px' : '110px',
                }}
              >
                <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: 'rgba(0,212,255,0.15)' }}>
                  NO FEED
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
