"""Configuration file storage for whisper-hotkey."""

import os
from pathlib import Path
from typing import Any

CONFIG_SCHEMA = {
    "WHISPER_CLI": str,
    "WHISPER_MODEL": str,
    "WHISPER_AUDIO_SOURCE": str,
    "WHISPER_PREFERRED_SOURCES": str,
    "WHISPER_CHUNK_SECONDS": float,
    "WHISPER_OVERLAP_SECONDS": float,
    "WHISPER_TYPE_DELAY_MS": int,
    "WHISPER_LANGUAGE": str,
    "WHISPER_SUPPRESS_REGEX": str,
    "WHISPER_SUPPRESS_NST": bool,
    "WHISPER_SMART_PUNCTUATION": bool,
    "WHISPER_SYMBOL_WORDS_TO_SYMBOLS": bool,
    "WHISPER_DIRECT_STREAMING": bool,
    "WHISPER_LOG_FILE": str,
    "WHISPER_LOG_LEVEL": str,
    "WHISPER_ACTIVATION_MODE": str,
    "WHISPER_POST_PROCESSING_ENABLED": bool,
    "WHISPER_POST_PROCESSING_MODE": str,
    "WHISPER_POST_PROCESSING_TRIGGER": str,
    "WHISPER_INDICATOR": bool,
}

CONFIG_DIR = Path(os.environ.get("WHISPER_CONFIG_DIR", "~/.config/whisper-hotkey")).expanduser()
CONFIG_FILE = CONFIG_DIR / "whisper-hotkey.env"


def default_config() -> dict[str, Any]:
    """Return default configuration values."""
    from . import app

    return {
        "WHISPER_CLI": str(app.default_whisper_cli()),
        "WHISPER_MODEL": str(app.DEFAULT_MODEL),
        "WHISPER_AUDIO_SOURCE": "",
        "WHISPER_PREFERRED_SOURCES": ",".join(app.DEFAULT_PREFERRED_SOURCES),
        "WHISPER_CHUNK_SECONDS": 3.5,
        "WHISPER_OVERLAP_SECONDS": 0.8,
        "WHISPER_TYPE_DELAY_MS": 1,
        "WHISPER_LANGUAGE": "en",
        "WHISPER_SUPPRESS_REGEX": "[,.]",
        "WHISPER_SUPPRESS_NST": True,
        "WHISPER_SMART_PUNCTUATION": True,
        "WHISPER_SYMBOL_WORDS_TO_SYMBOLS": False,
        "WHISPER_DIRECT_STREAMING": False,
        "WHISPER_LOG_FILE": str(app.DEFAULT_LOG_FILE),
        "WHISPER_LOG_LEVEL": "info",
        "WHISPER_ACTIVATION_MODE": "toggle",
        "WHISPER_POST_PROCESSING_ENABLED": False,
        "WHISPER_POST_PROCESSING_MODE": "off",
        "WHISPER_POST_PROCESSING_TRIGGER": "manual",
        "WHISPER_INDICATOR": True,
    }


def load_config() -> dict[str, Any]:
    """Load configuration from env file.

    Returns typed values according to CONFIG_SCHEMA.
    Returns empty dict if file doesn't exist.
    """
    config: dict[str, Any] = {}

    if not CONFIG_FILE.exists():
        return config

    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key in CONFIG_SCHEMA:
                    type_hint = CONFIG_SCHEMA[key]
                    try:
                        if type_hint is bool:
                            config[key] = value.lower() in ("true", "1", "yes", "on")
                        elif type_hint is int:
                            config[key] = int(value)
                        elif type_hint is float:
                            config[key] = float(value)
                        else:
                            config[key] = value
                    except (ValueError, TypeError):
                        pass

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to env file.

    Preserves comments and unknown keys.
    Creates parent directories if needed.
    """
    existing_lines = []
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    written_keys = set()
    output_lines = []

    for line in existing_lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            output_lines.append(line)
            continue

        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()

            if key in config:
                type_hint = CONFIG_SCHEMA.get(key, str)
                value = config[key]

                if isinstance(value, bool):
                    str_value = "true" if value else "false"
                else:
                    str_value = str(value)

                output_lines.append(f"{key}={str_value}\n")
                written_keys.add(key)
            else:
                output_lines.append(line)

    for key, value in config.items():
        if key not in written_keys and key in CONFIG_SCHEMA:
            if isinstance(value, bool):
                str_value = "true" if value else "false"
            else:
                str_value = str(value)

            output_lines.append(f"{key}={str_value}\n")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        f.writelines(output_lines)
