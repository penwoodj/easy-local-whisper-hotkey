mod commands;

use commands::*;
use tauri::Manager;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }))
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
        .setup(|app| {
            log::debug!("Easy Local Whisper Hotkey starting up...");
            log::debug!("Setup: app handle = {:?}", app.handle());

            #[cfg(not(debug_assertions))]
            {
                use tauri_plugin_autostart::ManagerExt;
                match app.autolaunch().is_enabled() {
                    Ok(false) => {
                        log::debug!("Autostart not enabled, enabling...");
                        if let Err(e) = app.autolaunch().enable() {
                            log::error!("Failed to enable autostart: {}", e);
                        } else {
                            log::debug!("Autostart enabled successfully");
                        }
                    }
                    Ok(true) => log::debug!("Autostart already enabled"),
                    Err(e) => log::error!("Failed to check autostart status: {}", e),
                }
            }
            #[cfg(debug_assertions)]
            log::debug!("Skipping autostart setup in debug mode");

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            get_config,
            set_config,
            get_status,
            start_daemon,
            stop_daemon,
            list_sources,
            get_diagnostics,
            enable_autostart,
            is_autostart_enabled,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
