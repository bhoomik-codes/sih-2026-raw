import React, { useState } from 'react';
import { VideoOff, RefreshCw } from 'lucide-react';
import { Camera } from '../../types/camera';

interface LiveStreamProps {
  camera: Camera | null;
  className?: string;
}

export const LiveStream: React.FC<LiveStreamProps> = ({ camera, className = '' }) => {
  const [hasError, setHasError] = useState<boolean>(false);
  const [retryKey, setRetryKey] = useState<number>(0);

  if (!camera) {
    return (
      <div className={`bg-[#070e19] flex flex-col items-center justify-center p-8 text-center text-[#8f9195] rounded-sm border border-[#232a36] ${className}`}>
        <VideoOff className="w-8 h-8 text-[#45474a] mb-2" />
        <span className="text-xs font-mono font-semibold text-[#c5c6cb] uppercase">NO_CAMERA_SELECTED</span>
        <span className="text-[11px] text-[#8f9195] mt-1">Select a camera node from matrix to view feed</span>
      </div>
    );
  }

  const streamUrl = camera.stream_url || (camera.camera_id ? `/api/streams/${encodeURIComponent(camera.camera_id)}` : '');

  const handleRetry = () => {
    setHasError(false);
    setRetryKey((k) => k + 1);
  };

  return (
    <div className={`relative bg-[#070e19] flex items-center justify-center rounded-sm border border-[#232a36] overflow-hidden ${className}`}>
      {/* Stream Top Banner (Tactical Overlay) */}
      <div className="absolute top-0 inset-x-0 p-2 bg-gradient-to-b from-[#070e19]/90 via-[#070e19]/40 to-transparent z-20 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center space-x-2">
          <span className={`w-1.5 h-1.5 rounded-full ${camera.status === 'ONLINE' ? 'bg-emerald-400' : 'bg-rose-500'}`} />
          <span className="font-bold text-[#dce2f3] text-[11px] tracking-wider uppercase">[{camera.camera_id}]</span>
          <span className="text-[11px] text-[#c5c6cb] font-sans font-semibold">
            {camera.name || 'FEED'}
          </span>
        </div>

        <div className="flex items-center space-x-2 text-[10px] font-mono text-[#8f9195]">
          {camera.resolution && <span>{camera.resolution}</span>}
          {camera.fps !== undefined && <span>{camera.fps} FPS</span>}
          <span className="px-1.5 py-0.2 rounded-sm bg-[#19202b] text-[#c5c6cb] uppercase border border-[#232a36]">
            {camera.source_type}
          </span>
        </div>
      </div>

      {/* Stream Display */}
      {hasError || camera.status === 'OFFLINE' ? (
        <div className="flex flex-col items-center justify-center p-8 text-center text-[#8f9195] space-y-2">
          <VideoOff className="w-8 h-8 text-rose-400/80 mb-1" />
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-rose-400">
            STREAM_OFFLINE
          </div>
          <div className="text-[10px] font-mono text-[#8f9195]">
            NODE: {camera.camera_id} • AWAITING_EDGE_SIGNAL
          </div>
          <button
            onClick={handleRetry}
            className="flex items-center space-x-1.5 px-3 py-1 rounded-sm bg-[#19202b] hover:bg-[#232a36] text-[#dce2f3] text-[11px] font-mono font-medium border border-[#232a36] transition"
          >
            <RefreshCw className="w-3 h-3" />
            <span>RECONNECT</span>
          </button>
        </div>
      ) : streamUrl ? (
        <img
          key={retryKey}
          src={streamUrl}
          alt={`Annotated stream for ${camera.camera_id}`}
          onError={() => setHasError(true)}
          className="w-full h-full object-contain"
        />
      ) : (
        <div className="flex flex-col items-center justify-center p-8 text-[#8f9195] text-xs font-mono">
          <span>ENDPOINT_UNCONFIGURED</span>
        </div>
      )}

      {/* Stream Bottom Info */}
      <div className="absolute bottom-0 inset-x-0 p-1.5 bg-gradient-to-t from-[#070e19]/90 to-transparent z-20 flex items-center justify-between text-[10px] font-mono text-[#8f9195]">
        <div>{camera.location?.lat ? `POS: ${camera.location.lat}, ${camera.location.lng}` : 'EDGE_ANALYTICS: ACTIVE'}</div>
        <div className="uppercase text-[9px] text-[#8f9195]">
          AI_INFERENCE: {camera.inference_enabled ? 'ENABLED' : 'DISABLED'}
        </div>
      </div>
    </div>
  );
};
