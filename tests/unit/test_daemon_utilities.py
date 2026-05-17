import unittest
from pathlib import Path
from unittest.mock import patch

from whisper_hotkey import app


class ShellJoinTests(unittest.TestCase):
    def test_shell_join_empty_list(self) -> None:
        result = app.shell_join([])
        self.assertEqual(result, "")

    def test_shell_join_single_item(self) -> None:
        result = app.shell_join(["command"])
        self.assertEqual(result, "command")

    def test_shell_join_multiple_items(self) -> None:
        result = app.shell_join(["ls", "-la", "/home/user"])
        self.assertEqual(result, "ls -la /home/user")

    def test_shell_join_items_with_spaces(self) -> None:
        result = app.shell_join(["echo", "hello world", "foo bar"])
        self.assertEqual(result, "echo 'hello world' 'foo bar'")

    def test_shell_join_items_with_quotes(self) -> None:
        result = app.shell_join(["echo", "'single'", '"double"'])
        # shlex.quote produces different escaping depending on the shell
        self.assertIn("echo", result)
        self.assertIn("single", result)
        self.assertIn("double", result)

    def test_shell_join_special_characters(self) -> None:
        result = app.shell_join(["cmd", "$VAR", ";bad"])
        self.assertEqual(result, "cmd '$VAR' ';bad'")


class ShutilWhichTests(unittest.TestCase):
    @patch.dict('os.environ', {'PATH': '/usr/bin:/bin'})
    @patch('pathlib.Path.is_file', return_value=True)
    @patch('os.access', return_value=True)
    def test_shutil_which_existing_command(self, _access, _is_file) -> None:
        result = app.shutil_which("ls")
        self.assertEqual(result, "/usr/bin/ls")

    @patch.dict('os.environ', {'PATH': '/usr/bin:/bin'})
    @patch('pathlib.Path.is_file', return_value=False)
    def test_shutil_which_missing_command(self, _is_file) -> None:
        result = app.shutil_which("nonexistent")
        self.assertEqual(result, "")

    @patch.dict('os.environ', {'PATH': ''})
    def test_shutil_which_empty_path(self) -> None:
        result = app.shutil_which("ls")
        self.assertEqual(result, "")

    @patch.dict('os.environ', {'PATH': '/usr/bin:/bin'})
    @patch('pathlib.Path.is_file', side_effect=lambda: False)
    @patch('os.access', return_value=True)
    def test_shutil_which_not_executable(self, _access, _is_file) -> None:
        result = app.shutil_which("ls")
        self.assertEqual(result, "")


class DefaultWhisperCliTests(unittest.TestCase):
    @patch.dict('os.environ', {}, clear=True)
    @patch('whisper_hotkey.app.shutil_which', return_value='/usr/bin/whisper-cli')
    def test_default_whisper_cli_from_path(self, _which) -> None:
        result = app.default_whisper_cli()
        self.assertEqual(result, Path("/usr/bin/whisper-cli"))

    @patch.dict('os.environ', {'WHISPER_CLI': '/custom/path/whisper'})
    def test_default_whisper_cli_from_env(self) -> None:
        result = app.default_whisper_cli()
        self.assertEqual(result, Path("/custom/path/whisper"))

    @patch.dict('os.environ', {'WHISPER_CLI': '~/whisper-cli'})
    def test_default_whisper_cli_expanduser(self) -> None:
        result = app.default_whisper_cli()
        self.assertTrue(str(result).startswith("/"))

    @patch.dict('os.environ', {}, clear=True)
    @patch('whisper_hotkey.app.shutil_which', return_value='')
    def test_default_whisper_cli_fallback(self, _which) -> None:
        result = app.default_whisper_cli()
        # No hardcoded fallback - returns empty Path (".") when not found
        self.assertEqual(result, Path())


class NormalizeTokenTests(unittest.TestCase):
    def test_normalize_token_basic(self) -> None:
        result = app.normalize_token("Hello")
        self.assertEqual(result, "hello")

    def test_normalize_token_with_special_chars(self) -> None:
        result = app.normalize_token("Hello, World!")
        self.assertEqual(result, "helloworld")

    def test_normalize_token_with_spaces(self) -> None:
        result = app.normalize_token("Hello World")
        self.assertEqual(result, "helloworld")

    def test_normalize_token_with_punctuation(self) -> None:
        result = app.normalize_token("test.value")
        self.assertEqual(result, "testvalue")

    def test_normalize_token_with_numbers(self) -> None:
        result = app.normalize_token("test123")
        self.assertEqual(result, "test123")

    def test_normalize_token_empty_string(self) -> None:
        result = app.normalize_token("")
        self.assertEqual(result, "")

    def test_normalize_token_with_underscores(self) -> None:
        result = app.normalize_token("test_value")
        self.assertEqual(result, "test_value")

    def test_normalize_token_with_hyphens(self) -> None:
        result = app.normalize_token("test-value")
        self.assertEqual(result, "testvalue")


class CollectDiagnosticsTests(unittest.TestCase):
    @patch('whisper_hotkey.app.list_sources', return_value=['source1', 'source2'])
    @patch('whisper_hotkey.app.get_default_source', return_value='default-source')
    @patch('whisper_hotkey.app.shutil_which')
    def test_collect_diagnostics_structure(self, mock_which, _default, _list_sources) -> None:
        mock_which.side_effect = lambda cmd: cmd == "parec"

        model = Path("/path/to/model")
        whisper_cli = Path("/path/to/whisper-cli")
        preferred_sources = ["source1", "source2"]

        result = app.collect_diagnostics(model, whisper_cli, preferred_sources)

        self.assertIsInstance(result, dict)
        self.assertIn("display", result)
        self.assertIn("xauthority", result)
        self.assertIn("model_path", result)
        self.assertIn("model_exists", result)
        self.assertIn("whisper_cli_path", result)
        self.assertIn("whisper_cli_exists", result)
        self.assertIn("commands", result)
        self.assertIn("preferred_sources", result)
        self.assertIn("default_source", result)
        self.assertIn("available_sources", result)
        self.assertIn("source_error", result)

    @patch('whisper_hotkey.app.list_sources', return_value=['source1'])
    @patch('whisper_hotkey.app.get_default_source', return_value='')
    @patch('whisper_hotkey.app.shutil_which', return_value='')
    def test_collect_diagnostics_with_source_error(self, _which, _default, mock_list_sources) -> None:
        mock_list_sources.side_effect = RuntimeError("unable to query audio sources")

        model = Path("/path/to/model")
        whisper_cli = Path("/path/to/whisper-cli")
        preferred_sources = ["source1"]

        result = app.collect_diagnostics(model, whisper_cli, preferred_sources)

        self.assertIn("source_error", result)
        self.assertEqual(result["source_error"], "unable to query audio sources")
        self.assertEqual(result["available_sources"], [])

    @patch('whisper_hotkey.app.list_sources', return_value=['source1'])
    @patch('whisper_hotkey.app.get_default_source', return_value='default-source')
    @patch('whisper_hotkey.app.shutil_which', side_effect=lambda cmd: cmd)
    def test_collect_diagnostics_commands_present(self, _which, _default, _list_sources) -> None:
        model = Path("/path/to/model")
        whisper_cli = Path("/path/to/whisper-cli")
        preferred_sources = ["source1"]

        result = app.collect_diagnostics(model, whisper_cli, preferred_sources)

        commands = result["commands"]
        self.assertTrue(commands["parec"])
        self.assertTrue(commands["pactl"])
        self.assertTrue(commands["xdotool"])

    @patch('whisper_hotkey.app.list_sources', return_value=['source1'])
    @patch('whisper_hotkey.app.get_default_source', return_value='default-source')
    @patch.dict('os.environ', {'DISPLAY': ':0', 'XAUTHORITY': '/tmp/xauth'})
    @patch('whisper_hotkey.app.shutil_which', return_value='')
    def test_collect_diagnostics_environment(self, _which, _default, _list_sources) -> None:
        model = Path("/path/to/model")
        whisper_cli = Path("/path/to/whisper-cli")
        preferred_sources = ["source1"]

        result = app.collect_diagnostics(model, whisper_cli, preferred_sources)

        self.assertEqual(result["display"], ":0")
        self.assertEqual(result["xauthority"], "/tmp/xauth")


if __name__ == "__main__":
    unittest.main()
