import sys
import os
import json
import logging
import threading
import queue
import time
import requests

# Disable Intel MKL to prevent CTranslate2 0xC0000005 segmentation faults on virtualized CPUs
os.environ["CT2_USE_MKL"] = "0"
# Force CTranslate2 to use generic CPU instruction set (no AVX/AVX2/AVX512) for maximum compatibility on VMs
os.environ["CT2_FORCE_CPU_ISA"] = "GENERIC"
# Permit duplicate OpenMP library loading
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Handle PyInstaller paths
if getattr(sys, 'frozen', False):
    # If running as a bundle, the modules are in the temp folder
    bundle_dir = sys._MEIPASS
else:
    # If running in dev, use the current folder
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(bundle_dir)

from injector import TextInjector
# Import heavy dependencies in the main thread to prevent Windows DLL loader lock deadlocks with blocking stdin reads.
from audio_recorder import AudioRecorder
from transcriber import Transcriber

# Configure logging to stderr so it doesn't mess with stdout IPC
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("MikeWhisperSidecar")

class MikeWhisperSidecar:
    def __init__(self):
        logger.info("Initializing MikeWhisper Sidecar Engine...")
        
        # AudioRecorder and Transcriber will be asynchronously loaded
        self.recorder = None
        self.transcriber = None
        self.current_loaded_model = None
        self.injector = TextInjector()
        
        self.processing_queue = queue.Queue()
        self.is_running = True
        self.is_live = False
        self.is_loading = False
        self.models_loaded = False
        
        self.config = {
            "api_key": "",
            "mode": "raw",
            "vocabulary": "",
            "model_size": "base.en"
        }
        
        # Start processing worker
        self.processor_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.processor_thread.start()
        
        # Send Ready signals immediately to unblock Tauri
        self._send_event("READY")
        self._send_event("STATUS", "INITIALIZING")
        
        # Start background model initialization
        self.init_thread = threading.Thread(target=self._initialize_models, daemon=True)
        self.init_thread.start()

    def _send_event(self, event_type, data=None):
        """Sends a JSON event to stdout for Tauri to consume."""
        message = {"type": event_type}
        if data:
            message["data"] = data
        print(json.dumps(message), flush=True)

    def _format_text_ai(self, text):
        """Uses OpenRouter to format the transcribed text based on the current mode."""
        if not self.config["api_key"] or self.config["mode"] == "raw":
            return text

        logger.info(f"Formatting text with AI mode: {self.config['mode']}")
        
        prompts = {
            "email": "Rewrite the following spoken draft into a professional, clear email. Keep the original intent but fix the grammar and structure: ",
            "notes": "Convert the following speech into a concise set of vertically separated bullet points. IMPORTANT: Every single bullet point MUST start on a new line. Format: \n- Point 1\n- Point 2\n\nText: ",
            "fix": "Fix any grammar, punctuation, or spelling errors in the following text while keeping it exactly as spoken. Do not change the meaning or style: "
        }

        prompt_prefix = prompts.get(self.config["mode"], "")
        
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config['api_key']}",
                },
                data=json.dumps({
                    "model": "google/gemini-2.0-flash-001", # Fast and reliable for formatting
                    "messages": [
                        {"role": "user", "content": f"{prompt_prefix}\n\n{text}"}
                    ]
                }),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                formatted_text = result['choices'][0]['message']['content'].strip()
                logger.info(f"AI returned: {formatted_text!r}")
                return formatted_text
            else:
                logger.error(f"OpenRouter Error: {response.status_code} - Body: {response.text}")
                return text # Fallback to raw text on error
        except Exception as e:
            logger.error(f"AI Formatting failed: {e}")
            return text

    def _initialize_models(self):
        """Background thread to load Whisper/VAD models."""
        self.is_loading = True
        self._send_event("STATUS", "INITIALIZING")
        
        try:
            # Wait briefly to let SET_CONFIG command arrive from Tauri (which has the configured model size)
            time.sleep(0.5)
            
            model_size = self.config.get("model_size", "base.en")
            logger.info(f"Background thread loading models (Whisper: {model_size})...")
            
            self.recorder = AudioRecorder()
            self.transcriber = Transcriber(model_size=model_size)
            self.current_loaded_model = model_size
            
            self.models_loaded = True
            self.is_loading = False
            logger.info("Background thread initialization complete. Engine is READY.")
            self._send_event("STATUS", "READY")
        except Exception as e:
            self.is_loading = False
            logger.error(f"Error during background initialization: {e}")
            self._send_event("ERROR", f"Initialization failed: {e}")

    def _reload_model(self, model_size):
        """Reloads the Whisper model with a new size in the background."""
        if self.is_loading:
            return
        
        logger.info(f"Reloading Whisper model to '{model_size}'...")
        self.is_loading = True
        self._send_event("STATUS", "INITIALIZING")
        
        try:
            from transcriber import Transcriber
            self.transcriber = Transcriber(model_size=model_size)
            self.current_loaded_model = model_size
            self.is_loading = False
            logger.info(f"Model reloaded successfully to '{model_size}'. Ready.")
            self._send_event("STATUS", "READY")
        except Exception as e:
            self.is_loading = False
            logger.error(f"Failed to reload model: {e}")
            self._send_event("ERROR", f"Model reload failed: {e}")

    def _partial_transcription_worker(self):
        """Worker thread to transcribe partial data while recording."""
        logger.info("Starting partial transcription worker...")
        while self.is_live:
            time.sleep(1.0)  # Throttled to 1000ms
            if not self.is_live:
                break
            
            # Auto-stop from silence timeout
            if self.recorder and getattr(self.recorder, 'timeout_triggered', False):
                logger.info("Silence timeout hit, stopping recording automatically.")
                self.recorder.timeout_triggered = False
                self.is_live = False
                audio_data = self.recorder.stop_recording()
                if audio_data.size > 0:
                    self.processing_queue.put(audio_data)
                else:
                    self._send_event("STATUS", "READY" if self.models_loaded else "INITIALIZING")
                break

            # Only transcribe partial if user actually spoke since last tick
            if self.recorder and getattr(self.recorder, 'speech_detected_since_last_poll', False):
                self.recorder.speech_detected_since_last_poll = False
                audio_data = self.recorder.get_current_buffer()
                if audio_data.size > 16000: # At least 1 second
                    text = self.transcriber.transcribe(
                        audio_data, 
                        initial_prompt=self.config.get("vocabulary")
                    )
                    if text and self.is_live:
                        self._send_event("PARTIAL_RESULT", text)

    def _process_worker(self):
        while self.is_running:
            try:
                audio_data = self.processing_queue.get(timeout=0.5)
                self._send_event("STATUS", "PROCESSING")
                
                if self.transcriber:
                    text = self.transcriber.transcribe(
                        audio_data, 
                        initial_prompt=self.config.get("vocabulary")
                    )
                else:
                    text = ""
                
                if text:
                    # Apply AI formatting if enabled
                    final_text = self._format_text_ai(text)
                    
                    # Inject text directly
                    self.injector.inject(final_text)
                    self._send_event("RESULT", final_text)
                else:
                    self._send_event("STATUS", "NO_SPEECH")
                
                self._send_event("STATUS", "READY" if self.models_loaded else "INITIALIZING")
                self.processing_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in sidecar worker: {e}")
                self._send_event("ERROR", str(e))

    def run(self):
        """Listen for commands from stdin."""
        logger.info("Sidecar listening for commands...")
        self.is_live = False
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                # Handle JSON commands (for config) or string commands
                command = None
                try:
                    cmd_data = json.loads(line)
                    if cmd_data.get("type") == "SET_CONFIG":
                        new_config = cmd_data.get("data", {})
                        self.config.update(new_config)
                        new_model = self.config.get("model_size", "base.en")
                        
                        logger.info(f"Updated config: mode={self.config.get('mode')}, model={new_model}")
                        
                        # If models are loaded and model_size changed, trigger reload in background
                        if self.models_loaded and new_model != self.current_loaded_model:
                            threading.Thread(target=self._reload_model, args=(new_model,), daemon=True).start()
                        continue
                    # If it's a JSON command but not SET_CONFIG, treat it as an unknown JSON command
                    logger.warning(f"Received unknown JSON command: {cmd_data}")
                    continue
                except json.JSONDecodeError:
                    # Not a JSON command, treat as a string command
                    command = line
                
                if command is None: # Should not happen if JSONDecodeError is caught
                    continue

                logger.info(f"Received command: {command}")
                
                if command == "PING":
                    self._send_event("STATUS", "READY" if self.models_loaded else "INITIALIZING")
                elif command == "START_RECORDING":
                    if not self.models_loaded or self.is_loading:
                        logger.warning("Recording requested but models are not loaded yet.")
                        self._send_event("STATUS", "INITIALIZING")
                        continue
                    self.recorder.start_recording()
                    self.is_live = True
                    self.partial_thread = threading.Thread(target=self._partial_transcription_worker, daemon=True)
                    self.partial_thread.start()
                    self._send_event("STATUS", "RECORDING")
                
                elif command == "STOP_RECORDING":
                    self.is_live = False
                    if not self.models_loaded or self.is_loading:
                        self._send_event("STATUS", "INITIALIZING")
                        continue
                    audio_data = self.recorder.stop_recording()
                    if audio_data.size > 0:
                        self.processing_queue.put(audio_data)
                    else:
                        self._send_event("STATUS", "READY")
                
                elif command == "EXIT":
                    self.is_running = False
                    break
        except EOFError:
            pass
        except Exception as e:
            logger.error(f"Sidecar input loop error: {e}")

if __name__ == "__main__":
    sidecar = MikeWhisperSidecar()
    sidecar.run()
