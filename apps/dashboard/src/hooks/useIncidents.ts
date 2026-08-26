import { useState, useEffect, useCallback } from 'react';
import { Incident } from '../types/incident';
import { getIncidents, acknowledgeIncident as apiAcknowledge } from '../api/incidents';

export function useIncidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAcknowledging, setIsAcknowledging] = useState<boolean>(false);

  const fetchIncidents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getIncidents();
      setIncidents(data);
    } catch (err: any) {
      setError(err.message || 'Unable to load incidents');
      setIncidents([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  const handleNewIncident = useCallback((newInc: Incident) => {
    setIncidents((prev) => {
      // Deduplicate if already present
      const exists = prev.some((i) => i.incident_id === newInc.incident_id);
      if (exists) {
        return prev.map((i) => (i.incident_id === newInc.incident_id ? newInc : i));
      }
      return [newInc, ...prev];
    });
  }, []);

  const acknowledge = useCallback(async (id: string) => {
    setIsAcknowledging(true);
    try {
      const updated = await apiAcknowledge(id);
      setIncidents((prev) =>
        prev.map((i) => (i.incident_id === id ? { ...i, status: 'acknowledged', acknowledged_at: Date.now() } : i))
      );
      if (selectedIncident?.incident_id === id) {
        setSelectedIncident((prev) => (prev ? { ...prev, status: 'acknowledged', acknowledged_at: Date.now() } : null));
      }
      return updated;
    } catch (err: any) {
      throw err;
    } finally {
      setIsAcknowledging(false);
    }
  }, [selectedIncident]);

  return {
    incidents,
    activeIncidents: incidents.filter((i) => i.status !== 'resolved' && i.status !== 'false_alarm'),
    selectedIncident,
    setSelectedIncident,
    isLoading,
    error,
    refresh: fetchIncidents,
    handleNewIncident,
    acknowledge,
    isAcknowledging,
  };
}
