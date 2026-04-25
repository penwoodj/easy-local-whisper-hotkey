import { useState, useEffect, useCallback } from 'react';
import * as api from '../api/client';
import type { WhisperConfig, WhisperStatus } from '../api/types';

export function useWhisperApi() {
  const [config, setConfig] = useState<WhisperConfig | null>(null);
  const [status, setStatus] = useState<WhisperStatus>({ is_running: false, stream_text: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConfig = useCallback(async () => {
    try {
      setError(null);
      const loadedConfig = await api.fetchConfig();
      setConfig(loadedConfig);
    } catch (err) {
      setError(`Failed to load config: ${err}`);
    }
  }, []);

  const saveConfig = useCallback(async (newConfig: WhisperConfig) => {
    setConfig(newConfig);
    try {
      setError(null);
      await api.saveConfig(newConfig);
    } catch (err) {
      setError(`Failed to save config: ${err}`);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const newStatus = await api.getStatus();
      setStatus(newStatus);
    } catch (err) {
      setError(`Failed to get status: ${err}`);
    }
  }, []);

  const startDaemon = useCallback(async () => {
    try {
      setError(null);
      await api.startDaemon();
      await refreshStatus();
    } catch (err) {
      setError(`Failed to start daemon: ${err}`);
    }
  }, [refreshStatus]);

  const stopDaemon = useCallback(async () => {
    try {
      setError(null);
      await api.stopDaemon();
      await refreshStatus();
    } catch (err) {
      setError(`Failed to stop daemon: ${err}`);
    }
  }, [refreshStatus]);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await loadConfig();
      await refreshStatus();
      setIsLoading(false);
    };
    init();

    const es = api.connectEvents(
      (event) => {
        const msg = event as MessageEvent;
        try {
          const data = JSON.parse(msg.data as string) as { event?: string; [key: string]: unknown };
          if (data.event === 'status') {
            setStatus(data as unknown as WhisperStatus);
          } else if (data.event === 'transcription') {
            setStatus((prev) => ({ ...prev, stream_text: (data as { text: string }).text }));
          }
        } catch {
          // Ignore parsing errors
        }
      },
      () => setError('Event stream disconnected')
    );

    return () => es.close();
  }, [loadConfig, refreshStatus]);

  return {
    config,
    status,
    isLoading,
    error,
    saveConfig,
    refreshStatus,
    startDaemon,
    stopDaemon,
  };
}
