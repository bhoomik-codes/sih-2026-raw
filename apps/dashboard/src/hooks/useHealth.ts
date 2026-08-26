import { useState, useEffect, useCallback } from 'react';
import { HealthStatusLevel } from '../types/health';
import { getHealth } from '../api/health';

export function useHealth(isWsConnected: boolean) {
  const [healthStatus, setHealthStatus] = useState<HealthStatusLevel>('CONNECTING');
  const [activeCameraCount, setActiveCameraCount] = useState<number>(0);
  const [uptimeSeconds, setUptimeSeconds] = useState<number | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const data = await getHealth();
      if (data.status === 'healthy') {
        setHealthStatus(isWsConnected ? 'ONLINE' : 'DEGRADED');
      } else if (data.status === 'degraded') {
        setHealthStatus('DEGRADED');
      } else {
        setHealthStatus('OFFLINE');
      }
      setActiveCameraCount(data.active_cameras || 0);
      setUptimeSeconds(data.uptime_seconds || null);
    } catch {
      setHealthStatus('OFFLINE');
    }
  }, [isWsConnected]);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 8000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return {
    healthStatus,
    activeCameraCount,
    uptimeSeconds,
    refreshHealth: checkHealth,
  };
}
