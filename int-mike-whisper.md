# Build Your Own SuperWhisper (Local-First)

### Full Reverse-Engineering + Architecture Blueprint (2026)

This document is a **complete product + engineering spec** for building a local-first AI dictation system similar to SuperWhisper that runs entirely on a laptop.

Goal:
Create a fast, private, always-on voice → text → AI formatting tool usable across any app.

---

# 1. Product Vision

A local AI voice companion that:

* Converts speech → text instantly
* Cleans + formats with LLM
* Inserts into any app globally
* Runs fully local (optional cloud)
* Works offline
* Is extremely low latency

Think:
**Keyboard replacement for thinking**

---

# 2. Core Features to Replicate

## 2.1 Real-Time Dictation

* Global hotkey activation
* Always-listening optional mode
* Push-to-talk mode
* Live transcription overlay
* Cursor insertion into any app

### Requirements

* < 300ms perceived latency
* Streaming transcription
* Interruptible
* Background service

---

## 2.2 AI Formatting Engine

After transcription:

* Grammar correction
* Rewrite modes
* Tone changes
* Summarisation
* Prompt expansion

Example modes:

* Email
* Notes
* Code
* Brain dump → structured
* Meeting notes

### Implementation concept

Speech → raw text → LLM cleanup → final output

---

## 2.3 Custom Vocabulary + Memory

* User dictionary
* Name recognition
* Project terms
* Writing style memory
* Prompt presets

Store locally:

```
/user_profile/
   vocab.json
   writing_style.json
   prompts/
```

---

## 2.4 Global Injection (Critical)

Must type into:

* Cursor location
* Any app
* Browser
* IDE
* Terminal

Methods:

* macOS accessibility API
* Windows input simulation
* Clipboard paste fallback

---

## 2.5 Modes System (Key Differentiator)

User speaks → system transforms depending on mode.

Example:

| Mode    | Result             |
| ------- | ------------------ |
| Notes   | clean paragraph    |
| Email   | formatted email    |
| Command | structured prompt  |
| Code    | formatted code     |
| Journal | reflective writing |

Architecture:

```
speech → transcript → mode router → LLM prompt template → output
```

---

## 2.6 Local + Cloud Model Switching

User can choose:

* Fully local (privacy)
* Hybrid
* Cloud (best quality)

---

# 3. System Architecture

```
[Mic Input]
   ↓
[Audio Capture Engine]
   ↓
[VAD - Voice Detection]
   ↓
[Streaming Transcription Engine]
   ↓
[Text Buffer]
   ↓
[LLM Formatter]
   ↓
[Injector Engine]
   ↓
[Any App Cursor]
```

---

# 4. Model Stack (Best Current Options)

## 4.1 Speech-to-Text (Local)

### Best quality

* Whisper large-v3 (GPU)
* Whisper medium (CPU)
* FasterWhisper (recommended)

### Best performance

* whisper.cpp
* mlx-whisper (Mac Apple Silicon)
* Nvidia faster-whisper

Recommended default:

```
faster-whisper medium.en
```

---

## 4.2 Voice Activity Detection

Needed for responsiveness.

Use:

* Silero VAD (best)
* WebRTC VAD (fastest)

---

## 4.3 LLM Formatting Engine

Local options:

* Llama 3 8B
* Mistral 7B
* Phi-3 mini
* Gemma 2B

Cloud optional:

* Gemini flash
* GPT-4o mini
* Groq llama

Recommended hybrid:

```
Local small model
+
Optional cloud fallback
```

---

# 5. Tech Stack

## Desktop Framework

Choose one:

### Electron (fastest build)

* JS ecosystem
* Cross platform
* Easy global shortcuts

### Tauri (recommended)

* Rust core
* Lightweight
* Secure
* Fast startup

### Native

* Swift (Mac)
* C# (Windows)

---

## Backend Engine

Python or Rust recommended.

Python:

* fastest prototyping
* whisper support
* AI ecosystem

Rust:

* fastest runtime
* best for production
* low memory

Ideal hybrid:

```
UI: Tauri
Core: Python
Audio engine: Rust optional
```

---

# 6. Key Modules to Build

## Module 1 — Audio Capture

Handles:

* Microphone stream
* Noise suppression
* Gain control
* Streaming buffer

Libraries:

* PyAudio
* sounddevice
* CoreAudio (Mac)
* WASAPI (Windows)

---

## Module 2 — Transcription Engine

Pipeline:

```
audio chunks → VAD → whisper → streaming text
```

Must support:

* partial transcription
* correction updates
* low latency

---

## Module 3 — Formatting Engine

Input:

```
raw transcript
mode
user style
```

Output:

```
final formatted text
```

Example prompt template:

```
Rewrite the following dictated text clearly.

Mode: email
Tone: concise
User style: direct founder

Text:
{transcript}
```

---

## Module 4 — Overlay UI

Floating window showing:

* live transcript
* status
* mode
* mic state

Must:

* stay on top
* be minimal
* movable
* fade when inactive

---

## Module 5 — Global Hotkeys

Examples:

* Ctrl+Space → talk
* Ctrl+Shift+E → email mode
* Ctrl+Shift+C → code mode

Use:

* keyboard hooks
* OS accessibility APIs

---

## Module 6 — Text Injection

Hardest part.

Methods:

1. Direct typing simulation
2. Clipboard paste
3. Accessibility insertion

Must:

* detect active window
* detect cursor
* support all apps

---

# 7. Performance Targets

| Metric          | Target |
| --------------- | ------ |
| Start listening | <100ms |
| Speech latency  | <500ms |
| Formatting      | <1.5s  |
| Memory usage    | <2GB   |
| CPU idle        | low    |

---

# 8. Advanced Features to Add Later

## 8.1 Voice Commands

Examples:

* “delete last sentence”
* “rewrite professionally”
* “summarise that”

## 8.2 Meeting Mode

* multi speaker
* summarise
* action items

## 8.3 Memory Engine

Learns:

* writing style
* common prompts
* tone

## 8.4 On-device fine tuning

Personal speech adaptation.

---

# 9. MVP Build Order (Do This First)

### Phase 1 — Core dictation

* mic capture
* faster-whisper
* text output

### Phase 2 — global typing

* inject into apps
* hotkeys

### Phase 3 — AI formatting

* local LLM
* mode system

### Phase 4 — overlay UI

* floating window
* status

### Phase 5 — optimisation

* latency tuning
* GPU support

---

# 10. Hardware Requirements

Minimum:

* 16GB RAM
* modern CPU
* SSD

Ideal:

* 32GB RAM
* Apple Silicon / RTX GPU

---

# 11. Estimated Build Time

Solo hacker:

* MVP: 1–2 weeks
* Full SuperWhisper clone: 4–8 weeks
* Polished product: 3 months

Team:

* 2 engineers → 3–4 weeks

---

# 12. If You Build This Properly…

You end up with:

* A personal AI thinking interface
* Local privacy-first dictation
* Prompt generation engine
* Full keyboard replacement

This is not just dictation.

It becomes:
**Voice → thought → structured intelligence**

---

# 13. Want the insane version?

Next doc I can generate:

**“Build a $10M SuperWhisper competitor”**

Includes:

* exact model stack founders use
* latency tricks
* monetisation
* moat strategy
* why these apps are exploding

Just say: **INSANE BUILD**
