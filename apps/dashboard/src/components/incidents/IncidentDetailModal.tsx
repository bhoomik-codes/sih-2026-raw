import React, { useState, useEffect } from 'react';
import {
  X, Shield, Check, AlertTriangle, Clock, Camera,
  TrendingUp, ChevronRight, Activity, Zap,
} from 'lucide-react';
import { Incident, IncidentContributingEvent } from '../../types/incident';
import { SeverityBadge } from '../common/SeverityBadge';

interface IncidentDetailModalProps {
  incident: Incident;
  onClose: () => void;
  onAcknowledge: (id: string) => Promise<any>;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getRiskColor(score: number): { text: string; bar: string; glow: string } {
  if (score >= 80) return { text: 'text-rose-400', bar: 'bg-rose-500', glow: 'shadow-rose-500/40' };
  if (score >= 60) return { text: 'text-orange-400', bar: 'bg-orange-500', glow: 'shadow-orange-500/40' };
  if (score >= 30) return { text: 'text-amber-400', bar: 'bg-amber-400', glow: 'shadow-amber-400/40' };
  return { text: 'text-cyan-400', bar: 'bg-cyan-400', glow: 'shadow-cyan-400/40' };
}

function getRiskLabel(score: number): string {
  if (score >= 80) return 'CRITICAL';
  if (score >= 60) return 'HIGH';
  if (score >= 30) return 'MEDIUM';
  return 'LOW';
}

function formatTs(ts: string | number | null | undefined): string {
  if (!ts) return '—';
  try {
    if (typeof ts === 'number') {
      return new Date(ts < 1e11 ? ts * 1000 : ts).toLocaleTimeString('en-GB', { hour12: false });
    }
    return new Date(ts).toLocaleTimeString('en-GB', { hour12: false });
  } catch {
    return String(ts);
  }
}

function formatFullTs(ts: string | number | null | undefined): string {
  if (!ts) return '—';
  try {
    const d = typeof ts === 'number' ? new Date(ts < 1e11 ? ts * 1000 : ts) : new Date(ts);
    return d.toLocaleString('en-GB', { hour12: false });
  } catch {
    return String(ts);
  }
}

/** Normalise the event_type from DB (uppercase) or WS (mixed) for display */
function formatEventType(type: string): string {
  return type
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Get contribution events from new DB shape or legacy WS shape */
function getContributingEvents(incident: Incident): Array<{
  key: string;
  label: string;
  score: number;
  severity: string;
  ts: string | number | null | undefined;
  isPrimary: boolean;
}> {
  // New Supabase shape: incident_events[]
  if (incident.incident_events && incident.incident_events.length > 0) {
    return incident.incident_events.map((ie: IncidentContributingEvent, i) => ({
      key: ie.event_id || String(i),
      label: ie.events?.event_type ? formatEventType(String(ie.events.event_type)) : `Event ${i + 1}`,
      score: ie.contribution_score ?? 0,
      severity: ie.events?.severity || 'LOW',
      ts: ie.events?.event_ts,
      isPrimary: ie.is_primary,
    }));
  }

  // Legacy WS shape: triggering_events[]
  if (incident.triggering_events && incident.triggering_events.length > 0) {
    return incident.triggering_events.map((ev, i) => ({
      key: ev.event_id || String(i),
      label: ev.rule_name ? formatEventType(ev.rule_name) : formatEventType(String(ev.event_type)),
      score: 0,
      severity: String(ev.severity),
      ts: ev.timestamp || ev.event_ts,
      isPrimary: i === 0,
    }));
  }

  return [];
}

/** Get the canonical incident ID for the acknowledge call */
function getIncidentId(incident: Incident): string {
  return incident.id || incident.incident_id || '';
}

// ── Risk Gauge ────────────────────────────────────────────────────────────────

const RiskGauge: React.FC<{ score: number }> = ({ score }) => {
  const [animatedScore, setAnimatedScore] = useState(0);
  const colors = getRiskColor(score);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 80);
    return () => clearTimeout(timer);
  }, [score]);

  const circumference = 2 * Math.PI * 36;
  const dashOffset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center w-24 h-24">
      <svg className="w-24 h-24 -rotate-90" viewBox="0 0 80 80">
        {/* Track */}
        <circle
          cx="40" cy="40" r="36"
          fill="none"
          stroke="#232a36"
          strokeWidth="6"
        />
        {/* Progress arc */}
        <circle
          cx="40" cy="40" r="36"
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className={`${colors.text} transition-all duration-700 ease-out`}
          style={{ filter: `drop-shadow(0 0 6px currentColor)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-mono font-black leading-none ${colors.text}`}>
          {animatedScore}
        </span>
        <span className="text-[8px] font-mono text-[#8f9195] uppercase tracking-wider">/ 100</span>
      </div>
    </div>
  );
};

// ── Contribution Bar ──────────────────────────────────────────────────────────

const ContributionBar: React.FC<{
  label: string;
  score: number;
  maxScore: number;
  severity: string;
  ts: string | number | null | undefined;
  isPrimary: boolean;
  index: number;
}> = ({ label, score, maxScore, severity, ts, isPrimary, index }) => {
  const [animatedWidth, setAnimatedWidth] = useState(0);
  const pct = maxScore > 0 ? (score / maxScore) * 100 : 0;
  const sev = severity.toLowerCase();

  const barColor =
    sev === 'critical' ? 'bg-rose-500' :
    sev === 'high'     ? 'bg-orange-500' :
    sev === 'medium'   ? 'bg-amber-400' :
                         'bg-cyan-400';

  useEffect(() => {
    const t = setTimeout(() => setAnimatedWidth(pct), 100 + index * 60);
    return () => clearTimeout(t);
  }, [pct, index]);

  return (
    <div className="group space-y-1">
      <div className="flex items-center justify-between font-mono text-[10px]">
        <div className="flex items-center space-x-1.5">
          {isPrimary && <Zap className="w-2.5 h-2.5 text-amber-400 flex-shrink-0" />}
          {!isPrimary && <ChevronRight className="w-2.5 h-2.5 text-[#8f9195] flex-shrink-0" />}
          <span className="text-[#dce2f3] font-semibold truncate max-w-[160px]">{label}</span>
          <SeverityBadge severity={severity} />
        </div>
        <div className="flex items-center space-x-2 flex-shrink-0">
          {score > 0 && (
            <span className="text-[#dce2f3] font-bold tabular-nums">+{score}</span>
          )}
          <span className="text-[#8f9195]">{formatTs(ts)}</span>
        </div>
      </div>
      {score > 0 && (
        <div className="h-1 w-full bg-[#232a36] rounded-full overflow-hidden">
          <div
            className={`h-full ${barColor} rounded-full transition-all duration-500 ease-out`}
            style={{ width: `${animatedWidth}%` }}
          />
        </div>
      )}
    </div>
  );
};

// ── Main Modal ────────────────────────────────────────────────────────────────

export const IncidentDetailModal: React.FC<IncidentDetailModalProps> = ({
  incident,
  onClose,
  onAcknowledge,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ackError, setAckError] = useState<string | null>(null);
  const [acknowledged, setAcknowledged] = useState(
    incident.status === 'ACKNOWLEDGED' || incident.status === 'acknowledged'
  );

  const incidentId = getIncidentId(incident);
  const contributingEvents = getContributingEvents(incident);
  const colors = getRiskColor(incident.risk_score);
  const maxContribution = Math.max(...contributingEvents.map(e => e.score), 1);
  const totalDerivedScore = contributingEvents.reduce((sum, e) => sum + (e.score || 0), 0);

  // Display code: prefer incident_code, fallback to id prefix or legacy incident_id
  const displayCode = incident.incident_code
    || (incident.id ? `INC-${incident.id.slice(-6).toUpperCase()}` : null)
    || incident.incident_id
    || '—';

  const handleAck = async () => {
    setIsSubmitting(true);
    setAckError(null);
    try {
      await onAcknowledge(incidentId);
      setAcknowledged(true);
    } catch (err: any) {
      setAckError(err.message || 'Failed to acknowledge incident');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-[#070e19]/85 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-[#0f1621] border border-[#374151] rounded-lg max-w-2xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden font-sans">

        {/* ── Header ── */}
        <div className="px-5 py-3.5 border-b border-[#232a36] flex items-center justify-between bg-[#151c27]">
          <div className="flex items-center space-x-3">
            <div className={`w-2 h-2 rounded-full animate-pulse ${
              incident.severity?.toLowerCase() === 'critical' ? 'bg-rose-500' :
              incident.severity?.toLowerCase() === 'high' ? 'bg-orange-500' :
              incident.severity?.toLowerCase() === 'medium' ? 'bg-amber-400' :
              'bg-cyan-400'
            }`} />
            <span className="font-mono font-bold text-sm text-[#dce2f3] tracking-wider">
              {displayCode}
            </span>
            <SeverityBadge severity={incident.severity} />
            {acknowledged && (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-blue-500/15 text-blue-400 border border-blue-500/30">
                ACKNOWLEDGED
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded text-[#8f9195] hover:text-[#dce2f3] hover:bg-[#232a36] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Content ── */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">

          {/* Risk Score + Meta Grid */}
          <div className="flex items-center gap-5 bg-[#070e19] p-4 rounded-lg border border-[#232a36]">
            {/* Animated Ring Gauge */}
            <RiskGauge score={incident.risk_score} />

            {/* Meta */}
            <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-3">
              <div>
                <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-[#8f9195]">RISK LEVEL</div>
                <div className={`text-sm font-mono font-black mt-0.5 ${colors.text}`}>
                  {getRiskLabel(incident.risk_score)}
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-[#8f9195]">CAMERA NODE</div>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <Camera className="w-3 h-3 text-[#8f9195]" />
                  <span className="text-sm font-mono text-[#dce2f3] font-semibold truncate">
                    {incident.camera_id || '—'}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-[#8f9195]">TARGET TRACK</div>
                <div className="text-sm font-mono text-[#dce2f3] font-semibold mt-0.5">
                  {incident.track_id ? `#${incident.track_id}` : '—'}
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-[#8f9195]">INCIDENT TYPE</div>
                <div className="text-sm font-mono text-[#dce2f3] font-semibold mt-0.5 uppercase">
                  {incident.incident_type || '—'}
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-[#8f9195]">FIRST EVENT</div>
                <div className="flex items-center space-x-1 mt-0.5">
                  <Clock className="w-3 h-3 text-[#8f9195]" />
                  <span className="text-[11px] font-mono text-[#c5c6cb]">
                    {formatTs(incident.first_event_ts || incident.timestamp)}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-[#8f9195]">LAST EVENT</div>
                <div className="flex items-center space-x-1 mt-0.5">
                  <Activity className="w-3 h-3 text-[#8f9195]" />
                  <span className="text-[11px] font-mono text-[#c5c6cb]">
                    {formatTs(incident.last_event_ts || incident.timestamp)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Title + Description */}
          {(incident.title || incident.description) && (
            <div className="space-y-1.5">
              {incident.title && (
                <div className="text-sm font-semibold text-[#dce2f3]">{incident.title}</div>
              )}
              {incident.description && (
                <p className="text-xs text-[#c5c6cb] bg-[#070e19] p-3 rounded border border-[#232a36] leading-relaxed">
                  {incident.description}
                </p>
              )}
            </div>
          )}

          {/* ── Explainability Breakdown ── */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Shield className="w-4 h-4 text-blue-400" />
                <span className="font-mono font-bold text-xs text-[#dce2f3] uppercase tracking-wider">
                  WHY DID THIS ALERT FIRE?
                </span>
              </div>
              {totalDerivedScore > 0 && (
                <div className="flex items-center space-x-1.5 text-[10px] font-mono">
                  <TrendingUp className="w-3 h-3 text-[#8f9195]" />
                  <span className="text-[#8f9195]">
                    Σ contributions: <span className={`font-bold ${colors.text}`}>{totalDerivedScore}</span>
                  </span>
                </div>
              )}
            </div>

            <div className="bg-[#070e19] rounded-lg border border-[#232a36] p-4 space-y-3">
              {contributingEvents.length > 0 ? (
                <>
                  {contributingEvents.map((ev, i) => (
                    <ContributionBar
                      key={ev.key}
                      label={ev.label}
                      score={ev.score}
                      maxScore={maxContribution}
                      severity={ev.severity}
                      ts={ev.ts}
                      isPrimary={ev.isPrimary}
                      index={i}
                    />
                  ))}

                  {/* Total bar */}
                  {totalDerivedScore > 0 && (
                    <div className="pt-2 border-t border-[#232a36] flex items-center justify-between font-mono text-[11px]">
                      <span className="text-[#8f9195] uppercase tracking-wider">Total Risk Score</span>
                      <div className="flex items-center space-x-2">
                        <span className={`font-black text-base ${colors.text}`}>
                          {incident.risk_score}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase border ${
                          colors.text === 'text-rose-400'
                            ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                            : colors.text === 'text-orange-400'
                            ? 'bg-orange-500/20 text-orange-300 border-orange-500/40'
                            : colors.text === 'text-amber-400'
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                            : 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                        }`}>
                          {getRiskLabel(incident.risk_score)}
                        </span>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-4 space-y-1">
                  <Shield className="w-6 h-6 text-[#45474a] mx-auto" />
                  <div className="text-[11px] font-mono text-[#8f9195]">
                    Event correlation data not yet available
                  </div>
                  <div className="text-[10px] text-[#45474a]">
                    Individual events will appear here once the edge pipeline writes them
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ── Three-Clock Timestamp Audit ── */}
          {(incident.first_event_ts || (incident.triggering_events?.[0]?.capture_ts)) && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#8f9195]">
                THREE_CLOCK_LATENCY_AUDIT
              </span>
              <div className="grid grid-cols-3 gap-2 font-mono text-[10px]">
                {[
                  { label: '① CAPTURE_TS', value: incident.first_event_ts || incident.triggering_events?.[0]?.capture_ts, color: 'text-[#dce2f3]' },
                  { label: '② INGEST_TS', value: incident.triggering_events?.[0]?.ingest_ts, color: 'text-emerald-400' },
                  { label: '③ DISPLAY_TS', value: incident.triggering_events?.[0]?.display_ts, color: 'text-blue-400' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="p-2 bg-[#070e19] rounded border border-[#232a36]">
                    <div className="text-[#8f9195] text-[9px] mb-1">{label}</div>
                    <div className={`${color} truncate`}>{value ? formatFullTs(value) : '—'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {ackError && (
            <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 text-[11px] font-mono">
              ERROR: {ackError}
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="px-5 py-3 border-t border-[#232a36] bg-[#0f1621] flex items-center justify-between">
          <div className="text-[10px] text-[#8f9195] font-mono">
            LOGGED: {formatFullTs(incident.created_at || incident.timestamp)}
            {incident.acknowledged_by && (
              <span className="ml-3 text-blue-400">ACK BY: {incident.acknowledged_by}</span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded bg-[#232a36] hover:bg-[#2e3541] text-[#c5c6cb] text-xs font-mono uppercase tracking-wider transition"
            >
              CLOSE
            </button>
            {!acknowledged && (
              <button
                onClick={handleAck}
                disabled={isSubmitting}
                className="flex items-center space-x-1.5 px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-mono font-bold uppercase tracking-wider transition shadow-lg shadow-blue-500/20"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{isSubmitting ? 'PROCESSING...' : 'ACKNOWLEDGE'}</span>
              </button>
            )}
            {acknowledged && (
              <div className="flex items-center space-x-1.5 px-4 py-1.5 rounded bg-blue-500/15 border border-blue-500/30 text-blue-400 text-xs font-mono font-bold uppercase tracking-wider">
                <Check className="w-3.5 h-3.5" />
                <span>ACKNOWLEDGED</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
