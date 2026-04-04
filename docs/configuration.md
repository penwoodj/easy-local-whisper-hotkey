# Configuration

`whisper-hotkey` reads configuration from CLI flags first, then environment variables, then built-in defaults.

## Core Paths

- `--whisper-cli` / `WHISPER_CLI`
- `--model` / `WHISPER_MODEL`
- `--log-file` / `WHISPER_LOG_FILE`

Defaults:

- whisper CLI: `whisper-cli` on `PATH`, then the legacy local build path
- model: `~/.local/share/whisper-hotkey/models/ggml-base.en.bin`
- log: `/tmp/whisper_hotkey.log`

## Audio Selection

### Exact Override

Use this when you know the exact source name:

- `--source`
- `WHISPER_AUDIO_SOURCE`

### Priority List

Use this for stable fallback order:

- `--preferred-sources`
- `WHISPER_PREFERRED_SOURCES`

Format:

```text
source_one,source_two,source_three
```

If neither is set, the default priority is:

1. Razer Seiren Mini
2. Anker PowerConf C200
3. current desktop default source
4. first capture-capable source

## Streaming Behavior

- `--chunk-seconds` / `WHISPER_CHUNK_SECONDS`
- `--overlap-seconds` / `WHISPER_OVERLAP_SECONDS`
- `--type-delay-ms` / `WHISPER_TYPE_DELAY_MS`
- `--language` / `WHISPER_LANGUAGE`

Recommended defaults:

- chunk: `1.8`
- overlap: `0.4`
- type delay: `1`
- language: `en`

## Service Environment File

For the bundled user service, place overrides in:

```text
~/.config/whisper-hotkey/whisper-hotkey.env
```

The service will load that file automatically if it exists.
