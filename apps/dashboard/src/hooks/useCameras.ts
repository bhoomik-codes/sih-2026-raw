import { useState, useEffect, useCallback } from 'react';
import { Camera } from '../types/camera';
import { getCameras } from '../api/cameras';

export function useCameras() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCameras = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getCameras();
      setCameras(data);
      if (data.length > 0 && !selectedCameraId) {
        setSelectedCameraId(data[0].camera_id);
      }
    } catch (err: any) {
      setError(err.message || 'Unable to load cameras');
      setCameras([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCameraId]);

  useEffect(() => {
    fetchCameras();
  }, []);

  const selectedCamera = cameras.find((c) => c.camera_id === selectedCameraId) || cameras[0] || null;

  return {
    cameras,
    selectedCamera,
    selectedCameraId,
    setSelectedCameraId,
    isLoading,
    error,
    refresh: fetchCameras,
  };
}
