import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { useWhisperState } from './hooks/useWhisperState';
import type { PostProcessingMode, PostProcessingTrigger, VoiceActivationMode } from './types/whisper';

vi.mock('./hooks/useWhisperState');

const defaultMockReturn = {
  config: {
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
    voice_activation_mode: 'hold' as VoiceActivationMode,
    indicator_enabled: true,
    post_processing_enabled: false,
    post_processing_mode: 'off' as PostProcessingMode,
    post_processing_trigger: 'manual' as PostProcessingTrigger,
  },
  status: {
    is_running: false,
    stream_text: '',
  },
  isLoading: false,
  error: null,
  saveConfig: vi.fn(),
  refreshStatus: vi.fn(),
  startDaemon: vi.fn(),
  stopDaemon: vi.fn(),
};

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      isLoading: true,
    });
    render(<App />);
    expect(screen.getByText(/Loading Whisper Hotkey\.\.\.*/i)).toBeInTheDocument();
  });

  it('renders main interface after loading', () => {
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: false,
        stream_text: 'Some transcribed text',
      },
    });

    render(<App />);
    expect(screen.getByText('🎙️ Status')).toBeInTheDocument();
    expect(screen.getByText('⚡ Modes')).toBeInTheDocument();
    expect(screen.getByText('⚙️ Config')).toBeInTheDocument();
    expect(screen.getByText('Idle')).toBeInTheDocument();
    expect(screen.getByText('Some transcribed text')).toBeInTheDocument();
  });

  it('renders streaming text display', () => {
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: false,
        stream_text: 'This is transcribed text',
      },
    });

    render(<App />);
    const streamingText = screen.getByText('This is transcribed text');
    expect(streamingText).toBeInTheDocument();
  });

  it('applies breathing animation class based on daemon status', () => {
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: false,
        stream_text: 'Some text',
      },
    });

    render(<App />);
    const statusEmoji = screen.getByRole('img', { name: 'Status indicator' });

    expect(statusEmoji).toHaveClass('animate-breathe-slow');
    expect(statusEmoji).not.toHaveClass('animate-breathe-fast');
  });

  it('applies breathing animation class when daemon is running', () => {
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: true,
        stream_text: 'Streaming text',
      },
    });

    render(<App />);
    const statusEmoji = screen.getByRole('img', { name: 'Status indicator' });

    expect(statusEmoji).toHaveClass('animate-breathe-fast');
    expect(statusEmoji).not.toHaveClass('animate-breathe-slow');
  });

  it('navigates between tabs', async () => {
    const user = userEvent.setup();
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: false,
        stream_text: 'Some text',
      },
    });

    render(<App />);

    const statusTab = screen.getByRole('button', { name: /Status/i });
    const modesTab = screen.getByRole('button', { name: /Modes/i });
    const configTab = screen.getByRole('button', { name: /Config/i });

    expect(statusTab).toHaveClass('bg-primary text-primary-foreground');
    expect(modesTab).toHaveClass('bg-background text-muted-foreground');
    expect(configTab).toHaveClass('bg-background text-muted-foreground');

    await user.click(modesTab);
    expect(modesTab).toHaveClass('bg-primary text-primary-foreground');
    expect(statusTab).toHaveClass('bg-background text-muted-foreground');
    expect(configTab).toHaveClass('bg-background text-muted-foreground');
  });

  it('disables start button when daemon is running', () => {
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: true,
        stream_text: 'Streaming text',
      },
    });

    render(<App />);

    const startButton = screen.queryByRole('button', { name: /Start/i });
    const stopButton = screen.getByRole('button', { name: /Stop/i });

    expect(startButton).not.toBeInTheDocument();
    expect(stopButton).toBeInTheDocument();
  });

  it('shows error message when error state is set', () => {
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: false,
        stream_text: 'Some text',
      },
      error: 'Failed to load config',
    });

    render(<App />);

    const errorCard = screen.queryByText('Failed to load config');
    expect(errorCard).toBeInTheDocument();
  });

  it('shows warning when daemon is running during config change', async () => {
    const user = userEvent.setup();
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: true,
        stream_text: 'Streaming text',
      },
    });

    render(<App />);

    await user.click(screen.getByRole('button', { name: /Modes/i }));

    expect(screen.getByText('Stop daemon to apply changes')).toBeInTheDocument();
  });

  it('renders keyboard shortcut hints in footer', () => {
    vi.mocked(useWhisperState).mockReturnValue({
      ...defaultMockReturn,
      status: {
        is_running: false,
        stream_text: 'Some text',
      },
    });

    render(<App />);

    const footerHold = screen.getByText('Hold');
    expect(footerHold).toBeInTheDocument();
    expect(screen.getByText('Ctrl+Space', { selector: 'kbd' })).toBeInTheDocument();
    expect(screen.getByText('Ctrl+Shift+S', { selector: 'kbd' })).toBeInTheDocument();
    expect(screen.getByText('Modes')).toBeInTheDocument();
  });
});
