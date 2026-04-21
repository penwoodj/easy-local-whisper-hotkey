import unittest
import tempfile
from pathlib import Path

from whisper_hotkey.cli import load_env_file, add_runtime_options, forwarded_runtime_args, runtime_snapshot, print_human_snapshot, build_parser
from whisper_hotkey import app


class LoadEnvFileTests(unittest.TestCase):
    def test_load_valid_env_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("KEY1=value1\n")
            f.write("KEY2=value2\n")
            f.write("KEY3=value with spaces\n")
            f.flush()
            path = f.name

        try:
            result = load_env_file(path)
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()

    def test_load_missing_file_returns_empty_dict(self) -> None:
        result = load_env_file("/nonexistent/file.env")
        self.assertEqual(result, {})

    def test_load_empty_file_returns_empty_dict(self) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            path = f.name

        try:
            result = load_env_file(path)
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()

    def test_load_file_with_comments_only(self) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# comment 1\n")
            f.write("# comment 2\n")
            f.flush()
            path = f.name

        try:
            result = load_env_file(path)
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()

    def test_load_file_with_malformed_lines(self) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("KEY1=value1\n")
            f.write("line without equals\n")
            f.write("KEY2=value2\n")
            f.flush()
            path = f.name

        try:
            result = load_env_file(path)
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()

    def test_load_file_with_empty_values(self) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("KEY1=\n")
            f.write("KEY2=value2\n")
            f.write("KEY3=\n")
            f.flush()
            path = f.name

        try:
            result = load_env_file(path)
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()

    def test_load_file_with_whitespace_stripping(self) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("  KEY1  =  value1  \n")
            f.write("KEY2=value2\n")
            f.flush()
            path = f.name

        try:
            result = load_env_file(path)
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()

    def test_load_file_with_equals_in_value(self) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("KEY1=value=with=equals\n")
            f.write("KEY2=value2\n")
            f.flush()
            path = f.name

        try:
            result = load_env_file(path)
            self.assertEqual(result, {})
        finally:
            Path(path).unlink()


class AddRuntimeOptionsTests(unittest.TestCase):
    def test_add_runtime_options_adds_all_arguments(self) -> None:
        import argparse
        parser = argparse.ArgumentParser()
        add_runtime_options(parser)
        args = parser.parse_args([])
        self.assertTrue(hasattr(args, 'whisper_cli'))
        self.assertTrue(hasattr(args, 'model'))
        self.assertTrue(hasattr(args, 'source'))
        self.assertTrue(hasattr(args, 'preferred_sources'))
        self.assertTrue(hasattr(args, 'chunk_seconds'))
        self.assertTrue(hasattr(args, 'overlap_seconds'))
        self.assertTrue(hasattr(args, 'type_delay_ms'))
        self.assertTrue(hasattr(args, 'language'))
        self.assertTrue(hasattr(args, 'suppress_regex'))
        self.assertTrue(hasattr(args, 'suppress_nst'))
        self.assertTrue(hasattr(args, 'smart_punctuation'))
        self.assertTrue(hasattr(args, 'symbol_words_to_symbols'))
        self.assertTrue(hasattr(args, 'direct_streaming'))
        self.assertTrue(hasattr(args, 'config_env_file'))
        self.assertTrue(hasattr(args, 'log_file'))

    def test_add_runtime_options_sets_defaults(self) -> None:
        import argparse
        parser = argparse.ArgumentParser()
        add_runtime_options(parser)
        args = parser.parse_args([])
        self.assertIsNotNone(args.whisper_cli)
        self.assertIsNotNone(args.model)
        self.assertEqual(args.source, "")
        self.assertIsNotNone(args.preferred_sources)
        self.assertIsInstance(args.chunk_seconds, float)
        self.assertIsInstance(args.overlap_seconds, float)
        self.assertIsInstance(args.type_delay_ms, int)
        self.assertEqual(args.language, "en")
        self.assertEqual(args.suppress_regex, "[,.]")
        self.assertIsInstance(args.suppress_nst, bool)
        self.assertIsInstance(args.smart_punctuation, bool)
        self.assertIsInstance(args.symbol_words_to_symbols, bool)
        self.assertIsInstance(args.direct_streaming, bool)
        self.assertEqual(args.config_env_file, "")
        self.assertIsNotNone(args.log_file)


class ForwardedRuntimeArgsTests(unittest.TestCase):
    def test_forwarded_runtime_args_basic(self) -> None:
        import argparse
        from whisper_hotkey.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["run"])
        forwarded = forwarded_runtime_args(args)
        self.assertIn("--whisper-cli", forwarded)
        self.assertIn("--model", forwarded)
        self.assertIn("--source", forwarded)
        self.assertIn("--preferred-sources", forwarded)
        self.assertIn("--chunk-seconds", forwarded)
        self.assertIn("--overlap-seconds", forwarded)
        self.assertIn("--type-delay-ms", forwarded)
        self.assertIn("--language", forwarded)
        self.assertIn("--log-file", forwarded)

    def test_forwarded_runtime_args_with_flags(self) -> None:
        import argparse
        from whisper_hotkey.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["run", "--suppress-nst", "--smart-punctuation"])
        forwarded = forwarded_runtime_args(args)
        self.assertIn("--suppress-nst", forwarded)
        self.assertIn("--smart-punctuation", forwarded)

    def test_forwarded_runtime_args_values(self) -> None:
        import argparse
        from whisper_hotkey.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["run", "--model", "/path/to/model", "--language", "es"])
        forwarded = forwarded_runtime_args(args)
        self.assertIn("--model", forwarded)
        model_idx = forwarded.index("--model")
        self.assertEqual(forwarded[model_idx + 1], "/path/to/model")
        self.assertIn("--language", forwarded)
        lang_idx = forwarded.index("--language")
        self.assertEqual(forwarded[lang_idx + 1], "es")


class RuntimeSnapshotTests(unittest.TestCase):
    def test_runtime_snapshot_structure(self) -> None:
        import argparse
        from whisper_hotkey.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["run"])
        snapshot = runtime_snapshot(args)
        self.assertIsInstance(snapshot, dict)
        self.assertIn("version", snapshot)
        self.assertIn("model_path", snapshot)
        self.assertIn("whisper_cli_path", snapshot)
        self.assertIn("requested_source", snapshot)
        self.assertIn("chunk_seconds", snapshot)
        self.assertIn("overlap_seconds", snapshot)
        self.assertIn("type_delay_ms", snapshot)
        self.assertIn("language", snapshot)
        self.assertIn("commands", snapshot)

    def test_runtime_snapshot_contains_diagnostics(self) -> None:
        import argparse
        from whisper_hotkey.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["run"])
        snapshot = runtime_snapshot(args)
        commands = snapshot["commands"]
        self.assertIn("parec", commands)
        self.assertIn("pactl", commands)
        self.assertIn("xdotool", commands)


class PrintHumanSnapshotTests(unittest.TestCase):
    def test_print_human_snapshot_output_format(self) -> None:
        import io
        import sys
        from whisper_hotkey.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["run"])
        snapshot = runtime_snapshot(args)

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            print_human_snapshot(snapshot)
            output = buffer.getvalue()
            self.assertIn("Version:", output)
            self.assertIn("whisper-cli:", output)
            self.assertIn("Model:", output)
            self.assertIn("DISPLAY:", output)
            self.assertIn("Requested source:", output)
            self.assertIn("Preferred sources:", output)
            self.assertIn("Chunk seconds:", output)
            self.assertIn("Overlap seconds:", output)
        finally:
            sys.stdout = old_stdout


class BuildParserTests(unittest.TestCase):
    def test_build_parser_creates_subparsers(self) -> None:
        import argparse
        parser = build_parser()
        subparsers_actions = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
        self.assertEqual(len(subparsers_actions), 1)
        subparsers = subparsers_actions[0]
        self.assertIn("run", subparsers.choices)
        self.assertIn("test", subparsers.choices)
        self.assertIn("doctor", subparsers.choices)
        self.assertIn("list-sources", subparsers.choices)
        self.assertIn("print-config", subparsers.choices)

    def test_build_parser_run_command_has_runtime_options(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run"])
        self.assertTrue(hasattr(args, 'whisper_cli'))
        self.assertTrue(hasattr(args, 'model'))
        self.assertTrue(hasattr(args, 'source'))

    def test_build_parser_test_command_has_seconds_arg(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["test", "--seconds", "5.0"])
        self.assertEqual(args.seconds, 5.0)

    def test_build_parser_doctor_command_has_json_arg(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["doctor", "--json"])
        self.assertTrue(args.json)

    def test_build_parser_print_config_command_has_json_arg(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["print-config", "--json"])
        self.assertTrue(args.json)

    def test_build_parser_version_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--version"])
        self.assertTrue(args.version)


if __name__ == "__main__":
    unittest.main()
