"""
Extended unit tests for postprocessor.py to reach 95%+ coverage.
Tests additional edge cases and installation functions.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from whisper_hotkey.postprocessor import (
    PostProcessor,
    PostProcessMode,
    PostProcessTrigger,
    install_deepmultilingualpunctuation,
    install_llama_cpp,
    install_anthropic,
)


class PostProcessorExceptionHandlingTests(unittest.TestCase):
    """Tests for exception handling in PostProcessor.process()."""

    @patch('whisper_hotkey.postprocessor.PostProcessor._process_light')
    def test_process_returns_original_on_exception(self, mock_process_light) -> None:
        """Test that process returns original text when an exception occurs."""
        mock_process_light.side_effect = Exception("Processing error")

        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "this is a test"

        result = pp.process(text)

        # Should return original text on exception
        self.assertEqual(result, text)


class PostProcessorModeTests(unittest.TestCase):
    """Tests for specific post-processing modes."""

    def test_process_code_mode_returns_text(self) -> None:
        """Test that code mode returns text unchanged."""
        pp = PostProcessor(
            mode=PostProcessMode.CODE,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "def hello():\n    print('world')"

        result = pp.process(text)

        # Code mode is passthrough
        self.assertEqual(result, text)

    def test_process_persona_mode_returns_text(self) -> None:
        """Test that persona mode returns text unchanged."""
        pp = PostProcessor(
            mode=PostProcessMode.PERSONA,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "This is a test message"

        result = pp.process(text)

        # Persona mode is passthrough
        self.assertEqual(result, text)


class FindQwenModelTests(unittest.TestCase):
    """Tests for _find_qwen_model method."""

    def test_find_qwen_model_not_found(self) -> None:
        """Test _find_qwen_model when no model files exist."""
        pp = PostProcessor(
            mode=PostProcessMode.AGGRESSIVE,
            trigger=PostProcessTrigger.ALWAYS,
        )

        result = pp._find_qwen_model()

        # Should return None when no model is found
        self.assertIsNone(result)

    def test_find_qwen_model_in_home(self) -> None:
        """Test _find_qwen_model finds model in home directory."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .local/share/models/ structure
            models_dir = Path(tmpdir) / ".local" / "share" / "models"
            models_dir.mkdir(parents=True)
            model_file = models_dir / "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
            model_file.touch()

            pp = PostProcessor(
                mode=PostProcessMode.AGGRESSIVE,
                trigger=PostProcessTrigger.ALWAYS,
            )

            # Mock Path.home() to return our temp directory
            with patch('whisper_hotkey.postprocessor.Path.home', return_value=Path(tmpdir)):
                result = pp._find_qwen_model()

            # Should find the model file
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf")

    def test_find_qwen_model_in_cache(self) -> None:
        """Test _find_qwen_model finds model in huggingface cache."""
        # Create a temporary directory structure simulating huggingface cache
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / ".cache" / "huggingface" / "hub"
            cache_dir.mkdir(parents=True)
            model_dir = cache_dir / "models--test--qwen"
            model_dir.mkdir()
            model_file = model_dir / "Qwen2.5-0.5B-Q4_K_M.gguf"
            model_file.touch()

            pp = PostProcessor(
                mode=PostProcessMode.AGGRESSIVE,
                trigger=PostProcessTrigger.ALWAYS,
            )

            # Mock Path.home() to return our temp directory
            with patch('whisper_hotkey.postprocessor.Path.home', return_value=Path(tmpdir)):
                result = pp._find_qwen_model()

            # Should find the model file in cache
            self.assertIsNotNone(result)
            self.assertTrue("Qwen2.5" in result.name)
            self.assertTrue("0.5B" in result.name)


class InstallDeepmultilingualpunctuationTests(unittest.TestCase):
    """Tests for install_deepmultilingualpunctuation function."""

    @patch('whisper_hotkey.postprocessor.subprocess.run')
    def test_install_deepmultilingualpunctuation_success(self, mock_run) -> None:
        """Test successful installation of deepmultilingualpunctuation."""
        mock_run.return_value = None  # subprocess.run doesn't return anything on success

        result = install_deepmultilingualpunctuation()

        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pip", "install", "deepmultilingualpunctuation", "-q"],
            check=True,
            capture_output=True,
        )

    @patch('whisper_hotkey.postprocessor.subprocess.run')
    def test_install_deepmultilingualpunctuation_failure(self, mock_run) -> None:
        """Test failed installation of deepmultilingualpunctuation."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "pip", stderr="Installation failed"
        )

        result = install_deepmultilingualpunctuation()

        self.assertFalse(result)
        mock_run.assert_called_once()


class InstallLlamaCppTests(unittest.TestCase):
    """Tests for install_llama_cpp function."""

    @patch('whisper_hotkey.postprocessor.subprocess.run')
    def test_install_llama_cpp_success(self, mock_run) -> None:
        """Test successful installation of llama-cpp-python."""
        mock_run.return_value = None

        result = install_llama_cpp()

        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pip", "install", "llama-cpp-python", "-q"],
            check=True,
            capture_output=True,
        )

    @patch('whisper_hotkey.postprocessor.subprocess.run')
    def test_install_llama_cpp_failure(self, mock_run) -> None:
        """Test failed installation of llama-cpp-python."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "pip", stderr="Installation failed"
        )

        result = install_llama_cpp()

        self.assertFalse(result)
        mock_run.assert_called_once()


class InstallAnthropicTests(unittest.TestCase):
    """Tests for install_anthropic function."""

    @patch('whisper_hotkey.postprocessor.subprocess.run')
    def test_install_anthropic_success(self, mock_run) -> None:
        """Test successful installation of anthropic."""
        mock_run.return_value = None

        result = install_anthropic()

        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pip", "install", "anthropic", "-q"],
            check=True,
            capture_output=True,
        )

    @patch('whisper_hotkey.postprocessor.subprocess.run')
    def test_install_anthropic_failure(self, mock_run) -> None:
        """Test failed installation of anthropic."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "pip", stderr="Installation failed"
        )

        result = install_anthropic()

        self.assertFalse(result)
        mock_run.assert_called_once()


class PostProcessorEdgeCaseTests(unittest.TestCase):
    """Tests for edge cases in PostProcessor."""

    def test_process_whitespace_only(self) -> None:
        """Test processing whitespace-only text."""
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.ALWAYS,
        )

        test_cases = [
            "",
            "   ",
            "\t",
            "\n",
            "  \t\n  ",
        ]

        for text in test_cases:
            with self.subTest(text=repr(text)):
                result = pp.process(text)
                # Whitespace-only text should be returned as-is
                self.assertEqual(result, text)

    def test_process_mixed_whitespace_and_content(self) -> None:
        """Test processing text with mixed whitespace."""
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.ALWAYS,
        )

        test_cases = [
            "  hello  ",
            "\nworld\n",
            "  \ttest\t  ",
        ]

        for text in test_cases:
            with self.subTest(text=repr(text)):
                result = pp.process(text)
                # Text with content should be processed
                # (in this case, returns unchanged due to missing dependency)
                self.assertEqual(result, text)


class PostProcessorTriggerTests(unittest.TestCase):
    """Additional tests for trigger behavior."""

    def test_should_process_with_whitespace_text(self) -> None:
        """Test should_process with various whitespace inputs."""
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.ALWAYS,
        )

        # All these should return False for whitespace
        self.assertFalse(pp.should_process(""))
        self.assertFalse(pp.should_process("   "))
        self.assertFalse(pp.should_process("\n\t"))

        # Non-whitespace should return True
        self.assertTrue(pp.should_process("test"))
        self.assertTrue(pp.should_process("  test  "))

    def test_should_process_off_mode(self) -> None:
        """Test should_process when mode is OFF."""
        pp = PostProcessor(
            mode=PostProcessMode.OFF,
            trigger=PostProcessTrigger.ALWAYS,
        )

        # OFF mode should always return False
        self.assertFalse(pp.should_process(""))
        self.assertFalse(pp.should_process("test"))
        self.assertFalse(pp.should_process("long text with many words"))


if __name__ == "__main__":
    unittest.main()
