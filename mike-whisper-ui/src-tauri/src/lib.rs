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
    current_shortcut_cursor: Mutex<Option<Shortcut>>,
    current_shortcut_brain: Mutex<Option<Shortcut>>,
    stderr_lines: Arc<Mutex<Vec<String>>>,
}

fn write_log_file(app: &tauri::AppHandle, message: &str) {
    if let Ok(log_dir) = app.path().app_log_dir() {
        let _ = std::fs::create_dir_all(&log_dir);
        let log_file = log_dir.join("mike-whisper-engine.log");
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_file)
        {
            let timestamp = match std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH) {
                Ok(n) => n.as_secs().to_string(),
                Err(_) => "0".to_string(),
            };
            let _ = writeln!(file, "[{}] {}", timestamp, message);
        }
    }
}

fn spawn_engine(app: &tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<EngineState>();
    let stderr_lines = state.stderr_lines.clone();
    
    write_log_file(app, "Attempting to spawn engine...");
    
    #[cfg(debug_assertions)]
    let mut child = {
        let cwd = std::env::current_dir().unwrap();
        let project_root = cwd.parent().unwrap().parent().unwrap();
        let python_path = project_root.join("venv").join("Scripts").join("python.exe");
        let script_path = project_root.join("src").join("sidecar_main.py");
        
        println!("Starting Python Engine via std::process (DEV): {:?}", script_path);
        write_log_file(app, &format!("DEV Python path: {:?}", python_path));
        write_log_file(app, &format!("DEV Script path: {:?}", script_path));
        
        std::process::Command::new(python_path)
            .arg(script_path)
            .current_dir(project_root)
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to spawn DEV process: {}", e))?
    };

    #[cfg(not(debug_assertions))]
    use tauri_plugin_shell::ShellExt;
    #[cfg(not(debug_assertions))]
    let sidecar_command = app.shell().sidecar("mike-whisper-engine")
        .map_err(|e| format!("Failed to resolve sidecar command: {}", e))?;
    
    #[cfg(not(debug_assertions))]
    let (mut rx, mut child) = sidecar_command
        .spawn()
        .map_err(|e| {
            let err = format!("Failed to spawn release sidecar: {}", e);
            write_log_file(app, &err);
            err
        })?;

    // Set up stdout/stderr reading
    #[cfg(debug_assertions)]
    let (stdout, stderr) = (child.stdout.take().unwrap(), child.stderr.take().unwrap());
    
    #[cfg(debug_assertions)]
    let stdout_reader = std::io::BufReader::new(stdout);
    #[cfg(debug_assertions)]
    let stderr_reader = std::io::BufReader::new(stderr);
    
    #[cfg(debug_assertions)]
    {
        let app_clone = app.clone();
        tauri::async_runtime::spawn(async move {
            use std::io::BufRead;
            let mut lines = stdout_reader.lines();
            while let Some(line) = lines.next() {
                if let Ok(l) = line {
                    write_log_file(&app_clone, &format!("Stdout: {}", l));
                    let _ = app_clone.emit("sidecar-event", &l);
                    if l.contains("PARTIAL_RESULT") || l.contains("RESULT") || l.contains("STATUS") {
                        let _ = app_clone.emit_to("overlay", "overlay-event", &l);
                    }
                }
            }
        });

        let app_clone_err = app.clone();
        let stderr_lines_clone = stderr_lines.clone();
        tauri::async_runtime::spawn(async move {
            use std::io::BufRead;
            let mut lines = stderr_reader.lines();
            while let Some(line) = lines.next() {
                if let Ok(l) = line {
                    write_log_file(&app_clone_err, &format!("Stderr: {}", l));
                    let mut err_lock = stderr_lines_clone.lock().unwrap();
                    err_lock.push(l.clone());
                    if err_lock.len() > 20 { err_lock.remove(0); }
                    let _ = app_clone_err.emit("sidecar-event", format!("{{\"type\": \"LOG\", \"data\": \"{}\"}}", l));
                }
            }
        });
    }

    #[cfg(not(debug_assertions))]
    {
        let app_clone = app.clone();
        let stderr_lines_clone = stderr_lines.clone();
        tauri::async_runtime::spawn(async move {
            use tauri_plugin_shell::process::CommandEvent;
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(line) => {
                        if let Ok(l) = String::from_utf8(line) {
                            write_log_file(&app_clone, &format!("Stdout: {}", l));
                            let _ = app_clone.emit("sidecar-event", &l);
                            if l.contains("PARTIAL_RESULT") || l.contains("RESULT") || l.contains("STATUS") {
                                    let _ = app_clone.emit_to("overlay", "overlay-event", &l);
                            }
                        }
                    }
                    CommandEvent::Stderr(line) => {
                        if let Ok(l) = String::from_utf8(line) {
                            write_log_file(&app_clone, &format!("Stderr: {}", l));
                            let mut err_lock = stderr_lines_clone.lock().unwrap();
                            err_lock.push(l.clone());
                            if err_lock.len() > 20 { err_lock.remove(0); }
                            let _ = app_clone.emit("sidecar-event", format!("{{\"type\": \"LOG\", \"data\": \"{}\"}}", l));
                        }
                    }
                    CommandEvent::Terminated(payload) => {
                        let last_errors = {
                            let lines = stderr_lines_clone.lock().unwrap();
                            lines.join("\n")
                        };
                        let err_msg = format!(
                            "Engine exited unexpectedly (code: {:?}).\n{}",
                            payload.code, last_errors
                        );
                        write_log_file(&app_clone, &err_msg);
                        let _ = app_clone.emit("sidecar-event", format!(
                            "{{\"type\": \"ERROR\", \"data\": {}}}",
                            serde_json::to_string(&err_msg).unwrap()
                        ));
                    }
                    _ => {}
                }
            }
        });
    }

    // Store child handle
    #[cfg(debug_assertions)]
    { *state.child.lock().unwrap() = Some(EngineChild::Std(child)); }
    #[cfg(not(debug_assertions))]
    { *state.child.lock().unwrap() = Some(EngineChild::Sidecar(child)); }
    
    // Sync initial config
    sync_sidecar_config(app);
    
    Ok(())
}

#[tauri::command]
async fn restart_engine(app: AppHandle) -> Result<(), String> {
    write_log_file(&app, "Restart engine command invoked.");
    // 1. Kill old engine if any is stored
    {
        let state = app.state::<EngineState>();
        let mut child_lock = state.child.lock().unwrap();
        if let Some(child) = child_lock.take() {
            match child {
                EngineChild::Std(mut c) => { let _ = c.kill(); }
                EngineChild::Sidecar(c) => { let _ = c.kill(); }
            }
        }
    }
    
    // Clear stderr lines
    {
        let state = app.state::<EngineState>();
        state.stderr_lines.lock().unwrap().clear();
    }
    
    // 2. Spawn new engine
    spawn_engine(&app)?;
    
    Ok(())
}

impl EngineChild {
    fn stdin_write(&mut self, data: &[u8]) -> std::io::Result<()> {
        match self {
            EngineChild::Std(child) => {
                if let Some(stdin) = child.stdin.as_mut() {
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
    get_hotkey_cursor(app)
}

#[tauri::command]
fn get_hotkey_cursor(app: AppHandle) -> String {
    let state = app.state::<EngineState>();
    let lock = state.current_shortcut_cursor.lock().unwrap();
    lock.as_ref()
        .map(|s| s.to_string())
        .unwrap_or_else(|| "Ctrl+Space".to_string())
}

#[tauri::command]
fn get_hotkey_brain(app: AppHandle) -> String {
    let state = app.state::<EngineState>();
    let lock = state.current_shortcut_brain.lock().unwrap();
    lock.as_ref()
        .map(|s| s.to_string())
        .unwrap_or_else(|| "Ctrl+Alt+Space".to_string())
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
        .inner_size(440.0, 560.0)
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
            let vocabulary = store.get("custom_vocabulary")
                .and_then(|v| v.as_str().map(|s| s.to_string()))
                .unwrap_or_else(|| "".to_string());
            let model_size = store.get("model_size")
                .and_then(|v| v.as_str().map(|s| s.to_string()))
                .unwrap_or_else(|| "base.en".to_string());
            
            let config_cmd = serde_json::json!({
                "type": "SET_CONFIG",
                "data": {
                    "api_key": api_key,
                    "mode": mode,
                    "vocabulary": vocabulary,
                    "model_size": model_size
                }
            });
            
            let _ = child.stdin_write(format!("{}\n", config_cmd.to_string()).as_bytes());
        }
    }
}

#[tauri::command]
async fn update_hotkey(app: AppHandle, hotkey_str: String) -> Result<(), String> {
    update_hotkey_cursor(app, hotkey_str).await
}

#[tauri::command]
async fn update_hotkey_cursor(app: AppHandle, hotkey_str: String) -> Result<(), String> {
    use tauri_plugin_store::StoreExt;

    let state = app.state::<EngineState>();
    let shortcut = Shortcut::from_str(&hotkey_str)
        .map_err(|e| format!("Invalid hotkey format: {}", e))?;

    let global_shortcut = app.global_shortcut();
    let mut current_lock = state.current_shortcut_cursor.lock().unwrap();
    if let Some(old_shortcut) = current_lock.take() {
        let _ = global_shortcut.unregister(old_shortcut);
    }

    global_shortcut.register(shortcut)
        .map_err(|e| format!("Failed to register hotkey: {}", e))?;
    
    *current_lock = Some(shortcut);
    
    let store = app.store("settings.json")
        .map_err(|e| e.to_string())?;
    store.set("hotkey", serde_json::json!(hotkey_str.clone()));
    store.set("hotkey_cursor", serde_json::json!(hotkey_str));
    store.save().map_err(|e| e.to_string())?;
    
    Ok(())
}

#[tauri::command]
async fn update_hotkey_brain(app: AppHandle, hotkey_str: String) -> Result<(), String> {
    use tauri_plugin_store::StoreExt;

    let state = app.state::<EngineState>();
    let shortcut = Shortcut::from_str(&hotkey_str)
        .map_err(|e| format!("Invalid brain hotkey format: {}", e))?;

    let global_shortcut = app.global_shortcut();
    let mut current_lock = state.current_shortcut_brain.lock().unwrap();
    if let Some(old_shortcut) = current_lock.take() {
        let _ = global_shortcut.unregister(old_shortcut);
    }

    global_shortcut.register(shortcut)
        .map_err(|e| format!("Failed to register brain hotkey: {}", e))?;
    
    *current_lock = Some(shortcut);
    
    let store = app.store("settings.json")
        .map_err(|e| e.to_string())?;
    store.set("hotkey_brain", serde_json::json!(hotkey_str));
    store.save().map_err(|e| e.to_string())?;
    
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let engine_state = EngineState {
        child: Arc::new(Mutex::new(None)),
        current_shortcut_cursor: Mutex::new(None),
        current_shortcut_brain: Mutex::new(None),
        stderr_lines: Arc::new(Mutex::new(Vec::new())),
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
                    let cursor_lock = engine_state.current_shortcut_cursor.lock().unwrap();
                    let brain_lock = engine_state.current_shortcut_brain.lock().unwrap();
                    
                    let is_cursor = Some(shortcut) == cursor_lock.as_ref();
                    let is_brain = Some(shortcut) == brain_lock.as_ref();

                    if is_cursor || is_brain {
                        println!("Hotkey triggered (mode: {}): {:?}", if is_brain { "brain" } else { "cursor" }, event.state());
                        let mut child_lock = engine_state.child.lock().unwrap();
                        
                        if let Some(child) = child_lock.as_mut() {
                            match event.state() {
                                ShortcutState::Pressed => {
                                    let cmd: &[u8] = if is_brain { b"START_RECORDING_BRAIN\n" } else { b"START_RECORDING\n" };
                                    println!("Sending command to sidecar: {:?}", std::str::from_utf8(cmd).unwrap().trim());
                                    let _ = child.stdin_write(cmd);
                                    let _ = app.emit("sidecar-event", "{\"type\": \"STATUS\", \"data\": \"RECORDING\"}");
                                }
                                ShortcutState::Released => {
                                    let cmd: &[u8] = if is_brain { b"STOP_RECORDING_BRAIN\n" } else { b"STOP_RECORDING\n" };
                                    println!("Sending command to sidecar: {:?}", std::str::from_utf8(cmd).unwrap().trim());
                                    let _ = child.stdin_write(cmd);
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

            // Load shortcuts from store
            let hotkey_cursor_str = if let Ok(store) = app.store("settings.json") {
                store.get("hotkey_cursor")
                    .or_else(|| store.get("hotkey"))
                    .and_then(|v| v.as_str().map(|s| s.to_string()))
                    .unwrap_or_else(|| "Ctrl+Space".to_string())
            } else {
                "Ctrl+Space".to_string()
            };

            let hotkey_brain_str = if let Ok(store) = app.store("settings.json") {
                store.get("hotkey_brain")
                    .and_then(|v| v.as_str().map(|s| s.to_string()))
                    .unwrap_or_else(|| "Ctrl+Alt+Space".to_string())
            } else {
                "Ctrl+Alt+Space".to_string()
            };

            println!("Registering Cursor hotkey: {}", hotkey_cursor_str);
            let shortcut_cursor = match Shortcut::from_str(&hotkey_cursor_str) {
                Ok(s) => s,
                Err(_) => Shortcut::from_str("Ctrl+Space").unwrap_or_else(|_| Shortcut::from_str("F2").unwrap()),
            };
            if let Err(e) = app.global_shortcut().register(shortcut_cursor) {
                let _ = app.emit("sidecar-event", format!("{{\"type\": \"ERROR\", \"data\": \"Cursor hotkey registration failed: {}\"}}", e));
                eprintln!("Failed to register cursor hotkey {}: {}", hotkey_cursor_str, e);
            } else {
                *app.state::<EngineState>().current_shortcut_cursor.lock().unwrap() = Some(shortcut_cursor);
            }

            println!("Registering Daily Brain hotkey: {}", hotkey_brain_str);
            let shortcut_brain = match Shortcut::from_str(&hotkey_brain_str) {
                Ok(s) => s,
                Err(_) => Shortcut::from_str("Ctrl+Alt+Space").unwrap_or_else(|_| Shortcut::from_str("F3").unwrap()),
            };
            if let Err(e) = app.global_shortcut().register(shortcut_brain) {
                let _ = app.emit("sidecar-event", format!("{{\"type\": \"ERROR\", \"data\": \"Brain hotkey registration failed: {}\"}}", e));
                eprintln!("Failed to register brain hotkey {}: {}", hotkey_brain_str, e);
            } else {
                *app.state::<EngineState>().current_shortcut_brain.lock().unwrap() = Some(shortcut_brain);
            }

            // Spawn AI Engine
            spawn_engine(app.handle()).map_err(|e| Box::new(std::io::Error::new(std::io::ErrorKind::Other, e)))?;

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
            get_hotkey_cursor,
            get_hotkey_brain,
            update_hotkey, 
            update_hotkey_cursor,
            update_hotkey_brain,
            get_setting, 
            update_settings, 
            ping_sidecar, 
            force_record_start, 
            force_record_stop,
            open_settings_window,
            restart_engine
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
