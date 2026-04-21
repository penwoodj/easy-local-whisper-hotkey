# Config Persistence Audit Report

**Date:** 2026-04-19  
**Project:** easy-local-whisper-hotkey  
**Severity:** HIGH  
**Component:** Config Persistence (Rust ↔ TypeScript ↔ Python)

---

## Executive Summary

The config persistence system has a field count mismatch between Rust (20 fields), TypeScript (20 fields), and Python (19 fields). The `log_level` field exists in Rust and TypeScript but is **not defined** in the Python daemon's argument parser. However, the 5 previously missing fields (`voice_activation_mode`, `post_processing_enabled`, `post_processing_mode`, `post_processing_trigger`, `indicator_enabled`) have been **added to Rust** — the struct now has 20 fields matching TypeScript.

The remaining issue is that `forwarded_runtime_args()` in `cli.py` does NOT forward `--activation-mode`, `--postprocess`, `--postprocess-mode`, or `--postprocess-trigger` flags to the daemon subprocess. These settings can only reach the daemon via the env file (WHISPER_CONFIG_ENV_FILE).

---

## Field-by-Field Comparison

### Rust WhisperConfig (commands.rs:115-141) — 20 fields

| # | Field | Type | Env Var | Line |
|---|-------|------|---------|------|
| 1 | whisper_cli | String | WHISPER_CLI | L116 |
| 2 | model | String | WHISPER_MODEL | L117 |
| 3 | source | String | WHISPER_AUDIO_SOURCE | L118 |
| 4 | preferred_sources | String | WHISPER_PREFERRED_SOURCES | L119 |
| 5 | chunk_seconds | f64 | WHISPER_CHUNK_SECONDS | L120 |
| 6 | overlap_seconds | f64 | WHISPER_OVERLAP_SECONDS | L121 |
| 7 | type_delay_ms | i32 | WHISPER_TYPE_DELAY_MS | L122 |
| 8 | language | String | WHISPER_LANGUAGE | L123 |
| 9 | suppress_regex | String | WHISPER_SUPPRESS_REGEX | L124 |
| 10 | suppress_nst | bool | WHISPER_SUPPRESS_NST | L125 |
| 11 | smart_punctuation | bool | WHISPER_SMART_PUNCTUATION | L126 |
| 12 | symbol_words_to_symbols | bool | WHISPER_SYMBOL_WORDS_TO_SYMBOLS | L127 |
| 13 | direct_streaming | bool | WHISPER_DIRECT_STREAMING | L128 |
| 14 | log_file | String | WHISPER_LOG_FILE | L129 |
| 15 | log_level | LogLevel | WHISPER_LOG_LEVEL | L130 |
| 16 | voice_activation_mode | VoiceActivationMode | WHISPER_ACTIVATION_MODE | L132 |
| 17 | post_processing_enabled | bool | WHISPER_POST_PROCESSING_ENABLED | L134 |
| 18 | post_processing_mode | PostProcessingMode | WHISPER_POST_PROCESSING_MODE | L136 |
| 19 | post_processing_trigger | PostProcessingTrigger | WHISPER_POST_PROCESSING_TRIGGER | L138 |
| 20 | indicator_enabled | bool | WHISPER_INDICATOR | L140 |

### TypeScript WhisperConfig (whisper.ts:24-44) — 20 fields ✅ Match

All 20 fields present, types match Rust equivalents.

### Python Daemon (app.py parse_args:177-289) — 19 fields

| # | Field | CLI Arg | Line |
|---|-------|---------|------|
| 1 | whisper_cli | --whisper-cli | L182-185 |
| 2 | model | --model | L186 |
| 3 | source | --source | L187-191 |
| 4 | preferred_sources | --preferred-sources | L192-198 |
| 5 | chunk_seconds | --chunk-seconds | L200-204 |
| 6 | overlap_seconds | --overlap-seconds | L205-209 |
| 7 | type_delay_ms | --type-delay-ms | L210-214 |
| 8 | language | --language | L215-218 |
| 9 | suppress_regex | --suppress-regex | L219-223 |
| 10 | suppress_nst | --suppress-nst | L224-229 |
| 11 | smart_punctuation | --smart-punctuation | L230-235 |
| 12 | symbol_words_to_symbols | --symbol-words-to-symbols | L236-241 |
| 13 | direct_streaming | --direct-streaming | L242-247 |
| 14 | activation_mode | --activation-mode | L248-253 |
| 15 | indicator_enabled | --indicator | L254-259 |
| 16 | post_processing_enabled | --postprocess | L260-265 |
| 17 | post_processing_mode | --postprocess-mode | L266-271 |
| 18 | post_processing_trigger | --postprocess-trigger | L272-277 |
| 19 | log_file | --log-file | L278-281 |
| ❌ | **log_level** | **MISSING** | — |

### Discrepancy: log_level

- **Rust**: Has `log_level: LogLevel` field with `WHISPER_LOG_LEVEL` env var
- **TypeScript**: Has `log_level` in interface
- **Python**: ❌ No `--log-level` argument defined anywhere in the Python codebase

**Impact:** MEDIUM. The log level set in the Tauri UI is saved to the env file but never read by the Python daemon. The daemon uses its own default log level.

---

## CLI Flag Forwarding Gap

### `forwarded_runtime_args()` (cli.py:122-153)

This function builds CLI args for spawning the daemon. It forwards:

| Forwarded ✅ | Missing ❌ |
|-------------|-----------|
| --whisper-cli | --activation-mode |
| --model | --postprocess |
| --source | --postprocess-mode |
| --preferred-sources | --postprocess-trigger |
| --chunk-seconds | --log-level |
| --overlap-seconds | --indicator |
| --type-delay-ms | |
| --language | |
| --log-file | |
| --suppress-regex (conditional) | |
| --suppress-nst (conditional) | |
| --smart-punctuation (conditional) | |
| --symbol-words-to-symbols (conditional) | |
| --direct-streaming (conditional) | |

**However**, this is NOT a critical bug because the daemon reads config from the env file via `WHISPER_CONFIG_ENV_FILE`. The CLI forwarding path is only used when `easy-local-whisper-hotkey run` is invoked directly with flags. When launched from Tauri, the env file is the config source.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONFIG DATA FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TypeScript UI                                                   │
│  ┌──────────────────┐                                           │
│  │ WhisperConfig    │  20 fields                                │
│  │ (whisper.ts)     │                                           │
│  └────────┬─────────┘                                           │
│           │ invoke('save_config')                                │
│           ▼                                                      │
│  Rust Backend                                                    │
│  ┌──────────────────┐                                           │
│  │ WhisperConfig    │  20 fields                                │
│  │ (commands.rs)    │                                           │
│  └────────┬─────────┘                                           │
│           │ save_config_to_env_file()                            │
│           ▼                                                      │
│  .config/easy-local-whisper-hotkey/config.env                   │
│  ┌──────────────────┐                                           │
│  │ KEY=VALUE        │  20 env vars                              │
│  │ WHISPER_CLI=...  │                                           │
│  │ WHISPER_MODEL=...│                                           │
│  │ ...              │                                           │
│  └────────┬─────────┘                                           │
│           │ WHISPER_CONFIG_ENV_FILE=<path>                       │
│           ▼                                                      │
│  Python Daemon                                                   │
│  ┌──────────────────┐                                           │
│  │ parse_args()     │  19 fields (missing log_level)            │
│  │ (app.py)         │                                           │
│  └──────────────────┘                                           │
│                                                                  │
│  Result: log_level saved to env but ignored by daemon           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Verification Plan

### Test 1: Config Round-Trip (Rust ↔ Env File)

```bash
# Save config via Tauri, then read env file
cat ~/.config/easy-local-whisper-hotkey/config.env
# Verify all 20 KEY=VALUE pairs present
```

### Test 2: Python Reads All Env Vars

```bash
# Set all 20 env vars, run daemon with --help to verify arg parsing
easy-local-whisper-hotkey run --help
# Check that log_level is NOT a recognized flag (bug confirmed)
```

### Test 3: Forwarded Args Check

```bash
# Check which args are forwarded
grep -A 40 'def forwarded_runtime_args' src/whisper_hotkey/cli.py
# Verify --activation-mode, --postprocess* are missing
```

---

## Recommendations

### P1: Add log_level to Python (Medium Priority)

Add `--log-level` argument to `app.py parse_args()` and update the daemon to use it for configuring Python's logging module.

### P2: Add Missing Forwarded Args (Low Priority)

Update `forwarded_runtime_args()` in `cli.py` to forward:
- `--activation-mode`
- `--postprocess`
- `--postprocess-mode`
- `--postprocess-trigger`
- `--indicator`
- `--log-level`

This is low priority because the env file path handles config delivery in the Tauri flow.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| log_level config lost between UI and daemon | High | Low | Add --log-level to Python |
| forwarded_runtime_args incomplete | Medium | Low | Env file fallback exists |
| Serde silently drops unknown fields | None | None | All 20 fields now in Rust |

**Overall Risk:** LOW. The 5 previously missing Rust fields have been added. Only log_level gap remains between Rust/TS and Python.

---

**Report prepared by:** Automated Code Audit System  
**Review methodology:** Static code analysis, field count comparison, data flow tracing
