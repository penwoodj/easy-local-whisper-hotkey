import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AudioSourceSelect } from './AudioSourceSelect';
import { mockInvoke } from '../test/setup';

describe('AudioSourceSelect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it('renders loading state initially', () => {
    const onChange = vi.fn();
    render(
      <AudioSourceSelect
        value=""
        onChange={onChange}
      />
    );

    const combobox = screen.getByRole('combobox');
    expect(combobox).toBeInTheDocument();
    expect(combobox).toHaveTextContent('Loading...');
  });

  it('loads sources from invoke', async () => {
    const onChange = vi.fn();
    render(
      <AudioSourceSelect
        value="alsa_input.test"
        onChange={onChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).not.toHaveTextContent('Loading...');
    });

    expect(mockInvoke).toHaveBeenCalledWith('list_sources');
  });

  it('calls onChange when source selected', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    vi.mocked(mockInvoke).mockResolvedValue(['alsa_input.test', 'alsa_output.test']);

    render(
      <AudioSourceSelect
        value=""
        onChange={onChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).not.toHaveTextContent('Loading...');
    });

    const combobox = screen.getByRole('combobox');
    await user.click(combobox);

    const option = await screen.findByRole('option', { name: 'alsa_output.test' });
    await user.click(option);

    expect(onChange).toHaveBeenCalledWith('alsa_output.test');
  });

  it('handles invoke error gracefully', async () => {
    const onChange = vi.fn();
    vi.mocked(mockInvoke).mockRejectedValue(new Error('Failed to load sources'));

    render(
      <AudioSourceSelect
        value=""
        onChange={onChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).not.toHaveTextContent('Loading...');
    });

    expect(screen.getByRole('combobox')).toHaveTextContent('No audio sources found');
    expect(onChange).not.toHaveBeenCalled();
  });

  it('auto-selects first source if no value', async () => {
    const onChange = vi.fn();
    vi.mocked(mockInvoke).mockResolvedValue(['alsa_input.test', 'alsa_output.test']);

    render(
      <AudioSourceSelect
        value=""
        onChange={onChange}
      />
    );

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('alsa_input.test');
    });
  });

  it('does not auto-select if value already set', async () => {
    const onChange = vi.fn();
    vi.mocked(mockInvoke).mockResolvedValue(['alsa_input.test', 'alsa_output.test']);

    render(
      <AudioSourceSelect
        value="alsa_output.test"
        onChange={onChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).not.toHaveTextContent('Loading...');
    });

    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders disabled state', async () => {
    const onChange = vi.fn();
    vi.mocked(mockInvoke).mockResolvedValue(['alsa_input.test']);

    render(
      <AudioSourceSelect
        value="alsa_input.test"
        onChange={onChange}
        disabled
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).not.toHaveTextContent('Loading...');
    });

    const combobox = screen.getByRole('combobox');
    expect(combobox).toBeDisabled();
  });
});
