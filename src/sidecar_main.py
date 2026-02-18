import sys
import os
import json
import logging
import threading
import queue
import time

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

    def _process_worker(self):
        while self.is_running:
            try:
                audio_data = self.processing_queue.get(timeout=0.5)
                self._send_event("STATUS", "PROCESSING")
                
                text = self.transcriber.transcribe(audio_data)
                
                if text:
                    # Inject text directly
                    self.injector.inject(text)
                    self._send_event("RESULT", text)
                else:
                    self._send_event("STATUS", "NO_SPEECH")
                
                self._send_event("STATUS", "IDLE")
                self.processing_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in sidecar worker: {e}")
                self._send_event("ERROR", str(e))

    def run(self):
        """Listen for commands from stdin."""
        logger.info("Sidecar listening for commands...")
        try:
            for line in sys.stdin:
                command = line.strip()
                if not command:
                    continue
                
                logger.info(f"Received command: {command}")
                
                if command == "START_RECORDING":
                    self.recorder.start_recording()
                    self._send_event("STATUS", "RECORDING")
                
                elif command == "STOP_RECORDING":
                    audio_data = self.recorder.stop_recording()
                    if audio_data.size > 0:
                        self.processing_queue.put(audio_data)
                    else:
                        self._send_event("STATUS", "IDLE")
                
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
