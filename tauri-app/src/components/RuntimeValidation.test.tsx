import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigurationPanel } from './ConfigurationPanel';
import type { WhisperConfig } from '../types/whisper';
import { mockInvoke } from '../test/setup';

const fullConfig: WhisperConfig = {
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
  post_processing_enabled: true,
  post_processing_mode: 'light',
  post_processing_trigger: 'manual',
  log_level: 'info' as const,
};

describe('Runtime Validation: Config Panel', () => {
  beforeEach(() => {
    (window as any).__TAURI_INTERNALS__ = {};
    mockInvoke.mockImplementation((cmd: string) => {
      if (cmd === 'list_sources') return Promise.resolve(['alsa_input.test']);
      return Promise.resolve(undefined);
    });
  });

  afterEach(() => {
    delete (window as any).__TAURI_INTERNALS__;
  });

  it('all 7 config section headings render in DOM simultaneously', () => {
    render(<ConfigurationPanel config={fullConfig} onConfigChange={vi.fn()} />);

    expect(screen.getByText('Audio & Transcription')).toBeInTheDocument();
    expect(screen.getByText('Audio Source')).toBeInTheDocument();
    expect(screen.getByText('Streaming Behavior')).toBeInTheDocument();
    expect(screen.getByText('Features')).toBeInTheDocument();
    expect(screen.getByText('Post-Processing')).toBeInTheDocument();
    expect(screen.getByText('Voice Control')).toBeInTheDocument();
    expect(screen.getByText('Advanced')).toBeInTheDocument();
  });

  it('all section content is in DOM even when collapsed (test queries work)', () => {
    render(<ConfigurationPanel config={fullConfig} onConfigChange={vi.fn()} />);

    expect(screen.getByLabelText('Chunk (s)')).toBeInTheDocument();
    expect(screen.getByLabelText('Overlap (s)')).toBeInTheDocument();
    expect(screen.getByText('Enabled')).toBeInTheDocument();
    expect(screen.getByText('Visual Indicator')).toBeInTheDocument();
  });

  it('can open every section and interact with its contents', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ConfigurationPanel config={fullConfig} onConfigChange={onChange} />);

    await user.click(screen.getByText('Audio Source'));
    expect(screen.getByLabelText('Preferred')).toBeInTheDocument();

    await user.click(screen.getByText('Streaming Behavior'));
    const chunkInput = screen.getByLabelText('Chunk (s)');
    expect(chunkInput).toBeInTheDocument();
    expect(chunkInput).not.toBeDisabled();
  });

  it('config panel renders without crashing when all fields have non-default values', () => {
    const { container } = render(
      <ConfigurationPanel config={fullConfig} onConfigChange={vi.fn()} />
    );
    expect(container).toBeTruthy();
  });

  it('config panel does not crash when all sections are opened simultaneously', async () => {
    const user = userEvent.setup();
    render(<ConfigurationPanel config={fullConfig} onConfigChange={vi.fn()} />);

    const sections = [
      'Audio Source',
      'Streaming Behavior',
      'Post-Processing',
      'Voice Control',
      'Advanced',
    ];

    for (const section of sections) {
      await user.click(screen.getByText(section));
    }

    expect(screen.getByText('Audio & Transcription')).toBeInTheDocument();
  });
});
