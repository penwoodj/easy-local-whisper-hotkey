# QA Guide for Easy Local Whisper Hotkey

## Overview

This guide provides comprehensive instructions for Quality Assurance testing of the Easy Local Whisper Hotkey desktop application. It covers testing procedures, feedback mechanisms, and logging configuration for AI-assisted debugging.

## Prerequisites

- Whisper.cpp installed with a model (e.g., ggml-base.en.bin)
- Python CLI installed and configured
- Desktop environment (Linux X11, macOS, or Windows)
- Admin access for autostart testing

## Testing Environment Setup

### 1. Initial Configuration

```bash
# Run diagnostics to check system health
easy-local-whisper-hotkey doctor

# Verify audio sources
easy-local-whisper-hotkey list-sources

# Test basic transcription
easy-local-whisper-hotkey test --seconds 3
```

### 2. Desktop App Launch

```bash
cd tauri-app
npm run tauri dev
```

This starts the development server and launches the Tauri application.

## Logging Configuration

### Log Location

Logs are stored in:
- **Linux/macOS**: `~/.local/share/whisper-hotkey/logs/`
- **Windows**: `%APPDATA%\whisper-hotkey\logs\`

### Log Levels

Set log level in config (`.config/whisper-hotkey/whisper-hotkey.env`):

```
WHISPER_LOG_LEVEL=info   # General operational logs (default)
WHISPER_LOG_LEVEL=debug  # Detailed debug information
```

### Log Rotation

Logs automatically rotate every 1000 lines. Format: `whisper_YYYYMMDD_HHMMSS.log`

### Viewing Logs

```bash
# Linux/macOS
tail -f ~/.local/share/whisper-hotkey/logs/whisper_*.log

# Windows
Get-Content "$env:APPDATA\whisper-hotkey\logs\whisper_*.log" -Wait -Tail 20
```

## Testing Procedures

### Phase 1: Basic Functionality

#### Test 1.1: Application Startup
- [ ] App launches without errors
- [ ] Configuration panel displays
- [ ] No error messages in logs on startup
- [ ] Status shows "Ready" or similar

#### Test 1.2: Configuration Loading
- [ ] Settings from env file load correctly
- [ ] Model path displays correctly
- [ ] Audio source shows in dropdown
- [ ] All config options persist across restarts

#### Test 1.3: Daemon Control
- [ ] Start daemon button works
- [ ] Status changes to "Running"
- [ ] Stop daemon button works
- [ ] Status returns to "Stopped"
- [ ] Daemon process starts/stops correctly

### Phase 2: Transcription Features

#### Test 2.1: Hotkey Trigger
- [ ] Ctrl+Space triggers recording
- [ ] Visual indicator appears
- [ ] Recording stops when key released
- [ ] Text types into active window

#### Test 2.2: Audio Source Selection
- [ ] Can select different audio sources
- [ ] Preferred sources work
- [ ] Default source fallback works
- [ ] Audio source persists across restarts

#### Test 2.3: Model Configuration
- [ ] Can change model path
- [ ] Model exists check passes
- [ ] Different models load correctly
- [ ] Model path persists across restarts

#### Test 2.4: Language Settings
- [ ] Language selection works
- [ ] Selected language applies to transcription
- [ ] Language setting persists

### Phase 3: Advanced Features

#### Test 3.1: Post-Processing
- [ ] Regex suppression works
- [ ] NST suppression toggle works
- [ ] Smart punctuation toggle works
- [ ] Symbol words to symbols toggle works

#### Test 3.2: Streaming
- [ ] Direct streaming toggle works
- [ ] Streaming mode functions correctly
- [ ] Non-streaming mode functions correctly

#### Test 3.3: Type Timing
- [ ] Type delay applies correctly
- [ ] Different delays work
- [ ] Delay setting persists

### Phase 4: Auto-Startup

#### Test 4.1: Enable Autostart
- [ ] Autostart enable button works
- [ ] System confirms autostart enabled
- [ ] App starts on login
- [ ] No errors during autostart

#### Test 4.2: Disable Autostart
- [ ] Autostart disable button works
- [ ] System confirms autostart disabled
- [ ] App doesn't start on login after disable

### Phase 5: Logging & Diagnostics

#### Test 5.1: Info Level Logs
- [ ] Info level logs are readable
- [ ] Logs contain startup sequence
- [ ] Logs contain daemon events
- [ ] Logs contain transcription events
- [ ] No excessive debug information

#### Test 5.2: Debug Level Logs
- [ ] Debug level logs show details
- [ ] Logs show internal operations
- [ ] Logs show configuration changes
- [ ] Logs show audio capture details
- [ ] Logs show transcription timing

#### Test 5.3: Log Rotation
- [ ] Log files rotate at 1000 lines
- [ ] Old logs preserved with timestamps
- [ ] New logs continue after rotation
- [ ] No log data lost during rotation

#### Test 5.4: Diagnostics
- [ ] Diagnostics screen shows all system info
- [ ] Model existence check accurate
- [ ] CLI existence check accurate
- [ ] Audio source detection works
- [ ] Command availability check accurate
- [ ] Health status accurate

## Feedback Loop

### Providing Feedback to AI

When testing, provide the following information to assist AI debugging:

#### 1. Error Messages
- Copy exact error text from logs
- Include timestamps if available
- Note which operation triggered the error

#### 2. System Information
```bash
easy-local-whisper-hotkey doctor
```

#### 3. Relevant Log Excerpt
Extract 50-100 lines around the issue:
```bash
# Linux/macOS
grep -A 50 -B 10 "ERROR" ~/.local/share/whisper-hotkey/logs/whisper_*.log | tail -100

# Windows
Get-Content "$env:APPDATA\whisper-hotkey\logs\whisper_*.log" | Select-String -Pattern "ERROR" -Context 10,50
```

#### 4. Reproduction Steps
1. Clear description of what you did
2. Exact clicks/key presses
3. Configuration state before test
4. Expected vs actual behavior

#### 5. Screenshots
For UI issues:
- Take screenshot of the error
- Show configuration panel state
- Show any error dialogs

### Feedback Template

```
## Issue Description
[Short description of what's wrong]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [Third step]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Configuration
[Attach config or list key settings]

## Logs
[Relevant log excerpt]

## System Info
[Output from easy-local-whisper-hotkey doctor]
```

## Common Issues & Troubleshooting

### Issue: Daemon won't start

**Debug Steps:**
1. Check logs for error message
2. Verify whisper-cli is installed: `which whisper-cli`
3. Verify model exists: Check config path
4. Run diagnostics: `easy-local-whisper-hotkey doctor`

**Feedback to AI:**
"Daemon fails to start. Logs show: [error]. Diagnostics output: [output]."

### Issue: No audio captured

**Debug Steps:**
1. Test with audio test: `easy-local-whisper-hotkey test --seconds 3`
2. Check audio source selection
3. Verify audio permissions
4. Check logs for audio errors

**Feedback to AI:**
"No audio captured. Test works from CLI but not from desktop app. Selected source: [source]. Logs: [excerpt]."

### Issue: Transcription inaccurate

**Debug Steps:**
1. Test with debug logging enabled
2. Check audio quality in logs
3. Try different model
4. Verify language setting

**Feedback to AI:**
"Transcription inaccurate. Set debug logging. Logs show audio capture: [audio details]. Model: [model]. Language: [language]."

### Issue: Autostart not working

**Debug Steps:**
1. Check if autostart enabled: Check app status
2. Check system autostart config:
   - Linux: `systemctl --user list-units | grep whisper`
   - macOS: `launchctl list | grep whisper`
   - Windows: `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run"`
3. Check logs at login

**Feedback to AI:**
"Autostart not working. System: [OS]. Autostart status: [enabled/disabled]. System check: [output]. Login logs: [excerpt]."

## Performance Testing

### Load Testing
- Record 10 consecutive dictations
- Monitor for performance degradation
- Check memory usage over time
- Verify log rotation under load

### Stress Testing
- Enable debug logging
- Run continuous dictation for 5 minutes
- Monitor log file size
- Verify no crashes or freezes

## Cross-Platform Testing

### Linux (Arch)
- [ ] Systemd autostart works
- [ ] PipeWire audio works
- [ ] PulseAudio fallback works
- [ ] X11 typing works

### Windows
- [ ] Registry autostart works
- [ ] WASAPI audio works
- [ ] SendKeys typing works
- [ ] Log paths correct

### macOS
- [ ] LaunchAgent autostart works
- [ ] CoreAudio works
- [ ] Accessibility API typing works
- [ ] Log paths correct

## Continuous Monitoring

### Daily Checks
- Review logs for errors
- Verify autostart is working
- Check disk space for logs

### Weekly Checks
- Run full diagnostics
- Update model if needed
- Review and archive old logs

### Monthly Checks
- Test all features comprehensively
- Check for regressions
- Provide feedback to AI for improvements

## AI-Assisted Debugging

### When to Involve AI
- Unusual error messages
- Unexpected behavior not documented
- Performance issues
- Cross-platform specific issues

### What AI Needs
1. **Context**: What you're trying to do
2. **Error**: Exact error messages
3. **Logs**: Relevant log sections
4. **Config**: Current configuration
5. **System**: Platform and environment info

### What AI Can Do
- Analyze log patterns
- Identify configuration issues
- Suggest code fixes
- Improve error messages
- Add better logging
- Test hypotheses remotely

## Reporting Protocol

### Critical Issues
Blocker bugs (crashes, data loss, security):
1. Enable debug logging
2. Reproduce issue
3. Capture full logs
4. Provide complete feedback template
5. Stop using the feature until fixed

### Major Issues
Functional bugs (features not working):
1. Enable debug logging
2. Document reproduction steps
3. Capture relevant logs
4. Provide feedback template
5. Continue testing other features

### Minor Issues
UI glitches, cosmetic issues:
1. Note issue
2. Provide brief description
3. Include screenshot if applicable
4. Continue testing

### Suggestions
Improvements, new features:
1. Describe the improvement
2. Explain the use case
3. Suggest implementation approach
4. Reference similar tools if applicable

## Closing the Loop

After AI provides a fix:

1. **Test the fix**: Apply changes and verify
2. **Provide feedback**: Confirm fix works or report issues
3. **Document**: Update any documentation if needed
4. **Archive logs**: Save logs that helped debug
5. **Share**: Inform AI of success/failure

## Success Criteria

QA is successful when:
- [ ] All test phases pass
- [ ] No critical issues remain
- [ ] Logs provide sufficient debug information
- [ ] AI can diagnose issues from logs
- [ ] Feedback loop is documented and effective
- [ ] Cross-platform compatibility verified
- [ ] Performance is acceptable
