#!/usr/bin/env python3
import math
from pathlib import Path
from PIL import Image, ImageDraw


STATE_COLORS = {
    "IDLE": {
        "name": "idle",
        "base": (148, 163, 184),
        "bright": (226, 232, 240),
    },
    "RECORDING": {
        "name": "recording",
        "base": (14, 165, 233),
        "bright": (125, 211, 252),
    },
    "PROCESSING": {
        "name": "processing",
        "base": (139, 92, 246),
        "bright": (192, 132, 252),
    },
}


def generate_state_frames(
    output_dir: Path,
    state: str,
    frames: int = 32,
    size: int = 64
) -> None:
    """Generate frames for a specific state."""
    state_dir = output_dir / STATE_COLORS[state]["name"]
    state_dir.mkdir(parents=True, exist_ok=True)

    base_color = STATE_COLORS[state]["base"]
    bright_color = STATE_COLORS[state]["bright"]

    print(f"Generating {frames} frames for {state} state at {size}x{size}px...")

    for i in range(frames):
        phase = (i / frames) * 2 * math.pi
        pulse = (math.sin(phase) + 1) / 2
        opacity = 0.8 + 0.2 * pulse

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        center = size // 2
        max_radius = size // 2 - 2

        outer_radius = max_radius * 1.0
        outer_alpha = int(40 * opacity)
        if outer_radius > 0:
            for r in range(int(outer_radius), int(outer_radius) - 4, -1):
                if r > 0:
                    alpha = outer_alpha * (1 - (outer_radius - r) / 4)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(*base_color, alpha),
                        outline=None
                    )

        mid_radius = max_radius * 0.75
        mid_alpha = int(80 * opacity)
        if mid_radius > 0:
            for r in range(int(mid_radius), int(mid_radius) - 4, -1):
                if r > 0:
                    alpha = mid_alpha * (1 - (mid_radius - r) / 4)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(*base_color, alpha),
                        outline=None
                    )

        inner_radius = max_radius * 0.5
        inner_alpha = int(140 * opacity)
        if inner_radius > 0:
            for r in range(int(inner_radius), int(inner_radius) - 3, -1):
                if r > 0:
                    alpha = inner_alpha * (1 - (inner_radius - r) / 3)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(*bright_color, alpha),
                        outline=None
                    )

        core_radius = max_radius * 0.35
        if core_radius > 0:
            core_alpha = int(200 * opacity)
            draw.ellipse(
                [(center - core_radius, center - core_radius),
                 (center + core_radius, center + core_radius)],
                fill=(*bright_color, core_alpha),
                outline=None
            )

        center_radius = max(2, core_radius * 0.6)
        center_alpha = int(240 * opacity)
        draw.ellipse(
            [(center - center_radius, center - center_radius),
             (center + center_radius, center + center_radius)],
            fill=(255, 255, 255, center_alpha),
            outline=None
        )

        output_path = state_dir / f"frame_{i:03d}.png"
        img.save(output_path, optimize=True)

    print(f"Generated {frames} frames to {state_dir}")


def generate_gradient_frames(
    output_dir: Path,
    frames: int = 32,
    size: int = 64
) -> None:
    """Generate backward-compatible gradient frames (recording state)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    base_color = STATE_COLORS["RECORDING"]["base"]
    bright_color = STATE_COLORS["RECORDING"]["bright"]

    print(f"Generating {frames} backward-compatible gradient frames at {size}x{size}px...")

    for i in range(frames):
        phase = (i / frames) * 2 * math.pi
        pulse = (math.sin(phase) + 1) / 2
        opacity = 0.8 + 0.2 * pulse

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        center = size // 2
        max_radius = size // 2 - 2

        outer_radius = max_radius * 1.0
        outer_radius = max_radius * 1.0
        outer_alpha = int(40 * opacity)
        if outer_radius > 0:
            for r in range(int(outer_radius), int(outer_radius) - 4, -1):
                if r > 0:
                    alpha = outer_alpha * (1 - (outer_radius - r) / 4)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(*base_color, alpha),
                        outline=None
                    )

        mid_radius = max_radius * 0.75
        mid_alpha = int(80 * opacity)
        if mid_radius > 0:
            for r in range(int(mid_radius), int(mid_radius) - 4, -1):
                if r > 0:
                    alpha = mid_alpha * (1 - (mid_radius - r) / 4)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(*base_color, alpha),
                        outline=None
                    )

        inner_radius = max_radius * 0.5
        inner_alpha = int(140 * opacity)
        if inner_radius > 0:
            for r in range(int(inner_radius), int(inner_radius) - 3, -1):
                if r > 0:
                    alpha = inner_alpha * (1 - (inner_radius - r) / 3)
                    alpha = max(0, min(255, int(alpha)))
                    draw.ellipse(
                        [(center - r, center - r), (center + r, center + r)],
                        fill=(*bright_color, alpha),
                        outline=None
                    )

        core_radius = max_radius * 0.35
        if core_radius > 0:
            core_alpha = int(200 * opacity)
            draw.ellipse(
                [(center - core_radius, center - core_radius),
                 (center + core_radius, center + core_radius)],
                fill=(*bright_color, core_alpha),
                outline=None
            )

        center_radius = max(2, core_radius * 0.6)
        center_alpha = int(240 * opacity)
        draw.ellipse(
            [(center - center_radius, center - center_radius),
             (center + center_radius, center + center_radius)],
            fill=(255, 255, 255, center_alpha),
            outline=None
        )

        output_path = output_dir / f"gradient_frame_{i:03d}.png"
        img.save(output_path, optimize=True)

    print(f"Generated {frames} frames to {output_dir}")


def main() -> None:
    """Generate all indicator frames."""
    project_root = Path(__file__).parent.parent.parent
    output_dir = project_root / "src" / "whisper_hotkey" / "indicator_frames"

    print("=" * 60)
    print("Generating 64x64px indicator frames with breathing animation")
    print("=" * 60)

    for state in STATE_COLORS.keys():
        generate_state_frames(output_dir, state, frames=32, size=64)

    generate_gradient_frames(output_dir, frames=32, size=64)

    print("=" * 60)
    print("Frame generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
