import { useState, useEffect, useCallback } from 'react';
import { SystemMetrics } from '../types/metrics';
import { getMetrics } from '../api/metrics';

export function useMetrics() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const data = await getMetrics();
      if (data && typeof data === 'object' && Object.keys(data).length > 0) {
        setMetrics(data);
        setError(null);
      }
    } catch {
      // Keep last WebSocket/REST snapshot if the poll fails (e.g. empty demo mode)
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  const handleNewMetrics = useCallback((newMetrics: SystemMetrics) => {
    setMetrics(newMetrics);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    metrics,
    isLoading,
    error,
    refresh: fetchMetrics,
    handleNewMetrics,
  };
}
