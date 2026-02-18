# Design Document: MikeWhisper (Local-First AI Dictation)

**Date:** 2026-02-17
**Status:** Draft / Research
**Context:** Based on the `int-mike-whisper.md` blueprint.

## 1. Vision & Goals
Build a high-performance, local-first voice-to-text system for Windows that provides "SuperWhisper" class performance with <500ms latency.

### Primary Milestone (MVP)
A Python-based background service that:
- Listens for a global hotkey.
- Captures audio from the default microphone.
- Transcribes using `faster-whisper`.
- Injects text directly into the active cursor position.

---

## 2. Progressive Architecture

### Phase 1: Python-First Background Service (Current Focus)
- **Language:** Python 3.10+
- **Input:** `sounddevice` / `PyAudio` + `pynput` (Hotkeys).
- **Core Engine:** `faster-whisper` (utilizing CTranslate2 for speed).
- **Formatting:** Basic cleanup (stripping whitespace, basic capitalization).
- **Injection:** `keyboard` library for hardware-level typing simulation.

### Phase 2: Tauri + Python Sidecar (Evolution)
- **Frontend:** Tauri (Rust) for System Tray, Settings UI, and Global Hotkeys.
- **Backend:** Python Logic bundled as a "Sidecar" executable.
- **IPC:** Local localhost (HTTP/WebSocket) or Stdout/Stdin communication between Tauri and the Python process.
- **Benefits:** Native Windows feel, lighter idle footprint, better error recovery.

---

## 3. Component Details (Phase 1)

### 3.1 Audio Capture & VAD
- **Library:** `sounddevice` for low-latency streaming.
- **VAD (Voice Activity Detection):** `silero-vad` or simple energy thresholding. 
- **Workflow:** 
    - Press Hotkey -> Start Buffer.
    - Release Hotkey -> Finalize Buffer -> Send to Whisper.

### 3.2 Transcription Engine
- **Model:** `faster-whisper` (medium.en or small.en for speed).
- **Optimization:** Use float16 on GPU (if NVIDIA detected) or int8 on CPU.
- **Latency Target:** Transcription should start while audio is still being captured (streaming) or immediately upon hotkey release.

### 3.3 Text Injection (Windows)
- **Mechanism:** Using `keyboard.write()` or `pyautogui.typewrite()`.
- **Fallbacks:** If direct typing is blocked, copy to clipboard and trigger `Ctrl+V`.

---

## 4. Data Flow (MVP)
1. **User** presses `Ctrl + Shift + Space`.
2. **Key Hook** detects input and triggers the **Audio Module**.
3. **Audio Module** streams microphone data into a memory buffer.
4. **User** releases Hotkey.
5. **Whisper Module** processes the buffer.
6. **Injector Module** focus-checks the active window and "types" the result.

---

## 5. Success Criteria
- **Transcribe Speed:** < 1s for a 5-second sentence.
- **Accuracy:** > 95% for standard English.
- **Injection:** Works in Notepad, Browser, and Discord.

---

## 6. Phase 2 Migration Plan
Once Phase 1 is stable, we will:
1. Initialize a **Tauri** project.
2. Port the hotkey logic to Rust (more reliable).
3. Create a system tray icon.
4. Package the Python logic using **PyInstaller** or **Nuitka** as a sidecar.
