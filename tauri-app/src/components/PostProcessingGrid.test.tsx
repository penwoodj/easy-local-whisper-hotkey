import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PostProcessingGrid } from './PostProcessingGrid';

describe('PostProcessingGrid', () => {

  it('renders all 9 mode buttons', () => {
    const onChange = vi.fn();
    render(
      <PostProcessingGrid
        value="off"
        onChange={onChange}
      />
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

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(9);
  });

  it('highlights active mode with border-primary class', () => {
    const onChange = vi.fn();
    render(
      <PostProcessingGrid
        value="light"
        onChange={onChange}
      />
    );

    const lightButton = screen.getByText('Light').closest('button');
    expect(lightButton).toHaveClass('border-primary');

    const offButton = screen.getByText('Off').closest('button');
    expect(offButton).not.toHaveClass('border-primary');
  });

  it('calls onChange on click', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <PostProcessingGrid
        value="off"
        onChange={onChange}
      />
    );

    const aggressiveButton = screen.getByText('Aggressive');
    await user.click(aggressiveButton);

    expect(onChange).toHaveBeenCalledWith('aggressive');
  });

  it('disabled state disables all buttons', () => {
    const onChange = vi.fn();
    render(
      <PostProcessingGrid
        value="off"
        onChange={onChange}
        disabled
      />
    );

    const buttons = screen.getAllByRole('button');
    buttons.forEach(button => {
      expect(button).toBeDisabled();
      expect(button).toHaveClass('opacity-50');
      expect(button).toHaveClass('cursor-not-allowed');
    });
  });

  it('shows correct icons for each mode', () => {
    const onChange = vi.fn();
    render(
      <PostProcessingGrid
        value="off"
        onChange={onChange}
      />
    );

    expect(screen.getByText('⊘')).toBeInTheDocument();
    expect(screen.getByText('✨')).toBeInTheDocument();
    expect(screen.getByText('⚡')).toBeInTheDocument();
    expect(screen.getByText('🤖')).toBeInTheDocument();
    expect(screen.getByText('✏️')).toBeInTheDocument();
    expect(screen.getByText('💻')).toBeInTheDocument();
    expect(screen.getByText('📐')).toBeInTheDocument();
    expect(screen.getByText('🎭')).toBeInTheDocument();
    expect(screen.getByText('🔍')).toBeInTheDocument();
  });

  it('updates active mode when value prop changes', () => {
    const { rerender } = render(
      <PostProcessingGrid
        value="off"
        onChange={vi.fn()}
      />
    );

    const offButton = screen.getByText('Off').closest('button');
    expect(offButton).toHaveClass('border-primary');

    const lightButton = screen.getByText('Light').closest('button');
    expect(lightButton).not.toHaveClass('border-primary');

    rerender(
      <PostProcessingGrid
        value="light"
        onChange={vi.fn()}
      />
    );

    expect(offButton).not.toHaveClass('border-primary');
    expect(lightButton).toHaveClass('border-primary');
  });

  it('applies hover styles correctly', () => {
    const onChange = vi.fn();
    render(
      <PostProcessingGrid
        value="off"
        onChange={onChange}
      />
    );

    const offButton = screen.getByText('Off').closest('button')!;
    const lightButton = screen.getByText('Light').closest('button')!;

    expect(offButton).toHaveClass('border-2', 'bg-primary/10');
    expect(lightButton).toHaveClass('border', 'hover:bg-card/80');
  });
});
