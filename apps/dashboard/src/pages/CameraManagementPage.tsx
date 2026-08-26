import React, { useState } from 'react';
import {
  Cctv,
  Plus,
  Play,
  Square,
  RotateCcw,
  Trash2,
  AlertCircle,
  CheckCircle,
  RefreshCw,
} from 'lucide-react';
import { Camera, CameraCreatePayload, CameraSourceType } from '../types/camera';
import {
  createCamera,
  deleteCamera,
  startCamera,
  stopCamera,
  reconnectCamera,
} from '../api/cameras';
import { LoadingState } from '../components/common/LoadingState';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { CameraConnectionWizard } from '../components/cameras/CameraConnectionWizard';

interface CameraManagementPageProps {
  cameras: Camera[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const CameraManagementPage: React.FC<CameraManagementPageProps> = ({
  cameras,
  isLoading,
  error,
  onRefresh,
}) => {
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const handleWizardSubmit = async (data: CameraCreatePayload) => {
    setActionError(null);
    try {
      await createCamera(data);
      setActionSuccess(`Camera ${data.camera_id} registered successfully.`);
      setShowAddModal(false);
      onRefresh();
    } catch (err: any) {
      throw err;
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(`Are you sure you want to remove camera ${id}?`)) return;
    setActionError(null);
    try {
      await deleteCamera(id);
      setActionSuccess(`Camera ${id} removed.`);
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || `Failed to delete camera ${id}`);
    }
  };

  const handleStart = async (id: string) => {
    setActionError(null);
    try {
      const res = await startCamera(id);
      setActionSuccess(`Camera ${id} started.`);
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || `Failed to start camera ${id}`);
    }
  };

  const handleStop = async (id: string) => {
    setActionError(null);
    try {
      const res = await stopCamera(id);
      setActionSuccess(`Camera ${id} stopped.`);
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || `Failed to stop camera ${id}`);
    }
  };

  const handleReconnect = async (id: string) => {
    setActionError(null);
    try {
      const res = await reconnectCamera(id);
      setActionSuccess(`Reconnecting stream for camera ${id}...`);
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || `Failed to reconnect camera ${id}`);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between bg-slate-900 p-4 rounded-lg border border-slate-800">
        <div>
          <h1 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center space-x-2">
            <Cctv className="w-4 h-4 text-blue-400" />
            <span>Camera Management (FR-01)</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure IP cameras, RTSP streams, USB webcams, and smartphone CCTV sources.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={onRefresh}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Camera</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {actionError && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{actionError}</span>
        </div>
      )}
      {actionSuccess && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center space-x-2">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Camera Table */}
      <div className="flex-1 bg-slate-900 rounded-lg border border-slate-800 overflow-hidden flex flex-col">
        {isLoading && cameras.length === 0 ? (
          <LoadingState message="Loading cameras..." className="flex-1" />
        ) : error && cameras.length === 0 ? (
          <ErrorState message={error} onRetry={onRefresh} className="m-4" />
        ) : cameras.length === 0 ? (
          <EmptyState
            title="No cameras configured"
            message="Click 'Add Camera' above to register a new CCTV, RTSP or smartphone video source"
            className="flex-1"
          />
        ) : (
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left font-mono text-xs">
              <thead className="text-[10px] text-slate-400 uppercase tracking-wider border-b border-slate-800 bg-slate-950/60">
                <tr>
                  <th className="p-3">Status</th>
                  <th className="p-3">Camera ID</th>
                  <th className="p-3">Name</th>
                  <th className="p-3">Source URL</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Inference</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {cameras.map((cam) => (
                  <tr key={cam.camera_id} className="hover:bg-slate-850/50">
                    <td className="p-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          cam.status === 'ONLINE'
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {cam.status}
                      </span>
                    </td>
                    <td className="p-3 font-semibold text-slate-100">{cam.camera_id}</td>
                    <td className="p-3">{cam.name || '—'}</td>
                    <td className="p-3 text-slate-400 truncate max-w-xs">{cam.source_url}</td>
                    <td className="p-3 uppercase text-[10px] text-slate-400">{cam.source_type}</td>
                    <td className="p-3">
                      <span className={cam.inference_enabled ? 'text-emerald-400' : 'text-slate-500'}>
                        {cam.inference_enabled ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => handleStart(cam.camera_id)}
                          className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-emerald-400"
                          title="Start Stream"
                        >
                          <Play className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleStop(cam.camera_id)}
                          className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-amber-400"
                          title="Stop Stream"
                        >
                          <Square className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleReconnect(cam.camera_id)}
                          className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-blue-400"
                          title="Reconnect"
                        >
                          <RotateCcw className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleDelete(cam.camera_id)}
                          className="p-1.5 rounded bg-slate-800 hover:bg-rose-900/50 text-rose-400"
                          title="Delete Camera"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Camera Wizard */}
      {showAddModal && (
        <CameraConnectionWizard
          onClose={() => setShowAddModal(false)}
          onSubmit={handleWizardSubmit}
        />
      )}
    </div>
  );
};
