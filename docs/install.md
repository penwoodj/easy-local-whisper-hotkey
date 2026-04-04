# Installation

## Native Install

The native install path is the primary supported distribution method.

### 1. Install Runtime Dependencies

You need these host tools:

- `parec`
- `pactl`
- `xdotool`
- `whisper-cli` from `whisper.cpp`

On Debian and Ubuntu systems, a typical starting point is:

```bash
sudo apt-get update
sudo apt-get install -y pulseaudio-utils xdotool
```

`whisper-cli` must either be on `PATH` or provided with `WHISPER_CLI=/path/to/whisper-cli`.

### 2. Install a Model

Place a GGML model at the default location:

```text
~/.local/share/whisper-hotkey/models/ggml-base.en.bin
```

Or point `WHISPER_MODEL` at a different model path.

### 3. Install the Package

Preferred:

```bash
pipx install whisper-hotkey-<version>-py3-none-any.whl
```

Fallback:

```bash
python3 -m pip install --user whisper-hotkey-<version>-py3-none-any.whl
```

### 4. Run Diagnostics

```bash
whisper-hotkey doctor
```

This should confirm:

- `whisper-cli` exists
- the model file exists
- `parec`, `pactl`, and `xdotool` are available
- `DISPLAY` is set
- at least one capture source is visible

### 5. Install the User Service

Copy the service file:

```bash
mkdir -p ~/.config/systemd/user
cp packaging/systemd/whisper-hotkey.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now whisper-hotkey.service
```

### 6. Optional Environment File

Create:

```text
~/.config/whisper-hotkey/whisper-hotkey.env
```

Example:

```bash
WHISPER_MODEL=/home/you/.local/share/whisper-hotkey/models/ggml-base.en.bin
WHISPER_PREFERRED_SOURCES=alsa_input.usb-Razer_Inc_Razer_Seiren_Mini,alsa_input.usb-Anker_PowerConf
WHISPER_LANGUAGE=en
```

## Docker Install

The Docker image is for advanced users. Full desktop behavior still depends on host X11 and audio access.

Typical considerations:

- mount the X11 socket
- pass `DISPLAY`
- mount `XAUTHORITY`
- expose host audio devices or PulseAudio/PipeWire socket
- provide the model file

Example shape:

```bash
docker run --rm \
  -e DISPLAY \
  -e XAUTHORITY=/tmp/.Xauthority \
  -v "$XAUTHORITY:/tmp/.Xauthority:ro" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
  -v "$HOME/.local/share/whisper-hotkey/models:/models:ro" \
  whisper-hotkey:latest \
  doctor --model /models/ggml-base.en.bin
```

For most users, native install is the right answer.
