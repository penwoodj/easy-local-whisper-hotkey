# Post-Processor LLM Text Rewriting — Future Feature

## Summary

The postprocessor module provides AI-powered text rewriting of whisper transcription output. It was removed from the initial UI release to focus on core speech-to-text functionality. This feature will be re-added as a configurable option in a future release.

## Current Implementation

**Location**: `src/whisper_hotkey/postprocessor.py` (331 lines)

The postprocessor supports multiple modes for improving whisper output:

### Processing Modes

- **`off`** — No text processing
- **`light`** — Punctuation restoration via deepmultilingualpunctuation (fast, no LLM required)
- **`aggressive`** — Grammar correction via llama-cpp-python with Qwen2.5-0.5B (local, ~0.5B parameter model)
- **`agentic`** — Full rewrite via Anthropic Claude API (claude-3-haiku-20240307, requires ANTHROPIC_API_KEY)
- **`writing/code/structure/persona/clarity`** — Specialized modes that fall back to light or aggressive

### Processing Triggers

When to apply post-processing:

- **`always`** — Process every transcription
- **`manual`** — Only when explicitly triggered by user
- **`auto_long`** — Only when word count >= 50
- **`preview`** — For UI preview (not yet implemented)

## Dependencies

### External Libraries

- **`llama-cpp-python`** — Local LLM inference for aggressive mode
- **`anthropic`** — Python SDK for Claude API (agentic mode)
- **`deepmultilingualpunctuation`** — Punctuation restoration (light mode)

### Model Configuration (Local LLM)

For the `aggressive` mode, the system searches for Qwen2.5-0.5B models in these locations:

1. `~/.local/share/models/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf`
2. `~/.config/com.pais.handy/models/`
3. `~/.cache/huggingface/hub/`

**Model parameters**:
- Context size: 2048 tokens
- Max tokens: 1024
- Stop sequences: `"\n\n"`, `"Corrected text:"`
- Temperature: 0.1 (low temperature for deterministic output)

**Prompt template**:
```
Fix the grammar and punctuation of the following text. Return only the corrected text, no explanations:

{text}

Corrected text:
```

## Configuration Variables

The following environment variables control post-processing behavior:

- **`WHISPER_POST_PROCESSING_ENABLED`** (bool) — Enable/disable post-processing
- **`WHISPER_POST_PROCESSING_MODE`** (string) — Mode: `off/light/aggressive/agentic/writing/code/structure/persona/clarity`
- **`WHISPER_POST_PROCESSING_TRIGGER`** (string) — When to process: `always/manual/auto_long/preview`

## Re-integration Plan

When this feature is re-added to the UI:

1. **UI Toggle** — Add a checkbox in Configuration Panel under a new "Post-Processing" section
2. **Mode Selector** — Dropdown with descriptions for each mode (performance vs quality tradeoffs)
3. **Trigger Configuration** — Radio buttons or select for trigger mode
4. **Model Path** — File picker for local LLM model (aggressive mode)
5. **API Key Field** — Secure input field for ANTHROPIC_API_KEY (agentic mode, should be stored securely)
6. **Preview Pane** — Split view showing original transcription vs corrected output (preview trigger mode)
7. **Feedback Indicator** — Visual cue when post-processing is running (spinner or progress bar)

## Notes

- The `light` mode is fast and requires no external dependencies (uses deepmultilingualpunctuation only)
- The `aggressive` mode runs locally with llama-cpp-python but requires a ~0.5B model file
- The `agentic` mode provides highest quality but requires network connectivity and API key
- For production use, consider offering a "light" mode by default with option to enable heavier modes
- Processing latency can be significant for local LLM mode (hundreds of ms to seconds depending on hardware)

## See Also

- Original implementation: `src/whisper_hotkey/postprocessor.py`
- Configuration schema: See `CONFIG_SCHEMA` in `src/whisper_hotkey/config_store.py`
