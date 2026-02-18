import { useState, useEffect } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";

import "./App.css";

type SidecarStatus = "IDLE" | "RECORDING" | "PROCESSING" | "READY" | "ERROR" | "NO_SPEECH";

interface SidecarEvent {
  type: string;
  data?: any;
}

interface HistoryItem {
  id: string;
  text: string;
  timestamp: number;
}

function App() {
  const [status, setStatus] = useState<SidecarStatus>("IDLE");
  const [lastText, setLastText] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [aiMode, setAiMode] = useState("raw");
  const [error, setError] = useState("");

  const updateAiMode = async (mode: string) => {
    try {
      await invoke("update_settings", { key: "ai_mode", value: mode });
      setAiMode(mode);
    } catch (e) {
      alert(e);
    }
  };

  useEffect(() => {
    // Load history from localStorage
    const savedHistory = localStorage.getItem("mike-whisper-history");
    if (savedHistory) {
      try {
        setHistory(JSON.parse(savedHistory));
      } catch (e) {
        console.error("Failed to parse history", e);
      }
    }

    // Load Settings from Rust
    invoke<string>("get_setting", { key: "ai_mode" }).then((m) => setAiMode(m || "raw")).catch(console.error);

    // Initial Engine Check - give it 60s for first-run model download
    const timer = setTimeout(() => {
      setStatus(currentStatus => {
        if (currentStatus === "IDLE") {
          setError("Engine failed to respond. Try refreshing.");
          return "ERROR";
        }
        return currentStatus;
      });
    }, 60000);

    return () => clearTimeout(timer);
  }, []);

  // Ping the engine after the event listener is ready to get current status
  useEffect(() => {
    const pingTimer = setTimeout(() => {
      invoke("ping_sidecar").catch(console.error);
    }, 2000); // Wait 2s for listener to be registered, then ask engine for status
    return () => clearTimeout(pingTimer);
  }, []);

  const addToHistory = (text: string) => {
    const newItem: HistoryItem = {
      id: crypto.randomUUID(),
      text,
      timestamp: Date.now(),
    };
    setHistory((prev) => {
      const updated = [newItem, ...prev].slice(0, 50);
      localStorage.setItem("mike-whisper-history", JSON.stringify(updated));
      return updated;
    });
  };

  useEffect(() => {
    const unlisten = listen<string>("sidecar-event", (event) => {
      try {
        const payload: SidecarEvent = JSON.parse(event.payload);

        switch (payload.type) {
          case "READY":
            setStatus("READY");
            console.log("Engine is READY");
            break;
          case "STATUS":
            setStatus(payload.data as SidecarStatus);
            break;
          case "PARTIAL_RESULT":
            setLastText(payload.data);
            break;
          case "RESULT":
            setLastText(payload.data);
            addToHistory(payload.data);
            setStatus("READY");
            setError(""); // Clear any previous errors on success
            break;
          case "ERROR":
            setError(payload.data);
            setStatus("ERROR");
            break;
          default:
            console.log("Unknown event type:", payload.type);
        }
      } catch (e) {
        console.error("Failed to parse sidecar event:", e, event.payload);
      }
    });

    return () => {
      unlisten.then((f) => f());
    };
  }, []);

  return (
    <main className="container">
      <div className="status-header">
        <h1>MikeWhisper</h1>
        <div className="status-container">
          <div className={`status-badge ${status.toLowerCase()}`}>
            {status}
          </div>
          <button className="btn-icon" onClick={() => invoke("ping_sidecar")} title="Refresh Engine">
            🔄
          </button>
          <button
            className={`btn-icon ${status === 'RECORDING' ? 'active' : ''}`}
            onMouseDown={() => invoke("force_record_start")}
            onMouseUp={() => invoke("force_record_stop")}
            title="Hold to Record (Force)"
          >
            🎤
          </button>
        </div>
      </div>

      <div className="main-card">
        <section className="display-section">
          <h2>Last Transcription</h2>
          <div className="text-area">
            {lastText || <span className="placeholder">Start speaking to see results...</span>}
          </div>
        </section>

        <section className="compact-settings">
          <div className="setting-item-inline">
            <label>AI Mode</label>
            <select value={aiMode} onChange={(e) => updateAiMode(e.target.value)}>
              <option value="raw">Raw (Fastest)</option>
              <option value="email">Professional Email</option>
              <option value="notes">Bullet Notes</option>
              <option value="fix">Fix Grammar Only</option>
            </select>
          </div>
          <button className="btn-settings-small" onClick={() => invoke("open_settings_window")} title="Open Settings">
            ⚙️ Settings
          </button>
        </section>

        <section className="history-section">
          <h2>History</h2>
          <div className="history-list">
            {history.length === 0 ? (
              <p className="placeholder">No history yet.</p>
            ) : (
              history.map((item) => (
                <div key={item.id} className="history-item">
                  <div className="history-text">{item.text}</div>
                  <div className="history-meta">
                    <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                    <button
                      className="btn-link"
                      onClick={() => navigator.clipboard.writeText(item.text)}
                    >
                      Copy
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {error && <div className="error-footer">{error}</div>}

      <footer className="footer-info">
        <p>Press and hold hotkey to record. Release to transcribe & inject.</p>
      </footer>
    </main>
  );
}

export default App;
