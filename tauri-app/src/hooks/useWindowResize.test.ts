import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { resizeWindowForTab } from './useWindowResize';

vi.mock('@tauri-apps/api/window', () => ({
  getCurrentWindow: vi.fn(),
}));

vi.mock('@tauri-apps/api/dpi', () => {
  return {
    LogicalSize: class LogicalSize {
      width: number;
      height: number;
      constructor(w: number, h: number) {
        this.width = w;
        this.height = h;
      }
    },
  };
});

describe('useWindowResize', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (window as any).__TAURI_INTERNALS__ = {};
  });

  afterEach(() => {
    delete (window as any).__TAURI_INTERNALS__;
  });

  it('resizes window for status tab', async () => {
    const mockSetSize = vi.fn().mockResolvedValue(undefined);
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    vi.mocked(getCurrentWindow).mockReturnValue({
      setSize: mockSetSize,
    } as any);

    await resizeWindowForTab('status');

    expect(getCurrentWindow).toHaveBeenCalled();
    const callArg = mockSetSize.mock.calls[0][0];
    expect(callArg.width).toBe(300);
    expect(callArg.height).toBe(420);
  });

  it('resizes window for modes tab', async () => {
    const mockSetSize = vi.fn().mockResolvedValue(undefined);
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    vi.mocked(getCurrentWindow).mockReturnValue({
      setSize: mockSetSize,
    } as any);

    await resizeWindowForTab('modes');

    expect(getCurrentWindow).toHaveBeenCalled();
    const callArg = mockSetSize.mock.calls[0][0];
    expect(callArg.width).toBe(300);
    expect(callArg.height).toBe(480);
  });

  it('resizes window for config tab', async () => {
    const mockSetSize = vi.fn().mockResolvedValue(undefined);
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    vi.mocked(getCurrentWindow).mockReturnValue({
      setSize: mockSetSize,
    } as any);

    await resizeWindowForTab('config');

    expect(getCurrentWindow).toHaveBeenCalled();
    const callArg = mockSetSize.mock.calls[0][0];
    expect(callArg.width).toBe(300);
    expect(callArg.height).toBe(680);
  });

  it('uses default status size for unknown tab', async () => {
    const mockSetSize = vi.fn().mockResolvedValue(undefined);
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    vi.mocked(getCurrentWindow).mockReturnValue({
      setSize: mockSetSize,
    } as any);

    await resizeWindowForTab('unknown' as any);

    expect(getCurrentWindow).toHaveBeenCalled();
    const callArg = mockSetSize.mock.calls[0][0];
    expect(callArg.width).toBe(300);
    expect(callArg.height).toBe(420);
  });

  it('handles resize errors gracefully', async () => {
    const mockSetSize = vi.fn().mockRejectedValue(new Error('Resize failed'));
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    vi.mocked(getCurrentWindow).mockReturnValue({
      setSize: mockSetSize,
    } as any);

    await resizeWindowForTab('status');

    expect(getCurrentWindow).toHaveBeenCalled();
    expect(mockSetSize).toHaveBeenCalled();
  });

  it('skips resize when not in Tauri', async () => {
    delete (window as any).__TAURI_INTERNALS__;
    const { getCurrentWindow } = await import('@tauri-apps/api/window');

    await resizeWindowForTab('status');

    expect(getCurrentWindow).not.toHaveBeenCalled();
  });
});
