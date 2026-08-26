import React from 'react';
import { Activity } from 'lucide-react';
import { SystemMetrics } from '../../types/metrics';

interface SystemHealthBarProps {
  metrics: SystemMetrics | null;
  isLoading: boolean;
  error: string | null;
}

export const SystemHealthBar: React.FC<SystemHealthBarProps> = ({
  metrics,
  isLoading,
  error,
}) => {
  const formatVal = (val: number | null | undefined, unit: string = ''): string => {
    if (val === null || val === undefined) return '—';
    return `${val}${unit}`;
  };

  const formatVram = (): string => {
    if (!metrics || metrics.vram_used_mb === null || metrics.vram_total_mb === null) return '—';
    const usedGb = (metrics.vram_used_mb / 1024).toFixed(1);
    const totalGb = (metrics.vram_total_mb / 1024).toFixed(0);
    return `${usedGb}/${totalGb} GB`;
  };

  return (
    <div className="bg-[#151c27] rounded-sm border border-[#232a36] py-2 px-3 flex items-center justify-between text-xs font-mono select-none overflow-x-auto">
      <div className="flex items-center space-x-2 text-[#8f9195] font-bold uppercase tracking-wider text-[10px] pr-3 border-r border-[#232a36] flex-shrink-0">
        <Activity className="w-3.5 h-3.5 text-blue-400" />
        <span>SYS_TELEMETRY</span>
      </div>

      <div className="flex items-center space-x-4 px-2 flex-shrink-0 text-[11px]">
        {/* GPU */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[#8f9195]">GPU:</span>
          <span className="text-[#dce2f3] font-bold">{formatVal(metrics?.gpu_utilization_pct, '%')}</span>
        </div>

        {/* VRAM */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[#8f9195]">VRAM:</span>
          <span className="text-[#dce2f3] font-bold">{formatVram()}</span>
        </div>

        {/* Temperature */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[#8f9195]">TEMP:</span>
          <span className="text-[#dce2f3] font-bold">{formatVal(metrics?.gpu_temp_c, '°C')}</span>
        </div>

        {/* Inference FPS */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[#8f9195]">INFERENCE:</span>
          <span className="text-blue-400 font-bold">
            {metrics?.inference_fps !== null && metrics?.inference_fps !== undefined
              ? `${metrics.inference_fps.toFixed(1)} FPS`
              : '—'}
          </span>
        </div>

        {/* Latency */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[#8f9195]">LATENCY:</span>
          <span className="text-emerald-400 font-bold">
            {metrics?.inference_latency_ms !== null && metrics?.inference_latency_ms !== undefined
              ? `${metrics.inference_latency_ms.toFixed(1)} ms`
              : '—'}
          </span>
        </div>

        {/* Dropped Frames */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[#8f9195]">DROP:</span>
          <span className="text-[#dce2f3] font-bold">
            {metrics?.dropped_ratio !== null && metrics?.dropped_ratio !== undefined
              ? `${(metrics.dropped_ratio * 100).toFixed(1)}%`
              : metrics?.dropped_frames !== null && metrics?.dropped_frames !== undefined
              ? `${metrics.dropped_frames}`
              : '—'}
          </span>
        </div>

        {/* Queue Depth */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[#8f9195]">QUEUE:</span>
          <span className="text-[#dce2f3] font-bold">{formatVal(metrics?.queue_depth)}</span>
        </div>
      </div>

      <div className="pl-3 border-l border-[#232a36] text-[10px] font-mono text-[#8f9195] flex-shrink-0">
        {metrics ? 'SIGNAL: SYNCED' : isLoading ? 'POLLING...' : 'SIGNAL: STANDBY'}
      </div>
    </div>
  );
};
