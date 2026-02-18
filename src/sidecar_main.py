import sys
import os
import json
import logging
import threading
import queue
import time
import requests

# Handle PyInstaller paths
if getattr(sys, 'frozen', False):
    # If running as a bundle, the modules are in the temp folder
    bundle_dir = sys._MEIPASS
else:
    # If running in dev, use the current folder
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(bundle_dir)

from audio_recorder import AudioRecorder
from transcriber import Transcriber
from injector import TextInjector

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
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber(model_size="base.en")
        self.injector = TextInjector()
        
        self.processing_queue = queue.Queue()
        self.is_running = True
        self.is_live = False
        self.config = {
            "api_key": "",
            "mode": "raw"
        }
        
        # Start processing worker
        self.processor_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.processor_thread.start()
        
        # Send Ready signal
        self._send_event("READY")

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

    def _partial_transcription_worker(self):
        """Worker thread to transcribe partial data while recording."""
        logger.info("Starting partial transcription worker...")
        while self.is_live:
            time.sleep(0.8)  # Transcribe every 800ms
            if not self.is_live:
                break
            
            # Get current audio data without stopping
            audio_data = self.recorder.get_current_buffer()
            if audio_data.size > 16000: # At least 1 second
                # Use a fast model/settings for partials if needed, or same
                text = self.transcriber.transcribe(audio_data)
                if text and self.is_live:
                    self._send_event("PARTIAL_RESULT", text)

    def _process_worker(self):
        while self.is_running:
            try:
                audio_data = self.processing_queue.get(timeout=0.5)
                self._send_event("STATUS", "PROCESSING")
                
                text = self.transcriber.transcribe(audio_data)
                
                if text:
                    # Apply AI formatting if enabled
                    final_text = self._format_text_ai(text)
                    
                    # Inject text directly
                    self.injector.inject(final_text)
                    self._send_event("RESULT", final_text)
                else:
                    self._send_event("STATUS", "NO_SPEECH")
                
                self._send_event("STATUS", "READY")
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
                        self.config.update(cmd_data.get("data", {}))
                        logger.info(f"Updated config: {self.config.get('mode')}")
                        continue # Processed config, move to next line
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
                    self._send_event("STATUS", "READY")
                elif command == "START_RECORDING":
                    self.recorder.start_recording()
                    self.is_live = True
                    self.partial_thread = threading.Thread(target=self._partial_transcription_worker, daemon=True)
                    self.partial_thread.start()
                    self._send_event("STATUS", "RECORDING")
                
                elif command == "STOP_RECORDING":
                    self.is_live = False
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
