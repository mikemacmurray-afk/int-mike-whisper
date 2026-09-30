import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { enable, disable, isEnabled } from "@tauri-apps/plugin-autostart";
import "./App.css";

function SettingsApp() {
    const [hotkeyCursor, setHotkeyCursor] = useState("control+Space");
    const [hotkeyBrain, setHotkeyBrain] = useState("Fn+Space");
    const [editingA, setEditingA] = useState(false);
    const [editingB, setEditingB] = useState(false);
    const [tempA, setTempA] = useState("");
    const [tempB, setTempB] = useState("");
    const [autostart, setAutostart] = useState(false);
    const [openRouterKey, setOpenRouterKey] = useState("");
    const [vocabulary, setVocabulary] = useState("");
    const [modelSize, setModelSize] = useState("base.en");

    useEffect(() => {
        // Load Settings from Rust
        invoke<string>("get_hotkey_cursor")
            .then(setHotkeyCursor)
            .catch(() => {
                invoke<string>("get_hotkey").then(setHotkeyCursor).catch(console.error);
            });
        invoke<string>("get_hotkey_brain").then(setHotkeyBrain).catch(console.error);
        invoke<string>("get_setting", { key: "openrouter_key" }).then(setOpenRouterKey).catch(console.error);
        invoke<string>("get_setting", { key: "custom_vocabulary" }).then(setVocabulary).catch(console.error);
        invoke<string>("get_setting", { key: "model_size" }).then((m) => setModelSize(m || "base.en")).catch(console.error);
        isEnabled().then(setAutostart).catch(console.error);
    }, []);

    const updateModelSize = async (newModel: string) => {
        try {
            await invoke("update_settings", { key: "model_size", value: newModel });
            setModelSize(newModel);
        } catch (e) {
            alert("Failed to update model: " + e);
        }
    };

    const saveCursorHotkey = async () => {
        const trimmed = tempA.trim();
        if (!trimmed) {
            setEditingA(false);
            return;
        }
        try {
            await invoke("update_hotkey_cursor", { hotkeyStr: trimmed });
            setHotkeyCursor(trimmed);
            setEditingA(false);
        } catch (e) {
            alert(e);
        }
    };

    const saveBrainHotkey = async () => {
        const trimmed = tempB.trim();
        if (!trimmed) {
            setEditingB(false);
            return;
        }
        try {
            await invoke("update_hotkey_brain", { hotkeyStr: trimmed });
            setHotkeyBrain(trimmed);
            setEditingB(false);
        } catch (e) {
            alert(e);
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

    const saveVocabulary = async () => {
        try {
            await invoke("update_settings", { key: "custom_vocabulary", value: vocabulary });
        } catch (e) {
            console.error("Failed to save vocabulary:", e);
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
                        <label>Hotkey A</label>
                        <div className="hotkey-recorder">
                            {editingA ? (
                                <>
                                    <input
                                        type="text"
                                        className="hotkey-input"
                                        value={tempA}
                                        onChange={(e) => setTempA(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") saveCursorHotkey();
                                            if (e.key === "Escape") setEditingA(false);
                                        }}
                                        placeholder="e.g. control+Space"
                                        autoFocus
                                    />
                                    <button className="btn-small btn-save" onClick={saveCursorHotkey}>Save</button>
                                    <button className="btn-small" onClick={() => setEditingA(false)}>Cancel</button>
                                </>
                            ) : (
                                <>
                                    <code className="hotkey">{hotkeyCursor}</code>
                                    <button className="btn-small" onClick={() => { setTempA(hotkeyCursor); setEditingA(true); }}>Change</button>
                                </>
                            )}
                        </div>
                    </div>
                    <div className="setting-item">
                        <label>Hotkey B</label>
                        <div className="hotkey-recorder">
                            {editingB ? (
                                <>
                                    <input
                                        type="text"
                                        className="hotkey-input"
                                        value={tempB}
                                        onChange={(e) => setTempB(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") saveBrainHotkey();
                                            if (e.key === "Escape") setEditingB(false);
                                        }}
                                        placeholder="e.g. Fn+Space"
                                        autoFocus
                                    />
                                    <button className="btn-small btn-save" onClick={saveBrainHotkey}>Save</button>
                                    <button className="btn-small" onClick={() => setEditingB(false)}>Cancel</button>
                                </>
                            ) : (
                                <>
                                    <code className="hotkey">{hotkeyBrain}</code>
                                    <button className="btn-small" onClick={() => { setTempB(hotkeyBrain); setEditingB(true); }}>Change</button>
                                </>
                            )}
                        </div>
                    </div>
                    <div className="setting-item">
                        <label>Speech Model</label>
                        <select 
                            value={modelSize} 
                            onChange={(e) => updateModelSize(e.target.value)}
                        >
                            <option value="tiny.en">Tiny (Fastest, low accuracy)</option>
                            <option value="base.en">Base (Fast, normal accuracy)</option>
                            <option value="Systran/faster-distil-whisper-small.en">Distil Small (Very Fast, high accuracy)</option>
                            <option value="small.en">Small (Moderate, high accuracy)</option>
                            <option value="Systran/faster-distil-whisper-medium.en">Distil Medium (Fast, very high accuracy)</option>
                        </select>
                    </div>
                    <div className="setting-item-block">
                        <label>Custom Vocabulary</label>
                        <textarea
                            className="vocab-textarea"
                            placeholder="Enter names, technical terms, or phrases (comma separated)..."
                            value={vocabulary}
                            onChange={(e) => setVocabulary(e.target.value)}
                            onBlur={saveVocabulary}
                        />
                        <p className="hint-text">Whisper will prioritize these words during transcription.</p>
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
