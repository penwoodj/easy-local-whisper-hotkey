use anyhow::{Context, Result};
use chrono::Local;
use dirs::home_dir;
use std::fs::{File, OpenOptions};
use std::path::PathBuf;
use tracing_subscriber::fmt::MakeWriter;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;

const MAX_LOG_LINES: usize = 1000;

pub struct RotatingFileWriter {
    base_path: PathBuf,
    current_file: Option<File>,
    line_count: usize,
}

impl RotatingFileWriter {
    pub fn new(base_path: PathBuf) -> Result<Self> {
        let mut writer = Self {
            base_path,
            current_file: None,
            line_count: 0,
        };

        writer.rotate()?;
        Ok(writer)
    }

    pub fn get_default_log_dir() -> Result<PathBuf> {
        let log_dir = home_dir()
            .ok_or_else(|| anyhow::anyhow!("Cannot determine home directory"))?
            .join(".local/share/whisper-hotkey/logs");

        std::fs::create_dir_all(&log_dir).context("Failed to create log directory")?;

        Ok(log_dir)
    }

    fn rotate(&mut self) -> Result<()> {
        self.line_count = 0;

        let timestamp = Local::now().format("%Y%m%d_%H%M%S");
        let log_path = self.base_path.join(format!("whisper_{}.log", timestamp));

        self.current_file = Some(
            OpenOptions::new()
                .create(true)
                .append(true)
                .open(&log_path)
                .context("Failed to open log file")?,
        );

        log::info!("Rotated to new log file: {}", log_path.display());

        Ok(())
    }

    fn write_line(&mut self, line: &str) -> Result<()> {
        if self.line_count >= MAX_LOG_LINES {
            self.rotate()?;
        }

        if let Some(ref mut file) = self.current_file {
            use std::io::Write;
            writeln!(file, "{}", line).context("Failed to write to log file")?;
            self.line_count += 1;
        }

        Ok(())
    }
}

impl<'a> MakeWriter<'a> for RotatingFileWriter {
    type Writer = Self;

    fn make_writer(&'a self) -> Self::Writer {
        Self {
            base_path: self.base_path.clone(),
            current_file: self.current_file.as_ref().and_then(|f| f.try_clone().ok()),
            line_count: self.line_count,
        }
    }
}

impl std::io::Write for RotatingFileWriter {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        let line = String::from_utf8_lossy(buf);
        if let Err(e) = self.write_line(&line) {
            return Err(std::io::Error::new(std::io::ErrorKind::Other, e));
        }
        Ok(buf.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        if let Some(ref mut file) = self.current_file {
            file.flush()
        } else {
            Ok(())
        }
    }
}

pub fn init_logging(log_level: &str, log_dir: PathBuf) -> Result<()> {
    let level_filter = match log_level.to_lowercase().as_str() {
        "debug" => "debug",
        "info" => "info",
        _ => "info",
    };

    let env_filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(level_filter));

    let file_writer = RotatingFileWriter::new(log_dir.clone())?;

    tracing_subscriber::registry()
        .with(env_filter)
        .with(
            tracing_subscriber::fmt::layer()
                .with_writer(std::io::stdout)
                .with_ansi(cfg!(not(windows))),
        )
        .with(
            tracing_subscriber::fmt::layer()
                .with_writer(file_writer)
                .with_ansi(false)
                .with_target(false),
        )
        .try_init()
        .map_err(|e| anyhow::anyhow!("Failed to init logging: {}", e))?;

    log::info!(
        "Logging initialized. Level: {}, Dir: {}",
        log_level,
        log_dir.display()
    );

    Ok(())
}

pub fn set_log_level(level: &str) -> Result<()> {
    let filter = match level.to_lowercase().as_str() {
        "debug" => "debug",
        "info" => "info",
        _ => return Err(anyhow::anyhow!("Invalid log level: {}", level)),
    };

    let _env_filter = tracing_subscriber::EnvFilter::new(filter);

    tracing::subscriber::set_global_default(tracing_subscriber::Registry::default())
        .map_err(|e| anyhow::anyhow!("Failed to set global subscriber: {}", e))?;

    Ok(())
}
