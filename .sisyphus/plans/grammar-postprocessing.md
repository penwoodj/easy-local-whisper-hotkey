# Plan: Grammar & Readability Post-Processing

## Goal

On toggle-off, collect everything typed during the session, send to a tiny local model for grammar correction + punctuation restoration, and replace the typed text with the cleaned version.

## Architecture

### Flow
```
Toggle Off
  → Collect session_typed_text (accumulated during session)
  → Send to local grammar model
  → Select all typed text (Ctrl+Shift+Left selects back)
  → Delete selection
  → Type corrected text via xdotool
```

### Model Options (ranked by fit)

#### Option A: FullStop Punctuation Model (RECOMMENDED)
- **What**: `oliverguhr/fullstop-punctuation-multilang-large` — token classifier, not LLM
- **Size**: ~500MB RAM
- **Speed**: <1s for 200 words
- **Install**: `pip install deepmultilingualpunctuation` into existing .venv
- **Quality**: Good punctuation (. , ? - :). No grammar restructuring.
- **Pros**: Purpose-built, tiny, instant
- **Cons**: Only punctuation, no filler removal, no grammar fixes

#### Option B: Qwen2.5-0.5B-Instruct (Q4 GGUF via llama-cpp-python)
- **What**: 0.5B param instruction-following LLM, Q4 quantized
- **Size**: ~600MB RAM
- **Speed**: ~2-3s for 200 words on Ryzen 5 2600
- **Install**: `pip install llama-cpp-python` + download GGUF (~400MB)
- **Quality**: Grammar fix + punctuation + filler removal + rewording
- **Pros**: Full grammar correction, understands context
- **Cons**: Slower, may over-edit, needs prompt engineering

#### Option C: FullStop + Qwen2.5-0.5B Hybrid
- **What**: FullStop for fast punctuation, Qwen for grammar only when text >100 words
- **Size**: ~1.1GB RAM combined
- **Speed**: <1s (short) or ~3s (long sessions)
- **Install**: Both dependencies
- **Pros**: Best quality, adaptive speed
- **Cons**: More complex, more RAM

#### Option D: Ollama + TinyLlama
- **What**: Ollama daemon running tinyllama:1.1b
- **Size**: ~700MB + daemon overhead
- **Speed**: ~2-3s for 200 words
- **Install**: Install ollama, pull tinyllama
- **Pros**: Simple API, easy model switching
- **Cons**: Ollama not installed, daemon dependency, slower cold start

## Recommended: Option C (Hybrid)

### Implementation Steps

#### Step 1: Add session text tracking
- In `X11HotkeyDaemon`, add `self._session_typed_text = ""`
- In `_type_text`, append to `_session_typed_text`
- Reset on toggle-on

#### Step 2: Install dependencies
```bash
cd /home/jon/code/easy-local-whisper-hotkey
.venv/bin/pip install deepmultilingualpunctuation llama-cpp-python
```

#### Step 3: Create `src/whisper_hotkey/postprocess.py`
- `PunctuationRestorer` class wrapping FullStop model
- `GrammarCorrector` class wrapping llama-cpp-python + Qwen2.5-0.5B
- Both lazy-loaded (only instantiate on first use)
- `format_session_text(raw: str) -> str` combining both

#### Step 4: FullStop integration
```python
from deepmultilingualpunctuation import PunctuationModel

class PunctuationRestorer:
    def __init__(self):
        self._model = None

    def restore(self, text: str) -> str:
        if not self._model:
            self._model = PunctuationModel()
        return self._model.restore_punctuation(text)
```

#### Step 5: Qwen2.5-0.5B integration
```python
from llama_cpp import Llama

class GrammarCorrector:
    PROMPT = """Fix grammar, remove filler words (um, uh, you know, I mean, like), 
    and improve readability. Keep the original meaning. Output only the corrected text.
    
    Raw text: {text}
    
    Corrected:"""

    def __init__(self):
        self._model = None

    def correct(self, text: str) -> str:
        if not self._model:
            self._model = Llama(
                model_path="~/.config/com.pais.handy/models/qwen2.5-0.5b-instruct-q4_k_m.gguf",
                n_ctx=2048, n_threads=8, n_gpu_layers=0,
            )
        prompt = self.PROMPT.format(text=text)
        result = self._model(prompt, max_tokens=len(text.split()) * 2, temperature=0.0)
        return result["choices"][0]["text"].strip()
```

#### Step 6: Text replacement on toggle-off
- After toggle-off + trailing buffer + final segment:
  1. Wait for transcriber to finish (`transcriber.join()`)
  2. Get `session_typed_text` 
  3. If text >20 words, run through post-processing
  4. Use xdotool to select and replace:
     - Count characters of raw text
     - `xdotool key --clearmodifiers Shift+Home` (select to start of session)
     - Actually: use `xdotool type --clearmodifiers` to backspace and retype
     
**Replacement challenge**: xdotool can't select arbitrary ranges. Options:
  - A) Use clipboard: copy corrected text, select-all-typed, paste
  - B) Use xdotool BackSpace count + type corrected
  - C) Use xdotool key Ctrl+Shift+Home (select to beginning) then type

**Best approach**: 
1. Count characters of raw typed text
2. Send N BackSpace keystrokes to delete it
3. Type corrected text

This is fragile (wrong if user edited mid-session). Alternative:
1. Copy corrected text to clipboard (xclip)
2. User manually selects + pastes
3. Or: just log corrected text for user to copy manually

#### Step 7: Configuration
- `WHISPER_POSTPROCESS=true` env var
- `--postprocess` CLI flag
- `WHISPER_POSTPROCESS_MODEL=fullstop|qwen|hybrid` env var

### Atomic Commits
1. Add `postprocess.py` with FullStop only
2. Add session text tracking to daemon
3. Add postprocess on toggle-off (clipboard approach)
4. Add Qwen2.5-0.5B grammar corrector
5. Add hybrid mode + config flags

### Risks & Mitigations
- **xclip not installed**: Check availability, fallback to logging
- **Model download fails**: Graceful degradation, log warning
- **Grammar model too slow**: Add word count threshold (skip if <20 words)
- **Over-editing**: Temperature 0.0 + strict prompt to minimize hallucination
- **Text replacement breaks mid-edit**: Default to clipboard copy, not auto-replace

### Verification
- Unit test: `PunctuationRestorer.restore("hello world how are you")` → contains comma/period
- Unit test: `GrammarCorrector.correct("um uh I think that like you know")` → no filler
- Integration: toggle session, speak 50+ words, toggle off, check clipboard
- Performance: 200 words in <3s total

### Dependencies to Install
```bash
cd /home/jon/code/easy-local-whisper-hotkey
.venv/bin/pip install deepmultilingualpunctuation
# For Qwen2.5 (optional):
CMAKE_ARGS="-DLLAMA_CUBLAS=off" .venv/bin/pip install llama-cpp-python
# Download GGUF model:
wget -O ~/.config/com.pais.handy/models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
```

### System Check Needed
- xclip installed? `which xclip`
- xdotool version supports --delay? `xdotool --version`
