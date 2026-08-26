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
  const [formData, setFormData] = useState<CameraCreatePayload>({
    camera_id: '',
    name: '',
    source_url: '',
    source_type: 'rtsp',
    inference_enabled: true,
  });
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.camera_id || !formData.source_url) return;
    setIsSubmitting(true);
    setActionError(null);
    try {
      await createCamera(formData);
      setActionSuccess(`Camera ${formData.camera_id} registered successfully.`);
      setShowAddModal(false);
      setFormData({
        camera_id: '',
        name: '',
        source_url: '',
        source_type: 'rtsp',
        inference_enabled: true,
      });
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || 'Failed to register camera');
    } finally {
      setIsSubmitting(false);
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

      {/* Add Camera Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Register New Camera
            </h2>

            <form onSubmit={handleCreate} className="space-y-3 text-xs font-mono">
              <div>
                <label className="block text-slate-400 mb-1">Camera ID (e.g. BOP-CAM-02)</label>
                <input
                  type="text"
                  required
                  value={formData.camera_id}
                  onChange={(e) => setFormData({ ...formData, camera_id: e.target.value })}
                  placeholder="BOP-CAM-02"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Display Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Border Post North Gate"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Source URL / Path</label>
                <input
                  type="text"
                  required
                  value={formData.source_url}
                  onChange={(e) => setFormData({ ...formData, source_url: e.target.value })}
                  placeholder="rtsp://192.168.1.50:554/stream or /data/videos/test.mp4"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 mb-1">Source Type</label>
                  <select
                    value={formData.source_type}
                    onChange={(e) =>
                      setFormData({ ...formData, source_type: e.target.value as CameraSourceType })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value="rtsp">RTSP IP Camera</option>
                    <option value="http">HTTP Video / Smartphone</option>
                    <option value="mjpeg">MJPEG Stream</option>
                    <option value="file">Local Video File</option>
                    <option value="webcam">USB Webcam</option>
                  </select>
                </div>

                <div className="flex items-center space-x-2 pt-5">
                  <input
                    type="checkbox"
                    id="inf"
                    checked={formData.inference_enabled}
                    onChange={(e) => setFormData({ ...formData, inference_enabled: e.target.checked })}
                    className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                  />
                  <label htmlFor="inf" className="text-slate-300 text-[11px]">
                    Enable Edge AI
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-semibold disabled:opacity-50"
                >
                  {isSubmitting ? 'Registering...' : 'Register Camera'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
