/**
 * IBVAP — Alert Toast System (Revamped)
 * - Bottom-right position (away from nav interactions)
 * - Max 3 visible toasts at once
 * - 10-second dedup cooldown per camera+severity combo
 * - Slim glass-style pill cards with animated progress bar
 * - Slide-in-up animation (not right, less disruptive)
 */

import React, { useEffect, useCallback, useRef } from 'react';
import { create } from 'zustand';
import { X, AlertTriangle, Shield, Bell, BellOff } from 'lucide-react';

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
  /** ms before auto-dismiss */
  duration?: number;
}

// ── Dedup map (camera+severity → last toast timestamp) ────────────────────────
const dedupMap = new Map<string, number>();
const DEDUP_COOLDOWN_MS = 10_000;

// ── Store ──────────────────────────────────────────────────────────────────────

interface ToastStore {
  toasts: ToastItem[];
  soundEnabled: boolean;
  push: (toast: Omit<ToastItem, 'id' | 'timestamp'>) => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
  toggleSound: () => void;
}

const SEVERITY_DURATION: Record<string, number> = {
  CRITICAL: 10000,
  HIGH: 7000,
  MEDIUM: 5000,
  LOW: 5000,
};

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],
  soundEnabled: true,

  push(item) {
    const sev = item.severity?.toUpperCase() ?? 'LOW';
    const dedupKey = `${item.cameraId ?? 'unknown'}::${sev}`;
    const now = Date.now();

    // Dedup: skip if same camera+severity was toasted within cooldown window
    const lastToasted = dedupMap.get(dedupKey);
    if (lastToasted && now - lastToasted < DEDUP_COOLDOWN_MS) return;
    dedupMap.set(dedupKey, now);

    const toast: ToastItem = {
      ...item,
      id: `toast_${now}_${Math.random().toString(36).slice(2, 5)}`,
      timestamp: now,
      duration: item.duration ?? SEVERITY_DURATION[sev] ?? 6000,
    };

    // Cap at 3 visible toasts — drop the oldest
    set(state => ({
      toasts: [toast, ...state.toasts].slice(0, 3),
    }));

    // Sound: CRITICAL & HIGH only
    if (get().soundEnabled && (sev === 'CRITICAL' || sev === 'HIGH')) {
      try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(sev === 'CRITICAL' ? 900 : 660, ctx.currentTime);
        gain.gain.setValueAtTime(0.06, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.35);
      } catch { /* Audio unavailable — ignore */ }
    }
  },

  dismiss(id) {
    set(state => ({ toasts: state.toasts.filter(t => t.id !== id) }));
  },

  dismissAll() {
    set({ toasts: [] });
  },

  toggleSound() {
    set(state => ({ soundEnabled: !state.soundEnabled }));
  },
}));

// ── Hook ──────────────────────────────────────────────────────────────────────

export function usePushIncidentToast() {
  const push = useToastStore(s => s.push);
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

// ── Severity style tokens ──────────────────────────────────────────────────────

const SEV_STYLES: Record<string, { borderColor: string; iconColor: string; badgeBg: string; badgeText: string; barColor: string }> = {
  CRITICAL: {
    borderColor: 'rgba(255,50,50,0.55)',
    iconColor: '#ff5050',
    badgeBg: 'rgba(255,50,50,0.15)',
    badgeText: '#ff7070',
    barColor: '#ff3232',
  },
  HIGH: {
    borderColor: 'rgba(255,140,0,0.55)',
    iconColor: '#ffaa00',
    badgeBg: 'rgba(255,140,0,0.12)',
    badgeText: '#ffbf44',
    barColor: '#ff9900',
  },
  MEDIUM: {
    borderColor: 'rgba(255,200,0,0.5)',
    iconColor: '#ffd000',
    badgeBg: 'rgba(255,200,0,0.1)',
    badgeText: '#ffdf55',
    barColor: '#ffd000',
  },
  LOW: {
    borderColor: 'rgba(0,212,255,0.3)',
    iconColor: '#00d4ff',
    badgeBg: 'rgba(0,212,255,0.08)',
    badgeText: '#4dd9ff',
    barColor: '#00d4ff',
  },
};

function getStyles(sev: string) {
  return SEV_STYLES[sev?.toUpperCase()] ?? SEV_STYLES.LOW;
}

// ── Toast Card ────────────────────────────────────────────────────────────────

const ToastCard: React.FC<{ toast: ToastItem; onDismiss: (id: string) => void }> = ({
  toast,
  onDismiss,
}) => {
  const s = getStyles(toast.severity);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isCritical = toast.severity?.toUpperCase() === 'CRITICAL';

  useEffect(() => {
    timerRef.current = setTimeout(() => onDismiss(toast.id), toast.duration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [toast.id, toast.duration, onDismiss]);

  return (
    <div
      className="relative overflow-hidden animate-slide-in-up"
      style={{
        width: '280px',
        background: 'rgba(4,12,28,0.92)',
        backdropFilter: 'blur(14px)',
        border: `1px solid ${s.borderColor}`,
        borderRadius: '4px',
        boxShadow: `0 4px 20px rgba(0,0,0,0.6), 0 0 12px ${s.borderColor}`,
      }}
      role="alert"
    >
      {/* Progress bar at bottom */}
      <div
        className="absolute bottom-0 left-0 h-[2px]"
        style={{
          background: s.barColor,
          boxShadow: `0 0 6px ${s.barColor}`,
          animation: `shrink-width ${toast.duration}ms linear forwards`,
        }}
      />

      <div className="p-3 flex items-start gap-2">
        {/* Icon */}
        <div className={`flex-shrink-0 mt-0.5 ${isCritical ? 'animate-pulse' : ''}`}>
          {isCritical
            ? <AlertTriangle style={{ width: 14, height: 14, color: s.iconColor }} />
            : <Shield style={{ width: 14, height: 14, color: s.iconColor }} />
          }
        </div>

        <div className="flex-1 min-w-0">
          {/* Top row: severity badge + risk */}
          <div className="flex items-center gap-1.5 mb-1">
            <span
              className="px-1 py-0.5 rounded-sm font-mono text-[9px] font-bold uppercase"
              style={{ background: s.badgeBg, color: s.badgeText, border: `1px solid ${s.borderColor}` }}
            >
              {toast.severity?.toUpperCase()}
            </span>
            {toast.riskScore !== undefined && (
              <span className="font-mono text-[9px]" style={{ color: 'rgba(0,212,255,0.5)' }}>
                RISK: <span style={{ color: s.iconColor, fontWeight: 700 }}>{toast.riskScore}</span>
              </span>
            )}
          </div>

          {/* Title */}
          <div className="font-semibold text-[11px] truncate" style={{ color: '#c8d6f0' }}>
            {toast.title}
          </div>

          {/* Subtitle */}
          {toast.subtitle && (
            <div className="font-mono text-[9px] truncate mt-0.5" style={{ color: 'rgba(0,212,255,0.45)' }}>
              {toast.subtitle}
            </div>
          )}
        </div>

        {/* Dismiss */}
        <button
          onClick={() => onDismiss(toast.id)}
          className="flex-shrink-0 p-0.5 rounded transition-colors"
          style={{ color: 'rgba(0,212,255,0.35)' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#00d4ff')}
          onMouseLeave={e => (e.currentTarget.style.color = 'rgba(0,212,255,0.35)')}
        >
          <X style={{ width: 11, height: 11 }} />
        </button>
      </div>
    </div>
  );
};

// ── Container ─────────────────────────────────────────────────────────────────

export const ToastContainer: React.FC = () => {
  const toasts = useToastStore(s => s.toasts);
  const soundEnabled = useToastStore(s => s.soundEnabled);
  const dismiss = useToastStore(s => s.dismiss);
  const dismissAll = useToastStore(s => s.dismissAll);
  const toggleSound = useToastStore(s => s.toggleSound);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-2 items-end"
      aria-live="polite"
      aria-label="Alert notifications"
    >
      {/* Controls row */}
      <div className="flex items-center gap-2 mt-1">
        <button
          onClick={toggleSound}
          title={soundEnabled ? 'Mute alerts' : 'Enable alert sounds'}
          className="p-1 rounded transition-all"
          style={{
            background: 'rgba(4,12,28,0.85)',
            border: '1px solid rgba(0,212,255,0.15)',
            color: soundEnabled ? '#ffb800' : 'rgba(0,212,255,0.35)',
          }}
        >
          {soundEnabled
            ? <Bell style={{ width: 11, height: 11 }} />
            : <BellOff style={{ width: 11, height: 11 }} />
          }
        </button>
        {toasts.length > 1 && (
          <button
            onClick={dismissAll}
            className="font-mono text-[9px] px-2 py-1 rounded transition-all uppercase tracking-wider"
            style={{
              background: 'rgba(4,12,28,0.85)',
              border: '1px solid rgba(0,212,255,0.15)',
              color: 'rgba(0,212,255,0.5)',
            }}
          >
            CLEAR ALL ({toasts.length})
          </button>
        )}
      </div>

      {/* Toast cards (rendered bottom-to-top via flex-col-reverse) */}
      {toasts.map(toast => (
        <ToastCard key={toast.id} toast={toast} onDismiss={dismiss} />
      ))}
    </div>
  );
};
