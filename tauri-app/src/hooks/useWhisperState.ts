import { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import type { WhisperConfig, WhisperStatus } from '../types/whisper';

const isTauri = (): boolean => typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

const demoConfig: WhisperConfig = {
  whisper_cli: '/usr/local/bin/whisper-cli',
  model: '~/.local/share/whisper-hotkey/models/ggml-base.en.bin',
  language: 'en',
  source: 'alsa_input.usb-0000:00:00.0',
  preferred_sources: '',
  chunk_seconds: 2.0,
  overlap_seconds: 0.5,
  type_delay_ms: 30,
  direct_streaming: false,
  smart_punctuation: true,
  symbol_words_to_symbols: false,
  suppress_nst: true,
  suppress_regex: '',
  log_file: '/tmp/whisper_hotkey.log',
  voice_activation_mode: 'toggle',
  indicator_enabled: true,
  post_processing_enabled: false,
  post_processing_mode: 'off',
  post_processing_trigger: 'manual',
};

export function useWhisperState() {
  const [config, setConfig] = useState<WhisperConfig | null>(null);
  const [status, setStatus] = useState<WhisperStatus>({ is_running: false, stream_text: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConfig = useCallback(async () => {
    if (!isTauri()) {
      setConfig(demoConfig);
      return;
    }
    try {
      setError(null);
      const loadedConfig = await invoke<WhisperConfig>('get_config');
      setConfig(loadedConfig);
    } catch (err) {
      setError(`Failed to load config: ${err}`);
    }
  }, []);

  const saveConfig = useCallback(async (newConfig: WhisperConfig) => {
    if (!isTauri()) {
      setConfig(newConfig);
      return;
    }
    try {
      setError(null);
      await invoke('set_config', { config: newConfig });
      setConfig(newConfig);
    } catch (err) {
      setError(`Failed to save config: ${err}`);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    if (!isTauri()) {
      return;
    }
    try {
      const newStatus = await invoke<WhisperStatus>('get_status');
      setStatus(newStatus);
    } catch (err) {
      setError(`Failed to get status: ${err}`);
    }
  }, []);

  const startDaemon = useCallback(async () => {
    if (!isTauri()) {
      setStatus((prev) => ({ ...prev, is_running: true }));
      return;
    }
    try {
      setError(null);
      await invoke('start_daemon');
      await refreshStatus();
    } catch (err) {
      setError(`Failed to start daemon: ${err}`);
    }
  }, [refreshStatus]);

  const stopDaemon = useCallback(async () => {
    if (!isTauri()) {
      setStatus((prev) => ({ ...prev, is_running: false, stream_text: '' }));
      return;
    }
    try {
      setError(null);
      await invoke('stop_daemon');
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

    if (!isTauri()) {
      return;
    }

    const unlisten = listen<{ text: string }>('streaming-text', (event) => {
      setStatus((prev) => ({
        ...prev,
        stream_text: event.payload.text,
      }));
    });

    const unlistenStarted = listen<number>('daemon-started', (event) => {
      setStatus((prev) => ({
        ...prev,
        is_running: true,
        pid: event.payload,
      }));
    });

    const unlistenStopped = listen('daemon-stopped', () => {
      setStatus((prev) => ({
        ...prev,
        is_running: false,
        pid: undefined,
        stream_text: '',
      }));
    });

    return () => {
      unlisten.then((fn) => fn());
      unlistenStarted.then((fn) => fn());
      unlistenStopped.then((fn) => fn());
    };
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
