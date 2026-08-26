import React from 'react';
import { Inbox } from 'lucide-react';

export const EmptyState: React.FC<{
  title?: string;
  message?: string;
  icon?: React.ElementType;
  className?: string;
}> = ({
  title = 'No data available',
  message,
  icon: Icon = Inbox,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center text-slate-500 space-y-2 ${className}`}>
      <Icon className="w-8 h-8 text-slate-600 mb-1" />
      <div className="text-xs font-semibold text-slate-400">{title}</div>
      {message && <div className="text-[11px] text-slate-500 max-w-sm">{message}</div>}
    </div>
  );
};
