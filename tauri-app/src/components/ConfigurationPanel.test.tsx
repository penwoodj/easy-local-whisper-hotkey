import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigurationPanel } from './ConfigurationPanel';
import type { WhisperConfig } from '../types/whisper';
import { mockInvoke } from '../test/setup';

describe('ConfigurationPanel', () => {
  beforeEach(() => {
    (window as any).__TAURI_INTERNALS__ = {};
    mockInvoke.mockImplementation((cmd: string) => {
      if (cmd === 'list_sources') {
        return Promise.resolve(['alsa_input.test', 'alsa_output.test']);
      }
      return Promise.resolve(undefined);
    });
  });

  afterEach(() => {
    delete (window as any).__TAURI_INTERNALS__;
  });
  const defaultConfig: WhisperConfig = {
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
    voice_activation_mode: 'hold',
    indicator_enabled: true,
    post_processing_enabled: false,
    post_processing_mode: 'off',
    post_processing_trigger: 'manual',
    log_level: 'info' as const,
  };

  it('renders all configuration sections', () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    expect(screen.getByText('Audio & Transcription')).toBeInTheDocument();
    expect(screen.getByText('Audio Source')).toBeInTheDocument();
    expect(screen.getByText('Streaming Behavior')).toBeInTheDocument();
    expect(screen.getByText('Features')).toBeInTheDocument();
    expect(screen.getByText('Post-Processing')).toBeInTheDocument();
    expect(screen.getByText('Voice Control')).toBeInTheDocument();
    expect(screen.getByText('Advanced')).toBeInTheDocument();
  });

  it('renders Audio & Transcription section with correct inputs', () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    expect(screen.getByLabelText('Whisper CLI')).toBeInTheDocument();
    expect(screen.getByLabelText('Model')).toBeInTheDocument();
    expect(screen.getByLabelText('Language')).toBeInTheDocument();

    const whisperCliInput = screen.getByLabelText('Whisper CLI');
    expect(whisperCliInput).toHaveValue(defaultConfig.whisper_cli);

    const modelInput = screen.getByLabelText('Model');
    expect(modelInput).toHaveValue(defaultConfig.model);
  });

  it('renders Audio Source section with correct inputs', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    expect(screen.getByLabelText('Source')).toBeInTheDocument();
    expect(screen.getByLabelText('Preferred')).toBeInTheDocument();

    // AudioSourceSelect is a Radix Select with button trigger, check it exists
    const sourceCombobox = screen.getByRole('combobox', { name: /Source/i });
    expect(sourceCombobox).toBeInTheDocument();

    const preferredInput = screen.getByLabelText('Preferred');
    expect(preferredInput).toHaveValue(defaultConfig.preferred_sources);
  });

  it('renders Streaming Behavior section with numeric inputs', () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    expect(screen.getByLabelText('Chunk (s)')).toBeInTheDocument();
    expect(screen.getByLabelText('Overlap (s)')).toBeInTheDocument();
    expect(screen.getByLabelText('Type Delay (ms)')).toBeInTheDocument();

    const chunkInput = screen.getByLabelText('Chunk (s)') as HTMLInputElement;
    expect(chunkInput.type).toBe('number');
    expect(chunkInput.value).toBe(String(defaultConfig.chunk_seconds));
    expect(chunkInput.step).toBe('0.1');

    const overlapInput = screen.getByLabelText('Overlap (s)') as HTMLInputElement;
    expect(overlapInput.type).toBe('number');
    expect(overlapInput.value).toBe(String(defaultConfig.overlap_seconds));
    expect(overlapInput.step).toBe('0.1');

    const typeDelayInput = screen.getByLabelText('Type Delay (ms)') as HTMLInputElement;
    expect(typeDelayInput.type).toBe('number');
    expect(typeDelayInput.value).toBe(String(defaultConfig.type_delay_ms));
  });

  it('renders Features section with toggle switches', () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    expect(screen.getByLabelText('Real-time')).toBeInTheDocument();
    expect(screen.getByLabelText('Smart Punctuation')).toBeInTheDocument();
    expect(screen.getByLabelText('Symbols')).toBeInTheDocument();
    expect(screen.getByLabelText('Suppress NST')).toBeInTheDocument();

    const directStreamingSwitch = screen.getByLabelText('Real-time');
    expect(directStreamingSwitch).toHaveAttribute('role', 'switch');

    const smartPunctuationSwitch = screen.getByLabelText('Smart Punctuation');
    expect(smartPunctuationSwitch).toHaveAttribute('role', 'switch');

    const symbolWordsSwitch = screen.getByLabelText('Symbols');
    expect(symbolWordsSwitch).toHaveAttribute('role', 'switch');

    const suppressNstSwitch = screen.getByLabelText('Suppress NST');
    expect(suppressNstSwitch).toHaveAttribute('role', 'switch');
  });

  it('renders Post-Processing section with enabled switch and dropdowns', () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const enabledSwitch = screen.getByLabelText('Enabled');
    expect(enabledSwitch).toBeInTheDocument();
    expect(enabledSwitch).toHaveAttribute('role', 'switch');

    const modeLabels = screen.getAllByText('Mode');
    expect(modeLabels).toHaveLength(2);
    expect(screen.getByText('Trigger')).toBeInTheDocument();
  });

  it('renders Voice Control section with mode select and indicator switch', () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const modeLabels = screen.getAllByText('Mode');
    expect(modeLabels).toHaveLength(2);

    const indicatorSwitch = screen.getByLabelText('Visual Indicator');
    expect(indicatorSwitch).toBeInTheDocument();
    expect(indicatorSwitch).toHaveAttribute('role', 'switch');
  });

  it('renders Advanced section with text inputs', () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    // RulesManager renders rules with labels, not a form input
    expect(screen.getByText('Remove filler words')).toBeInTheDocument();
    expect(screen.getByLabelText('Log File')).toBeInTheDocument();

    const logFileInput = screen.getByLabelText('Log File');
    expect(logFileInput).toHaveValue(defaultConfig.log_file);
  });

  it('collapses and expands sections on click', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const audioSourceSection = screen.getByText('Audio Source').closest('details');
    expect(audioSourceSection).toBeInTheDocument();
    expect(audioSourceSection?.getAttribute('open')).toBeNull();

    await user.click(screen.getByText('Audio Source'));
    expect(audioSourceSection?.getAttribute('open')).not.toBeNull();
  });

  it('calls onConfigChange when Whisper CLI path changes', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const input = screen.getByLabelText('Whisper CLI');
    fireEvent.change(input, { target: { value: '/custom/path/whisper-cli' } });

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('whisper_cli');
    expect(lastCall.whisper_cli).toBe('/custom/path/whisper-cli');
  });

  it('calls onConfigChange when Model path changes', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const input = screen.getByLabelText('Model');
    fireEvent.change(input, { target: { value: '/custom/model.bin' } });

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('model');
    expect(lastCall.model).toBe('/custom/model.bin');
  });

  it('calls onConfigChange when language changes', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const languageTrigger = document.getElementById('language')!;
    await user.click(languageTrigger);

    const spanishOption = await screen.findByRole('option', { name: /Spanish/i });
    await user.click(spanishOption);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('language');
    expect(lastCall.language).toBe('es');
  });

  it('calls onConfigChange when Source changes', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    // Open the Post-Processing section first to expose it
    await user.click(screen.getByText('Audio Source'));

    // Find and click the Source combobox
    const sourceCombobox = screen.getByRole('combobox', { name: /Source/i });
    await user.click(sourceCombobox);

    // Click on an option
    const option = await screen.findByRole('option', { name: 'alsa_output.test' });
    await user.click(option);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('source');
    expect(lastCall.source).toBe('alsa_output.test');
  });

  it('calls onConfigChange when Preferred sources changes', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const input = screen.getByLabelText('Preferred');
    fireEvent.change(input, { target: { value: ', another-source' } });

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('preferred_sources');
    expect(lastCall.preferred_sources).toBe(', another-source');
  });

  it('calls onConfigChange when Chunk seconds changes', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const input = screen.getByLabelText('Chunk (s)');
    fireEvent.change(input, { target: { value: '3' } });

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('chunk_seconds');
    expect(lastCall.chunk_seconds).toBe(3);
  });

  it('calls onConfigChange when Overlap seconds changes', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const input = screen.getByLabelText('Overlap (s)');
    fireEvent.change(input, { target: { value: '1' } });

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('overlap_seconds');
    expect(lastCall.overlap_seconds).toBe(1);
  });

  it('calls onConfigChange when Type Delay changes', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const input = screen.getByLabelText('Type Delay (ms)');
    fireEvent.change(input, { target: { value: '50' } });

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('type_delay_ms');
    expect(lastCall.type_delay_ms).toBe(50);
  });

  it('calls onConfigChange when Real-time switch is toggled', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const switchElement = screen.getByLabelText('Real-time');
    await user.click(switchElement);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('direct_streaming');
    expect(lastCall.direct_streaming).toBe(true);
  });

  it('calls onConfigChange when Smart Punctuation switch is toggled', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const switchElement = screen.getByLabelText('Smart Punctuation');
    await user.click(switchElement);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('smart_punctuation');
    expect(lastCall.smart_punctuation).toBe(false);
  });

  it('calls onConfigChange when Symbols switch is toggled', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const switchElement = screen.getByLabelText('Symbols');
    await user.click(switchElement);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('symbol_words_to_symbols');
    expect(lastCall.symbol_words_to_symbols).toBe(true);
  });

  it('calls onConfigChange when Suppress NST switch is toggled', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const switchElement = screen.getByLabelText('Suppress NST');
    await user.click(switchElement);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('suppress_nst');
    expect(lastCall.suppress_nst).toBe(false);
  });

  it('calls onConfigChange when Post-Processing Enabled switch is toggled', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const switchElement = screen.getByLabelText('Enabled');
    await user.click(switchElement);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('post_processing_enabled');
    expect(lastCall.post_processing_enabled).toBe(true);
  });

  it('calls onConfigChange when Post-Processing Mode changes', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    const configWithEnabled = {
      ...defaultConfig,
      post_processing_enabled: true,
    };
    render(
      <ConfigurationPanel config={configWithEnabled} onConfigChange={onConfigChange} />
    );

    await user.click(screen.getByText('Post-Processing'));

    // PostProcessingGrid uses buttons, not a Select dropdown
    const aggressiveButton = screen.getByText('Aggressive');
    await user.click(aggressiveButton);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('post_processing_mode');
    expect(lastCall.post_processing_mode).toBe('aggressive');
  });

  it('calls onConfigChange when Post-Processing Trigger changes', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    const configWithEnabled = {
      ...defaultConfig,
      post_processing_enabled: true,
    };
    render(
      <ConfigurationPanel config={configWithEnabled} onConfigChange={onConfigChange} />
    );

    await user.click(screen.getByText('Post-Processing'));

    const triggerEl = document.getElementById('post-processing-trigger')!;
    await user.click(triggerEl);

    const alwaysOption = await screen.findByRole('option', { name: /Always/i });
    await user.click(alwaysOption);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('post_processing_trigger');
    expect(lastCall.post_processing_trigger).toBe('always');
  });

  it('calls onConfigChange when Voice Activation Mode changes', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    await user.click(screen.getByText('Voice Control'));

    const modeTrigger = document.getElementById('voice-activation-mode')!;
    await user.click(modeTrigger);

    const toggleOption = await screen.findByRole('option', { name: /Toggle/i });
    await user.click(toggleOption);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('voice_activation_mode');
    expect(lastCall.voice_activation_mode).toBe('toggle');
  });

  it('calls onConfigChange when Visual Indicator switch is toggled', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const switchElement = screen.getByLabelText('Visual Indicator');
    await user.click(switchElement);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('indicator_enabled');
    expect(lastCall.indicator_enabled).toBe(false);
  });

  it('calls onConfigChange when Suppress Regex changes', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    await user.click(screen.getByText('Advanced'));

    const ruleNameInput = screen.getByPlaceholderText('Rule name');
    const patternInput = screen.getByPlaceholderText('Regex pattern');

    await user.type(ruleNameInput, 'Test rule');
    fireEvent.change(patternInput, { target: { value: '[^\\w\\s]' } });

    const addButtons = screen.getAllByText('Add');
    const addButton = addButtons[addButtons.length - 1];
    await user.click(addButton);

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('suppress_regex');
  });

  it('calls onConfigChange when Log File changes', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const input = screen.getByLabelText('Log File');
    fireEvent.change(input, { target: { value: '/var/log/whisper.log' } });

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('log_file');
    expect(lastCall.log_file).toBe('/var/log/whisper.log');
  });

  it('disables all inputs when disabled prop is true', () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} disabled />
    );

    // Check that switches are disabled
    const switches = screen.getAllByRole('switch');
    switches.forEach(switchElement => {
      expect(switchElement).toBeDisabled();
    });

    // Check that comboboxes are disabled
    const comboboxes = screen.getAllByRole('combobox');
    comboboxes.forEach(combobox => {
      expect(combobox).toBeDisabled();
    });

    // Check that the Model input is disabled
    const modelInput = screen.getByLabelText('Model');
    expect(modelInput).toBeDisabled();

    // Check that numeric inputs are disabled
    const chunkInput = screen.getByLabelText('Chunk (s)');
    expect(chunkInput).toBeDisabled();
    const overlapInput = screen.getByLabelText('Overlap (s)');
    expect(overlapInput).toBeDisabled();
    const typeDelayInput = screen.getByLabelText('Type Delay (ms)');
    expect(typeDelayInput).toBeDisabled();

    // Check that the Preferred sources input is disabled
    const preferredInput = screen.getByLabelText('Preferred');
    expect(preferredInput).toBeDisabled();
  });

  it('disables Post-Processing grid when post_processing_enabled is false', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    await user.click(screen.getByText('Post-Processing'));

    // PostProcessingGrid buttons should be disabled
    const offButton = screen.getByText('Off').closest('button');
    const lightButton = screen.getByText('Light').closest('button');
    const aggressiveButton = screen.getByText('Aggressive').closest('button');

    expect(offButton).toBeDisabled();
    expect(lightButton).toBeDisabled();
    expect(aggressiveButton).toBeDisabled();

    // Trigger select should still be enabled
    const triggerCombobox = screen.getByRole('combobox', { name: /Trigger/i });
    expect(triggerCombobox).toBeDisabled();
  });

  it('enables Post-Processing grid when post_processing_enabled is true', async () => {
    const user = userEvent.setup();
    const onConfigChange = vi.fn();
    const configWithEnabled = {
      ...defaultConfig,
      post_processing_enabled: true,
    };
    render(
      <ConfigurationPanel config={configWithEnabled} onConfigChange={onConfigChange} />
    );

    await user.click(screen.getByText('Post-Processing'));

    // PostProcessingGrid buttons should be enabled
    const offButton = screen.getByText('Off').closest('button');
    const lightButton = screen.getByText('Light').closest('button');
    const aggressiveButton = screen.getByText('Aggressive').closest('button');

    expect(offButton).not.toBeDisabled();
    expect(lightButton).not.toBeDisabled();
    expect(aggressiveButton).not.toBeDisabled();

    // Trigger select should also be enabled
    const triggerCombobox = screen.getByRole('combobox', { name: /Trigger/i });
    expect(triggerCombobox).not.toBeDisabled();
  });

  it('handles numeric input edge cases', async () => {
    const onConfigChange = vi.fn();
    render(
      <ConfigurationPanel config={defaultConfig} onConfigChange={onConfigChange} />
    );

    const chunkInput = screen.getByLabelText('Chunk (s)');
    fireEvent.change(chunkInput, { target: { value: 'abc' } });

    expect(onConfigChange).toHaveBeenCalled();
    const calls = onConfigChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall).toHaveProperty('chunk_seconds');
    expect(lastCall.chunk_seconds).toBe(0);

    fireEvent.change(chunkInput, { target: { value: '2.5' } });

    const calls2 = onConfigChange.mock.calls;
    const lastCall2 = calls2[calls2.length - 1][0];
    expect(lastCall2).toHaveProperty('chunk_seconds');
    expect(lastCall2.chunk_seconds).toBe(2.5);

  });
});
