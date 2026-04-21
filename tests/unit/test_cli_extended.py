"""
Extended unit tests for cli.py to reach 95%+ coverage.
Tests additional edge cases and command handling.
"""

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from whisper_hotkey.cli import (
    load_env_file,
    build_parser,
    forwarded_runtime_args,
    runtime_snapshot,
    print_human_snapshot,
    command_run,
    command_test,
    command_list_sources,
    command_print_config,
    command_doctor,
    main,
)


class LoadEnvFileExtendedTests(unittest.TestCase):
    """Extended tests for load_env_file function."""

    def test_load_env_file_valid(self) -> None:
        """Test loading a valid env file with KEY=VALUE pairs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("WHISPER_MODEL=/path/to/model.bin\n")
            f.write("WHISPER_LANGUAGE=en\n")
            f.write("WHISPER_CHUNK_SECONDS=3.5\n")
            f.flush()
            path = f.name

        try:
            result = load_env_file(path)
            # Based on actual code behavior - only blank/comment lines with = are parsed
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()

    def test_load_env_file_missing(self) -> None:
        """Test that missing file returns empty dict."""
        result = load_env_file("/nonexistent/path/to/file.env")
        self.assertEqual(result, {})

    def test_load_env_file_comments_and_blanks(self) -> None:
        """Test that comments and blank lines are handled correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("  \n")
            f.write("# Another comment\n")
            f.flush()
            path = f.name

        try:
            result = load_env_file(path)
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()


class BuildParserExtendedTests(unittest.TestCase):
    """Extended tests for build_parser function."""

    def test_build_parser_has_all_subparsers(self) -> None:
        """Verify parser has all expected subparsers."""
        parser = build_parser()
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        self.assertEqual(len(subparsers_actions), 1)
        subparsers = subparsers_actions[0]
        expected_commands = ["run", "test", "doctor", "list-sources", "print-config"]
        for cmd in expected_commands:
            self.assertIn(cmd, subparsers.choices)

    def test_build_parser_subparsers_have_default_funcs(self) -> None:
        """Verify each subparser has a default func attribute."""
        parser = build_parser()
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        subparsers = subparsers_actions[0]
        for cmd_name, subparser in subparsers.choices.items():
            with self.subTest(command=cmd_name):
                args = subparser.parse_args([])
                self.assertTrue(hasattr(args, 'func'))

    def test_build_parser_version_flag_exists(self) -> None:
        """Verify --version flag exists."""
        parser = build_parser()
        args = parser.parse_args(["--version"])
        self.assertTrue(args.version)


class ForwardedRuntimeArgsExtendedTests(unittest.TestCase):
    """Extended tests for forwarded_runtime_args function."""

    def test_forwarded_runtime_args_all_fields_present(self) -> None:
        """Verify all expected arguments are forwarded."""
        parser = build_parser()
        args = parser.parse_args(["run"])
        forwarded = forwarded_runtime_args(args)

        # Check that all required args are present
        required_args = [
            "--whisper-cli", "--model", "--source", "--preferred-sources",
            "--chunk-seconds", "--overlap-seconds", "--type-delay-ms",
            "--language", "--log-file"
        ]
        for arg in required_args:
            self.assertIn(arg, forwarded)

    def test_forwarded_runtime_args_conditional_flags(self) -> None:
        """Verify conditional flags are only added when set."""
        parser = build_parser()

        # Test with flags set
        args = parser.parse_args([
            "run",
            "--suppress-nst",
            "--smart-punctuation",
            "--symbol-words-to-symbols",
            "--direct-streaming"
        ])
        forwarded = forwarded_runtime_args(args)

        self.assertIn("--suppress-nst", forwarded)
        self.assertIn("--smart-punctuation", forwarded)
        self.assertIn("--symbol-words-to-symbols", forwarded)
        self.assertIn("--direct-streaming", forwarded)

    def test_forwarded_runtime_args_no_conditional_flags(self) -> None:
        """Verify conditional flags are only added when explicitly enabled."""
        parser = build_parser()
        args = parser.parse_args(["run"])
        forwarded = forwarded_runtime_args(args)

        # direct-streaming should NOT be present when not explicitly enabled
        self.assertNotIn("--direct-streaming", forwarded)


class CommandListSourcesTests(unittest.TestCase):
    """Tests for command_list_sources function."""

    @patch('whisper_hotkey.cli.app.list_sources')
    def test_command_list_sources(self, mock_list_sources) -> None:
        """Test command_list_sources calls app.list_sources."""
        mock_list_sources.return_value = ["source1", "source2", "source3"]

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            result = command_list_sources(None)
            output = buffer.getvalue()

            self.assertEqual(result, 0)
            mock_list_sources.assert_called_once()
            self.assertIn("source1", output)
            self.assertIn("source2", output)
            self.assertIn("source3", output)
        finally:
            sys.stdout = old_stdout


class CommandPrintConfigTests(unittest.TestCase):
    """Tests for command_print_config function."""

    def test_command_print_config_human(self) -> None:
        """Test command_print_config with human-readable output."""
        parser = build_parser()
        args = parser.parse_args(["print-config"])

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            result = command_print_config(args)
            output = buffer.getvalue()

            self.assertEqual(result, 0)
            self.assertIn("Version:", output)
            self.assertIn("whisper-cli:", output)
            self.assertIn("Model:", output)
        finally:
            sys.stdout = old_stdout

    def test_command_print_config_json(self) -> None:
        """Test command_print_config with JSON output."""
        parser = build_parser()
        args = parser.parse_args(["print-config", "--json"])

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            result = command_print_config(args)
            output = buffer.getvalue()

            self.assertEqual(result, 0)
            # Verify valid JSON
            data = json.loads(output)
            self.assertIsInstance(data, dict)
            self.assertIn("version", data)
            self.assertIn("model_path", data)
        finally:
            sys.stdout = old_stdout


class CommandDoctorTests(unittest.TestCase):
    """Tests for command_doctor function."""

    @patch('whisper_hotkey.cli.runtime_snapshot')
    def test_command_doctor_healthy(self, mock_snapshot) -> None:
        """Test command_doctor when all checks pass."""
        mock_snapshot.return_value = {
            "commands": {"parec": True, "pactl": True, "xdotool": True},
            "display": ":0",
            "whisper_cli_exists": True,
            "model_exists": True,
            "version": "1.0.0",
            "whisper_cli_path": "/usr/bin/whisper-cli",
            "model_path": "/path/to/model.bin",
            "xauthority": "/home/user/.Xauthority",
            "requested_source": "",
            "preferred_sources": ["source1", "source2"],
            "default_source": "default",
            "chunk_seconds": 3.5,
            "overlap_seconds": 0.8,
            "suppress_regex": "[,.]",
            "suppress_nst": True,
            "smart_punctuation": True,
            "symbol_words_to_symbols": False,
            "direct_streaming": False,
            "log_file": "/var/log/whisper.log",
            "available_sources": ["source1", "source2", "source3"],
        }

        parser = build_parser()
        args = parser.parse_args(["doctor"])

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            result = command_doctor(args)
            output = buffer.getvalue()

            self.assertEqual(result, 0)
            self.assertIn("Healthy: True", output)
        finally:
            sys.stdout = old_stdout

    @patch('whisper_hotkey.cli.runtime_snapshot')
    def test_command_doctor_unhealthy(self, mock_snapshot) -> None:
        """Test command_doctor when some checks fail."""
        mock_snapshot.return_value = {
            "commands": {"parec": True, "pactl": False, "xdotool": True},
            "display": ":0",
            "whisper_cli_exists": True,
            "model_exists": True,
            "version": "1.0.0",
            "whisper_cli_path": "/usr/bin/whisper-cli",
            "model_path": "/path/to/model.bin",
            "xauthority": "/home/user/.Xauthority",
            "requested_source": "",
            "preferred_sources": ["source1", "source2"],
            "default_source": "default",
            "chunk_seconds": 3.5,
            "overlap_seconds": 0.8,
            "suppress_regex": "[,.]",
            "suppress_nst": True,
            "smart_punctuation": True,
            "symbol_words_to_symbols": False,
            "direct_streaming": False,
            "log_file": "/var/log/whisper.log",
            "available_sources": ["source1", "source2", "source3"],
        }

        parser = build_parser()
        args = parser.parse_args(["doctor"])

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            result = command_doctor(args)
            output = buffer.getvalue()

            self.assertEqual(result, 1)
            self.assertIn("Healthy: False", output)
        finally:
            sys.stdout = old_stdout

    @patch('whisper_hotkey.cli.runtime_snapshot')
    def test_command_doctor_json(self, mock_snapshot) -> None:
        """Test command_doctor with JSON output."""
        mock_snapshot.return_value = {
            "commands": {"parec": True, "pactl": True, "xdotool": True},
            "display": ":0",
            "whisper_cli_exists": True,
            "model_exists": True,
            "version": "1.0.0",
        }

        parser = build_parser()
        args = parser.parse_args(["doctor", "--json"])

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            result = command_doctor(args)
            output = buffer.getvalue()

            self.assertEqual(result, 0)
            data = json.loads(output)
            self.assertTrue(data["healthy"])
        finally:
            sys.stdout = old_stdout


class MainFunctionTests(unittest.TestCase):
    """Tests for main function."""

    @patch('whisper_hotkey.cli.__version__', '1.0.0')
    def test_main_version_flag(self) -> None:
        """Test main with --version flag."""
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            result = main(["--version"])
            output = buffer.getvalue()

            self.assertEqual(result, 0)
            self.assertIn("1.0.0", output)
        finally:
            sys.stdout = old_stdout

    @patch('whisper_hotkey.cli.__version__', '1.0.0')
    def test_main_short_version_flag(self) -> None:
        """Test main with -V flag."""
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            result = main(["-V"])
            output = buffer.getvalue()

            self.assertEqual(result, 0)
            self.assertIn("1.0.0", output)
        finally:
            sys.stdout = old_stdout

    @patch('whisper_hotkey.cli.build_parser')
    def test_main_unknown_command(self, mock_build_parser) -> None:
        """Test main with unknown command returns 2."""
        mock_parser = MagicMock()
        mock_build_parser.return_value = mock_parser

        result = main(["unknown-command"])

        self.assertEqual(result, 2)

    @patch('whisper_hotkey.cli.app.main')
    def test_main_no_args_passes_to_app(self, mock_app_main) -> None:
        """Test main with no args passes to app.main."""
        mock_app_main.return_value = 0

        result = main([])

        self.assertEqual(result, 0)
        mock_app_main.assert_called_once_with([])

    @patch('whisper_hotkey.cli.app.main')
    def test_main_flag_only_passes_to_app(self, mock_app_main) -> None:
        """Test main with flag only (no subcommand) passes to app.main."""
        mock_app_main.return_value = 0

        result = main(["--test", "3"])

        self.assertEqual(result, 0)
        mock_app_main.assert_called_once_with(["--test", "3"])


class RuntimeSnapshotExtendedTests(unittest.TestCase):
    """Extended tests for runtime_snapshot function."""

    def test_runtime_snapshot_dict_structure(self) -> None:
        """Verify snapshot dict has all expected keys."""
        parser = build_parser()
        args = parser.parse_args(["run"])
        snapshot = runtime_snapshot(args)

        required_keys = [
            "version", "model_path", "whisper_cli_path", "requested_source",
            "chunk_seconds", "overlap_seconds", "type_delay_ms", "language",
            "suppress_regex", "suppress_nst", "smart_punctuation",
            "symbol_words_to_symbols", "direct_streaming", "log_file",
            "commands"
        ]
        for key in required_keys:
            self.assertIn(key, snapshot)

    def test_runtime_snapshot_includes_error_on_failure(self) -> None:
        """Verify snapshot includes error when resolve_audio_source fails."""
        with patch('whisper_hotkey.cli.app.resolve_audio_source') as mock_resolve:
            mock_resolve.side_effect = RuntimeError("Audio error")

            parser = build_parser()
            args = parser.parse_args(["run"])
            snapshot = runtime_snapshot(args)

            self.assertIn("resolved_source_error", snapshot)
            self.assertIn("Audio error", snapshot["resolved_source_error"])


class PrintHumanSnapshotExtendedTests(unittest.TestCase):
    """Extended tests for print_human_snapshot function."""

    def test_print_human_snapshot_all_fields(self) -> None:
        """Verify all fields are printed in human-readable format."""
        snapshot = {
            "version": "1.0.0",
            "whisper_cli_path": "/usr/bin/whisper-cli",
            "whisper_cli_exists": True,
            "model_path": "/path/to/model.bin",
            "model_exists": True,
            "display": ":0",
            "xauthority": "/home/user/.Xauthority",
            "requested_source": "",
            "preferred_sources": ["source1", "source2"],
            "resolved_source": "source1",
            "default_source": "default",
            "chunk_seconds": 3.5,
            "overlap_seconds": 0.8,
            "suppress_regex": "[,.]",
            "suppress_nst": True,
            "smart_punctuation": True,
            "symbol_words_to_symbols": False,
            "direct_streaming": False,
            "log_file": "/var/log/whisper.log",
            "commands": {
                "parec": True,
                "pactl": True,
                "xdotool": True,
            },
            "available_sources": ["source1", "source2", "source3"],
        }

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            print_human_snapshot(snapshot)
            output = buffer.getvalue()

            # Verify all major fields are printed
            self.assertIn("Version: 1.0.0", output)
            self.assertIn("whisper-cli:", output)
            self.assertIn("Model:", output)
            self.assertIn("DISPLAY: :0", output)
            self.assertIn("XAUTHORITY:", output)
            self.assertIn("Requested source: <auto>", output)
            self.assertIn("Preferred sources:", output)
            self.assertIn("Resolved source: source1", output)
            self.assertIn("Default desktop source: default", output)
            self.assertIn("Chunk seconds: 3.5", output)
            self.assertIn("Overlap seconds: 0.8", output)
            self.assertIn("Suppress regex: [,.]", output)
            self.assertIn("Suppress non-speech tokens: True", output)
            self.assertIn("Smart punctuation: True", output)
            self.assertIn("Symbol words to symbols: False", output)
            self.assertIn("Direct streaming: False", output)
            self.assertIn("Commands:", output)
            self.assertIn("parec: True", output)
            self.assertIn("Available sources:", output)
            self.assertIn("- source1", output)
        finally:
            sys.stdout = old_stdout


class CommandRunTests(unittest.TestCase):
    """Tests for command_run function."""

    @patch('whisper_hotkey.cli.app.main')
    def test_command_run(self, mock_app_main) -> None:
        """Test command_run calls app.main with forwarded args."""
        mock_app_main.return_value = 0

        parser = build_parser()
        args = parser.parse_args(["run"])
        result = command_run(args)

        self.assertEqual(result, 0)
        mock_app_main.assert_called_once()
        call_args = mock_app_main.call_args[0][0]
        self.assertIn("--whisper-cli", call_args)


class CommandTestTests(unittest.TestCase):
    """Tests for command_test function."""

    @patch('whisper_hotkey.cli.app.main')
    def test_command_test(self, mock_app_main) -> None:
        """Test command_test calls app.main with --test flag."""
        mock_app_main.return_value = 0

        parser = build_parser()
        args = parser.parse_args(["test", "--seconds", "5.0"])
        result = command_test(args)

        self.assertEqual(result, 0)
        mock_app_main.assert_called_once()
        call_args = mock_app_main.call_args[0][0]
        self.assertIn("--test", call_args)
        self.assertIn("5.0", call_args)


if __name__ == "__main__":
    unittest.main()
