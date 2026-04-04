# Implementation Plan - Custom Vocabulary / Dictionary Support

The user wants to add technical phrases or specific words to Whisper's dictionary to improve recognition accuracy. The easiest way to achieve this with `faster-whisper` is using the `initial_prompt` parameter.

## Proposed Changes

### 1. Python Sidecar (`src/transcriber.py`)
- Update `Transcriber.transcribe` to accept an optional `initial_prompt` argument.
- Use this argument in the `self.model.transcribe` call.

### 2. Python Sidecar (`src/sidecar_main.py`)
- Update `MikeWhisperSidecar.config` to include a `vocabulary` key (empty string by default).
- Update the `SET_CONFIG` handler to update this key.
- Pass `self.config["vocabulary"]` to the `transcriber.transcribe` method.

### 3. Tauri Backend (`mike-whisper-ui/src-tauri/src/lib.rs`)
- Update `sync_sidecar_config` to read `custom_vocabulary` from the `settings.json` store.
- Include `custom_vocabulary` in the `SET_CONFIG` JSON sent to the sidecar.

### 4. Settings UI (`mike-whisper-ui/src/SettingsApp.tsx`)
- Add a new state variable `vocabulary`.
- Add a text area or a multi-line input in the settings for the user to enter their technical phrases (comma-separated or just a block of text).
- Add functionality to save this vocabulary using `update_settings`.

## Verification Plan

### Automated Tests
- Since I cannot easily run the full app with a mic, I'll rely on checking that the configuration flows correctly from the UI to the transcriber.
- I can create a small test script to verify that `Transcriber.transcribe` correctly accepts and uses `initial_prompt`.

### Manual Verification
- The user can test by adding a unique word (e.g., "AntigravityAI") and seeing if Whisper recognizes it correctly instead of "Anti gravity AI".
