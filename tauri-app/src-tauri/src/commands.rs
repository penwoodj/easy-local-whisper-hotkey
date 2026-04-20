use anyhow::{Context, Result};
use dirs::home_dir;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{AppHandle, Emitter};

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Default)]
#[serde(rename_all = "snake_case")]
pub enum LogLevel {
    #[default]
    Info,
    Debug,
}

impl std::fmt::Display for LogLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LogLevel::Info => write!(f, "info"),
            LogLevel::Debug => write!(f, "debug"),
        }
    }
}

impl std::str::FromStr for LogLevel {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "info" => Ok(LogLevel::Info),
            "debug" => Ok(LogLevel::Debug),
            _ => Err(format!("Invalid log level: {}", s)),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone, Default, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum VoiceActivationMode {
    #[default]
    Toggle,
    Hold,
}

impl std::fmt::Display for VoiceActivationMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            VoiceActivationMode::Hold => write!(f, "hold"),
            VoiceActivationMode::Toggle => write!(f, "toggle"),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone, Default, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum PostProcessingMode {
    #[default]
    Off,
    Light,
    Aggressive,
    Agentic,
    Writing,
    Code,
    Structure,
    Persona,
    Clarity,
}

impl std::fmt::Display for PostProcessingMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PostProcessingMode::Off => write!(f, "off"),
            PostProcessingMode::Light => write!(f, "light"),
            PostProcessingMode::Aggressive => write!(f, "aggressive"),
            PostProcessingMode::Agentic => write!(f, "agentic"),
            PostProcessingMode::Writing => write!(f, "writing"),
            PostProcessingMode::Code => write!(f, "code"),
            PostProcessingMode::Structure => write!(f, "structure"),
            PostProcessingMode::Persona => write!(f, "persona"),
            PostProcessingMode::Clarity => write!(f, "clarity"),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone, Default, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum PostProcessingTrigger {
    #[default]
    Always,
    Manual,
    #[serde(rename = "auto_long")]
    AutoLong,
    Preview,
}

impl std::fmt::Display for PostProcessingTrigger {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PostProcessingTrigger::Always => write!(f, "always"),
            PostProcessingTrigger::Manual => write!(f, "manual"),
            PostProcessingTrigger::AutoLong => write!(f, "auto_long"),
            PostProcessingTrigger::Preview => write!(f, "preview"),
        }
    }
}

fn default_indicator_enabled() -> bool {
    true
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct WhisperConfig {
    pub whisper_cli: String,
    pub model: String,
    pub source: String,
    pub preferred_sources: String,
    pub chunk_seconds: f64,
    pub overlap_seconds: f64,
    pub type_delay_ms: i32,
    pub language: String,
    pub suppress_regex: String,
    pub suppress_nst: bool,
    pub smart_punctuation: bool,
    pub symbol_words_to_symbols: bool,
    pub direct_streaming: bool,
    pub log_file: String,
    #[serde(default)]
    pub log_level: LogLevel,
    #[serde(default)]
    pub voice_activation_mode: VoiceActivationMode,
    #[serde(default)]
    pub post_processing_enabled: bool,
    #[serde(default)]
    pub post_processing_mode: PostProcessingMode,
    #[serde(default)]
    pub post_processing_trigger: PostProcessingTrigger,
    #[serde(default = "default_indicator_enabled")]
    pub indicator_enabled: bool,
}

impl Default for WhisperConfig {
    fn default() -> Self {
        let xdg_data = home_dir()
            .map(|h| h.join(".local/share"))
            .unwrap_or_else(|| PathBuf::from("/tmp"));

        Self {
            whisper_cli: "whisper-cli".to_string(),
            model: xdg_data
                .join("whisper-hotkey/models/ggml-base.en.bin")
                .to_string_lossy()
                .to_string(),
            source: String::new(),
            preferred_sources: String::new(),
            chunk_seconds: 3.5,
            overlap_seconds: 0.8,
            type_delay_ms: 1,
            language: "en".to_string(),
            suppress_regex: "[,.]".to_string(),
            suppress_nst: true,
            smart_punctuation: true,
            symbol_words_to_symbols: false,
            direct_streaming: false,
            log_file: "/tmp/whisper_hotkey.log".to_string(),
            log_level: LogLevel::Info,
            voice_activation_mode: VoiceActivationMode::Toggle,
            post_processing_enabled: false,
            post_processing_mode: PostProcessingMode::Off,
            post_processing_trigger: PostProcessingTrigger::Always,
            indicator_enabled: true,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WhisperStatus {
    pub is_running: bool,
    pub pid: Option<u32>,
    pub stream_text: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AudioSource {
    pub name: String,
    pub description: Option<String>,
    pub is_default: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DiagnosticInfo {
    pub display: String,
    pub xauthority: String,
    pub model_path: String,
    pub model_exists: bool,
    pub whisper_cli_path: String,
    pub whisper_cli_exists: bool,
    pub commands: HashMap<String, bool>,
    pub preferred_sources: Vec<String>,
    pub default_source: String,
    pub available_sources: Vec<String>,
    pub source_error: String,
    pub requested_source: String,
    pub chunk_seconds: f64,
    pub overlap_seconds: f64,
    pub type_delay_ms: i32,
    pub language: String,
    pub suppress_regex: String,
    pub suppress_nst: bool,
    pub smart_punctuation: bool,
    pub symbol_words_to_symbols: bool,
    pub direct_streaming: bool,
    pub log_file: String,
    pub healthy: bool,
    pub version: String,
}

impl Default for DiagnosticInfo {
    fn default() -> Self {
        Self {
            display: env::var("DISPLAY").unwrap_or_default(),
            xauthority: env::var("XAUTHORITY").unwrap_or_default(),
            model_path: String::new(),
            model_exists: false,
            whisper_cli_path: String::new(),
            whisper_cli_exists: false,
            commands: HashMap::new(),
            preferred_sources: Vec::new(),
            default_source: String::new(),
            available_sources: Vec::new(),
            source_error: String::new(),
            requested_source: String::new(),
            chunk_seconds: 0.0,
            overlap_seconds: 0.0,
            type_delay_ms: 0,
            language: String::new(),
            suppress_regex: String::new(),
            suppress_nst: false,
            smart_punctuation: false,
            symbol_words_to_symbols: false,
            direct_streaming: false,
            log_file: String::new(),
            healthy: false,
            version: env!("CARGO_PKG_VERSION").to_string(),
        }
    }
}

struct DaemonState {
    child: Option<Child>,
}

unsafe impl Send for DaemonState {}
unsafe impl Sync for DaemonState {}

static DAEMON_STATE: Mutex<DaemonState> = Mutex::new(DaemonState { child: None });

fn get_config_path() -> Result<PathBuf> {
    let xdg_config = home_dir()
        .ok_or_else(|| anyhow::anyhow!("Cannot determine home directory"))?
        .join(".config/whisper-hotkey");

    fs::create_dir_all(&xdg_config).context("Failed to create config directory")?;

    Ok(xdg_config.join("whisper-hotkey.env"))
}

fn load_config_from_env_file(path: &PathBuf) -> Result<WhisperConfig> {
    if !path.exists() {
        return Ok(WhisperConfig::default());
    }

    let content = fs::read_to_string(path).context("Failed to read config file")?;

    let mut config = WhisperConfig::default();

    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }

        if let Some((key, value)) = line.split_once('=') {
            let key = key.trim();
            let value = value.trim();

            match key {
                "WHISPER_CLI" => config.whisper_cli = value.to_string(),
                "WHISPER_MODEL" => config.model = value.to_string(),
                "WHISPER_AUDIO_SOURCE" => config.source = value.to_string(),
                "WHISPER_PREFERRED_SOURCES" => config.preferred_sources = value.to_string(),
                "WHISPER_CHUNK_SECONDS" => config.chunk_seconds = value.parse().unwrap_or(3.5),
                "WHISPER_OVERLAP_SECONDS" => config.overlap_seconds = value.parse().unwrap_or(0.8),
                "WHISPER_TYPE_DELAY_MS" => config.type_delay_ms = value.parse().unwrap_or(1),
                "WHISPER_LANGUAGE" => config.language = value.to_string(),
                "WHISPER_SUPPRESS_REGEX" => config.suppress_regex = value.to_string(),
                "WHISPER_SUPPRESS_NST" => config.suppress_nst = value.to_lowercase() == "true",
                "WHISPER_SMART_PUNCTUATION" => {
                    config.smart_punctuation = value.to_lowercase() == "true"
                }
                "WHISPER_SYMBOL_WORDS_TO_SYMBOLS" => {
                    config.symbol_words_to_symbols = value.to_lowercase() == "true"
                }
                "WHISPER_DIRECT_STREAMING" => {
                    config.direct_streaming = value.to_lowercase() == "true"
                }
                "WHISPER_LOG_FILE" => config.log_file = value.to_string(),
                "WHISPER_LOG_LEVEL" => {
                    config.log_level = value.parse().unwrap_or(LogLevel::Info);
                }
                "WHISPER_ACTIVATION_MODE" => {
                    config.voice_activation_mode = match value {
                        "hold" => VoiceActivationMode::Hold,
                        _ => VoiceActivationMode::Toggle,
                    };
                }
                "WHISPER_POST_PROCESSING_ENABLED" => {
                    config.post_processing_enabled = value == "true" || value == "1";
                }
                "WHISPER_POST_PROCESSING_MODE" => {
                    config.post_processing_mode = match value {
                        "light" => PostProcessingMode::Light,
                        "aggressive" => PostProcessingMode::Aggressive,
                        "agentic" => PostProcessingMode::Agentic,
                        "writing" => PostProcessingMode::Writing,
                        "code" => PostProcessingMode::Code,
                        "structure" => PostProcessingMode::Structure,
                        "persona" => PostProcessingMode::Persona,
                        "clarity" => PostProcessingMode::Clarity,
                        _ => PostProcessingMode::Off,
                    };
                }
                "WHISPER_POST_PROCESSING_TRIGGER" => {
                    config.post_processing_trigger = match value {
                        "manual" => PostProcessingTrigger::Manual,
                        "auto_long" => PostProcessingTrigger::AutoLong,
                        "preview" => PostProcessingTrigger::Preview,
                        _ => PostProcessingTrigger::Always,
                    };
                }
                "WHISPER_INDICATOR" => {
                    config.indicator_enabled = value == "true" || value == "1";
                }
                _ => {}
            }
        }
    }

    Ok(config)
}

fn save_config_to_env_file(path: &PathBuf, config: &WhisperConfig) -> Result<()> {
    let mut updates: HashMap<String, String> = HashMap::new();
    updates.insert("WHISPER_CLI".into(), config.whisper_cli.clone());
    updates.insert("WHISPER_MODEL".into(), config.model.clone());
    updates.insert("WHISPER_AUDIO_SOURCE".into(), config.source.clone());
    updates.insert(
        "WHISPER_PREFERRED_SOURCES".into(),
        config.preferred_sources.clone(),
    );
    updates.insert(
        "WHISPER_CHUNK_SECONDS".into(),
        config.chunk_seconds.to_string(),
    );
    updates.insert(
        "WHISPER_OVERLAP_SECONDS".into(),
        config.overlap_seconds.to_string(),
    );
    updates.insert(
        "WHISPER_TYPE_DELAY_MS".into(),
        config.type_delay_ms.to_string(),
    );
    updates.insert("WHISPER_LANGUAGE".into(), config.language.clone());
    updates.insert(
        "WHISPER_SUPPRESS_REGEX".into(),
        config.suppress_regex.clone(),
    );
    updates.insert(
        "WHISPER_SUPPRESS_NST".into(),
        config.suppress_nst.to_string(),
    );
    updates.insert(
        "WHISPER_SMART_PUNCTUATION".into(),
        config.smart_punctuation.to_string(),
    );
    updates.insert(
        "WHISPER_SYMBOL_WORDS_TO_SYMBOLS".into(),
        config.symbol_words_to_symbols.to_string(),
    );
    updates.insert(
        "WHISPER_DIRECT_STREAMING".into(),
        config.direct_streaming.to_string(),
    );
    updates.insert("WHISPER_LOG_FILE".into(), config.log_file.clone());
    updates.insert("WHISPER_LOG_LEVEL".into(), config.log_level.to_string());
    updates.insert(
        "WHISPER_ACTIVATION_MODE".into(),
        config.voice_activation_mode.to_string(),
    );
    updates.insert(
        "WHISPER_POST_PROCESSING_ENABLED".into(),
        config.post_processing_enabled.to_string(),
    );
    updates.insert(
        "WHISPER_POST_PROCESSING_MODE".into(),
        config.post_processing_mode.to_string(),
    );
    updates.insert(
        "WHISPER_POST_PROCESSING_TRIGGER".into(),
        config.post_processing_trigger.to_string(),
    );
    updates.insert(
        "WHISPER_INDICATOR".into(),
        config.indicator_enabled.to_string(),
    );

    if path.exists() {
        let existing = fs::read_to_string(path).context("Failed to read existing config")?;
        let mut result = String::new();
        let mut written_keys: std::collections::HashSet<String> = std::collections::HashSet::new();

        for line in existing.lines() {
            if let Some((key, _value)) = line.trim().split_once('=') {
                let key = key.trim();
                if let Some(new_value) = updates.get(key) {
                    result.push_str(&format!("{}={}\n", key, new_value));
                    written_keys.insert(key.to_string());
                    continue;
                }
            }
            result.push_str(line);
            result.push('\n');
        }

        for (key, value) in &updates {
            if !written_keys.contains(key) {
                result.push_str(&format!("{}={}\n", key, value));
            }
        }

        fs::write(path, result).context("Failed to write config file")?;
    } else {
        let mut content = String::from("# Whisper Hotkey Configuration\n");
        for (key, value) in &updates {
            content.push_str(&format!("{}={}\n", key, value));
        }
        fs::write(path, content).context("Failed to write config file")?;
    }

    Ok(())
}

#[tauri::command]
pub fn get_config() -> Result<WhisperConfig, String> {
    let config_path = get_config_path().map_err(|e| e.to_string())?;

    load_config_from_env_file(&config_path).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn set_config(config: WhisperConfig) -> Result<(), String> {
    let config_path = get_config_path().map_err(|e| e.to_string())?;

    save_config_to_env_file(&config_path, &config).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_status() -> WhisperStatus {
    let state = DAEMON_STATE.lock().unwrap();
    WhisperStatus {
        is_running: state.child.is_some(),
        pid: state.child.as_ref().map(|c| c.id()),
        stream_text: String::new(),
    }
}

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
        .env(
            "WHISPER_CONFIG_ENV_FILE",
            config_path.to_string_lossy().to_string(),
        )
        .env(
            "DISPLAY",
            env::var("DISPLAY").unwrap_or_else(|_| ":0".to_string()),
        )
        .spawn()
        .map_err(|e| format!("Failed to start daemon: {}", e))?;

    let _ = app_handle.emit("daemon-started", child.id());

    state.child = Some(child);

    Ok(())
}

#[tauri::command]
pub fn stop_daemon(app_handle: AppHandle) -> Result<(), String> {
    let mut state = DAEMON_STATE.lock().unwrap();

    if let Some(mut child) = state.child.take() {
        child
            .kill()
            .map_err(|e| format!("Failed to stop daemon: {}", e))?;

        let _ = app_handle.emit("daemon-stopped", ());

        Ok(())
    } else {
        Err("Daemon is not running".to_string())
    }
}

#[tauri::command]
pub fn list_sources() -> Result<Vec<AudioSource>, String> {
    let output = Command::new("pactl")
        .args(["list", "sources", "short"])
        .output()
        .map_err(|e| format!("Failed to list sources: {}", e))?;

    let mut sources = Vec::new();

    for line in String::from_utf8_lossy(&output.stdout).lines() {
        let fields: Vec<&str> = line.split_whitespace().collect();
        if fields.len() >= 2 {
            sources.push(AudioSource {
                name: fields[1].to_string(),
                description: None,
                is_default: false,
            });
        }
    }

    Ok(sources)
}

#[tauri::command]
pub fn enable_autostart(app_handle: AppHandle, enable: bool) -> Result<bool, String> {
    use tauri_plugin_autostart::ManagerExt;

    if enable {
        app_handle
            .autolaunch()
            .enable()
            .map_err(|e| e.to_string())?;
    } else {
        app_handle
            .autolaunch()
            .disable()
            .map_err(|e| e.to_string())?;
    }

    Ok(true)
}

#[tauri::command]
pub fn is_autostart_enabled(app_handle: AppHandle) -> Result<bool, String> {
    use tauri_plugin_autostart::ManagerExt;

    app_handle
        .autolaunch()
        .is_enabled()
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_diagnostics() -> Result<DiagnosticInfo, String> {
    let config_path = get_config_path().map_err(|e| e.to_string())?;

    let config = load_config_from_env_file(&config_path).map_err(|e| e.to_string())?;

    let mut diagnostics = DiagnosticInfo {
        model_path: config.model.clone(),
        model_exists: PathBuf::from(&config.model).exists(),
        whisper_cli_path: config.whisper_cli.clone(),
        whisper_cli_exists: which::which(&config.whisper_cli).is_ok(),
        requested_source: config.source.clone(),
        chunk_seconds: config.chunk_seconds,
        overlap_seconds: config.overlap_seconds,
        type_delay_ms: config.type_delay_ms,
        language: config.language.clone(),
        suppress_regex: config.suppress_regex.clone(),
        suppress_nst: config.suppress_nst,
        smart_punctuation: config.smart_punctuation,
        symbol_words_to_symbols: config.symbol_words_to_symbols,
        direct_streaming: config.direct_streaming,
        log_file: config.log_file.clone(),
        ..Default::default()
    };

    for cmd in ["parec", "pactl", "xdotool"] {
        diagnostics
            .commands
            .insert(cmd.to_string(), which::which(cmd).is_ok());
    }

    match Command::new("pactl").arg("get-default-source").output() {
        Ok(output) => {
            diagnostics.default_source = String::from_utf8_lossy(&output.stdout).trim().to_string();
        }
        Err(_) => {}
    }

    match list_sources() {
        Ok(sources) => {
            diagnostics.available_sources = sources.iter().map(|s| s.name.clone()).collect();
            diagnostics.preferred_sources = config
                .preferred_sources
                .split(',')
                .filter(|s| !s.is_empty())
                .map(|s| s.trim().to_string())
                .collect();
        }
        Err(e) => {
            diagnostics.source_error = e;
        }
    }

    diagnostics.healthy = diagnostics.model_exists
        && diagnostics.whisper_cli_exists
        && !diagnostics.display.is_empty()
        && diagnostics.commands.values().all(|&v| v)
        && diagnostics.source_error.is_empty();

    Ok(diagnostics)
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json;

    #[test]
    fn test_whisper_config_default_values() {
        let config = WhisperConfig::default();

        assert_eq!(config.whisper_cli, "whisper-cli");
        assert!(config.model.contains("ggml-base.en.bin"));
        assert_eq!(config.source, "");
        assert_eq!(config.preferred_sources, "");
        assert_eq!(config.chunk_seconds, 3.5);
        assert_eq!(config.overlap_seconds, 0.8);
        assert_eq!(config.type_delay_ms, 1);
        assert_eq!(config.language, "en");
        assert_eq!(config.suppress_regex, "[,.]");
        assert_eq!(config.suppress_nst, true);
        assert_eq!(config.smart_punctuation, true);
        assert_eq!(config.symbol_words_to_symbols, false);
        assert_eq!(config.direct_streaming, false);
        assert_eq!(config.log_file, "/tmp/whisper_hotkey.log");
        assert_eq!(config.log_level, LogLevel::Info);
        assert_eq!(config.voice_activation_mode, VoiceActivationMode::Toggle);
        assert_eq!(config.post_processing_enabled, false);
        assert_eq!(config.post_processing_mode, PostProcessingMode::Off);
        assert_eq!(
            config.post_processing_trigger,
            PostProcessingTrigger::Always
        );
        assert_eq!(config.indicator_enabled, true);
    }

    #[test]
    fn test_whisper_config_serialize_deserialize() {
        let config = WhisperConfig::default();

        let json = serde_json::to_string(&config).expect("Failed to serialize");

        let deserialized: WhisperConfig =
            serde_json::from_str(&json).expect("Failed to deserialize");

        assert_eq!(config.whisper_cli, deserialized.whisper_cli);
        assert_eq!(config.model, deserialized.model);
        assert_eq!(config.chunk_seconds, deserialized.chunk_seconds);
        assert_eq!(config.log_level, deserialized.log_level);
    }

    #[test]
    fn test_whisper_config_deserialize_partial() {
        let json = r#"{
            "whisper_cli": "custom-whisper",
            "model": "/custom/model.bin",
            "source": "",
            "preferred_sources": "",
            "chunk_seconds": 3.5,
            "overlap_seconds": 0.8,
            "type_delay_ms": 1,
            "language": "en",
            "suppress_regex": "[,.]",
            "suppress_nst": true,
            "smart_punctuation": true,
            "symbol_words_to_symbols": false,
            "direct_streaming": false,
            "log_file": "/tmp/whisper_hotkey.log",
            "log_level": "info",
            "indicator_enabled": true
        }"#;

        let config: WhisperConfig = serde_json::from_str(json).expect("Failed to deserialize");

        assert_eq!(config.whisper_cli, "custom-whisper");
        assert_eq!(config.model, "/custom/model.bin");
        assert_eq!(config.chunk_seconds, 3.5);
        assert_eq!(config.overlap_seconds, 0.8);
        assert_eq!(config.log_level, LogLevel::Info);
        assert_eq!(config.voice_activation_mode, VoiceActivationMode::Toggle);
    }

    #[test]
    fn test_whisper_config_deserialize_with_all_fields() {
        let json = r#"{
            "whisper_cli": "test-whisper",
            "model": "/test/model.bin",
            "source": "test-source",
            "preferred_sources": "source1,source2",
            "chunk_seconds": 5.0,
            "overlap_seconds": 1.0,
            "type_delay_ms": 100,
            "language": "es",
            "suppress_regex": "[.!?]",
            "suppress_nst": false,
            "smart_punctuation": false,
            "symbol_words_to_symbols": true,
            "direct_streaming": true,
            "log_file": "/var/log/whisper.log",
            "log_level": "debug",
            "voice_activation_mode": "hold",
            "post_processing_enabled": true,
            "post_processing_mode": "aggressive",
            "post_processing_trigger": "manual",
            "indicator_enabled": false
        }"#;

        let config: WhisperConfig = serde_json::from_str(json).expect("Failed to deserialize");

        assert_eq!(config.whisper_cli, "test-whisper");
        assert_eq!(config.model, "/test/model.bin");
        assert_eq!(config.source, "test-source");
        assert_eq!(config.preferred_sources, "source1,source2");
        assert_eq!(config.chunk_seconds, 5.0);
        assert_eq!(config.overlap_seconds, 1.0);
        assert_eq!(config.type_delay_ms, 100);
        assert_eq!(config.language, "es");
        assert_eq!(config.suppress_regex, "[.!?]");
        assert_eq!(config.suppress_nst, false);
        assert_eq!(config.smart_punctuation, false);
        assert_eq!(config.symbol_words_to_symbols, true);
        assert_eq!(config.direct_streaming, true);
        assert_eq!(config.log_file, "/var/log/whisper.log");
        assert_eq!(config.log_level, LogLevel::Debug);
        assert_eq!(config.voice_activation_mode, VoiceActivationMode::Hold);
        assert_eq!(config.post_processing_enabled, true);
        assert_eq!(config.post_processing_mode, PostProcessingMode::Aggressive);
        assert_eq!(
            config.post_processing_trigger,
            PostProcessingTrigger::Manual
        );
        assert_eq!(config.indicator_enabled, false);
    }

    #[test]
    fn test_load_config_from_env_file() {
        let temp_dir = std::env::temp_dir().join("whisper_test_load");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("test.env");

        let env_content = r#"WHISPER_CLI=my-whisper
WHISPER_MODEL=/my/model.bin
WHISPER_AUDIO_SOURCE=my-source
WHISPER_PREFERRED_SOURCES=pref1,pref2
WHISPER_CHUNK_SECONDS=4.5
WHISPER_OVERLAP_SECONDS=0.9
WHISPER_TYPE_DELAY_MS=50
WHISPER_LANGUAGE=fr
WHISPER_SUPPRESS_REGEX=[!?]
WHISPER_SUPPRESS_NST=false
WHISPER_SMART_PUNCTUATION=false
WHISPER_SYMBOL_WORDS_TO_SYMBOLS=true
WHISPER_DIRECT_STREAMING=true
WHISPER_LOG_FILE=/my/log.log
WHISPER_LOG_LEVEL=debug
WHISPER_ACTIVATION_MODE=hold
WHISPER_POST_PROCESSING_ENABLED=true
WHISPER_POST_PROCESSING_MODE=light
WHISPER_POST_PROCESSING_TRIGGER=auto_long
WHISPER_INDICATOR=false
"#;

        fs::write(&config_path, env_content).expect("Failed to write env file");

        let config =
            load_config_from_env_file(&config_path).expect("Failed to load config from env file");

        assert_eq!(config.whisper_cli, "my-whisper");
        assert_eq!(config.model, "/my/model.bin");
        assert_eq!(config.source, "my-source");
        assert_eq!(config.preferred_sources, "pref1,pref2");
        assert_eq!(config.chunk_seconds, 4.5);
        assert_eq!(config.overlap_seconds, 0.9);
        assert_eq!(config.type_delay_ms, 50);
        assert_eq!(config.language, "fr");
        assert_eq!(config.suppress_regex, "[!?]");
        assert_eq!(config.suppress_nst, false);
        assert_eq!(config.smart_punctuation, false);
        assert_eq!(config.symbol_words_to_symbols, true);
        assert_eq!(config.direct_streaming, true);
        assert_eq!(config.log_file, "/my/log.log");
        assert_eq!(config.log_level, LogLevel::Debug);
        assert_eq!(config.voice_activation_mode, VoiceActivationMode::Hold);
        assert_eq!(config.post_processing_enabled, true);
        assert_eq!(config.post_processing_mode, PostProcessingMode::Light);
        assert_eq!(
            config.post_processing_trigger,
            PostProcessingTrigger::AutoLong
        );
        assert_eq!(config.indicator_enabled, false);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_load_config_from_missing_file() {
        let temp_dir = std::env::temp_dir().join("whisper_test_missing");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("nonexistent.env");

        let config = load_config_from_env_file(&config_path)
            .expect("Failed to load config (should return default for missing file)");

        let default = WhisperConfig::default();
        assert_eq!(config.whisper_cli, default.whisper_cli);
        assert_eq!(config.chunk_seconds, default.chunk_seconds);
        assert_eq!(config.log_level, default.log_level);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_save_config_to_env_file() {
        let temp_dir = std::env::temp_dir().join("whisper_test_save");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("test.env");

        let config = WhisperConfig {
            whisper_cli: "test-cli".to_string(),
            model: "/test/model.bin".to_string(),
            source: "test-source".to_string(),
            preferred_sources: "src1,src2".to_string(),
            chunk_seconds: 6.0,
            overlap_seconds: 1.2,
            type_delay_ms: 75,
            language: "de".to_string(),
            suppress_regex: "[;]".to_string(),
            suppress_nst: false,
            smart_punctuation: true,
            symbol_words_to_symbols: false,
            direct_streaming: true,
            log_file: "/test/log.log".to_string(),
            log_level: LogLevel::Debug,
            voice_activation_mode: VoiceActivationMode::Hold,
            post_processing_enabled: true,
            post_processing_mode: PostProcessingMode::Aggressive,
            post_processing_trigger: PostProcessingTrigger::Manual,
            indicator_enabled: false,
        };

        save_config_to_env_file(&config_path, &config).expect("Failed to save config to env file");

        let content = fs::read_to_string(&config_path).expect("Failed to read saved env file");

        assert!(content.contains("WHISPER_CLI=test-cli"));
        assert!(content.contains("WHISPER_MODEL=/test/model.bin"));
        assert!(content.contains("WHISPER_AUDIO_SOURCE=test-source"));
        assert!(content.contains("WHISPER_PREFERRED_SOURCES=src1,src2"));
        assert!(content.contains("WHISPER_CHUNK_SECONDS=6"));
        assert!(content.contains("WHISPER_OVERLAP_SECONDS=1.2"));
        assert!(content.contains("WHISPER_TYPE_DELAY_MS=75"));
        assert!(content.contains("WHISPER_LANGUAGE=de"));
        assert!(content.contains("WHISPER_SUPPRESS_REGEX=[;]"));
        assert!(content.contains("WHISPER_SUPPRESS_NST=false"));
        assert!(content.contains("WHISPER_SMART_PUNCTUATION=true"));
        assert!(content.contains("WHISPER_SYMBOL_WORDS_TO_SYMBOLS=false"));
        assert!(content.contains("WHISPER_DIRECT_STREAMING=true"));
        assert!(content.contains("WHISPER_LOG_FILE=/test/log.log"));
        assert!(content.contains("WHISPER_LOG_LEVEL=debug"));
        assert!(content.contains("WHISPER_ACTIVATION_MODE=hold"));
        assert!(content.contains("WHISPER_POST_PROCESSING_ENABLED=true"));
        assert!(content.contains("WHISPER_POST_PROCESSING_MODE=aggressive"));
        assert!(content.contains("WHISPER_POST_PROCESSING_TRIGGER=manual"));
        assert!(content.contains("WHISPER_INDICATOR=false"));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_save_and_load_roundtrip() {
        let temp_dir = std::env::temp_dir().join("whisper_test_roundtrip");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("roundtrip.env");

        let original = WhisperConfig {
            whisper_cli: "roundtrip-cli".to_string(),
            model: "/roundtrip/model.bin".to_string(),
            source: "roundtrip-source".to_string(),
            preferred_sources: "a,b,c".to_string(),
            chunk_seconds: 7.5,
            overlap_seconds: 1.5,
            type_delay_ms: 200,
            language: "it".to_string(),
            suppress_regex: "[\\]".to_string(),
            suppress_nst: true,
            smart_punctuation: false,
            symbol_words_to_symbols: true,
            direct_streaming: false,
            log_file: "/roundtrip/log.log".to_string(),
            log_level: LogLevel::Debug,
            voice_activation_mode: VoiceActivationMode::Toggle,
            post_processing_enabled: true,
            post_processing_mode: PostProcessingMode::Code,
            post_processing_trigger: PostProcessingTrigger::Preview,
            indicator_enabled: true,
        };

        save_config_to_env_file(&config_path, &original).expect("Failed to save config");

        let loaded = load_config_from_env_file(&config_path).expect("Failed to load config");

        assert_eq!(original.whisper_cli, loaded.whisper_cli);
        assert_eq!(original.model, loaded.model);
        assert_eq!(original.source, loaded.source);
        assert_eq!(original.preferred_sources, loaded.preferred_sources);
        assert_eq!(original.chunk_seconds, loaded.chunk_seconds);
        assert_eq!(original.overlap_seconds, loaded.overlap_seconds);
        assert_eq!(original.type_delay_ms, loaded.type_delay_ms);
        assert_eq!(original.language, loaded.language);
        assert_eq!(original.suppress_regex, loaded.suppress_regex);
        assert_eq!(original.suppress_nst, loaded.suppress_nst);
        assert_eq!(original.smart_punctuation, loaded.smart_punctuation);
        assert_eq!(
            original.symbol_words_to_symbols,
            loaded.symbol_words_to_symbols
        );
        assert_eq!(original.direct_streaming, loaded.direct_streaming);
        assert_eq!(original.log_file, loaded.log_file);
        assert_eq!(original.log_level, loaded.log_level);
        assert_eq!(original.voice_activation_mode, loaded.voice_activation_mode);
        assert_eq!(
            original.post_processing_enabled,
            loaded.post_processing_enabled
        );
        assert_eq!(original.post_processing_mode, loaded.post_processing_mode);
        assert_eq!(
            original.post_processing_trigger,
            loaded.post_processing_trigger
        );
        assert_eq!(original.indicator_enabled, loaded.indicator_enabled);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_env_var_mapping() {
        let temp_dir = std::env::temp_dir().join("whisper_test_mapping");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("mapping.env");

        let env_content = r#"WHISPER_CLI=cli
WHISPER_MODEL=model
WHISPER_AUDIO_SOURCE=source
WHISPER_PREFERRED_SOURCES=pref
WHISPER_CHUNK_SECONDS=1
WHISPER_OVERLAP_SECONDS=2
WHISPER_TYPE_DELAY_MS=3
WHISPER_LANGUAGE=lang
WHISPER_SUPPRESS_REGEX=regex
WHISPER_SUPPRESS_NST=true
WHISPER_SMART_PUNCTUATION=true
WHISPER_SYMBOL_WORDS_TO_SYMBOLS=true
WHISPER_DIRECT_STREAMING=true
WHISPER_LOG_FILE=log
WHISPER_LOG_LEVEL=info
WHISPER_ACTIVATION_MODE=toggle
WHISPER_POST_PROCESSING_ENABLED=true
WHISPER_POST_PROCESSING_MODE=agentic
WHISPER_POST_PROCESSING_TRIGGER=always
WHISPER_INDICATOR=true
"#;

        fs::write(&config_path, env_content).expect("Failed to write env file");

        let config = load_config_from_env_file(&config_path).expect("Failed to load config");

        assert_eq!(config.whisper_cli, "cli");
        assert_eq!(config.model, "model");
        assert_eq!(config.source, "source");
        assert_eq!(config.preferred_sources, "pref");
        assert_eq!(config.chunk_seconds, 1.0);
        assert_eq!(config.overlap_seconds, 2.0);
        assert_eq!(config.type_delay_ms, 3);
        assert_eq!(config.language, "lang");
        assert_eq!(config.suppress_regex, "regex");
        assert_eq!(config.suppress_nst, true);
        assert_eq!(config.smart_punctuation, true);
        assert_eq!(config.symbol_words_to_symbols, true);
        assert_eq!(config.direct_streaming, true);
        assert_eq!(config.log_file, "log");
        assert_eq!(config.log_level, LogLevel::Info);
        assert_eq!(config.voice_activation_mode, VoiceActivationMode::Toggle);
        assert_eq!(config.post_processing_enabled, true);
        assert_eq!(config.post_processing_mode, PostProcessingMode::Agentic);
        assert_eq!(
            config.post_processing_trigger,
            PostProcessingTrigger::Always
        );
        assert_eq!(config.indicator_enabled, true);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_whisper_status_default() {
        let status = WhisperStatus {
            is_running: false,
            pid: None,
            stream_text: String::new(),
        };

        assert_eq!(status.is_running, false);
        assert_eq!(status.pid, None);
        assert_eq!(status.stream_text, "");
    }

    #[test]
    fn test_whisper_status_serialize() {
        let status = WhisperStatus {
            is_running: true,
            pid: Some(12345),
            stream_text: "test output".to_string(),
        };

        let json = serde_json::to_string(&status).expect("Failed to serialize status");

        assert!(json.contains("\"is_running\":true"));
        assert!(json.contains("\"pid\":12345"));
        assert!(json.contains("\"stream_text\":\"test output\""));

        let deserialized: WhisperStatus =
            serde_json::from_str(&json).expect("Failed to deserialize status");

        assert_eq!(deserialized.is_running, true);
        assert_eq!(deserialized.pid, Some(12345));
        assert_eq!(deserialized.stream_text, "test output");
    }

    #[test]
    fn test_config_with_special_characters() {
        let json = r#"{
            "whisper_cli": "whisper-cli-v2.0",
            "model": "/path/with spaces/model.bin",
            "source": "audio-source-with-dashes",
            "preferred_sources": "src with spaces,src2",
            "chunk_seconds": 3.5,
            "overlap_seconds": 0.8,
            "type_delay_ms": 1,
            "language": "中文",
            "suppress_regex": "[\"''']",
            "suppress_nst": true,
            "smart_punctuation": true,
            "symbol_words_to_symbols": false,
            "direct_streaming": false,
            "log_file": "/var/log/whisper hotkey.log",
            "log_level": "info",
            "indicator_enabled": true
        }"#;

        let config: WhisperConfig = serde_json::from_str(json).expect("Failed to deserialize");

        assert_eq!(config.whisper_cli, "whisper-cli-v2.0");
        assert_eq!(config.model, "/path/with spaces/model.bin");
        assert_eq!(config.source, "audio-source-with-dashes");
        assert_eq!(config.preferred_sources, "src with spaces,src2");
        assert_eq!(config.suppress_regex, "[\"''']");
        assert_eq!(config.log_file, "/var/log/whisper hotkey.log");
        assert_eq!(config.language, "中文");
    }

    #[test]
    fn test_config_numeric_fields() {
        let mut config = WhisperConfig {
            whisper_cli: "test".to_string(),
            model: "/test.bin".to_string(),
            ..Default::default()
        };

        config.chunk_seconds = 2.5;
        config.overlap_seconds = 0.3;
        config.type_delay_ms = 500;

        assert_eq!(config.chunk_seconds, 2.5);
        assert_eq!(config.overlap_seconds, 0.3);
        assert_eq!(config.type_delay_ms, 500);

        let json = serde_json::to_string(&config).expect("Failed to serialize");
        let deserialized: WhisperConfig =
            serde_json::from_str(&json).expect("Failed to deserialize");

        assert_eq!(deserialized.chunk_seconds, 2.5);
        assert_eq!(deserialized.overlap_seconds, 0.3);
        assert_eq!(deserialized.type_delay_ms, 500);
    }

    #[test]
    fn test_log_level_display_and_from_str() {
        assert_eq!(LogLevel::Info.to_string(), "info");
        assert_eq!(LogLevel::Debug.to_string(), "debug");

        assert_eq!("info".parse::<LogLevel>().unwrap(), LogLevel::Info);
        assert_eq!("debug".parse::<LogLevel>().unwrap(), LogLevel::Debug);
        assert_eq!("INFO".parse::<LogLevel>().unwrap(), LogLevel::Info);
        assert_eq!("DEBUG".parse::<LogLevel>().unwrap(), LogLevel::Debug);

        assert!("invalid".parse::<LogLevel>().is_err());
    }

    #[test]
    fn test_voice_activation_mode_display() {
        assert_eq!(VoiceActivationMode::Toggle.to_string(), "toggle");
        assert_eq!(VoiceActivationMode::Hold.to_string(), "hold");
    }

    #[test]
    fn test_post_processing_mode_display() {
        assert_eq!(PostProcessingMode::Off.to_string(), "off");
        assert_eq!(PostProcessingMode::Light.to_string(), "light");
        assert_eq!(PostProcessingMode::Aggressive.to_string(), "aggressive");
        assert_eq!(PostProcessingMode::Agentic.to_string(), "agentic");
        assert_eq!(PostProcessingMode::Writing.to_string(), "writing");
        assert_eq!(PostProcessingMode::Code.to_string(), "code");
        assert_eq!(PostProcessingMode::Structure.to_string(), "structure");
        assert_eq!(PostProcessingMode::Persona.to_string(), "persona");
        assert_eq!(PostProcessingMode::Clarity.to_string(), "clarity");
    }

    #[test]
    fn test_post_processing_trigger_display() {
        assert_eq!(PostProcessingTrigger::Always.to_string(), "always");
        assert_eq!(PostProcessingTrigger::Manual.to_string(), "manual");
        assert_eq!(PostProcessingTrigger::AutoLong.to_string(), "auto_long");
        assert_eq!(PostProcessingTrigger::Preview.to_string(), "preview");
    }

    #[test]
    fn test_env_file_with_comments_and_empty_lines() {
        let temp_dir = std::env::temp_dir().join("whisper_test_comments");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("comments.env");

        let env_content = r#"# This is a comment
WHISPER_CLI=test-cli

# Another comment
WHISPER_MODEL=/test/model.bin

WHISPER_LANGUAGE=de

"#;

        fs::write(&config_path, env_content).expect("Failed to write env file");

        let config = load_config_from_env_file(&config_path).expect("Failed to load config");

        assert_eq!(config.whisper_cli, "test-cli");
        assert_eq!(config.model, "/test/model.bin");
        assert_eq!(config.language, "de");

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_env_file_with_whitespace() {
        let temp_dir = std::env::temp_dir().join("whisper_test_whitespace");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("whitespace.env");

        let env_content = "WHISPER_CLI  =  test-cli  \nWHISPER_MODEL=/test/model.bin\n";

        fs::write(&config_path, env_content).expect("Failed to write env file");

        let config = load_config_from_env_file(&config_path).expect("Failed to load config");

        assert_eq!(config.whisper_cli, "test-cli");
        assert_eq!(config.model, "/test/model.bin");

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_update_existing_env_file() {
        let temp_dir = std::env::temp_dir().join("whisper_test_update");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("update.env");

        let initial_content = r#"WHISPER_CLI=old-cli
WHISPER_MODEL=/old/model.bin
WHISPER_LANGUAGE=en
WHISPER_CHUNK_SECONDS=3.5
"#;

        fs::write(&config_path, initial_content).expect("Failed to write initial env file");

        let updated_config = WhisperConfig {
            whisper_cli: "new-cli".to_string(),
            model: "/new/model.bin".to_string(),
            language: "fr".to_string(),
            chunk_seconds: 5.0,
            ..Default::default()
        };

        save_config_to_env_file(&config_path, &updated_config).expect("Failed to update env file");

        let content = fs::read_to_string(&config_path).expect("Failed to read updated env file");

        assert!(content.contains("WHISPER_CLI=new-cli"));
        assert!(content.contains("WHISPER_MODEL=/new/model.bin"));
        assert!(content.contains("WHISPER_LANGUAGE=fr"));
        assert!(content.contains("WHISPER_CHUNK_SECONDS=5"));

        let loaded =
            load_config_from_env_file(&config_path).expect("Failed to load updated config");

        assert_eq!(loaded.whisper_cli, "new-cli");
        assert_eq!(loaded.model, "/new/model.bin");
        assert_eq!(loaded.language, "fr");
        assert_eq!(loaded.chunk_seconds, 5.0);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_env_file_invalid_values_use_defaults() {
        let temp_dir = std::env::temp_dir().join("whisper_test_invalid");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("invalid.env");

        let env_content = r#"WHISPER_CLI=test-cli
WHISPER_MODEL=/test/model.bin
WHISPER_CHUNK_SECONDS=invalid_number
WHISPER_OVERLAP_SECONDS=not_a_float
WHISPER_TYPE_DELAY_MS=NaN
WHISPER_LOG_LEVEL=invalid_level
"#;

        fs::write(&config_path, env_content).expect("Failed to write env file");

        let config = load_config_from_env_file(&config_path).expect("Failed to load config");

        assert_eq!(config.whisper_cli, "test-cli");
        assert_eq!(config.model, "/test/model.bin");
        assert_eq!(config.chunk_seconds, 3.5);
        assert_eq!(config.overlap_seconds, 0.8);
        assert_eq!(config.type_delay_ms, 1);
        assert_eq!(config.log_level, LogLevel::Info);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_audio_source_struct() {
        let source = AudioSource {
            name: "test-source".to_string(),
            description: Some("Test audio source".to_string()),
            is_default: true,
        };

        assert_eq!(source.name, "test-source");
        assert_eq!(source.description, Some("Test audio source".to_string()));
        assert_eq!(source.is_default, true);

        let json = serde_json::to_string(&source).expect("Failed to serialize AudioSource");
        let deserialized: AudioSource =
            serde_json::from_str(&json).expect("Failed to deserialize AudioSource");

        assert_eq!(deserialized.name, "test-source");
        assert_eq!(
            deserialized.description,
            Some("Test audio source".to_string())
        );
        assert_eq!(deserialized.is_default, true);
    }

    #[test]
    fn test_bool_env_parsing() {
        let temp_dir = std::env::temp_dir().join("whisper_test_bool");
        fs::create_dir_all(&temp_dir).expect("Failed to create temp dir");
        let config_path = temp_dir.join("bool.env");

        let env_content = r#"WHISPER_CLI=test-cli
WHISPER_MODEL=/test/model.bin
WHISPER_SUPPRESS_NST=TRUE
WHISPER_SMART_PUNCTUATION=false
WHISPER_SYMBOL_WORDS_TO_SYMBOLS=True
WHISPER_DIRECT_STREAMING=FALSE
WHISPER_POST_PROCESSING_ENABLED=1
WHISPER_INDICATOR=0
"#;

        fs::write(&config_path, env_content).expect("Failed to write env file");

        let config = load_config_from_env_file(&config_path).expect("Failed to load config");

        assert_eq!(config.suppress_nst, true);
        assert_eq!(config.smart_punctuation, false);
        assert_eq!(config.symbol_words_to_symbols, true);
        assert_eq!(config.direct_streaming, false);
        assert_eq!(config.post_processing_enabled, true);
        assert_eq!(config.indicator_enabled, false);

        let _ = fs::remove_dir_all(temp_dir);
    }
}
