use tauri::{Manager, Emitter};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
use tauri_plugin_shell::ShellExt;
use std::sync::{Arc, Mutex};

struct EngineState {
    child: Arc<Mutex<Option<tauri_plugin_shell::process::CommandChild>>>,
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let ctrl_shift_space = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::Space);
    
    let engine_state = EngineState {
        child: Arc::new(Mutex::new(None)),
    };

    tauri::Builder::default()
        .manage(engine_state)
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(move |app, shortcut, event| {
                    if shortcut == &ctrl_shift_space {
                        let state = app.state::<EngineState>();
                        let mut child_lock = state.child.lock().unwrap();
                        
                        if let Some(child) = child_lock.as_mut() {
                            match event.state() {
                                ShortcutState::Pressed => {
                                    println!("Hotkey Pressed - Starting Record");
                                    let _ = child.write(b"START_RECORDING\n");
                                }
                                ShortcutState::Released => {
                                    println!("Hotkey Released - Stopping Record");
                                    let _ = child.write(b"STOP_RECORDING\n");
                                }
                            }
                        }
                    }
                })
                .build(),
        )
        .setup(move |app| {
            app.global_shortcut().register(ctrl_shift_space)?;

            // Spawn Sidecar
            let shell = app.shell();
            let sidecar_command = shell.sidecar("mike-whisper-engine")
                .map_err(|e| tauri::Error::Io(std::io::Error::new(std::io::ErrorKind::Other, e.to_string())))?;
            
            let (mut rx, child) = sidecar_command.spawn()
                .map_err(|e| tauri::Error::Io(std::io::Error::new(std::io::ErrorKind::Other, e.to_string())))?;

            // Store child handle
            let state = app.state::<EngineState>();
            *state.child.lock().unwrap() = Some(child);

            // Listen to sidecar events
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            let text = String::from_utf8_lossy(&line);
                            println!("Sidecar: {}", text);
                            // Emit to frontend
                            let _ = app_handle.emit("sidecar-event", text.to_string());
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("Sidecar Error: {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Error(err) => {
                            eprintln!("Sidecar Critical Error: {}", err);
                        }
                        CommandEvent::Terminated(payload) => {
                            println!("Sidecar terminated: {:?}", payload);
                        }
                        _ => {}
                    }
                }
            });

            // Setup Tray Menu
            let quit_i = tauri::menu::MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let settings_i = tauri::menu::MenuItem::with_id(app, "settings", "Settings", true, None::<&str>)?;
            let restart_i = tauri::menu::MenuItem::with_id(app, "restart", "Restart Engine", true, None::<&str>)?;
            
            let menu = tauri::menu::Menu::with_items(app, &[&settings_i, &restart_i, &quit_i])?;

            // Setup Tray Icon
            let _ = tauri::tray::TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .show_menu_on_left_click(false)
                .tooltip("MikeWhisper")
                .on_menu_event(|app: &tauri::AppHandle, event| {
                    if event.id == "quit" {
                        app.exit(0);
                    } else if event.id == "settings" {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    } else if event.id == "restart" {
                        println!("Restarting engine...");
                    }
                })
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
