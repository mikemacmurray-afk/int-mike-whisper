# MikeWhisper Enhanced Features Implementation Plan

## Goal: Implement Live Overlay, Hotkey Customization, and History.

### 1. Persistence & Hotkeys
- **Backend (Rust)**:
  - Create a `Config` struct to store `hotkey` (string).
  - Use `tauri-plugin-store` or simple file-based JSON for settings.
  - Implement a command `update_hotkey(new_hotkey: String)` that:
    - Unregisters the old hotkey.
    - Registers the new one.
    - Saves to disk.
- **Frontend (TS/React)**:
  - Add a "Record Hotkey" UI component.
  - Load saved hotkey on startup.

### 2. Live Streaming Overlay (Partial Results)
- **Transcription Engine (Python)**:
  - Update `AudioRecorder` to yield chunks while recording.
  - Update `Transcriber` to provide partial transcriptions using `faster-whisper`'s `transcribe` on a sliding window or using the `vad` logic.
  - Send `PARTIAL_RESULT` messages to Rust.
- **Backend (Rust)**:
  - Create a transparent, "always on top" overlay window.
  - Handle `PARTIAL_RESULT` and send it to the overlay window.
- **Frontend (UI)**:
  - Create a new Minimal Overlay UI that only shows the live text.

### 3. Transcription History
- **Frontend (State)**:
  - Use `localStorage` to persist a list of `{ id, text, timestamp }`.
  - Add a scrollable "History" section in the main Settings window.
  - Allow "Copy to Clipboard" from history.

## Execution Order:
1. **History UI** (Quickest win).
2. **Hotkey Persistence** (Critical for usability).
3. **Live Overlay** (Most "WOW" factor).
