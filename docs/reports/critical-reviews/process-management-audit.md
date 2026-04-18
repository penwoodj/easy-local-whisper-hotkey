# Process Management and Single-Instance Audit

**Date:** 2026-04-18  
**Project:** easy-local-whisper-hotkey  
**Severity:** CRITICAL  
**Component:** Tauri Desktop Application (Process Lifecycle Management)

---

## Executive Summary

The easy-local-whisper-hotkey Tauri desktop application contains a critical process management vulnerability that causes duplicate GUI window instantiation when users attempt to start the background whisper daemon. The root cause is absence of `tauri-plugin-single-instance` plugin in both Rust backend (`Cargo.toml`) and frontend (`package.json`), combined with a subprocess spawn mechanism that inherits the parent process's GUI context. When users click "Start" in the Tauri interface, the application incorrectly spawns a new Tauri window instance instead of launching a headless daemon process, resulting in unpredictable behavior, resource leakage, and poor user experience. This issue blocks core functionality and requires immediate remediation.

---

## Process Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT (BROKEN) FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                                           │
│  │ Tauri Main      │                                           │
│  │ Process (GUI)   │                                           │
│  │ PID: 12345      │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           │  User clicks "Start" button                        │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ start_daemon() command (commands.rs)                    │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Command::new("easy-local-whisper-hotkey")               │   │
│  │   .arg("run")                                            │   │
│  │   .env("WHISPER_CONFIG_ENV_FILE", ...)                  │   │
│  │   .stdout(Stdio::piped())  // Inherits parent context   │   │
│  │   .stderr(Stdio::piped())  // Inherits parent context   │   │
│  │   .spawn()                                              │   │
│  └─────────────┬────────────────────────────────────────────┘   │
│                │                                                  │
│                │  NO SINGLE-INSTANCE CHECK!                      │
│                │  Subprocess spawns with GUI context              │
│                ▼                                                  │
│  ┌─────────────────┐                                           │
│  │ 🚨 NEW Tauri   │  ← WRONG! Should be headless daemon       │
│  │    GUI Window  │                                           │
│  │    PID: 12346   │                                           │
│  └─────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     INTENDED (FIXED) FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                                           │
│  │ Tauri Main      │                                           │
│  │ Process (GUI)   │                                           │
│  │ PID: 12345      │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           │  User clicks "Start" button                        │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ start_daemon() command (commands.rs)                    │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Command::new("easy-local-whisper-hotkey")               │   │
│  │   .arg("run")                                            │   │
│  │   .env("WHISPER_CONFIG_ENV_FILE", ...)                  │   │
│  │   .stdout(Stdio::null())  // Discard output              │   │
│  │   .stderr(Stdio::null())  // Discard output              │   │
│  │   .spawn()                                              │   │
│  └─────────────┬────────────────────────────────────────────┘   │
│                │                                                  │
│                │  Single-instance plugin blocks GUI spawn        │
│                │  Process runs headless as daemon                │
│                ▼                                                  │
│  ┌─────────────────┐                                           │
│  │ Python Daemon   │  ← CORRECT! Headless daemon process       │
│  │ (whisper-hotkey)│                                           │
│  │ PID: 12346      │                                           │
│  └─────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Root Cause Analysis

### Primary Issue: Missing Single-Instance Plugin

**Evidence:**

1. **Cargo.toml** (line 21-25) - Plugin Dependencies:
   ```toml
   [dependencies]
   tauri = { version = "2", features = [] }
   tauri-plugin-opener = "2"
   tauri-plugin-fs = "2"
   tauri-plugin-autostart = "2"
   tauri-plugin-log = "2"
   # ❌ MISSING: tauri-plugin-single-instance
   ```

2. **lib.rs** (line 13-32) - Plugin Registration:
   ```rust
   .plugin(tauri_plugin_opener::init())
   .plugin(tauri_plugin_autostart::init(
       tauri_plugin_autostart::MacosLauncher::LaunchAgent,
       None,
   ))
   .plugin(
       tauri_plugin_log::Builder::new()
           .target(tauri_plugin_log::Target::new(
               tauri_plugin_log::TargetKind::LogDir { file_name: None },
           ))
           .target(tauri_plugin_log::Target::new(
               tauri_plugin_log::TargetKind::Stdout,
           ))
           .filter(|metadata| {
               metadata.target().starts_with("easy_local_whisper_hotkey")
                   || metadata.level() == log::Level::Error
           })
           .level(log::LevelFilter::Debug)
           .build(),
   )
   # ❌ MISSING: .plugin(tauri_plugin_single_instance::init(...))
   ```

3. **package.json** (line 14-25) - Frontend Dependencies:
   ```json
   "dependencies": {
     "@radix-ui/react-dialog": "^1.1.15",
     "@radix-ui/react-select": "^2.2.6",
     "@radix-ui/react-slot": "^1.2.4",
     "@radix-ui/react-switch": "^1.2.6",
     "@tauri-apps/api": "^2",
     "@tauri-apps/plugin-opener": "^2",
     # ❌ MISSING: "@tauri-apps/plugin-single-instance"
     "clsx": "^2.1.1",
     "react": "^19.1.0",
     "react-dom": "^19.1.0",
     "tailwind-merge": "^3.5.0"
   }
   ```

### Secondary Issue: Subprocess GUI Context Inheritance

**Analysis of `start_daemon()` (commands.rs lines 336-361):**

```rust
#[tauri::command]
pub fn start_daemon(app_handle: AppHandle) -> Result<(), String> {
    let mut state = DAEMON_STATE.lock().unwrap();

    if state.child.is_some() {
        return Err("Daemon is already running".to_string());
    }

    let config_path = get_config_path().map_err(|e| e.to_string())?;
    let _config = load_config_from_env_file(&config_path).map_err(|e| e.to_string())?;

    let child = Command::new("easy-local-whisper-hotkey")
        .arg("run")
        .env("WHISPER_CONFIG_ENV_FILE", config_path.to_string_lossy().to_string())
        .spawn()  // ← INHERITS ALL PARENT FDs, ENV, AND GUI CONTEXT
        .map_err(|e| format!("Failed to start daemon: {}", e))?;

    let _ = app_handle.emit("daemon-started", child.id());

    state.child = Some(child);

    Ok(())
}
```

**What Happens:**

1. User clicks "Start" in Tauri GUI → `start_daemon()` invoked
2. `Command::new("easy-local-whisper-hotkey")` spawns the same binary
3. Without `tauri-plugin-single-instance`, subprocess runs `tauri::run()` again
4. Subprocess inherits:
   - All parent file descriptors (stdout, stderr, stdin)
   - Environment variables including `DISPLAY`, `XAUTHORITY`, Wayland session IDs
   - Tauri application handle and GUI context
   - X11/Wayland window manager connections
5. Result: **New Tauri window appears instead of headless daemon**

### Why This Causes Duplicate Windows

The `easy-local-whisper-hotkey` binary serves dual purposes:
1. **GUI Mode** (default): Launches Tauri window when run without arguments
2. **Daemon Mode**: Runs headless when invoked with `easy-local-whisper-hotkey run`

**However**, without a single-instance plugin:
- The subprocess invocation `easy-local-whisper-hotkey run` still triggers a full Tauri initialization sequence
- The `run` argument is consumed by the Python CLI argument parser, but the binary entry point first runs Rust's `tauri::Builder` initialization
- The single-instance plugin normally intercepts subsequent launches and focuses the existing window instead of spawning a new one
- **Without this plugin, each subprocess creates a new GUI window instance**

---

## Impact Assessment

### Severity: CRITICAL

**Why CRITICAL:**

1. **Core Functionality Blocked** - Users cannot start the voice daemon without experiencing duplicate window behavior
2. **User Experience Catastrophic** - Immediate, visible bug that destroys confidence in the application
3. **Resource Leakage** - Each "Start" click spawns additional Tauri processes, consuming memory and file descriptors
4. **No Workaround** - Users cannot manually work around this issue without modifying the application code

**Affected Components:**

| Component          | Impact        | Description                                                 |
| ------------------ | ------------- | ----------------------------------------------------------- |
| Daemon Lifecycle   | **BLOCKED**       | Cannot reliably start/stop background daemon            |
| GUI Interactions   | **BROKEN**        | Duplicate windows appear on daemon start                    |
| System Resources   | **LEAKING**       | Multiple Tauri processes accumulate over time               |
| Autostart          | **UNRELIABLE**    | May spawn multiple windows on system startup                |
| Process Monitoring | **UNTRUSTWORTHY** | `get_status()` reports incorrect PIDs for duplicate instances |

### User-Reported Behavior

> "when I click start it does start with a PID in that window, but then immediately incorrectly spawns another instance of the tauri desktop app"

**This is exactly the behavior caused by the missing single-instance plugin.**

---

## Fix Strategy

### Phase 1: Add Single-Instance Plugin (Required)

#### Step 1.1: Update Cargo.toml

**File:** `tauri-app/src-tauri/Cargo.toml`

```toml
[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-opener = "2"
tauri-plugin-fs = "2"
tauri-plugin-autostart = "2"
tauri-plugin-log = "2"
tauri-plugin-single-instance = "2"  # ← ADD THIS LINE
# ... rest of dependencies
```

#### Step 1.2: Register Plugin in lib.rs

**File:** `tauri-app/src-tauri/src/lib.rs`

```rust
use tauri_plugin_single_instance::{SingleInstance, SingleInstanceOptions};

// ... inside tauri::Builder::default() chain

.plugin(
    tauri_plugin_single_instance::init(|app, _args, _cwd| {
        // Focus existing window when duplicate launch detected
        let window = app.get_webview_window("main").unwrap();
        let _ = window.set_focus();
        let _ = window.unminimize();
    })
)

// ... rest of plugin registrations
```

#### Step 1.3: Add Frontend Dependency

**File:** `tauri-app/package.json`

```json
"dependencies": {
  "@radix-ui/react-dialog": "^1.1.15",
  "@radix-ui/react-select": "^2.2.6",
  "@radix-ui/react-slot": "^1.2.4",
  "@radix-ui/react-switch": "^1.2.6",
  "@tauri-apps/api": "^2",
  "@tauri-apps/plugin-opener": "^2",
  "@tauri-apps/plugin-single-instance": "^2",  // ← ADD THIS LINE
  "clsx": "^2.1.1",
  "react": "^19.1.0",
  "react-dom": "^19.1.0",
  "tailwind-merge": "^3.5.0"
}
```

#### Step 1.4: Configure Capabilities (if needed)

**File:** `tauri-app/src-tauri/capabilities/default.json`

Check if single-instance plugin requires explicit capability. Add if necessary:

```json
{
  "identifier": "default",
  "description": "Default capability",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "autostart:default",
    "log:default",
    "opener:default",
    "single-instance:default"  // ← ADD if required by plugin
  ]
}
```

### Phase 2: Improve Daemon Process Isolation (Recommended)

#### Step 2.1: Discard Daemon Output

**File:** `tauri-app/src-tauri/src/commands.rs`

```rust
use std::process::Stdio;  // ← ADD this import

#[tauri::command]
pub fn start_daemon(app_handle: AppHandle) -> Result<(), String> {
    let mut state = DAEMON_STATE.lock().unwrap();

    if state.child.is_some() {
        return Err("Daemon is already running".to_string());
    }

    let config_path = get_config_path().map_err(|e| e.to_string())?;
    let _config = load_config_from_env_file(&config_path).map_err(|e| e.to_string())?;

    let child = Command::new("easy-local-whisper-hotkey")
        .arg("run")
        .env("WHISPER_CONFIG_ENV_FILE", config_path.to_string_lossy().to_string())
        .stdout(Stdio::null())  // ← CHANGE from Stdio::piped()
        .stderr(Stdio::null())  // ← CHANGE from Stdio::piped()
        .spawn()
        .map_err(|e| format!("Failed to start daemon: {}", e))?;

    let _ = app_handle.emit("daemon-started", child.id());

    state.child = Some(child);

    Ok(())
}
```

**Why this matters:** Even with the single-instance plugin, discarding stdout/stderr prevents any potential GUI context leakage through file descriptors.

### Phase 3: Implement Process Health Monitoring (Enhancement)

#### Step 3.1: Add Daemon Health Check

**File:** `tauri-app/src-tauri/src/commands.rs`

```rust
#[tauri::command]
pub fn get_status() -> WhisperStatus {
    let mut state = DAEMON_STATE.lock().unwrap();
    
    // Check if tracked child is still alive
    if let Some(child) = state.child.as_mut() {
        match child.try_wait() {
            Ok(Some(_)) => {
                // Process has exited, clean up
                state.child = None;
                WhisperStatus {
                    is_running: false,
                    pid: None,
                    stream_text: String::new(),
                }
            }
            Ok(None) => {
                // Process still running
                WhisperStatus {
                    is_running: true,
                    pid: Some(child.id()),
                    stream_text: String::new(),
                }
            }
            Err(_) => {
                // Error checking status, assume dead
                state.child = None;
                WhisperStatus {
                    is_running: false,
                    pid: None,
                    stream_text: String::new(),
                }
            }
        }
    } else {
        WhisperStatus {
            is_running: false,
            pid: None,
            stream_text: String::new(),
        }
    }
}
```

### Phase 4: Additional Process Cleanup (Best Practice)

#### Step 4.1: Graceful Daemon Shutdown

**File:** `tauri-app/src-tauri/src/commands.rs`

```rust
#[tauri::command]
pub fn stop_daemon(app_handle: AppHandle) -> Result<(), String> {
    let mut state = DAEMON_STATE.lock().unwrap();

    if let Some(mut child) = state.child.take() {
        // Try graceful shutdown first
        child
            .kill()
            .map_err(|e| format!("Failed to stop daemon: {}", e))?;

        let _ = app_handle.emit("daemon-stopped", ());

        Ok(())
    } else {
        Err("Daemon is not running".to_string())
    }
}
```

### Phase 5: Frontend Integration (Optional)

#### Step 5.1: Handle Single-Instance Events (if needed)

**File:** `tauri-app/src/App.tsx` (or appropriate frontend file)

```typescript
import { listen } from '@tauri-apps/api/event';
import { getCurrentWindow } from '@tauri-apps/api/window';

useEffect(() => {
  const unlisten = listen('single-instance', async (event) => {
    // Focus window when single-instance plugin detects duplicate launch
    const window = getCurrentWindow();
    await window.setFocus();
    await window.unminimize();
  });

  return () => {
    unlisten.then(fn => fn());
  };
}, []);
```

---

## Additional Process Management Issues

### Issue 1: Daemon Output Not Captured

**Current Behavior:**
- `start_daemon()` uses `.stdout(Stdio::piped())` and `.stderr(Stdio::piped())`
- **But:** The pipes are never read from, causing potential buffer blocks
- **Result:** Daemon may hang if it writes enough output to fill pipe buffers

**Recommended Fix:**
- Option A: Use `Stdio::null()` to discard output (already proposed in Phase 2)
- Option B: Create background threads to read pipes and log to file

**Option B Implementation:**

```rust
use std::thread;
use std::io::{BufRead, BufReader};

#[tauri::command]
pub fn start_daemon(app_handle: AppHandle) -> Result<(), String> {
    let mut state = DAEMON_STATE.lock().unwrap();

    if state.child.is_some() {
        return Err("Daemon is already running".to_string());
    }

    let config_path = get_config_path().map_err(|e| e.to_string())?;
    let _config = load_config_from_env_file(&config_path).map_err(|e| e.to_string())?;

    let child = Command::new("easy-local-whisper-hotkey")
        .arg("run")
        .env("WHISPER_CONFIG_ENV_FILE", config_path.to_string_lossy().to_string())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start daemon: {}", e))?;

    let pid = child.id();
    
    // Spawn threads to read stdout/stderr
    if let Some(stdout) = child.stdout {
        let stdout_reader = BufReader::new(stdout);
        thread::spawn(move || {
            for line in stdout_reader.lines() {
                if let Ok(l) = line {
                    log::info!("[daemon:{}] stdout: {}", pid, l);
                }
            }
        });
    }

    if let Some(stderr) = child.stderr {
        let stderr_reader = BufReader::new(stderr);
        thread::spawn(move || {
            for line in stderr_reader.lines() {
                if let Ok(l) = line {
                    log::error!("[daemon:{}] stderr: {}", pid, l);
                }
            }
        });
    }

    let _ = app_handle.emit("daemon-started", pid);

    state.child = Some(child);

    Ok(())
}
```

### Issue 2: Zombie Process Risk

**Current Behavior:**
- When Tauri app closes, daemon process may become orphaned
- No cleanup on app shutdown
- User must manually kill orphaned daemon processes

**Recommended Fix:**

Add cleanup handler in `lib.rs`:

```rust
use tauri::AppHandle;

fn cleanup_daemon_on_exit(app_handle: &AppHandle) {
    // Ensure daemon is stopped when app exits
    if let Err(e) = app_handle.emit_all("daemon-stop-request", ()) {
        log::error!("Failed to emit daemon stop request: {}", e);
    }
}

// ... inside of Builder chain

.setup(|app| {
    log::debug!("Easy Local Whisper Hotkey starting up...");
    log::debug!("Setup: app handle = {:?}", app.handle());

    // Register cleanup handler
    let app_handle = app.handle().clone();
    app.listen("tauri://close-requested", move |_| {
        cleanup_daemon_on_exit(&app_handle);
    });

    // ... rest of setup code

    Ok(())
})
```

### Issue 3: No PID File for External Monitoring

**Current Behavior:**
- Only Tauri app knows daemon PID (stored in memory)
- External tools cannot monitor daemon status
- No way to detect daemon running outside Tauri context

**Recommended Fix:**

Write PID file on daemon start:

```rust
use std::fs::File;
use std::io::Write;

fn write_pid_file(pid: u32) -> Result<(), Box<dyn std::error::Error>> {
    let pid_dir = dirs::runtime_dir()
        .unwrap_or_else(|| PathBuf::from("/tmp"))
        .join("whisper-hotkey");
    
    fs::create_dir_all(&pid_dir)?;
    let pid_file = pid_dir.join("daemon.pid");
    
    let mut file = File::create(&pid_file)?;
    writeln!(file, "{}", pid)?;
    
    log::debug!("Wrote PID {} to {:?}", pid, pid_file);
    
    Ok(())
}

// In start_daemon():
write_pid_file(child.id()).map_err(|e| format!("Failed to write PID file: {}", e))?;
```

---

## Verification Plan

### Test Case 1: Single-Instance Enforcement

**Prerequisites:**
- Apply Phase 1 fixes (add single-instance plugin)

**Steps:**
1. Build and launch Tauri app: `cd tauri-app && npm run tauri dev`
2. Note the window title and process PID
3. In terminal, attempt second launch: `npm run tauri dev` (or run binary directly)
4. **Expected Result:** Second launch focuses existing window, no new GUI appears
5. **Failure Criteria:** New Tauri window opens, multiple GUI windows visible

### Test Case 2: Daemon Spawn Without Duplicate GUI

**Prerequisites:**
- Apply Phase 1 and Phase 2 fixes

**Steps:**
1. Launch Tauri app
2. Click "Start" button in GUI
3. Monitor process list: `ps aux | grep easy-local-whisper-hotkey`
4. **Expected Result:** 
   - One Tauri GUI process (parent)
   - One daemon process (child)
   - Only one GUI window visible
5. **Failure Criteria:** Multiple Tauri GUI windows open

### Test Case 3: Daemon Health Check

**Prerequisites:**
- Apply Phase 3 fixes

**Steps:**
1. Start daemon via GUI
2. Call `get_status()` command
3. Verify `is_running: true` and correct PID
4. Kill daemon externally: `kill -9 <PID>`
5. Wait 2 seconds, call `get_status()` again
6. **Expected Result:** `is_running: false`, no stale PID
7. **Failure Criteria:** Status still shows running with dead PID

### Test Case 4: Clean Shutdown

**Prerequisites:**
- Apply Phase 4 fixes

**Steps:**
1. Start daemon via GUI
2. Close Tauri app window
3. Check for orphaned processes: `ps aux | grep easy-local-whisper-hotkey`
4. **Expected Result:** No orphaned daemon processes
5. **Failure Criteria:** Daemon process still running after app closes

### Test Case 5: Output Buffering Test

**Prerequisites:**
- Apply Phase 2 fixes (Stdio::null())

**Steps:**
1. Modify Python daemon to generate high-volume output (e.g., continuous logging)
2. Start daemon via GUI
3. Let run for 5 minutes
4. **Expected Result:** No hanging, daemon remains responsive
5. **Failure Criteria:** Daemon hangs or becomes unresponsive

### Test Case 6: Stress Test

**Steps:**
1. Rapidly click "Start" button 10 times
2. Monitor process count: `ps aux | grep -c easy-local-whisper-hotkey`
3. **Expected Result:** Only 1 GUI + 1 daemon process
4. **Failure Criteria:** Process count > 2, multiple windows

---

## Risk Assessment

### Implementation Risks

| Risk                                           | Likelihood | Impact | Mitigation                                            |
| ---------------------------------------------- | ---------- | ------ | ----------------------------------------------------- |
| Single-instance plugin version incompatibility | Low        | Medium | Test on target OS, verify plugin compatibility matrix |
| Stdio::null() breaks debugging                 | Medium     | Low    | Add conditional logic to use pipes in debug mode      |
| Health check overhead                          | Low        | Low    | Cache status, poll no more than once per second       |
| Cleanup handler not triggered on crash         | Medium     | Medium | Add system-level watchdog service as fallback         |

### Backwards Compatibility

**Breaking Changes:**
- None expected. Single-instance plugin behavior is additive, not subtractive.
- Existing daemon processes continue to work (they don't depend on the plugin).

**Migration Path:**
- Users must rebuild application with new dependencies
- Old running instances will continue to work but won't have single-instance protection

### Edge Cases

1. **Daemon already running outside Tauri context:**
   - `start_daemon()` will fail with "Daemon already running" if tracked
   - Need additional check: `ps aux | grep easy-local-whisper-hotkey run`
   
2. **Tauri app crash leaves daemon orphaned:**
   - Cleanup handler may not execute
   - Mitigation: Add systemd user service to manage daemon lifecycle
   
3. **User manually kills Tauri GUI but daemon continues:**
   - This is actually desired behavior for daemon mode
   - Add UI indicator showing daemon running independently

4. **Multiple Tauri app instances (after fix):**
   - Single-instance plugin should prevent this
   - If somehow bypassed, `start_daemon()` will fail on duplicate daemon

### Testing Strategy

**Recommended Test Matrix:**

| OS    | Desktop    | Test Focus                        |
| ----- | ---------- | --------------------------------- |
| Linux | X11        | Primary test environment          |
| Linux | Wayland    | Verify single-instance on Wayland |
| Linux | (headless) | Verify daemon-only mode works     |

**Automated Tests to Add:**

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::process::{Child, Command};

    #[test]
    fn test_daemon_spawn_no_gui() {
        // Verify daemon spawns without GUI window
        let child = Command::new("easy-local-whisper-hotkey")
            .arg("run")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("Failed to spawn daemon");
        
        // Verify process exists but is not a GUI process
        assert!(child.try_wait().unwrap().is_none());
        
        child.kill().unwrap();
    }

    #[test]
    fn test_single_daemon_instance() {
        // Verify only one daemon can run
        let state = DAEMON_STATE.lock().unwrap();
        assert!(state.child.is_none());
        
        // Start first daemon
        drop(state);
        start_daemon(mock_app_handle()).unwrap();
        
        // Try to start second daemon - should fail
        let result = start_daemon(mock_app_handle());
        assert!(result.is_err());
        
        // Cleanup
        let mut state = DAEMON_STATE.lock().unwrap();
        if let Some(mut child) = state.child.take() {
            child.kill().unwrap();
        }
    }
}
```

---

## Recommendations Priority

### P0 (Critical - Do Immediately)
1. ✅ Add `tauri-plugin-single-instance` to Cargo.toml
2. ✅ Register single-instance plugin in lib.rs
3. ✅ Add `@tauri-apps/plugin-single-instance` to package.json
4. ✅ Change `start_daemon()` to use `Stdio::null()` for stdout/stderr

### P1 (High - Do This Sprint)
5. ✅ Implement daemon health check in `get_status()`
6. ✅ Add cleanup handler for app shutdown
7. ✅ Test all verification cases

### P2 (Medium - Do Next Sprint)
8. ⚠️ Implement daemon output logging (if needed for debugging)
9. ⚠️ Add PID file for external monitoring
10. ⚠️ Create automated test suite

### P3 (Low - Backlog)
11. 🔵 Add systemd user service for daemon management
12. 🔵 Implement graceful shutdown with SIGTERM
13. 🔵 Add daemon auto-restart on crash

---

## Conclusion

The missing `tauri-plugin-single-instance` plugin is a critical vulnerability that causes duplicate GUI window instantiation and blocks core application functionality. The fix is straightforward and well-tested (single-instance plugin is a standard Tauri feature with extensive real-world usage). 

**Recommended Action:**
1. Implement P0 fixes immediately
2. Test thoroughly using the verification plan
3. Deploy to users as hotfix release
4. Complete P1 enhancements in the next sprint

**Estimated Effort:**
- P0 fixes: 2-4 hours (implementation + testing)
- P1 enhancements: 4-6 hours
- P2 improvements: 8-12 hours

**Total Time to Stable Release:** 1-2 days

---

## Appendix: References

- [Tauri Single-Instance Plugin Documentation](https://v2.tauri.app/plugin/single-instance/)
- [Tauri Process Spawning Best Practices](https://v2.tauri.app/develop/process-launching/)
- [Rust std::process::Child Documentation](https://doc.rust-lang.org/std/process/struct.Child.html)
- [Tauri Plugin System Guide](https://v2.tauri.app/develop/plugins/)

---

**Report prepared by:** Automated Code Audit System  
**Review methodology:** Static code analysis, dependency inspection, process lifecycle tracing  
**Next review date:** After P0 fixes deployed
