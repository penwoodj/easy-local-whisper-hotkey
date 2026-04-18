"""
Post-processing module for grammar and text enhancement.

Supports multiple modes:
- off: No post-processing
- light: deepmultilingualpunctuation (fast, punctuation only)
- aggressive: llama-cpp-python + Qwen2.5-0.5B (full grammar)
- agentic: Anthropic Claude API
- writing: Writing style improvements
- code: Code-specific corrections
- structure: Document structure improvements
- persona: Persona-based text adaptation
- clarity: Clarity and readability improvements
"""

import logging
import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


class PostProcessMode(str, Enum):
    OFF = "off"
    LIGHT = "light"
    AGGRESSIVE = "aggressive"
    AGENTIC = "agentic"
    WRITING = "writing"
    CODE = "code"
    STRUCTURE = "structure"
    PERSONA = "persona"
    CLARITY = "clarity"


class PostProcessTrigger(str, Enum):
    ALWAYS = "always"
    MANUAL = "manual"
    AUTO_LONG = "auto-long"
    PREVIEW = "preview"


class PostProcessor:
    """
    Handles text post-processing using various modes.

    Modes:
    - off: No processing
    - light: deepmultilingualpunctuation for punctuation restoration
    - aggressive: Qwen2.5-0.5B for full grammar correction
    - agentic: Anthropic Claude API for AI-powered enhancement
    - writing: Writing style improvements
    - code: Code-specific corrections
    - structure: Document structure improvements
    - persona: Persona-based text adaptation
    - clarity: Clarity and readability improvements
    """

    def __init__(
        self,
        mode: PostProcessMode = PostProcessMode.OFF,
        trigger: PostProcessTrigger = PostProcessTrigger.MANUAL,
    ):
        self.mode = mode
        self.trigger = trigger
        self._deepmultilingualpunctuation_model = None
        self._llama_model = None
        self._anthropic_client = None

    def should_process(self, text: str) -> bool:
        """Determine if post-processing should run based on trigger and text."""
        if self.mode == PostProcessMode.OFF:
            return False

        if self.trigger == PostProcessTrigger.ALWAYS:
            return bool(text.strip())

        if self.trigger == PostProcessTrigger.MANUAL:
            return False

        if self.trigger == PostProcessTrigger.AUTO_LONG:
            word_count = len(text.split())
            return word_count >= 50 and bool(text.strip())

        if self.trigger == PostProcessTrigger.PREVIEW:
            return False

        return False

    def process(self, text: str) -> str:
        """
        Process text according to the configured mode.

        Args:
            text: Input text to process

        Returns:
            Processed text (or original if processing fails)
        """
        if not text.strip():
            return text

        try:
            if self.mode == PostProcessMode.LIGHT:
                return self._process_light(text)
            elif self.mode == PostProcessMode.AGGRESSIVE:
                return self._process_aggressive(text)
            elif self.mode == PostProcessMode.AGENTIC:
                return self._process_agentic(text)
            elif self.mode == PostProcessMode.WRITING:
                return self._process_writing(text)
            elif self.mode == PostProcessMode.CODE:
                return self._process_code(text)
            elif self.mode == PostProcessMode.STRUCTURE:
                return self._process_structure(text)
            elif self.mode == PostProcessMode.PERSONA:
                return self._process_persona(text)
            elif self.mode == PostProcessMode.CLARITY:
                return self._process_clarity(text)
            else:
                return text
        except Exception as e:
            logger.error(f"Post-processing failed: {e}")
            return text

    def _process_light(self, text: str) -> str:
        """
        Light mode: deepmultilingualpunctuation for punctuation restoration.

        Fast, punctuation-only processing. Ideal for real-time use.
        """
        try:
            from deepmultilingualpunctuation import PunctuationModel

            if self._deepmultilingualpunctuation_model is None:
                logger.debug("Loading deepmultilingualpunctuation model...")
                self._deepmultilingualpunctuation_model = PunctuationModel()

            result = self._deepmultilingualpunctuation_model.restore_punctuation(text)
            return result
        except ImportError:
            logger.warning("deepmultilingualpunctuation not installed. Install with: pip install deepmultilingualpunctuation")
            return text

    def _process_aggressive(self, text: str) -> str:
        """
        Aggressive mode: llama-cpp-python + Qwen2.5-0.5B for full grammar.

        Slower but comprehensive grammar correction.
        """
        try:
            from llama_cpp import Llama

            if self._llama_model is None:
                model_path = self._find_qwen_model()
                if not model_path:
                    logger.warning("Qwen2.5-0.5B model not found. Install with: ./install-qwen-model.sh")
                    return text

                logger.debug(f"Loading Qwen2.5-0.5B model from {model_path}...")
                self._llama_model = Llama(
                    model_path=str(model_path),
                    n_ctx=2048,
                    n_gpu_layers=-1,
                    verbose=False,
                )

            prompt = f"Fix the grammar and punctuation of the following text. Return only the corrected text, no explanations:\n\n{text}\n\nCorrected text:"

            response = self._llama_model(
                prompt,
                max_tokens=1024,
                stop=["\n\n", "Corrected text:"],
                temperature=0.1,
            )

            return response["choices"][0]["text"].strip()
        except ImportError:
            logger.warning("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
            return text

    def _process_agentic(self, text: str) -> str:
        """
        Agentic mode: Anthropic Claude API for AI-powered enhancement.

        Requires ANTHROPIC_API_KEY environment variable.
        """
        try:
            import anthropic

            if self._anthropic_client is None:
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    logger.warning("ANTHROPIC_API_KEY not set. Skipping agentic mode.")
                    return text

                self._anthropic_client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""Improve the following text for clarity, grammar, and style. Keep the original meaning but make it more polished:

{text}

Return only the improved text, no explanations."""

            response = self._anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text.strip()
        except ImportError:
            logger.warning("anthropic not installed. Install with: pip install anthropic")
            return text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return text

    def _process_writing(self, text: str) -> str:
        """Writing mode: Improve writing style, flow, and coherence."""
        # For now, fallback to aggressive mode
        return self._process_aggressive(text)

    def _process_code(self, text: str) -> str:
        """Code mode: Code-specific corrections and formatting."""
        # For now, return text unchanged (code mode needs special handling)
        return text

    def _process_structure(self, text: str) -> str:
        """Structure mode: Improve document structure and organization."""
        # For now, fallback to aggressive mode
        return self._process_aggressive(text)

    def _process_persona(self, text: str) -> str:
        """Persona mode: Adapt text to a specific persona (e.g., formal, casual)."""
        # For now, return text unchanged (persona mode needs configuration)
        return text

    def _process_clarity(self, text: str) -> str:
        """Clarity mode: Improve clarity and readability."""
        # For now, use light mode for punctuation-based clarity
        return self._process_light(text)

    def _find_qwen_model(self) -> Path | None:
        """
        Find Qwen2.5-0.5B GGUF model in standard locations.

        Returns:
            Path to model file if found, None otherwise
        """
        # Standard model locations
        search_paths = [
            Path.home() / ".local/share/models/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf",
            Path.home() / ".config/com.pais.handy/models/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf",
            Path.cwd() / "models/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf",
        ]

        for path in search_paths:
            if path.exists():
                return path

        # Search in ~/.cache/huggingface/hub/
        cache_dir = Path.home() / ".cache/huggingface/hub"
        if cache_dir.exists():
            for gguf_file in cache_dir.rglob("Qwen2.5*.gguf"):
                if "0.5B" in gguf_file.name:
                    return gguf_file

        return None


def install_deepmultilingualpunctuation() -> bool:
    """
    Install deepmultilingualpunctuation package.

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        subprocess.run(
            ["pip", "install", "deepmultilingualpunctuation", "-q"],
            check=True,
            capture_output=True,
        )
        logger.info("deepmultilingualpunctuation installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install deepmultilingualpunctuation: {e}")
        return False


def install_llama_cpp() -> bool:
    """
    Install llama-cpp-python package.

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        subprocess.run(
            ["pip", "install", "llama-cpp-python", "-q"],
            check=True,
            capture_output=True,
        )
        logger.info("llama-cpp-python installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install llama-cpp-python: {e}")
        return False


def install_anthropic() -> bool:
    """
    Install anthropic package.

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        subprocess.run(
            ["pip", "install", "anthropic", "-q"],
            check=True,
            capture_output=True,
        )
        logger.info("anthropic installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install anthropic: {e}")
        return False
