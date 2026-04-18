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

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum LogLevel {
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

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
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

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
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

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
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
