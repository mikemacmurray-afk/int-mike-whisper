# MikeWhisper Phase 1 Implementation Plan

> **For Agent:** REQUIRED SUB-SKILL: Use [executing-plans] to implement this plan task-by-task.

**Goal:** Build a Python background service that transcribes speech to text via a hotkey and injects it into any active Windows application.
**Architecture:** A lightweight Python service using `sounddevice` for audio, `faster-whisper` for ML, and `pynput/keyboard` for OS interaction.
**Tech Stack:** Python 3.10+, faster-whisper, sounddevice, keyboard, pynput.

---

## Task 1: Environment Setup
**Goal:** Initialize the project structure and install core dependencies.

1. **Setup**:
   - Create `src/` directory.
   - Create `requirements.txt`.
2. **Action**: 
   - Run `python -m venv venv`.
   - Install dependencies: `faster-whisper`, `sounddevice`, `pynput`, `keyboard`, `numpy`, `scipy`.
3. **Verification**: 
   - Run `python -c "import faster_whisper; print('Whisper Loaded')"` to ensure ML stack is ready.

## Task 2: Audio Recording Module
**Goal:** Capture microphone input into a buffer.

1. **Test**: Create `tests/test_audio.py` that records 2 seconds and asserts the buffer is non-zero.
2. **Implementation**: Build `src/audio_recorder.py`.
3. **Verification**: Run `python tests/test_audio.py`.

## Task 3: Faster-Whisper Integration
**Goal:** Convert audio buffers into strings.

1. **Test**: Create `tests/test_transcribe.py` with a pre-recorded `hello.wav` and assert output contains "hello".
2. **Implementation**: Build `src/transcriber.py` using `FastWhisper` (base.en).
3. **Verification**: Run `python tests/test_transcribe.py`.

## Task 4: Global Hotkey Manager
**Goal:** Detect Push-To-Talk (PTT) events.

1. **Test**: Create `tests/test_hotkeys.py` that prints "ACTIVE" while `CTRL+SHIFT+SPACE` is held.
2. **Implementation**: Build `src/hotkeys.py` using `pynput`.
3. **Verification**: Manual visual verification of terminal output.

## Task 5: Text Injector
**Goal:** Simulate keyboard input into external apps.

1. **Test**: Create `tests/test_injection.py` that waits 2 seconds then types "Test Injection".
2. **Implementation**: Build `src/injector.py` using `keyboard.write`.
3. **Verification**: Run test and focus on a Notepad window to see if text appears.

## Task 6: Main Integration Loop
**Goal:** Connect all modules into a functional service.

1. **Test**: End-to-end integration test in `src/main.py`.
2. **Implementation**: Wire modules: Hotkey (Trigger) -> Audio (Capture) -> Transcriber (Process) -> Injector (Output).
3. **Verification**: Use the tool globally to dictate into this chat window.
