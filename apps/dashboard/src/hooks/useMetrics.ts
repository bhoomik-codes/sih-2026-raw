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
      setMetrics(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Metrics unavailable');
      setMetrics(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    // Poll metrics every 5 seconds if WebSocket is not streaming metrics
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
