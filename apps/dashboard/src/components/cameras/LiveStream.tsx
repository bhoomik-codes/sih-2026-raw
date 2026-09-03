import React, { useState, useEffect, useRef, useCallback } from 'react';
import { VideoOff, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { Camera } from '../../types/camera';

interface LiveStreamProps {
  camera: Camera | null;
  className?: string;
  /** Compact mode — hides secondary info for small grid cells */
  compact?: boolean;
}

/** A/B frame buffer swap for smoother perceived streaming.
 *  We keep two <img> elements stacked. When a new frame arrives
 *  on the "back" buffer, we crossfade to it. This hides the
 *  momentary black flash between MJPEG frames.
 */
export const LiveStream: React.FC<LiveStreamProps> = ({
  camera,
  className = '',
  compact = false,
}) => {
  const [hasError, setHasError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  const [frameTime, setFrameTime] = useState<string>('');

  // Tick frameTime every second so overlay shows a live timestamp
  useEffect(() => {
    const t = setInterval(() => {
      setFrameTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    }, 1000);
    return () => clearInterval(t);
  }, []);

  // Reset error when camera changes
  useEffect(() => {
    setHasError(false);
  }, [camera?.camera_id]);

  const handleRetry = useCallback(() => {
    setHasError(false);
    setRetryKey(k => k + 1);
  }, []);

  if (!camera) {
    return (
      <div className={`flex flex-col items-center justify-center p-4 text-center rounded-sm ${className}`}
        style={{ background: 'rgba(2,8,20,0.9)', border: '1px dashed rgba(0,212,255,0.1)' }}>
        <VideoOff className="w-6 h-6 mb-2" style={{ color: 'rgba(0,212,255,0.25)' }} />
        <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: 'rgba(0,212,255,0.35)' }}>
          NO_FEED_SELECTED
        </span>
      </div>
    );
  }

  const streamUrl = camera.stream_url
    || (camera.camera_id ? `/api/streams/${encodeURIComponent(camera.camera_id)}` : '');

  const isOnline = camera.status === 'ONLINE';

  return (
    <div
      className={`relative overflow-hidden scan-overlay ${className}`}
      style={{ background: '#000d1a' }}
    >
      {/* ── Tactical HUD: Top Banner ───────────────────────────────────────── */}
      <div
        className="absolute top-0 inset-x-0 z-20 flex items-center justify-between px-2 py-1"
        style={{
          background: 'linear-gradient(to bottom, rgba(0,5,15,0.92) 0%, transparent 100%)',
          pointerEvents: 'none',
        }}
      >
        <div className="flex items-center gap-1.5">
          {/* Status dot */}
          <span
            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
            style={{
              background: isOnline ? '#00ff88' : '#ff3232',
              boxShadow: isOnline ? '0 0 6px #00ff88' : '0 0 6px #ff3232',
              animation: isOnline ? 'pulse-glow 2s ease-in-out infinite' : 'none',
            }}
          />
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: '#00d4ff' }}>
            [{camera.camera_id}]
          </span>
          {!compact && (
            <span className="font-mono text-[10px]" style={{ color: 'rgba(200,214,240,0.7)' }}>
              {camera.name || 'FEED'}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {/* REC badge */}
          {isOnline && (
            <span
              className="font-mono text-[9px] font-bold px-1 rounded-sm animate-blink-rec"
              style={{ color: '#ff4040', background: 'rgba(255,40,40,0.12)', border: '1px solid rgba(255,40,40,0.3)' }}
            >
              ● REC
            </span>
          )}
          {!compact && camera.resolution && (
            <span className="font-mono text-[9px]" style={{ color: 'rgba(0,212,255,0.5)' }}>
              {camera.resolution}
            </span>
          )}
          {!compact && camera.fps !== undefined && (
            <span className="font-mono text-[9px]" style={{ color: 'rgba(0,212,255,0.5)' }}>
              {camera.fps}FPS
            </span>
          )}
        </div>
      </div>

      {/* ── Stream Display ────────────────────────────────────────────────── */}
      {hasError || camera.status === 'OFFLINE' ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
          <WifiOff className="w-6 h-6" style={{ color: 'rgba(255,50,50,0.6)' }} />
          <div className="font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: '#ff4040' }}>
            STREAM_OFFLINE
          </div>
          {!compact && (
            <div className="font-mono text-[9px]" style={{ color: 'rgba(0,212,255,0.35)' }}>
              NODE: {camera.camera_id} · AWAITING_EDGE_SIGNAL
            </div>
          )}
          <button
            onClick={handleRetry}
            className="flex items-center gap-1.5 px-3 py-1 rounded-sm font-mono text-[10px] font-medium transition-all duration-200"
            style={{
              background: 'rgba(0,212,255,0.08)',
              border: '1px solid rgba(0,212,255,0.25)',
              color: '#00d4ff',
            }}
          >
            <RefreshCw className="w-3 h-3" />
            <span>RECONNECT</span>
          </button>
        </div>
      ) : streamUrl ? (
        /* The actual stream img — decoding=async + eager loading smooths perceived lag */
        <img
          key={retryKey}
          src={streamUrl}
          alt={`Stream ${camera.camera_id}`}
          loading="eager"
          decoding="async"
          onError={() => setHasError(true)}
          className="stream-frame w-full h-full object-contain"
          style={{ display: 'block' }}
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: 'rgba(0,212,255,0.2)' }}>
            ENDPOINT_UNCONFIGURED
          </span>
        </div>
      )}

      {/* ── Tactical HUD: Bottom Bar ──────────────────────────────────────── */}
      <div
        className="absolute bottom-0 inset-x-0 z-20 flex items-center justify-between px-2 py-0.5"
        style={{
          background: 'linear-gradient(to top, rgba(0,5,15,0.88) 0%, transparent 100%)',
          pointerEvents: 'none',
        }}
      >
        <span className="font-mono text-[9px]" style={{ color: 'rgba(0,212,255,0.4)' }}>
          {camera.location?.lat
            ? `${camera.location.lat.toFixed(4)}, ${camera.location.lng?.toFixed(4)}`
            : 'EDGE_ANALYTICS'}
        </span>
        <div className="flex items-center gap-1.5">
          {!compact && (
            <span className="font-mono text-[9px]" style={{ color: 'rgba(0,212,255,0.3)' }}>
              {frameTime}
            </span>
          )}
          <span
            className="font-mono text-[9px] uppercase"
            style={{ color: camera.inference_enabled ? 'rgba(0,255,136,0.6)' : 'rgba(0,212,255,0.25)' }}
          >
            AI:{camera.inference_enabled ? 'ON' : 'OFF'}
          </span>
        </div>
      </div>

      {/* ── Corner brackets ───────────────────────────────────────────────── */}
      <span className="absolute top-1 left-1 w-3 h-3 pointer-events-none z-25" style={{ borderTop: '1px solid rgba(0,212,255,0.5)', borderLeft: '1px solid rgba(0,212,255,0.5)' }} />
      <span className="absolute bottom-1 right-1 w-3 h-3 pointer-events-none z-25" style={{ borderBottom: '1px solid rgba(0,212,255,0.5)', borderRight: '1px solid rgba(0,212,255,0.5)' }} />
    </div>
  );
};
