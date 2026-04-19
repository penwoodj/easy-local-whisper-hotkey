import { useRef, useEffect } from 'react';

interface VolumeWaveformProps {
  volume: number;
  isActive: boolean;
}

export function VolumeWaveform({ volume, isActive }: VolumeWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const NUM_BARS = 24;
    const CANVAS_WIDTH = 240;
    const CANVAS_HEIGHT = 48;
    const BAR_WIDTH = 8;
    const BAR_GAP = 2;
    const BAR_RADIUS = 2;

    let time = 0;

    const draw = () => {
      ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

      const centerX = CANVAS_WIDTH / 2;
      const startY = CANVAS_HEIGHT;

      for (let i = 0; i < NUM_BARS; i++) {
        const distanceFromCenter = Math.abs(i - (NUM_BARS - 1) / 2) / (NUM_BARS / 2);
        const sineModulation = Math.sin(time + i * 0.2) * 0.3 + 0.7;

        let amplitude: number;
        if (isActive) {
          amplitude = volume * 40 * sineModulation * (1 - distanceFromCenter * 0.5);
        } else {
          amplitude = 2;
        }

        const x = centerX + (i - (NUM_BARS - 1) / 2) * (BAR_WIDTH + BAR_GAP) - BAR_WIDTH / 2;
        const y = startY - amplitude;

        const hue = 159 + (101 * distanceFromCenter);
        ctx.fillStyle = `hsl(${hue}, 84%, 39%)`;

        ctx.beginPath();
        ctx.roundRect(x, y, BAR_WIDTH, amplitude, [BAR_RADIUS, BAR_RADIUS, 0, 0]);
        ctx.fill();
      }

      time += 0.08;
      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [volume, isActive]);

  return (
    <canvas
      ref={canvasRef}
      width={240}
      height={48}
      className="w-full h-12"
    />
  );
}
