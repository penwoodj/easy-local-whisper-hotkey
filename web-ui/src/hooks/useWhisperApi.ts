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

  const refreshStatus = useCallback(async () => {
    try {
      const newStatus = await api.getStatus();
      setStatus(newStatus);
    } catch (err) {
      setError(`Failed to get status: ${err}`);
    }
  }, []);

  const validateConfig = useCallback((newConfig: WhisperConfig): boolean => {
    const requiredFields = ['WHISPER_CLI', 'WHISPER_MODEL', 'WHISPER_LOG_FILE'];
    const missingFields = requiredFields.filter((field) => !newConfig[field as keyof WhisperConfig]?.toString().trim());

    if (missingFields.length > 0) {
      setError(`Missing required fields: ${missingFields.join(', ')}`);
      return false;
    }

    if (newConfig.WHISPER_CHUNK_SECONDS < 0.1 || newConfig.WHISPER_CHUNK_SECONDS > 10.0) {
      setError('WHISPER_CHUNK_SECONDS must be between 0.1 and 10.0');
      return false;
    }

    if (newConfig.WHISPER_OVERLAP_SECONDS < 0.0 || newConfig.WHISPER_OVERLAP_SECONDS > 2.0) {
      setError('WHISPER_OVERLAP_SECONDS must be between 0.0 and 2.0');
      return false;
    }

    if (newConfig.WHISPER_TYPE_DELAY_MS < 1 || newConfig.WHISPER_TYPE_DELAY_MS > 1000) {
      setError('WHISPER_TYPE_DELAY_MS must be between 1 and 1000');
      return false;
    }

    return true;
  }, []);

  const saveConfig = useCallback(async (newConfig: WhisperConfig) => {
    if (!validateConfig(newConfig)) {
      return;
    }

    try {
      setError(null);
      const savedConfig = await api.saveConfig(newConfig);
      setConfig(savedConfig);
    } catch (err) {
      setError(`Failed to save config: ${err}`);
      throw err;
    }
  }, [validateConfig]);

  const setConfigDirectly = useCallback((newConfig: WhisperConfig) => {
    setConfig(newConfig);
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
    setConfig: setConfigDirectly,
    refreshStatus,
    startDaemon,
    stopDaemon,
  };
}
