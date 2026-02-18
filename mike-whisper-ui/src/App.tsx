import { useState, useEffect } from "react";
import { listen } from "@tauri-apps/api/event";
import "./App.css";

type SidecarStatus = "IDLE" | "RECORDING" | "PROCESSING" | "READY" | "ERROR" | "NO_SPEECH";

interface SidecarEvent {
  type: string;
  data?: any;
}

function App() {
  const [status, setStatus] = useState<SidecarStatus>("IDLE");
  const [lastText, setLastText] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const unlisten = listen<string>("sidecar-event", (event) => {
      try {
        const payload: SidecarEvent = JSON.parse(event.payload);
        
        switch (payload.type) {
          case "READY":
            setStatus("IDLE");
            break;
          case "STATUS":
            setStatus(payload.data as SidecarStatus);
            break;
          case "RESULT":
            setLastText(payload.data);
            setStatus("IDLE");
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
        <div className={`status-badge ${status.toLowerCase()}`}>
          {status}
        </div>
      </div>

      <div className="main-card">
        <section className="display-section">
          <h2>Last Transcription</h2>
          <div className="text-area">
            {lastText || <span className="placeholder">Start speaking to see results...</span>}
          </div>
        </section>

        <section className="settings-section">
          <h2>Settings</h2>
          <div className="setting-item">
            <label>Model Engine</label>
            <select disabled value="base.en">
              <option value="tiny.en">Tiny (Fastest)</option>
              <option value="base.en">Base (Balanced)</option>
              <option value="small.en">Small (Slowest but accurate)</option>
            </select>
          </div>
          <div className="setting-item">
            <label>Hotkey</label>
            <code className="hotkey">Ctrl + Shift + Space</code>
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
