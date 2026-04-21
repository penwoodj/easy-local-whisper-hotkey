import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FilePickerInput } from './FilePickerInput';

const mockHomeDir = vi.fn().mockResolvedValue('/home/user');
const mockOpen = vi.fn().mockResolvedValue(null);

vi.mock('@tauri-apps/api/path', () => ({
  homeDir: (...args: unknown[]) => mockHomeDir(...args),
}));

vi.mock('@tauri-apps/plugin-dialog', () => ({
  open: (...args: unknown[]) => mockOpen(...args),
}));

describe('FilePickerInput', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHomeDir.mockResolvedValue('/home/user');
    mockOpen.mockResolvedValue(null);
    (window as any).__TAURI_INTERNALS__ = {};
  });

  afterEach(() => {
    delete (window as any).__TAURI_INTERNALS__;
  });

  it('renders input with value', () => {
    const onChange = vi.fn();
    render(
      <FilePickerInput
        value="/test/path"
        onChange={onChange}
        placeholder="Test placeholder"
      />
    );

    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue('/test/path');
    expect(input).toHaveAttribute('placeholder', 'Test placeholder');
  });

  it('calls onChange when typing', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <FilePickerInput
        value="/initial/path"
        onChange={onChange}
      />
    );

    const input = screen.getByRole('textbox');
    await user.clear(input);
    await user.type(input, '/new/path');

    expect(onChange).toHaveBeenCalledWith('/new/path');
  });

  it('expands ~/ path when typing', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <FilePickerInput
        value="/home/user/old/path"
        onChange={onChange}
      />
    );

    const input = screen.getByRole('textbox');
    await user.clear(input);
    await user.type(input, '~/new/path');

    expect(mockHomeDir).toHaveBeenCalled();
    expect(onChange).toHaveBeenCalled();
  });

  it('browse button triggers file picker', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    mockOpen.mockResolvedValue('/selected/file/path');

    render(
      <FilePickerInput
        value="/current/path"
        onChange={onChange}
      />
    );

    const browseButton = screen.getByLabelText('Browse for file');
    await user.click(browseButton);

    expect(mockOpen).toHaveBeenCalledWith({
      multiple: false,
      directory: false,
    });
    expect(onChange).toHaveBeenCalledWith('/selected/file/path');
  });

  it('handles file picker cancellation gracefully', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    mockOpen.mockResolvedValue(null);

    render(
      <FilePickerInput
        value="/current/path"
        onChange={onChange}
      />
    );

    const browseButton = screen.getByLabelText('Browse for file');
    await user.click(browseButton);

    expect(mockOpen).toHaveBeenCalled();
    expect(onChange).not.toHaveBeenCalled();
  });

  it('updates display value when value prop changes', async () => {
    const { rerender } = render(
      <FilePickerInput
        value="/initial/path"
        onChange={vi.fn()}
      />
    );

    const input = screen.getByRole('textbox');
    expect(input).toHaveValue('/initial/path');

    rerender(
      <FilePickerInput
        value="/updated/path"
        onChange={vi.fn()}
      />
    );

    expect(input).toHaveValue('/updated/path');
  });

  it('renders placeholder text', () => {
    render(
      <FilePickerInput
        value=""
        onChange={vi.fn()}
        placeholder="Select a file"
      />
    );

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('placeholder', 'Select a file');
  });
});
