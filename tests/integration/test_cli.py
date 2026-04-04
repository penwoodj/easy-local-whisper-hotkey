import io
import unittest
from unittest.mock import patch

from whisper_hotkey import __version__
from whisper_hotkey import cli


class CliTests(unittest.TestCase):
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_version_flag_prints_version(self, stdout) -> None:
        result = cli.main(["--version"])
        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue().strip(), __version__)

    @patch("whisper_hotkey.cli.app.main", return_value=0)
    def test_run_command_forwards_runtime_args(self, main_mock) -> None:
        result = cli.main(["run", "--model", "/tmp/model.bin", "--source", "mic-a"])
        self.assertEqual(result, 0)
        forwarded = main_mock.call_args.args[0]
        self.assertIn("--model", forwarded)
        self.assertIn("/tmp/model.bin", forwarded)
        self.assertIn("--source", forwarded)
        self.assertIn("mic-a", forwarded)

    @patch("whisper_hotkey.cli.app.resolve_audio_source", return_value="mic-a")
    @patch(
        "whisper_hotkey.cli.app.collect_diagnostics",
        return_value={
            "commands": {"parec": True, "pactl": True, "xdotool": True},
            "display": ":0",
            "xauthority": "/tmp/.Xauthority",
            "model_path": "/tmp/model.bin",
            "model_exists": True,
            "whisper_cli_path": "/usr/bin/whisper-cli",
            "whisper_cli_exists": True,
            "preferred_sources": ["mic-a"],
            "default_source": "mic-a",
            "available_sources": ["mic-a"],
            "source_error": "",
        },
    )
    def test_doctor_returns_zero_when_healthy(self, _diagnostics, _resolve) -> None:
        result = cli.main(["doctor", "--model", "/tmp/model.bin", "--source", "mic-a", "--json"])
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
