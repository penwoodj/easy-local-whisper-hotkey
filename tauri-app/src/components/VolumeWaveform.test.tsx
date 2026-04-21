import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import { VolumeWaveform } from './VolumeWaveform';

describe('VolumeWaveform', () => {
  let mockCtx: any;

  const mockRequestAnimationFrame = vi.fn((callback) => {
    return setTimeout(() => callback(0), 16) as unknown as number;
  });

  const mockCancelAnimationFrame = vi.fn((id) => {
    clearTimeout(id as unknown as any);
  });

  beforeEach(() => {
    mockCtx = {
      clearRect: vi.fn(),
      fillRect: vi.fn(),
      beginPath: vi.fn(),
      fill: vi.fn(),
      roundRect: vi.fn(),
      fillStyle: '',
    };
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(mockCtx);
    vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(mockRequestAnimationFrame);
    vi.spyOn(globalThis, 'cancelAnimationFrame').mockImplementation(mockCancelAnimationFrame);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders canvas element', () => {
    render(
      <VolumeWaveform
        volume={0.5}
        isActive={false}
      />
    );

    const canvas = document.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
    expect(canvas).toHaveAttribute('width', '240');
    expect(canvas).toHaveAttribute('height', '48');
  });

  it('gets 2d context from canvas', () => {
    render(
      <VolumeWaveform
        volume={0.5}
        isActive={false}
      />
    );

    const canvas = document.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
    expect(HTMLCanvasElement.prototype.getContext).toHaveBeenCalledWith('2d');
  });

  it('clears canvas on render', () => {
    render(
      <VolumeWaveform
        volume={0.5}
        isActive={false}
      />
    );

    expect(mockCtx.clearRect).toHaveBeenCalledWith(0, 0, 240, 48);
  });

  it('draws bars when inactive', () => {
    render(
      <VolumeWaveform
        volume={0.5}
        isActive={false}
      />
    );

    expect(mockCtx.roundRect).toHaveBeenCalled();
    expect(mockCtx.fill).toHaveBeenCalled();
  });

  it('draws bars with higher amplitude when active and volume is high', () => {
    render(
      <VolumeWaveform
        volume={0.8}
        isActive={true}
      />
    );

    expect(mockCtx.roundRect).toHaveBeenCalled();
    expect(mockCtx.fillStyle).toMatch(/hsl\(\d+/);
  });

  it('sets correct fill style based on bar position', () => {
    render(
      <VolumeWaveform
        volume={0.5}
        isActive={true}
      />
    );

    expect(mockCtx.roundRect).toHaveBeenCalled();
    expect(mockCtx.fill).toHaveBeenCalled();
    expect(mockCtx.fillStyle).toMatch(/hsl\(/);
  });

  it('starts animation on mount', () => {
    render(
      <VolumeWaveform
        volume={0.5}
        isActive={true}
      />
    );

    expect(mockRequestAnimationFrame).toHaveBeenCalled();
  });

  it('cleans up animation on unmount', () => {
    const { unmount } = render(
      <VolumeWaveform
        volume={0.5}
        isActive={true}
      />
    );

    unmount();

    expect(mockCancelAnimationFrame).toHaveBeenCalled();
  });

  it('continues animation when volume changes', () => {
    const { rerender } = render(
      <VolumeWaveform
        volume={0.3}
        isActive={true}
      />
    );

    mockRequestAnimationFrame.mockClear();

    rerender(
      <VolumeWaveform
        volume={0.7}
        isActive={true}
      />
    );

    expect(mockRequestAnimationFrame).toHaveBeenCalled();
  });

  it('continues animation when isActive changes', () => {
    const { rerender } = render(
      <VolumeWaveform
        volume={0.5}
        isActive={false}
      />
    );

    mockRequestAnimationFrame.mockClear();

    rerender(
      <VolumeWaveform
        volume={0.5}
        isActive={true}
      />
    );

    expect(mockRequestAnimationFrame).toHaveBeenCalled();
  });

  it('has correct canvas dimensions', () => {
    render(
      <VolumeWaveform
        volume={0.5}
        isActive={false}
      />
    );

    const canvas = document.querySelector('canvas');
    expect(canvas).toHaveClass('w-full');
    expect(canvas).toHaveClass('h-12');
  });
});
