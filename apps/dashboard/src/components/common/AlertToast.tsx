/**
 * IBVAP — Alert Toast System
 * Slide-in real-time alert notifications for WebSocket-delivered incidents/events.
 * Usage:
 *   import { useToastStore, ToastContainer } from '../common/AlertToast';
 *   // Push a toast: useToastStore.getState().push(incident)
 *   // In App.tsx root: <ToastContainer />
 */

import React, { useEffect, useCallback, useRef } from 'react';
import { create } from 'zustand';
import { X, AlertTriangle, Shield, Radio, Bell } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────

export type ToastSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;

export interface ToastItem {
  id: string;
  severity: ToastSeverity;
  title: string;
  subtitle?: string;
  riskScore?: number;
  cameraId?: string;
  timestamp: number;
  /** ms before auto-dismiss — defaults to 8000 */
  duration?: number;
}

// ── Store ──────────────────────────────────────────────────────────────────────

interface ToastStore {
  toasts: ToastItem[];
  soundEnabled: boolean;
  push: (toast: Omit<ToastItem, 'id' | 'timestamp'>) => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
  toggleSound: () => void;
}

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],
  soundEnabled: true,

  push(item) {
    const toast: ToastItem = {
      ...item,
      id: `toast_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      timestamp: Date.now(),
      duration: item.duration ?? (
        item.severity?.toUpperCase() === 'CRITICAL' ? 12000 : 8000
      ),
    };

    // Cap at 5 visible toasts — remove the oldest
    set((state) => ({
      toasts: [toast, ...state.toasts].slice(0, 5),
    }));

    // Play sound if enabled (CRITICAL & HIGH only)
    const sev = item.severity?.toUpperCase();
    if (get().soundEnabled && (sev === 'CRITICAL' || sev === 'HIGH')) {
      try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        const oscillator = ctx.createOscillator();
        const gain = ctx.createGain();
        oscillator.connect(gain);
        gain.connect(ctx.destination);
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(sev === 'CRITICAL' ? 880 : 660, ctx.currentTime);
        gain.gain.setValueAtTime(0.08, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
        oscillator.start(ctx.currentTime);
        oscillator.stop(ctx.currentTime + 0.4);
      } catch {
        // Audio not available — silently ignore
      }
    }
  },

  dismiss(id) {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },

  dismissAll() {
    set({ toasts: [] });
  },

  toggleSound() {
    set((state) => ({ soundEnabled: !state.soundEnabled }));
  },
}));

// ── Hook to push from incident/event data ─────────────────────────────────────

export function usePushIncidentToast() {
  const push = useToastStore((s) => s.push);
  return useCallback(
    (incident: {
      severity?: string;
      title?: string;
      description?: string;
      risk_score?: number;
      camera_id?: string;
      incident_code?: string;
      incident_id?: string;
    }) => {
      const code = incident.incident_code || incident.incident_id || 'ALERT';
      push({
        severity: incident.severity || 'HIGH',
        title: `${code} — ${incident.title || 'Security Alert'}`,
        subtitle: incident.description || `Camera: ${incident.camera_id || 'Unknown'}`,
        riskScore: incident.risk_score,
        cameraId: incident.camera_id,
      });
    },
    [push]
  );
}

// ── Toast Card ────────────────────────────────────────────────────────────────

const SEVERITY_STYLES: Record<string, { border: string; icon: string; badge: string; dot: string }> = {
  CRITICAL: {
    border: 'border-rose-500/60',
    icon: 'text-rose-400',
    badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    dot: 'bg-rose-500',
  },
  HIGH: {
    border: 'border-orange-500/60',
    icon: 'text-orange-400',
    badge: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
    dot: 'bg-orange-500',
  },
  MEDIUM: {
    border: 'border-amber-400/60',
    icon: 'text-amber-400',
    badge: 'bg-amber-400/20 text-amber-300 border-amber-400/40',
    dot: 'bg-amber-400',
  },
  LOW: {
    border: 'border-cyan-400/40',
    icon: 'text-cyan-400',
    badge: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
    dot: 'bg-cyan-400',
  },
};

function getStyles(severity: string) {
  return SEVERITY_STYLES[severity?.toUpperCase()] || SEVERITY_STYLES.LOW;
}

const ToastCard: React.FC<{ toast: ToastItem; onDismiss: (id: string) => void }> = ({
  toast,
  onDismiss,
}) => {
  const styles = getStyles(toast.severity);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    timerRef.current = setTimeout(() => onDismiss(toast.id), toast.duration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [toast.id, toast.duration, onDismiss]);

  const isCritical = toast.severity?.toUpperCase() === 'CRITICAL';

  return (
    <div
      className={`
        relative w-80 bg-[#0f1621] border ${styles.border}
        rounded-lg shadow-2xl overflow-hidden
        animate-slide-in-right
        ${isCritical ? 'shadow-rose-500/10' : ''}
      `}
      role="alert"
    >
      {/* Progress bar */}
      <div
        className={`absolute bottom-0 left-0 h-0.5 ${styles.dot}`}
        style={{
          animation: `shrink-width ${toast.duration}ms linear forwards`,
        }}
      />

      <div className="p-3.5">
        {/* Top row */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center space-x-2">
            <div className={`mt-0.5 ${isCritical ? 'animate-pulse' : ''}`}>
              {isCritical
                ? <AlertTriangle className={`w-4 h-4 ${styles.icon}`} />
                : <Shield className={`w-4 h-4 ${styles.icon}`} />
              }
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-1.5 mb-0.5">
                <span className={`px-1 py-0.5 rounded text-[9px] font-mono font-bold uppercase border ${styles.badge}`}>
                  {toast.severity?.toUpperCase()}
                </span>
                {toast.riskScore !== undefined && (
                  <span className="text-[10px] font-mono text-[#8f9195]">
                    RISK: <span className={`font-bold ${styles.icon}`}>{toast.riskScore}</span>
                  </span>
                )}
              </div>
              <div className="text-xs font-semibold text-[#dce2f3] truncate leading-tight">
                {toast.title}
              </div>
            </div>
          </div>
          <button
            onClick={() => onDismiss(toast.id)}
            className="flex-shrink-0 p-0.5 rounded text-[#8f9195] hover:text-[#dce2f3] hover:bg-[#232a36] transition"
          >
            <X className="w-3 h-3" />
          </button>
        </div>

        {/* Subtitle */}
        {toast.subtitle && (
          <div className="mt-1.5 ml-6 text-[10px] text-[#8f9195] font-mono truncate">
            {toast.subtitle}
          </div>
        )}
      </div>
    </div>
  );
};

// ── Container ─────────────────────────────────────────────────────────────────

export const ToastContainer: React.FC = () => {
  const toasts = useToastStore((s) => s.toasts);
  const soundEnabled = useToastStore((s) => s.soundEnabled);
  const dismiss = useToastStore((s) => s.dismiss);
  const dismissAll = useToastStore((s) => s.dismissAll);
  const toggleSound = useToastStore((s) => s.toggleSound);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 items-end"
      aria-live="polite"
      aria-label="Alert notifications"
    >
      {/* Controls */}
      <div className="flex items-center space-x-2 mb-1">
        <button
          onClick={toggleSound}
          title={soundEnabled ? 'Mute alerts' : 'Enable alert sounds'}
          className="p-1 rounded bg-[#0f1621] border border-[#232a36] text-[#8f9195] hover:text-[#dce2f3] hover:border-[#374151] transition"
        >
          <Bell className={`w-3 h-3 ${soundEnabled ? 'text-amber-400' : ''}`} />
        </button>
        {toasts.length > 1 && (
          <button
            onClick={dismissAll}
            className="text-[10px] font-mono text-[#8f9195] hover:text-[#dce2f3] transition px-1.5 py-1 rounded bg-[#0f1621] border border-[#232a36]"
          >
            CLEAR ALL ({toasts.length})
          </button>
        )}
      </div>

      {/* Toasts */}
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} onDismiss={dismiss} />
      ))}
    </div>
  );
};
