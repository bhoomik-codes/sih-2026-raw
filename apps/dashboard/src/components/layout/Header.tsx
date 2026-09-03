import React, { useState, useEffect } from 'react';
import { HealthStatusLevel } from '../../types/health';
import { ConnectionBadge } from '../common/ConnectionBadge';
import { NavigationTabs, DashboardPage } from './NavigationTabs';

interface HeaderProps {
  healthStatus: HealthStatusLevel;
  currentPage: DashboardPage;
  onSelectPage: (page: DashboardPage) => void;
  activeIncidentCount?: number;
}

export const Header: React.FC<HeaderProps> = ({
  healthStatus,
  currentPage,
  onSelectPage,
  activeIncidentCount = 0,
}) => {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [currentDate, setCurrentDate] = useState<string>('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('en-US', { hour12: false }));
      setCurrentDate(
        now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
          .toUpperCase()
          .replace(/ /g, '-')
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const threatLevel = activeIncidentCount === 0
    ? { label: 'NOMINAL', color: 'text-emerald-400', bg: 'bg-emerald-400/10 border-emerald-400/30' }
    : activeIncidentCount <= 2
      ? { label: 'ELEVATED', color: 'text-amber-400', bg: 'bg-amber-400/10 border-amber-400/30' }
      : { label: 'CRITICAL', color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/30' };

  return (
    <header
      className="flex-shrink-0 h-14 flex items-center justify-between px-4 z-40 select-none scan-sweep"
      style={{
        background: 'linear-gradient(180deg, rgba(0,8,20,0.98) 0%, rgba(2,12,30,0.95) 100%)',
        borderBottom: '1px solid rgba(0, 212, 255, 0.2)',
        boxShadow: '0 1px 0 rgba(0,212,255,0.08), 0 4px 20px rgba(0,0,0,0.6)',
      }}
    >
      {/* ── Brand / Logo ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Logo image with glitch on hover */}
        <div className="animate-glitch flex-shrink-0">
          <img
            src="/ibvap_logo.jpg"
            alt="IBVAP Logo"
            className="h-8 w-8 rounded object-cover"
            style={{ filter: 'brightness(1.1) saturate(1.2)' }}
          />
        </div>

        {/* Wordmark */}
        <div className="flex flex-col leading-none">
          <span
            className="font-bold text-sm tracking-[0.18em] uppercase text-glow-cyan"
            style={{ fontFamily: "'Orbitron', monospace", color: '#00d4ff', lineHeight: 1 }}
          >
            IBVAP
          </span>
          <span
            className="font-mono text-[9px] tracking-[0.22em] uppercase mt-0.5"
            style={{ color: 'rgba(0,212,255,0.5)', lineHeight: 1 }}
          >
            SSB · SOC · SECTOR-4
          </span>
        </div>

        {/* Divider */}
        <div className="hidden sm:block h-7 w-px mx-1" style={{ background: 'rgba(0,212,255,0.15)' }} />

        {/* LIVE badge */}
        <div className="hidden sm:flex live-badge">
          <span className="dot" />
          LIVE
        </div>

        {/* Threat level */}
        <div className={`hidden md:flex items-center gap-1.5 px-2 py-0.5 rounded-sm border text-[10px] font-mono font-bold tracking-widest ${threatLevel.bg} ${threatLevel.color}`}>
          THREAT: <span>{threatLevel.label}</span>
          {activeIncidentCount > 0 && (
            <span className="ml-1 opacity-70">({activeIncidentCount})</span>
          )}
        </div>
      </div>

      {/* ── Center Navigation ─────────────────────────────────────────────── */}
      <div className="hidden lg:block">
        <NavigationTabs
          currentPage={currentPage}
          onSelectPage={onSelectPage}
          activeIncidentCount={activeIncidentCount}
        />
      </div>

      {/* ── Right Status Cluster ───────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <ConnectionBadge status={healthStatus} />

        <div
          className="hidden sm:flex flex-col items-end pl-3"
          style={{ borderLeft: '1px solid rgba(0,212,255,0.12)' }}
        >
          <span className="font-mono text-[11px] font-bold" style={{ color: '#00d4ff', letterSpacing: '0.1em' }}>
            {currentTime}
          </span>
          <span className="font-mono text-[9px] tracking-widest" style={{ color: 'rgba(0,212,255,0.4)' }}>
            {currentDate} · UTC+5:30
          </span>
        </div>
      </div>
    </header>
  );
};
