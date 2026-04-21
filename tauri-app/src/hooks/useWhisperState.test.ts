import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useWhisperState } from './useWhisperState';

const mockInvoke = vi.fn();
const mockListen = vi.fn().mockResolvedValue(vi.fn());

vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => mockInvoke(...args),
}));

vi.mock('@tauri-apps/api/event', () => ({
  listen: (...args: unknown[]) => mockListen(...args),
}));

describe('useWhisperState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockInvoke.mockResolvedValue({});
    mockListen.mockResolvedValue(vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete (window as any).__TAURI_INTERNALS__;
  });

  it('initializes with loading state', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(result.current.isLoading).toBe(true);
  });

  it('initializes with no error', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(result.current.error).toBeNull();
  });

  it('returns saveConfig function', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(typeof result.current.saveConfig).toBe('function');
  });

  it('returns startDaemon function', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(typeof result.current.startDaemon).toBe('function');
  });

  it('returns stopDaemon function', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(typeof result.current.stopDaemon).toBe('function');
  });

  it('returns refreshStatus function', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(typeof result.current.refreshStatus).toBe('function');
  });

  it('returns config state', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(typeof result.current.config).toBe('object');
  });

  it('returns status state', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(typeof result.current.status).toBe('object');
  });

  it('returns volumeLevel state', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(typeof result.current.volumeLevel).toBe('number');
  });

  it('returns isRecording state', () => {
    const { result } = renderHook(() => useWhisperState());
    expect(typeof result.current.isRecording).toBe('boolean');
  });

  it('sets up event listeners when in Tauri environment', async () => {
    (window as any).__TAURI_INTERNALS__ = {};

    renderHook(() => useWhisperState());

    await waitFor(() => {
      expect(mockListen).toHaveBeenCalledWith('streaming-text', expect.any(Function));
    }, { timeout: 3000 });

    expect(mockListen).toHaveBeenCalledWith('daemon-started', expect.any(Function));
    expect(mockListen).toHaveBeenCalledWith('daemon-stopped', expect.any(Function));
    expect(mockListen).toHaveBeenCalledWith('volume-level', expect.any(Function));
    expect(mockListen).toHaveBeenCalledWith('recording-state', expect.any(Function));
  });
});
