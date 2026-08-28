import { useState, useEffect, useCallback } from 'react';
import { Incident } from '../types/incident';
import { getIncidents, acknowledgeIncident as apiAcknowledge } from '../api/incidents';

/** Returns the canonical ID for an incident (new DB shape uses `id`, WS uses `incident_id`) */
function getIncidentKey(incident: Incident): string {
  return incident.id || incident.incident_id || '';
}

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
    const newKey = getIncidentKey(newInc);
    setIncidents((prev) => {
      // Deduplicate by either id or incident_id
      const exists = prev.some((i) => getIncidentKey(i) === newKey);
      if (exists) {
        return prev.map((i) => (getIncidentKey(i) === newKey ? newInc : i));
      }
      return [newInc, ...prev];
    });
  }, []);

  const acknowledge = useCallback(async (id: string) => {
    setIsAcknowledging(true);
    try {
      const updated = await apiAcknowledge(id);
      const now = new Date().toISOString();

      setIncidents((prev) =>
        prev.map((i) =>
          getIncidentKey(i) === id
            ? { ...i, status: 'ACKNOWLEDGED', acknowledged_at: now }
            : i
        )
      );
      if (selectedIncident && getIncidentKey(selectedIncident) === id) {
        setSelectedIncident((prev) =>
          prev ? { ...prev, status: 'ACKNOWLEDGED', acknowledged_at: now } : null
        );
      }
      return updated;
    } catch (err: any) {
      throw err;
    } finally {
      setIsAcknowledging(false);
    }
  }, [selectedIncident]);

  const activeIncidents = incidents.filter((i) => {
    const status = i.status?.toUpperCase();
    return status !== 'RESOLVED' && status !== 'FALSE_POSITIVE' && status !== 'DISMISSED' && status !== 'FALSE_ALARM';
  });

  return {
    incidents,
    activeIncidents,
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
