# Installation

## Docker Install (Recommended)

The Docker install path is the primary supported distribution method.

### Prerequisites

- Docker and Docker Compose installed
- Linux host with X11
- PipeWire or PulseAudio for audio
- `xdotool` for typing

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/easy-local-whisper-hotkey.git
cd easy-local-whisper-hotkey
```

### 2. Build and Start the Inference Server

```bash
docker compose up -d
```

This command:
- Builds the inference server container from `packaging/docker/Dockerfile.inference`
- Pre-downloads the `base.en` faster-whisper model during the build
- Starts the container listening on Unix socket at `$XDG_RUNTIME_DIR/whisper/whisper.sock`
- Runs the container with strong security sandboxing: no network, read-only filesystem, no capabilities, non-root user

The socket is shared via the volume mount `${XDG_RUNTIME_DIR}/whisper:/run/whisper`.

### 3. Install the Host CLI

```bash
pipx install .
```

Or as a fallback:

```bash
pip install --user .
```

The console entry point is `easy-local-whisper-hotkey`.

### 4. Verify the Installation

```bash
easy-local-whisper-hotkey doctor
```

This checks:
- `xdotool` is available
- `DISPLAY` is set
- Audio sources are visible via PipeWire or PulseAudio
- Docker inference server is reachable via the Unix socket

### 5. Optional: Install Systemd User Service

Create the user service directory and copy the service file:

```bash
mkdir -p ~/.config/systemd/user
cp packaging/systemd/whisper-hotkey.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now whisper-hotkey.service
```

This starts the application automatically on login.

### Optional Docker Configuration

Create a `.env` file in the repository root to customize the inference server:

```bash
WHISPER_MODEL=base.en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_LANGUAGE=en
```

These settings configure the faster-whisper model used by the inference server.

## Native Install (Advanced)

The native install path uses whisper.cpp's `whisper-cli` directly on the host. No Docker needed, but you must build whisper.cpp yourself.

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

```bash
pipx install .
```

Or as a fallback:

```bash
pip install --user .
```

### 4. Run Diagnostics

```bash
easy-local-whisper-hotkey doctor
```

This confirms:
- `whisper-cli` exists
- The model file exists
- `parec`, `pactl`, and `xdotool` are available
- `DISPLAY` is set
- At least one capture source is visible

### 5. Optional: Install Systemd User Service

```bash
mkdir -p ~/.config/systemd/user
cp packaging/systemd/whisper-hotkey.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now whisper-hotkey.service
```