import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingState: React.FC<{ message?: string; className?: string }> = ({
  message = 'Loading...',
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-slate-400 space-y-2.5 ${className}`}>
      <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
      <span className="text-xs font-medium">{message}</span>
    </div>
  );
};
