import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { useWhisperState } from './hooks/useWhisperState';
import type { PostProcessingMode, PostProcessingTrigger, VoiceActivationMode } from './types/whisper';

vi.mock('./hooks/useWhisperState');

const mockConfig = {
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
  voice_activation_mode: 'toggle' as VoiceActivationMode,
  indicator_enabled: true,
  post_processing_enabled: false,
  post_processing_mode: 'off' as PostProcessingMode,
  post_processing_trigger: 'manual' as PostProcessingTrigger,
  log_level: 'info' as const,
};

describe('Runtime Validation: App Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const defaultReturn = {
    config: mockConfig,
    status: { is_running: false, stream_text: '' },
    isLoading: false,
    error: null,
    saveConfig: vi.fn(),
    refreshStatus: vi.fn(),
    startDaemon: vi.fn(),
    stopDaemon: vi.fn(),
    volumeLevel: 0,
    isRecording: false,
  };

  it('root container uses flex-col layout', () => {
    vi.mocked(useWhisperState).mockReturnValue(defaultReturn);
    const { container } = render(<App />);
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain('flex-col');
  });

  it('tab bar is shrink-0 (does not compress)', () => {
    vi.mocked(useWhisperState).mockReturnValue(defaultReturn);
    render(<App />);
    const tabBar = screen.getByText('🎙️ Status').closest('div');
    expect(tabBar?.className).toContain('shrink-0');
  });

  it('footer is shrink-0 (does not compress)', () => {
    vi.mocked(useWhisperState).mockReturnValue(defaultReturn);
    render(<App />);
    expect(screen.getByText('Toggle')).toBeInTheDocument();
    const footer = screen.getByText('Toggle').closest('div')?.parentElement;
    expect(footer?.className).toContain('shrink-0');
  });

  it('content area has overflow-y-auto for scrolling', () => {
    vi.mocked(useWhisperState).mockReturnValue(defaultReturn);
    render(<App />);
    const contentArea = screen.getByText('Stopped').closest('.flex-1');
    expect(contentArea?.className).toContain('overflow-y-auto');
  });

  it('switching to config tab shows config panel without crash', async () => {
    const user = userEvent.setup();
    vi.mocked(useWhisperState).mockReturnValue(defaultReturn);
    render(<App />);

    await user.click(screen.getByRole('button', { name: /Config/i }));
    expect(screen.getByText('Audio & Transcription')).toBeInTheDocument();
    expect(screen.getByText('Features')).toBeInTheDocument();
  });

  it('switching to modes tab shows mode grid without crash', async () => {
    const user = userEvent.setup();
    vi.mocked(useWhisperState).mockReturnValue(defaultReturn);
    render(<App />);

    await user.click(screen.getByRole('button', { name: /Modes/i }));
    expect(screen.getByText('Current')).toBeInTheDocument();
    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
  });

  it('all 3 tabs are clickable and render unique content', async () => {
    const user = userEvent.setup();
    vi.mocked(useWhisperState).mockReturnValue(defaultReturn);
    render(<App />);

    await user.click(screen.getByRole('button', { name: /Status/i }));
    expect(screen.getByText('Stopped')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Modes/i }));
    expect(screen.getByText('Current')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Config/i }));
    expect(screen.getByText('Audio & Transcription')).toBeInTheDocument();
  });
});
