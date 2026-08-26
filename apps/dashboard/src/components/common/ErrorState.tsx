import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}> = ({
  title = 'Backend unavailable',
  message,
  onRetry,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-6 text-center text-slate-400 space-y-2.5 bg-slate-950/40 rounded-lg border border-slate-800 ${className}`}>
      <AlertCircle className="w-6 h-6 text-rose-500/80" />
      <div className="text-xs font-semibold text-slate-300">{title}</div>
      {message && <div className="text-[11px] text-slate-500 max-w-sm">{message}</div>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
};
