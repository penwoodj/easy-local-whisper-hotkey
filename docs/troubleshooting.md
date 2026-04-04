# Troubleshooting

## `doctor` Fails Because `DISPLAY` Is Missing

The packaged daemon targets X11. Run it inside an X11 desktop session, or make sure the service has `DISPLAY` and `XAUTHORITY` set correctly.

## `doctor` Fails Because the Model Is Missing

Either:

- place the model at `~/.local/share/whisper-hotkey/models/ggml-base.en.bin`
- or set `WHISPER_MODEL`

## `list-sources` Shows No Microphones

Check:

- the device is connected
- PipeWire or PulseAudio is running
- `pactl list sources short` works outside the app

## The Hotkey Grabs But Nothing Types

Check:

- `xdotool` is installed
- the session is X11, not Wayland
- the target window accepts normal keyboard input
- the log file at `/tmp/whisper_hotkey.log`

## The Wrong Microphone Is Selected

Use:

```bash
whisper-hotkey list-sources
whisper-hotkey print-config
```

Then set either:

- `WHISPER_AUDIO_SOURCE` for an exact match
- or `WHISPER_PREFERRED_SOURCES` for a fallback list

## Hold Sessions Stop Too Early

The current design buffers recognized chunks until release and types afterward to avoid interfering with the pressed-state check. If this regresses, collect:

- `/tmp/whisper_hotkey.log`
- `whisper-hotkey doctor --json`
- `whisper-hotkey print-config --json`

## Service Starts But Fails At Login

Inspect:

```bash
systemctl --user status whisper-hotkey.service --no-pager
journalctl --user -u whisper-hotkey.service -n 100 --no-pager
```
