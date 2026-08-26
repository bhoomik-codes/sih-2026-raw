import React from 'react';
import { Activity, Cpu, HardDrive, Thermometer, Zap, Layers, RefreshCw } from 'lucide-react';
import { SystemMetrics } from '../types/metrics';
import { HealthStatusLevel } from '../types/health';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';

interface SystemHealthPageProps {
  metrics: SystemMetrics | null;
  healthStatus: HealthStatusLevel;
  activeCameraCount: number;
  uptimeSeconds: number | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const SystemHealthPage: React.FC<SystemHealthPageProps> = ({
  metrics,
  healthStatus,
  activeCameraCount,
  uptimeSeconds,
  isLoading,
  error,
  onRefresh,
}) => {
  const formatVal = (val: number | null | undefined, unit: string = ''): string => {
    if (val === null || val === undefined) return '—';
    return `${val}${unit}`;
  };

  const formatVram = (): string => {
    if (!metrics || metrics.vram_used_mb === null || metrics.vram_total_mb === null) return '—';
    return `${(metrics.vram_used_mb / 1024).toFixed(1)} / ${(metrics.vram_total_mb / 1024).toFixed(0)} GB`;
  };

  const formatRam = (): string => {
    if (!metrics || metrics.ram_used_mb === null || metrics.ram_total_mb === null) return '—';
    return `${(metrics.ram_used_mb / 1024).toFixed(1)} / ${(metrics.ram_total_mb / 1024).toFixed(0)} GB`;
  };

  const formatUptime = (): string => {
    if (uptimeSeconds === null || uptimeSeconds === undefined) return '—';
    const hrs = Math.floor(uptimeSeconds / 3600);
    const mins = Math.floor((uptimeSeconds % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto p-4 space-y-4 font-mono text-xs">
      {/* Header */}
      <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 flex items-center justify-between">
        <div>
          <h1 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center space-x-2 font-sans">
            <Activity className="w-4 h-4 text-blue-400" />
            <span>System Observability & Health (Laptop 1 / Laptop 2)</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5 font-sans">
            Real-time hardware metrics and pipeline latency reported by the Edge AI inference node.
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {isLoading && !metrics ? (
        <LoadingState message="Loading system metrics..." className="py-12" />
      ) : error && !metrics ? (
        <ErrorState message={error} onRetry={onRefresh} className="py-12" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Edge GPU & VRAM */}
          <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center space-x-2 text-slate-200 font-bold uppercase tracking-wider font-sans border-b border-slate-800 pb-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Edge GPU (Laptop 1)</span>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">GPU Utilization:</span>
                <span className="text-slate-100 font-semibold">{formatVal(metrics?.gpu_utilization_pct, '%')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">VRAM Usage:</span>
                <span className="text-slate-100 font-semibold">{formatVram()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">GPU Temperature:</span>
                <span className="text-slate-100 font-semibold">{formatVal(metrics?.gpu_temp_c, '°C')}</span>
              </div>
            </div>
          </div>

          {/* Card 2: Host CPU & RAM */}
          <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center space-x-2 text-slate-200 font-bold uppercase tracking-wider font-sans border-b border-slate-800 pb-2">
              <Cpu className="w-4 h-4 text-blue-400" />
              <span>Host CPU & Memory</span>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">CPU Usage:</span>
                <span className="text-slate-100 font-semibold">{formatVal(metrics?.cpu_utilization_pct, '%')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Host RAM:</span>
                <span className="text-slate-100 font-semibold">{formatRam()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">System Uptime:</span>
                <span className="text-slate-100 font-semibold">{formatUptime()}</span>
              </div>
            </div>
          </div>

          {/* Card 3: Inference & Pipeline Performance */}
          <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center space-x-2 text-slate-200 font-bold uppercase tracking-wider font-sans border-b border-slate-800 pb-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span>Inference Pipeline</span>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Inference Rate:</span>
                <span className="text-emerald-400 font-bold">
                  {metrics?.inference_fps !== null && metrics?.inference_fps !== undefined
                    ? `${metrics.inference_fps.toFixed(1)} FPS`
                    : '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Inference Latency:</span>
                <span className="text-blue-400 font-semibold">
                  {metrics?.inference_latency_ms !== null && metrics?.inference_latency_ms !== undefined
                    ? `${metrics.inference_latency_ms.toFixed(1)} ms`
                    : '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Total Pipeline Latency:</span>
                <span className="text-slate-100 font-semibold">
                  {metrics?.total_latency_ms !== null && metrics?.total_latency_ms !== undefined
                    ? `${metrics.total_latency_ms.toFixed(1)} ms`
                    : '—'}
                </span>
              </div>
            </div>
          </div>

          {/* Card 4: Frame Queue & Loss */}
          <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center space-x-2 text-slate-200 font-bold uppercase tracking-wider font-sans border-b border-slate-800 pb-2">
              <HardDrive className="w-4 h-4 text-purple-400" />
              <span>Queue & Frame Loss</span>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Queue Depth:</span>
                <span className="text-slate-100 font-semibold">{formatVal(metrics?.queue_depth)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Dropped Ratio:</span>
                <span className="text-slate-100 font-semibold">
                  {metrics?.dropped_ratio !== null && metrics?.dropped_ratio !== undefined
                    ? `${(metrics.dropped_ratio * 100).toFixed(1)}%`
                    : '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Total Processed Frames:</span>
                <span className="text-slate-100 font-semibold">{formatVal(metrics?.processed_frames)}</span>
              </div>
            </div>
          </div>

          {/* Card 5: Pipeline Component Status */}
          <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center space-x-2 text-slate-200 font-bold uppercase tracking-wider font-sans border-b border-slate-800 pb-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>Component Status</span>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Detector:</span>
                <span className="text-emerald-400 font-semibold">{metrics?.detector_status || 'Active'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Tracker:</span>
                <span className="text-emerald-400 font-semibold">{metrics?.tracker_status || 'Active (ByteTrack)'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Active Cameras:</span>
                <span className="text-slate-100 font-semibold">{activeCameraCount}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
