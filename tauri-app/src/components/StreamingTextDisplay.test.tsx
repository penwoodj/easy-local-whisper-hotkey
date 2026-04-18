import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StreamingTextDisplay } from './StreamingTextDisplay';

describe('StreamingTextDisplay', () => {
  it('renders listening indicator when streaming', () => {
    render(
      <StreamingTextDisplay text="Hello world" isStreaming={true} />
    );

    expect(screen.getByText('Listening...')).toBeInTheDocument();
  });

  it('does not render listening indicator when not streaming', () => {
    render(
      <StreamingTextDisplay text="Hello world" isStreaming={false} />
    );

    expect(screen.queryByText('Listening...')).not.toBeInTheDocument();
  });

  it('renders streaming text', () => {
    render(
      <StreamingTextDisplay text="This is transcribed text" isStreaming={false} />
    );

    expect(screen.getByText('This is transcribed text')).toBeInTheDocument();
  });

  it('renders placeholder when text is empty', () => {
    render(
      <StreamingTextDisplay text="" isStreaming={false} />
    );

    expect(screen.getByText('Hold Ctrl+Space to start dictation...')).toBeInTheDocument();
  });

  it('updates when text and isStreaming props change', () => {
    const { rerender } = render(
      <StreamingTextDisplay text="" isStreaming={false} />
    );

    rerender(<StreamingTextDisplay text="New text" isStreaming={true} />);
    expect(screen.getByText('Listening...')).toBeInTheDocument();

    rerender(<StreamingTextDisplay text="Updated text" isStreaming={true} />);
    expect(screen.getByText('Updated text')).toBeInTheDocument();
  });
});
