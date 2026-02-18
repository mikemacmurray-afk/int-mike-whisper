import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { enable, disable, isEnabled } from "@tauri-apps/plugin-autostart";
import "./App.css";

function SettingsApp() {
    const [hotkey, setHotkey] = useState("Ctrl+Shift+Space");
    const [autostart, setAutostart] = useState(false);
    const [openRouterKey, setOpenRouterKey] = useState("");

    useEffect(() => {
        // Load Settings from Rust
        invoke<string>("get_hotkey").then(setHotkey).catch(console.error);
        invoke<string>("get_setting", { key: "openrouter_key" }).then(setOpenRouterKey).catch(console.error);
        isEnabled().then(setAutostart).catch(console.error);
    }, []);

    const updateHotkey = async () => {
        const newHotkey = prompt("Enter new hotkey (e.g. F1, Ctrl+S):", hotkey);
        if (newHotkey && newHotkey !== hotkey) {
            try {
                await invoke("update_hotkey", { hotkeyStr: newHotkey });
                setHotkey(newHotkey);
            } catch (e) {
                alert(e);
            }
        }
    };

    const updateApiKey = async () => {
        const key = prompt("Enter OpenRouter API Key:", openRouterKey);
        if (key !== null) {
            try {
                await invoke("update_settings", { key: "openrouter_key", value: key });
                setOpenRouterKey(key);
            } catch (e) {
                alert(e);
            }
        }
    };

    const toggleAutostart = async () => {
        try {
            if (autostart) {
                await disable();
            } else {
                await enable();
            }
            setAutostart(!autostart);
        } catch (e) {
            alert("Failed to change autostart: " + e);
        }
    };

    return (
        <main className="container settings-window">
            <div className="status-header">
                <h1>Settings</h1>
            </div>

            <div className="main-card">
                <section className="settings-section">
                    <div className="setting-item">
                        <label>Start at Boot</label>
                        <input
                            type="checkbox"
                            checked={autostart}
                            onChange={toggleAutostart}
                            className="checkbox-custom"
                        />
                    </div>
                    <div className="setting-item">
                        <label>API Key</label>
                        <button className="btn-small" onClick={updateApiKey}>
                            {openRouterKey ? "••••••••" : "Set Key"}
                        </button>
                    </div>
                    <div className="setting-item">
                        <label>Hotkey</label>
                        <div className="hotkey-recorder">
                            <code className="hotkey">{hotkey}</code>
                            <button className="btn-small" onClick={updateHotkey}>Change</button>
                        </div>
                    </div>
                </section>
            </div>

            <footer className="footer-info">
                <p>Settings are saved automatically.</p>
            </footer>
        </main>
    );
}

export default SettingsApp;
