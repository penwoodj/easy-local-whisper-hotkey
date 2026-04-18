#!/usr/bin/env python3
"""
Generate 32 PNG frames for pulsing light ball indicator.
Creates a glowing orb with breathing animation using multi-layered gradients.
"""
import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def generate_pulsing_light_frames(output_dir: Path, frames: int = 32) -> None:
    """Generate 32 frames of pulsing light ball indicator."""
    output_dir.mkdir(parents=True, exist_ok=True)

    size = 10
    center = size // 2
    max_radius = size // 2 - 1

    for i in range(frames):
        phase = (i / frames) * 2 * np.pi
        pulse = np.sin(phase)

        intensity = 0.7 + 0.3 * pulse
        size_pulse = 0.85 + 0.15 * pulse

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Layer 1: Outer glow (cool blue, very diffuse)
        outer_radius = max_radius * size_pulse
        outer_alpha = int(40 * intensity)
        if outer_radius > 0:
            for r in range(int(outer_radius), int(outer_radius) - 2, -1):
                if r > 0:
                    alpha = outer_alpha * (1 - (outer_radius - r) / 2)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(100, 140, 180, alpha),
                        outline=None
                    )

        mid_radius = max_radius * 0.75 * size_pulse
        mid_alpha = int(80 * intensity)
        if mid_radius > 0:
            for r in range(int(mid_radius), int(mid_radius) - 2, -1):
                if r > 0:
                    alpha = mid_alpha * (1 - (mid_radius - r) / 2)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(140, 190, 220, alpha),
                        outline=None
                    )

        inner_radius = max_radius * 0.5 * size_pulse
        inner_alpha = int(140 * intensity)
        if inner_radius > 0:
            for r in range(int(inner_radius), int(inner_radius) - 2, -1):
                if r > 0:
                    alpha = inner_alpha * (1 - (inner_radius - r) / 2)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(220, 230, 255, alpha),
                        outline=None
                    )

        core_radius = max_radius * 0.35 * size_pulse
        if core_radius > 0:
            core_alpha = int(200 * intensity)
            draw.ellipse(
                [(center - core_radius, center - core_radius),
                 (center + core_radius, center + core_radius)],
                fill=(255, 255, 240, core_alpha),
                outline=None
            )

            center_radius = max(1, core_radius * 0.6)
            draw.ellipse(
                [(center - center_radius, center - center_radius),
                 (center + center_radius, center + center_radius)],
                fill=(255, 255, 255, 255),
                outline=None
            )

        output_path = output_dir / f"gradient_frame_{i:03d}.png"
        img.save(output_path, optimize=True)
        print(f"Generated frame {i+1}/{frames}: {output_path}")

    print(f"\nGenerated {frames} frames to {output_dir}")


def main() -> None:
    """Generate pulsing light ball frames for indicator."""
    project_root = Path(__file__).parent.parent.parent
    output_dir = project_root / "src" / "whisper_hotkey" / "indicator_frames"

    generate_pulsing_light_frames(output_dir, frames=32)


if __name__ == "__main__":
    main()
