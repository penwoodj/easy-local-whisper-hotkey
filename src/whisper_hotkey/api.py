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

# Daemon state (thread-safe)
_daemon_lock = threading.Lock()
_daemon_process: subprocess.Popen | None = None
_daemon_started_at: str | None = None
_last_transcription: str = ""


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


@api.get("/api/health")
def health_check() -> dict[str, Any]:
    """Simple health check."""
    return {
        "status": "ok",
        "version": "0.1.0",
    }


@api.get("/api/status")
def get_status() -> dict[str, Any]:
    """Get daemon status."""
    with _daemon_lock:
        is_running = _daemon_process is not None

        # Check if process still alive
        if is_running and _daemon_process:
            try:
                _daemon_process.poll()
                if _daemon_process.returncode is not None:
                    # Process exited
                    _daemon_process = None
                    _daemon_started_at = None
                    is_running = False
            except Exception:
                pass

        return {
            "is_running": is_running,
            "pid": _daemon_process.pid if _daemon_process else None,
            "last_started": _daemon_started_at,
            "stream_text": _last_transcription,
        }


@api.post("/api/daemon/start")
def start_daemon() -> dict[str, Any]:
    """Start the daemon subprocess."""
    with _daemon_lock:
        if _daemon_process is not None:
            # Check if still alive
            try:
                _daemon_process.poll()
                if _daemon_process.returncode is None:
                    raise HTTPException(status_code=409, detail="Daemon already running")
            except Exception:
                _daemon_process = None

        # Load current config
        config = get_config()
        args = forward_config_args(config)

        logger.info(f"Starting daemon with args: {' '.join(args)}")

        try:
            # Spawn daemon process
            _daemon_process = subprocess.Popen(
                ["easy-local-whisper-hotkey", "run"] + args,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            _daemon_started_at = datetime.now().isoformat()

            logger.info(f"Daemon started with PID {_daemon_process.pid}")

            return {
                "started": True,
                "pid": _daemon_process.pid,
            }

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start daemon: {e}")


@api.post("/api/daemon/stop")
def stop_daemon() -> dict[str, Any]:
    """Stop the daemon subprocess."""
    with _daemon_lock:
        if _daemon_process is None:
            raise HTTPException(status_code=404, detail="Daemon not running")

        try:
            _daemon_process.poll()
            if _daemon_process.returncode is not None:
                raise HTTPException(status_code=404, detail="Daemon not running (already stopped)")

            # Send SIGTERM
            _daemon_process.terminate()

            # Wait up to 5 seconds
            try:
                _daemon_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Daemon did not stop gracefully, sending SIGKILL")
                _daemon_process.kill()
                _daemon_process.wait()

            _daemon_process = None
            _daemon_started_at = None
            _last_transcription = ""

            logger.info("Daemon stopped")

            return {"stopped": True}

        except Exception as e:
            logger.error(f"Failed to stop daemon: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop daemon: {e}")


@api.get("/api/sources")
def list_sources() -> list[str]:
    """List available audio sources."""
    try:
        sources = whisper_app.list_sources()
        return sources
    except Exception as e:
        logger.error(f"Failed to list sources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sources: {e}")


@api.get("/api/diagnostics")
def get_diagnostics() -> dict[str, Any]:
    """Get full system diagnostics."""
    try:
        config = get_config()

        # Build model and whisper_cli paths
        model_path = Path(config.get("WHISPER_MODEL", "")).expanduser()
        whisper_cli_path = Path(config.get("WHISPER_CLI", "")).expanduser()

        # Get preferred sources
        preferred_sources_str = config.get("WHISPER_PREFERRED_SOURCES", "")
        preferred_sources = whisper_app.parse_preferred_sources(preferred_sources_str)

        # Get diagnostics from app module with error handling
        diagnostics = whisper_app.collect_diagnostics(model_path, whisper_cli_path, preferred_sources)

        # Add config values
        diagnostics["requested_source"] = config.get("WHISPER_AUDIO_SOURCE", "")
        diagnostics["chunk_seconds"] = config.get("WHISPER_CHUNK_SECONDS", 3.5)
        diagnostics["overlap_seconds"] = config.get("WHISPER_OVERLAP_SECONDS", 0.8)
        diagnostics["type_delay_ms"] = config.get("WHISPER_TYPE_DELAY_MS", 1)
        diagnostics["language"] = config.get("WHISPER_LANGUAGE", "en")
        diagnostics["suppress_regex"] = config.get("WHISPER_SUPPRESS_REGEX", "[,.]")
        diagnostics["suppress_nst"] = config.get("WHISPER_SUPPRESS_NST", True)
        diagnostics["smart_punctuation"] = config.get("WHISPER_SMART_PUNCTUATION", True)
        diagnostics["symbol_words_to_symbols"] = config.get("WHISPER_SYMBOL_WORDS_TO_SYMBOLS", False)
        diagnostics["direct_streaming"] = config.get("WHISPER_DIRECT_STREAMING", False)
        diagnostics["log_file"] = config.get("WHISPER_LOG_FILE", "")

        # Add version (hardcoded for API)
        diagnostics["version"] = "0.1.0"

        return diagnostics

    except Exception as e:
        logger.error(f"Failed to collect diagnostics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Diagnostics collection failed: {str(e)}"
        )
        diagnostics["healthy"] = healthy

        return diagnostics

    except Exception as e:
        logger.error(f"Failed to collect diagnostics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect diagnostics: {e}")


async def event_generator() -> None:
    """SSE event generator."""
    while True:
        try:
            # Send status update
            status = get_status()
            yield f"event: status\ndata: {status}\n\n"

            # TODO: Parse log file for transcription updates
            # For now, just send what we have
            if _last_transcription:
                yield f"event: transcription\ndata: {{'text': '{_last_transcription}'}}\n\n"

        except Exception as e:
            logger.error(f"Error in SSE generator: {e}")

        # Wait 1 second
        import asyncio
        await asyncio.sleep(1)


@api.get("/api/events")
async def sse_events() -> StreamingResponse:
    """SSE endpoint for real-time events."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@api.get("/api/health")
def health_check() -> dict[str, Any]:
    """Simple health check."""
    from . import __version__
    return {
        "status": "ok",
        "version": __version__.__version__,
    }


if __name__ == "__main__":
    import uvicorn

    # Run API server
    uvicorn.run(
        api,
        host="127.0.0.1",
        port=8420,
        log_level="info",
    )
