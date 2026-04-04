import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from . import app


KNOWN_COMMANDS = {
    "run",
    "test",
    "doctor",
    "list-sources",
    "print-config",
}


def add_runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--whisper-cli",
        default=str(app.default_whisper_cli()),
        help="Path to whisper.cpp's whisper-cli executable.",
    )
    parser.add_argument(
        "--model",
        default=str(app.DEFAULT_MODEL),
        help="Path to the ggml model file.",
    )
    parser.add_argument(
        "--source",
        default="",
        help="Exact PulseAudio/PipeWire source to use.",
    )
    parser.add_argument(
        "--preferred-sources",
        default=",".join(app.DEFAULT_PREFERRED_SOURCES),
        help="Comma-separated priority list used when --source is not set.",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=float,
        default=1.8,
        help="Streaming segment length before transcription.",
    )
    parser.add_argument(
        "--overlap-seconds",
        type=float,
        default=0.4,
        help="Overlap between adjacent transcription segments.",
    )
    parser.add_argument(
        "--type-delay-ms",
        type=int,
        default=1,
        help="Per-character xdotool delay in milliseconds.",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code passed to whisper-cli.",
    )
    parser.add_argument(
        "--log-file",
        default=str(app.DEFAULT_LOG_FILE),
        help="Path to the runtime log file.",
    )


def forwarded_runtime_args(namespace: argparse.Namespace) -> list[str]:
    return [
        "--whisper-cli",
        namespace.whisper_cli,
        "--model",
        namespace.model,
        "--source",
        namespace.source,
        "--preferred-sources",
        namespace.preferred_sources,
        "--chunk-seconds",
        str(namespace.chunk_seconds),
        "--overlap-seconds",
        str(namespace.overlap_seconds),
        "--type-delay-ms",
        str(namespace.type_delay_ms),
        "--language",
        namespace.language,
        "--log-file",
        namespace.log_file,
    ]


def runtime_snapshot(namespace: argparse.Namespace) -> dict[str, object]:
    model = Path(namespace.model).expanduser()
    whisper_cli = Path(namespace.whisper_cli).expanduser()
    preferred_sources = app.parse_preferred_sources(namespace.preferred_sources)
    diagnostics = app.collect_diagnostics(model, whisper_cli, preferred_sources)
    diagnostics.update(
        {
            "requested_source": namespace.source,
            "chunk_seconds": namespace.chunk_seconds,
            "overlap_seconds": namespace.overlap_seconds,
            "type_delay_ms": namespace.type_delay_ms,
            "language": namespace.language,
            "log_file": namespace.log_file,
            "version": __version__,
        }
    )
    try:
        diagnostics["resolved_source"] = app.resolve_audio_source(
            namespace.source,
            preferred_sources,
        )
    except RuntimeError as exc:
        diagnostics["resolved_source_error"] = str(exc)
    return diagnostics


def print_human_snapshot(snapshot: dict[str, object]) -> None:
    commands = snapshot["commands"]
    print(f"Version: {snapshot['version']}")
    print(f"whisper-cli: {snapshot['whisper_cli_path']} (exists={snapshot['whisper_cli_exists']})")
    print(f"Model: {snapshot['model_path']} (exists={snapshot['model_exists']})")
    print(f"DISPLAY: {snapshot['display'] or '<unset>'}")
    print(f"XAUTHORITY: {snapshot['xauthority'] or '<unset>'}")
    print(f"Requested source: {snapshot['requested_source'] or '<auto>'}")
    print(f"Preferred sources: {', '.join(snapshot['preferred_sources'])}")
    print(f"Resolved source: {snapshot.get('resolved_source', '<unresolved>')}")
    if snapshot.get("resolved_source_error"):
        print(f"Resolved source error: {snapshot['resolved_source_error']}")
    print(f"Default desktop source: {snapshot['default_source'] or '<unknown>'}")
    print("Commands:")
    print(f"  parec: {commands['parec']}")
    print(f"  pactl: {commands['pactl']}")
    print(f"  xdotool: {commands['xdotool']}")
    print("Available sources:")
    for source in snapshot.get("available_sources", []):
        print(f"  - {source}")
    if snapshot.get("source_error"):
        print(f"Source query error: {snapshot['source_error']}")


def command_run(namespace: argparse.Namespace) -> int:
    return app.main(forwarded_runtime_args(namespace))


def command_test(namespace: argparse.Namespace) -> int:
    forwarded = forwarded_runtime_args(namespace)
    forwarded.extend(["--test", str(namespace.seconds)])
    return app.main(forwarded)


def command_list_sources(_namespace: argparse.Namespace) -> int:
    for source in app.list_sources():
        print(source)
    return 0


def command_print_config(namespace: argparse.Namespace) -> int:
    snapshot = runtime_snapshot(namespace)
    if namespace.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print_human_snapshot(snapshot)
    return 0


def command_doctor(namespace: argparse.Namespace) -> int:
    snapshot = runtime_snapshot(namespace)
    healthy = all(snapshot["commands"].values())
    healthy = healthy and bool(snapshot["display"])
    healthy = healthy and bool(snapshot["whisper_cli_exists"])
    healthy = healthy and bool(snapshot["model_exists"])
    healthy = healthy and "resolved_source_error" not in snapshot

    if namespace.json:
        payload = dict(snapshot)
        payload["healthy"] = healthy
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human_snapshot(snapshot)
        print(f"Healthy: {healthy}")

    return 0 if healthy else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whisper-hotkey",
        description="Local X11 push-to-talk dictation powered by whisper.cpp.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the package version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the long-lived Ctrl+Space daemon.")
    add_runtime_options(run_parser)
    run_parser.set_defaults(func=command_run)

    test_parser = subparsers.add_parser("test", help="Record once, transcribe, and type the result.")
    add_runtime_options(test_parser)
    test_parser.add_argument(
        "--seconds",
        type=float,
        default=3.0,
        help="Number of seconds to record before transcription.",
    )
    test_parser.set_defaults(func=command_test)

    list_parser = subparsers.add_parser("list-sources", help="Print detected capture sources.")
    list_parser.set_defaults(func=command_list_sources)

    doctor_parser = subparsers.add_parser("doctor", help="Validate runtime prerequisites.")
    add_runtime_options(doctor_parser)
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the doctor report as JSON.",
    )
    doctor_parser.set_defaults(func=command_doctor)

    config_parser = subparsers.add_parser("print-config", help="Show resolved runtime configuration.")
    add_runtime_options(config_parser)
    config_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the config report as JSON.",
    )
    config_parser.set_defaults(func=command_print_config)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--version"] or args == ["-V"]:
        print(__version__)
        return 0

    if not args or args[0].startswith("-"):
        return app.main(args)

    if args[0] not in KNOWN_COMMANDS:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        parser = build_parser()
        parser.print_help(sys.stderr)
        return 2

    parser = build_parser()
    namespace = parser.parse_args(args)
    if getattr(namespace, "version", False):
        print(__version__)
        return 0
    return namespace.func(namespace)
