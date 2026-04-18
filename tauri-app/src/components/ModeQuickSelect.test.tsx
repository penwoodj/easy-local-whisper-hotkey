import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ModeQuickSelect } from './ModeQuickSelect';

describe('ModeQuickSelect', () => {
  it('renders all mode buttons', () => {
    const onModeChange = vi.fn();
    render(
      <ModeQuickSelect currentMode="off" onModeChange={onModeChange} />
    );

    expect(screen.getByText('Off')).toBeInTheDocument();
    expect(screen.getByText('Light')).toBeInTheDocument();
    expect(screen.getByText('Aggressive')).toBeInTheDocument();
    expect(screen.getByText('Agentic')).toBeInTheDocument();
    expect(screen.getByText('Writing')).toBeInTheDocument();
    expect(screen.getByText('Code')).toBeInTheDocument();
    expect(screen.getByText('Structure')).toBeInTheDocument();
    expect(screen.getByText('Persona')).toBeInTheDocument();
    expect(screen.getByText('Clarity')).toBeInTheDocument();
  });

  it('highlights the selected mode with default variant', () => {
    const onModeChange = vi.fn();
    render(
      <ModeQuickSelect currentMode="light" onModeChange={onModeChange} />
    );

    const lightButton = screen.getByText('Light').closest('button')!;
    expect(lightButton).toHaveClass('bg-primary');

    const offButton = screen.getByText('Off').closest('button')!;
    expect(offButton).not.toHaveClass('bg-primary');
  });

  it('calls onModeChange when mode button is clicked', async () => {
    const user = userEvent.setup();
    const onModeChange = vi.fn();
    render(
      <ModeQuickSelect currentMode="off" onModeChange={onModeChange} />
    );

    const aggressiveButton = screen.getByText('Aggressive');
    await user.click(aggressiveButton);

    expect(onModeChange).toHaveBeenCalledWith('aggressive');
  });

  it('disables all buttons when disabled prop is true', () => {
    const onModeChange = vi.fn();
    render(
      <ModeQuickSelect currentMode="off" onModeChange={onModeChange} disabled />
    );

    const buttons = screen.getAllByRole('button');
    buttons.forEach(button => {
      expect(button).toBeDisabled();
    });
  });

  it('displays emoji and label correctly', () => {
    const onModeChange = vi.fn();
    render(
      <ModeQuickSelect currentMode="off" onModeChange={onModeChange} />
    );

    const offButton = screen.getByText('Off').closest('button')!;
    expect(offButton).toBeInTheDocument();
    expect(offButton).toHaveTextContent('🎙️');
    const lightButton = screen.getByText('Light').closest('button')!;
    expect(lightButton).toBeInTheDocument();
    expect(lightButton).toHaveTextContent('✨');
  });

  it('has radiogroup role for accessibility', () => {
    const onModeChange = vi.fn();
    render(
      <ModeQuickSelect currentMode="off" onModeChange={onModeChange} />
    );

    const grid = screen.getByRole('radiogroup');
    expect(grid).toBeInTheDocument();
  });
});
