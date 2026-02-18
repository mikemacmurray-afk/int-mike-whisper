use tauri::{Manager, Emitter, AppHandle};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

use tauri_plugin_autostart::MacosLauncher;
use std::sync::{Arc, Mutex};
use std::str::FromStr;
use std::io::Write;

enum EngineChild {
    Std(std::process::Child),
    Sidecar(tauri_plugin_shell::process::CommandChild),
}

struct EngineState {
    child: Arc<Mutex<Option<EngineChild>>>,
    current_shortcut: Mutex<Option<Shortcut>>,
}

impl EngineChild {
    fn stdin_write(&mut self, data: &[u8]) -> std::io::Result<()> {
        match self {
            EngineChild::Std(child) => {
                if let Some(mut stdin) = child.stdin.as_mut() {
                    stdin.write_all(data)?;
                    stdin.flush()?;
                }
                Ok(())
            }
            EngineChild::Sidecar(child) => {
                child.write(data).map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))
            }
        }
    }
}

#[tauri::command]
fn ping_sidecar(app: AppHandle) {
    let state = app.state::<EngineState>();
    let mut child_lock = state.child.lock().unwrap();
    if let Some(child) = child_lock.as_mut() {
        let _ = child.stdin_write(b"PING\n");
    }
}

#[tauri::command]
fn force_record_start(app: AppHandle) {
    let state = app.state::<EngineState>();
    let mut child_lock = state.child.lock().unwrap();
    if let Some(child) = child_lock.as_mut() {
        let _ = child.stdin_write(b"START_RECORDING\n");
    }
}

#[tauri::command]
fn force_record_stop(app: AppHandle) {
    let state = app.state::<EngineState>();
    let mut child_lock = state.child.lock().unwrap();
    if let Some(child) = child_lock.as_mut() {
        let _ = child.stdin_write(b"STOP_RECORDING\n");
    }
}

#[tauri::command]
fn get_hotkey(app: AppHandle) -> String {
    let state = app.state::<EngineState>();
    let lock = state.current_shortcut.lock().unwrap();
    lock.as_ref()
        .map(|s| s.to_string())
        .unwrap_or_else(|| "Ctrl+Shift+Space".to_string())
}

#[tauri::command]
async fn open_settings_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("settings") {
        let _ = window.show();
        let _ = window.set_focus();
    } else {
        let _window = tauri::WebviewWindowBuilder::new(
            &app,
            "settings",
            tauri::WebviewUrl::App("settings.html".into())
        )
        .title("MikeWhisper Settings")
        .inner_size(400.0, 500.0)
        .resizable(false)
        .build()
        .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn get_setting(app: AppHandle, key: String) -> String {
    use tauri_plugin_store::StoreExt;
    if let Ok(store) = app.store("settings.json") {
        store.get(key)
            .and_then(|v| v.as_str().map(|s| s.to_string()))
            .unwrap_or_else(|| "".to_string())
    } else {
        "".to_string()
    }
}

#[tauri::command]
async fn update_settings(app: AppHandle, key: String, value: String) -> Result<(), String> {
    use tauri_plugin_store::StoreExt;
    let store = app.store("settings.json")
        .map_err(|e| e.to_string())?;
    store.set(key.clone(), serde_json::json!(value));
    store.save().map_err(|e| e.to_string())?;
    
    // Sync with sidecar
    sync_sidecar_config(&app);
    
    Ok(())
}

fn sync_sidecar_config(app: &AppHandle) {
    use tauri_plugin_store::StoreExt;
    let state = app.state::<EngineState>();
    let mut child_lock = state.child.lock().unwrap();
    
    if let Some(child) = child_lock.as_mut() {
        if let Ok(store) = app.store("settings.json") {
            let api_key = store.get("openrouter_key")
                .and_then(|v| v.as_str().map(|s| s.to_string()))
                .unwrap_or_else(|| "".to_string());
            let mode = store.get("ai_mode")
                .and_then(|v| v.as_str().map(|s| s.to_string()))
                .unwrap_or_else(|| "raw".to_string());
            
            let config_cmd = serde_json::json!({
                "type": "SET_CONFIG",
                "data": {
                    "api_key": api_key,
                    "mode": mode
                }
            });
            
            let _ = child.stdin_write(format!("{}\n", config_cmd.to_string()).as_bytes());
        }
    }
}

#[tauri::command]
async fn update_hotkey(app: AppHandle, hotkey_str: String) -> Result<(), String> {
    use tauri_plugin_store::StoreExt;

    let state = app.state::<EngineState>();
    
    // Parse shortcut
    let shortcut = Shortcut::from_str(&hotkey_str)
        .map_err(|e| format!("Invalid hotkey format: {}", e))?;

    let global_shortcut = app.global_shortcut();
    
    // Unregister old shortcut
    let mut current_lock = state.current_shortcut.lock().unwrap();
    if let Some(old_shortcut) = current_lock.take() {
        let _ = global_shortcut.unregister(old_shortcut);
    }

    // Register new shortcut
    global_shortcut.register(shortcut)
        .map_err(|e| format!("Failed to register hotkey: {}", e))?;
    
    *current_lock = Some(shortcut);
    
    // Save to store
    let store = app.store("settings.json")
        .map_err(|e| e.to_string())?;
    store.set("hotkey", serde_json::json!(hotkey_str));
    store.save().map_err(|e| e.to_string())?;
    
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let engine_state = EngineState {
        child: Arc::new(Mutex::new(None)),
        current_shortcut: Mutex::new(None),
    };

    tauri::Builder::default()
        .manage(engine_state)
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, Some(vec!["--minimized"])))
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(move |app, shortcut, event| {
                    let engine_state = app.state::<EngineState>();
                    let current_lock = engine_state.current_shortcut.lock().unwrap();
                    
                    if Some(shortcut) == current_lock.as_ref() {
                        println!("Hotkey triggered: {:?}", event.state());
                        let mut child_lock = engine_state.child.lock().unwrap();
                        
                        if let Some(child) = child_lock.as_mut() {
                            match event.state() {
                                ShortcutState::Pressed => {
                                    println!("Sending command to sidecar: START_RECORDING");
                                    let _ = child.stdin_write(b"START_RECORDING\n");
                                    let _ = app.emit("sidecar-event", "{\"type\": \"STATUS\", \"data\": \"RECORDING\"}");
                                }
                                ShortcutState::Released => {
                                    println!("Sending command to sidecar: STOP_RECORDING");
                                    let _ = child.stdin_write(b"STOP_RECORDING\n");
                                }
                            }
                        } else {
                            println!("Sidecar NOT FOUND when hotkey triggered!");
                        }
                    }
                })
                .build(),
        )
        .setup(move |app| {
            use tauri_plugin_store::StoreExt;
            
            // Handle "Hide to Tray" on close
            let main_window = app.get_webview_window("main").unwrap();
            let main_window_clone = main_window.clone();
            main_window.on_window_event(move |event| {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let _ = main_window_clone.hide();
                }
            });

            // Load shortcut from store
            let hotkey_str = if let Ok(store) = app.store("settings.json") {
                store.get("hotkey")
                    .and_then(|v| v.as_str().map(|s| s.to_string()))
                    .unwrap_or_else(|| "Ctrl+Shift+Space".to_string())
            } else {
                "Ctrl+Shift+Space".to_string()
            };

            println!("Registering hotkey: {}", hotkey_str);
            let shortcut = match Shortcut::from_str(&hotkey_str) {
                Ok(s) => s,
                Err(_) => Shortcut::from_str("F2").unwrap_or_else(|_| Shortcut::from_str("Ctrl+Shift+Space").unwrap()),
            };
            if let Err(e) = app.global_shortcut().register(shortcut) {
                let _ = app.emit("sidecar-event", format!("{{\"type\": \"ERROR\", \"data\": \"Hotkey registration failed: {}\"}}", e));
                eprintln!("Failed to register hotkey {}: {}", hotkey_str, e);
            }
            *app.state::<EngineState>().current_shortcut.lock().unwrap() = Some(shortcut);

            // Spawn AI Engine
            #[cfg(debug_assertions)]
            let (python_path, script_path, project_root) = {
                let cwd = std::env::current_dir().unwrap();
                let project_root = cwd.parent().unwrap().parent().unwrap();
                let python_path = project_root.join("venv").join("Scripts").join("python.exe");
                let script_path = project_root.join("src").join("sidecar_main.py");
                (python_path, script_path, project_root.to_path_buf())
            };

            #[cfg(debug_assertions)]
            println!("Starting Python Engine via std::process (DEV): {:?}", script_path);
            
            #[cfg(debug_assertions)]
            let mut child = std::process::Command::new(python_path)
                .arg(script_path)
                .current_dir(project_root)
                .stdin(std::process::Stdio::piped())
                .stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::piped())
                .spawn()
                .map_err(|e| Box::new(e))?;

            #[cfg(not(debug_assertions))]
            use tauri_plugin_shell::ShellExt;
            #[cfg(not(debug_assertions))]
            let sidecar_command = app.shell().sidecar("mike-whisper-engine")
                .map_err(|e| Box::new(std::io::Error::new(std::io::ErrorKind::Other, e.to_string())))?;
            
            #[cfg(not(debug_assertions))]
            let (mut rx, mut child) = sidecar_command
                .spawn()
                .map_err(|e| Box::new(std::io::Error::new(std::io::ErrorKind::Other, e.to_string())))?;

            #[cfg(debug_assertions)]
            let (stdout, stderr) = (child.stdout.take().unwrap(), child.stderr.take().unwrap());
            
            #[cfg(debug_assertions)]
            let stdout_reader = std::io::BufReader::new(stdout);
            #[cfg(debug_assertions)]
            let stderr_reader = std::io::BufReader::new(stderr);
            
            #[cfg(debug_assertions)]
            {
                let app_clone = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    use std::io::BufRead;
                    let mut lines = stdout_reader.lines();
                    while let Some(line) = lines.next() {
                        if let Ok(l) = line {
                            let _ = app_clone.emit("sidecar-event", &l);
                            if l.contains("PARTIAL_RESULT") || l.contains("RESULT") || l.contains("STATUS") {
                                let _ = app_clone.emit_to("overlay", "overlay-event", &l);
                            }
                        }
                    }
                });

                let app_clone_err = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    use std::io::BufRead;
                    let mut lines = stderr_reader.lines();
                    while let Some(line) = lines.next() {
                        if let Ok(l) = line {
                            eprintln!("Sidecar Stderr: {}", l);
                            let _ = app_clone_err.emit("sidecar-event", format!("{{\"type\": \"LOG\", \"data\": \"{}\"}}", l));
                        }
                    }
                });
            }

            #[cfg(not(debug_assertions))]
            {
                let app_clone = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    use tauri_plugin_shell::process::CommandEvent;
                    while let Some(event) = rx.recv().await {
                        match event {
                            CommandEvent::Stdout(line) => {
                                if let Ok(l) = String::from_utf8(line) {
                                    let _ = app_clone.emit("sidecar-event", &l);
                                    if l.contains("PARTIAL_RESULT") || l.contains("RESULT") || l.contains("STATUS") {
                                        let _ = app_clone.emit_to("overlay", "overlay-event", &l);
                                    }
                                }
                            }
                            CommandEvent::Stderr(line) => {
                                if let Ok(l) = String::from_utf8(line) {
                                    eprintln!("Sidecar Stderr: {}", l);
                                    let _ = app_clone.emit("sidecar-event", format!("{{\"type\": \"LOG\", \"data\": \"{}\"}}", l));
                                }
                            }
                            _ => {}
                        }
                    }
                });
            }

            // Store child handle
            let state = app.state::<EngineState>();
            #[cfg(debug_assertions)]
            { *state.child.lock().unwrap() = Some(EngineChild::Std(child)); }
            #[cfg(not(debug_assertions))]
            { *state.child.lock().unwrap() = Some(EngineChild::Sidecar(child)); }
            
            // Sync initial config
            sync_sidecar_config(app.handle());

            // Create Overlay Window
            let _overlay_window = tauri::WebviewWindowBuilder::new(
                app,
                "overlay",
                tauri::WebviewUrl::App("overlay.html".into())
            )
            .title("MikeWhisper Overlay")
            .inner_size(600.0, 100.0)
            .resizable(false)
            .fullscreen(false)
            .decorations(false)
            .transparent(true)
            .always_on_top(true)
            .visible(false)
            .build()?;
            
            #[cfg(target_os = "windows")]
            {
                let overlay = app.get_webview_window("overlay").unwrap();
                let _ = overlay.set_ignore_cursor_events(true);
            }



            // Setup Tray
            let quit_i = tauri::menu::MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let settings_i = tauri::menu::MenuItem::with_id(app, "settings", "Settings", true, None::<&str>)?;
            let menu = tauri::menu::Menu::with_items(app, &[&settings_i, &quit_i])?;

            let _ = tauri::tray::TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| {
                    if event.id == "quit" { app.exit(0); }
                    else if event.id == "settings" {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_hotkey, 
            update_hotkey, 
            get_setting, 
            update_settings, 
            ping_sidecar, 
            force_record_start, 
            force_record_stop,
            open_settings_window
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
