# Setup Guide - Easy Local Whisper Hotkey

## Overview

This guide covers the new features added:
- Multi-platform auto-startup configuration (Linux, Windows, Mac)
- Comprehensive logging with debug/info levels
- Rotating log files (1000 lines each)
- QA documentation for testing

## Auto-Startup Configuration

### How It Works

The app now supports auto-startup on login across all three major platforms:
- **Linux**: Uses systemd user services
- **Windows**: Uses registry keys
- **macOS**: Uses Launch Agents

### Enabling/Disabling Autostart

#### From the Desktop App (Recommended)

The configuration panel includes autostart controls. Simply toggle the "Enable Autostart" setting.

#### From Config File

Edit `~/.config/whisper-hotkey/whisper-hotkey.env`:
```
# Not applicable - use the desktop app settings
```

#### System-Level Verification

**Linux**:
```bash
systemctl --user status whisper-hotkey
```

**Windows**:
```powershell
Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" | Select-Object -ExpandProperty PSChildPath
```

**macOS**:
```bash
launchctl list | grep whisper
```

## Logging Configuration

### Log Location

Logs are automatically stored in:
- **Linux/macOS**: `~/.local/share/whisper-hotkey/logs/`
- **Windows**: `%APPDATA%\whisper-hotkey\logs\`

### Setting Log Level

#### Method 1: Config File (Recommended)

Edit `~/.config/whisper-hotkey/whisper-hotkey.env`:
```
WHISPER_LOG_LEVEL=info    # Normal operation logs
WHISPER_LOG_LEVEL=debug   # Detailed debug information
```

#### Method 2: Environment Variable

Set before starting the app:
```bash
export WHISPER_LOG_LEVEL=debug
npm run tauri dev
```

### Log Levels

#### INFO (Default)
- Application startup/shutdown
- Daemon control events
- Configuration changes
- Major errors
- Basic transcription events

#### DEBUG (For Troubleshooting)
- All INFO level messages
- Internal operations
- Audio capture details
- Transcription timing
- Memory/resource usage
- Detailed error context

### Log Rotation

Logs automatically rotate at 1000 lines:
- Format: `whisper_YYYYMMDD_HHMMSS.log`
- Old logs are preserved
- No manual rotation needed

### Viewing Logs

#### Real-time Monitoring

**Linux/macOS**:
```bash
# Follow the most recent log
tail -f ~/.local/share/whisper-hotkey/logs/whisper_*.log | grep -v "^$"

# Or use journalctl if using systemd
journalctl -u whisper-hotkey -f
```

**Windows**:
```powershell
# Follow the most recent log
Get-ChildItem "$env:APPDATA\whisper-hotkey\logs" -Filter "whisper_*.log" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 |
  ForEach-Object { Get-Content $_.FullName -Wait -Tail 20 }
```

#### Searching Logs

**Find errors**:
```bash
grep "ERROR\|error" ~/.local/share/whisper-hotkey/logs/whisper_*.log
```

**Find transcription events**:
```bash
grep "transcription\|Transcribed" ~/.local/share/whisper-hotkey/logs/whisper_*.log
```

**Search for specific time period**:
```bash
grep "2025-04-15" ~/.local/share/whisper-hotkey/logs/whisper_*.log
```

## Starting the Application

### Development Mode

```bash
cd tauri-app
npm run tauri dev
```

This starts the dev server and launches the Tauri application.

### Production Build

```bash
cd tauri-app
npm run tauri build
```

This creates platform-specific installers in `src-tauri/target/release/bundle/`.

## QA Testing

See [QA.md](QA.md) for comprehensive testing procedures including:
- Basic functionality tests
- Transcription feature tests
- Advanced feature tests
- Auto-startup verification
- Logging verification
- Cross-platform testing
- Feedback protocols

## Troubleshooting

### Autostart Not Working

1. **Enable debug logging**:
   ```
   WHISPER_LOG_LEVEL=debug
   ```

2. **Check logs for autostart errors**:
   ```bash
   grep "autostart\|Autostart" ~/.local/share/whisper-hotkey/logs/whisper_*.log
   ```

3. **Verify system-level configuration**:
   ```bash
   # Linux
   systemctl --user list-units | grep whisper

   # macOS
   launchctl list | grep whisper

   # Windows
   Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
   ```

4. **Provide feedback to AI** (see QA.md for template)

### No Logs Being Created

1. **Check permissions on log directory**:
   ```bash
   ls -la ~/.local/share/whisper-hotkey/logs
   ```

2. **Verify logging is initialized** (check logs on startup):
   ```bash
   grep "Logging initialized" ~/.local/share/whisper-hotkey/logs/whisper_*.log
   ```

3. **Check log level is set correctly**:
   ```bash
   grep "WHISPER_LOG_LEVEL" ~/.config/whisper-hotkey/whisper-hotkey.env
   ```

### Logs Not Detailed Enough

1. **Switch to debug level**:
   ```
   WHISPER_LOG_LEVEL=debug
   ```

2. **Restart the app** to apply the new log level

3. **Verify debug is active**:
   ```bash
   grep "Logging initialized.*Level: debug" ~/.local/share/whisper-hotkey/logs/whisper_*.log
   ```

## Cross-Platform Notes

### Linux (Arch)

- Systemd autostart requires systemd user services
- PipeWire/PulseAudio for audio capture
- X11 for window typing (Wayland not yet supported)
- Logs: `~/.local/share/whisper-hotkey/logs/`

### Windows

- Registry-based autostart
- WASAPI for audio capture
- SendKeys API for typing
- Logs: `%APPDATA%\whisper-hotkey\logs\`

### macOS

- LaunchAgent for autostart
- CoreAudio for audio capture
- Accessibility API for typing
- Logs: `~/Library/Application Support/whisper-hotkey/logs/`

## Quick Start

1. **Install dependencies**:
   ```bash
   # Install whisper.cpp
   pip install whisper-cpp

   # Install Python CLI
   pip install -e .
   ```

2. **Configure audio source**:
   ```bash
   easy-local-whisper-hotkey list-sources
   # Update config with preferred source
   ```

3. **Download model**:
   ```bash
   # Download ggml-base.en.bin to ~/.local/share/whisper-hotkey/models/
   # Or set WHISPER_MODEL to your model path
   ```

4. **Start the app**:
   ```bash
   cd tauri-app
   npm run tauri dev
   ```

5. **Enable autostart** (optional):
   - Use the desktop app configuration panel
   - Toggle "Enable Autostart"

6. **Set log level** (optional):
   ```
   WHISPER_LOG_LEVEL=debug   # For troubleshooting
   WHISPER_LOG_LEVEL=info    # Default, normal operation
   ```

## Getting Help

For detailed testing instructions, see [QA.md](QA.md).

For troubleshooting, provide the following to the AI:
1. Error messages from logs
2. Relevant log excerpt (50-100 lines)
3. System information: `easy-local-whisper-hotkey doctor`
4. Steps to reproduce
5. Configuration settings

Use the feedback template in QA.md for structured bug reports.
