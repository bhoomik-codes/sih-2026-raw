import React from 'react';
import { Cctv, RefreshCw } from 'lucide-react';
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
  const getStatusColor = (status: Camera['status']) => {
    switch (status) {
      case 'ONLINE':
        return 'bg-emerald-400';
      case 'CONNECTING':
        return 'bg-blue-400 animate-pulse';
      case 'ERROR':
        return 'bg-rose-500';
      default:
        return 'bg-slate-500';
    }
  };

  return (
    <div className="bg-[#151c27] rounded-sm border border-[#232a36] flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 bg-[#19202b] border-b border-[#232a36] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Cctv className="w-3.5 h-3.5 text-[#8f9195]" />
          <span className="text-[11px] font-mono font-bold text-[#dce2f3] uppercase tracking-wider">
            CAMERA_MATRIX
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[10px] font-mono text-[#8f9195] font-semibold">
            [{cameras.length} NODES]
          </span>
          <button
            onClick={onRefresh}
            className="p-1 rounded-sm text-[#8f9195] hover:text-[#dce2f3] hover:bg-[#232a36] transition"
            title="Refresh Cameras"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
        {isLoading && cameras.length === 0 ? (
          <LoadingState message="Loading cameras..." className="py-6" />
        ) : error && cameras.length === 0 ? (
          <ErrorState message={error} onRetry={onRefresh} className="p-3" />
        ) : cameras.length === 0 ? (
          <EmptyState title="No cameras available" message="No video sources configured on edge node" className="py-6" />
        ) : (
          cameras.map((cam) => {
            const isSelected = cam.camera_id === selectedCameraId;
            return (
              <button
                key={cam.camera_id}
                onClick={() => onSelectCamera(cam.camera_id)}
                className={`w-full text-left p-2 rounded-sm border transition flex items-center justify-between ${
                  isSelected
                    ? 'bg-[#19202b] border-l-2 border-l-blue-400 border-t-[#232a36] border-r-[#232a36] border-b-[#232a36] text-[#dce2f3]'
                    : 'bg-[#0c141f]/70 border-[#232a36]/60 hover:bg-[#19202b]/60 text-[#c5c6cb]'
                }`}
              >
                <div className="flex items-center space-x-2 overflow-hidden">
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${getStatusColor(cam.status)}`} />
                  <div className="truncate">
                    <div className="text-xs font-semibold truncate text-[#dce2f3] font-sans">
                      {cam.name || cam.camera_id}
                    </div>
                    <div className="text-[10px] font-mono text-[#8f9195] truncate">
                      {cam.camera_id}
                    </div>
                  </div>
                </div>

                <div className="text-[9px] font-mono font-bold text-[#8f9195] uppercase ml-2 flex-shrink-0 tracking-wider">
                  {cam.status}
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
