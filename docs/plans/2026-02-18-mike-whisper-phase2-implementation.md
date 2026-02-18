# MikeWhisper Phase 2 Implementation Plan (Tauri + Sidecar)

> **For Agent:** REQUIRED SUB-SKILL: Use [executing-plans] to implement this plan task-by-task.

**Goal:** Transform the Python script into a desktop application with a System Tray icon and a Settings UI.
**Architecture:** Tauri (Rust) as the host, Python (Sidecar) as the transcription engine.
**Tech Stack:** Rust, Tauri, React/Vite (UI), Python (CTranslate2/Whisper).

---

## Task 1: Tauri Project Initialization
**Goal:** Create the basic Tauri app structure.
1. **Action**: Initialize Tauri using `npx create-tauri-app@latest`.
2. **Configuration**:
   - Project Name: `mike-whisper-ui`
   - Frontend: `React / Vite`
   - Language: `TypeScript`
3. **Verification**: Run `npm run tauri dev` and see a default window.

## Task 2: System Tray & Global Hotkeys (Rust)
**Goal:** Move hotkey logic from Python to Rust for better OS integration.
1. **Implementation**:
   - Add `tauri-plugin-global-shortcut` to `src-tauri/Cargo.toml`.
   - Setup System Tray with "Settings", "Restart Engine", and "Quit".
   - Map `Ctrl+Shift+Space` in Rust to emit a frontend event.
2. **Verification**: Clicking "Quit" closes the app; pressing hotkey shows a notification or log.

## Task 3: Python Sidecar Packaging
**Goal:** Bundle the Python script into an executable that Tauri can launch.
1. **Action**: Use `PyInstaller` or `Nuitka` to create a standalone `.exe`.
2. **Sidecar Config**: Add the executable to `src-tauri/tauri.conf.json` as a sidecar.
3. **Verification**: Run `npm run tauri dev` and check if the Python process starts automatically.

## Task 4: IPC Bridge (Tauri <-> Python)
**Goal:** Communitcate between the Rust host and the Python engine.
1. **Architecture**: Use localhost WebSockets or Stdout/Stdin for lowest latency.
2. **Implementation**:
   - Rust: Send "START_RECORDING" / "STOP_RECORDING" to Sidecar.
   - Python: Send "TRANSCRIPTION_RESULT" back to Rust.
3. **Verification**: Log messages in the Tauri console showing successful handshakes.

## Task 5: Premium UI (Settings & Status)
**Goal:** Build a beautiful, minimal UI for controlling the app.
1. **Design**:
   - Dark mode, glassmorphism.
   - Model selector (Tiny, Base, Medium).
   - Audio input selector.
2. **Implementation**: React components for settings and a "listening" overlay status.
3. **Verification**: Changing the model in UI updates the Python engine.

## Task 6: Final Integration & Build
**Goal:** Clean up and create a distributable Windows installer.
1. **Action**: Run `npm run tauri build`.
2. **Verification**: Install the `.msi` and verify MikeWhisper works without a terminal.
