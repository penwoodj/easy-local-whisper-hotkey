"""FastAPI REST API server for whisper-hotkey control.

Provides HTTP endpoints for configuration, daemon management,
and system diagnostics via HTTP (no Tauri required).
"""
import subprocess
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from .config_store import load_config, save_config, default_config, CONFIG_SCHEMA
from . import app as whisper_app
from .daemon_state import get_daemon_state

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app setup
api = FastAPI(
    title="Whisper Hotkey API",
    version="0.1.0",
    description="REST API for easy-local-whisper-hotkey speech-to-text system"
)

# CORS middleware for local development
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:8420"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def forward_config_args(config: dict[str, Any]) -> list[str]:
    """Build CLI args from config dict, matching cli.py pattern."""
    args = [
        "--whisper-cli", config.get("WHISPER_CLI", ""),
        "--model", config.get("WHISPER_MODEL", ""),
        "--source", config.get("WHISPER_AUDIO_SOURCE", ""),
        "--preferred-sources", config.get("WHISPER_PREFERRED_SOURCES", ""),
        "--chunk-seconds", str(config.get("WHISPER_CHUNK_SECONDS", 3.5)),
        "--overlap-seconds", str(config.get("WHISPER_OVERLAP_SECONDS", 0.8)),
        "--type-delay-ms", str(config.get("WHISPER_TYPE_DELAY_MS", 1)),
        "--language", config.get("WHISPER_LANGUAGE", "en"),
        "--log-file", config.get("WHISPER_LOG_FILE", ""),
    ]

    # Add optional flags
    if config.get("WHISPER_SUPPRESS_REGEX", "[,.]"):
        args.extend(["--suppress-regex", config["WHISPER_SUPPRESS_REGEX"]])
    if config.get("WHISPER_SUPPRESS_NST", True):
        args.append("--suppress-nst")
    if config.get("WHISPER_SMART_PUNCTUATION", True):
        args.append("--smart-punctuation")
    if config.get("WHISPER_SYMBOL_WORDS_TO_SYMBOLS", False):
        args.append("--symbol-words-to-symbols")
    if config.get("WHISPER_DIRECT_STREAMING", False):
        args.append("--direct-streaming")

    return args


@api.get("/api/config")
def get_config() -> dict[str, Any]:
    """Get current configuration.

    Merges env file values with defaults.
    """
    env_config = load_config()
    defaults = default_config()

    # Merge: defaults first, env values override
    result = defaults.copy()
    result.update(env_config)

    return result


@api.put("/api/config")
def update_config(config: dict[str, Any]) -> dict[str, Any]:
    """Update and save configuration.

    Validates all keys against known schema.
    """
    # Validate keys
    invalid_keys = set(config.keys()) - set(CONFIG_SCHEMA.keys())
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid config keys: {', '.join(sorted(invalid_keys))}"
        )

    # Save to env file
    save_config(config)

    # Return merged config
    return get_config()


@api.get("/api/status")
def get_status() -> dict[str, Any]:
    """Get daemon status."""
    daemon = get_daemon_state()
    return daemon.get_status()


@api.post("/api/daemon/start")
def start_daemon() -> dict[str, Any]:
    """Start daemon subprocess."""
    config = get_config()
    args = forward_config_args(config)
    daemon = get_daemon_state()
    result = daemon.start(args)
    return result


@api.post("/api/daemon/stop")
def stop_daemon() -> dict[str, Any]:
    """Stop daemon subprocess."""
    daemon = get_daemon_state()
    result = daemon.stop()
    return result


async def event_generator() -> None:
    """SSE event generator."""
    daemon = get_daemon_state()
    while True:
        try:
            status = daemon.get_status()
            yield f"event: status\ndata: {status}\n\n"

            # TODO: Parse log file for transcription updates
            # For now, just send what we have
            if daemon._last_transcription:
                yield f"event: transcription\ndata: {{'text': '{daemon._last_transcription}'}}\n\n"

        except Exception as e:
            logger.error(f"Error in SSE generator: {e}")


if __name__ == "__main__":
    import uvicorn

    # Run API server
    uvicorn.run(
        api,
        host="127.0.0.1",
        port=8420,
        log_level="info",
    )
