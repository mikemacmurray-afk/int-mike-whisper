import sys
import os
import time
import logging
import threading
import queue

# Add src to path if needed for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_recorder import AudioRecorder
from transcriber import Transcriber
from hotkeys import HotkeyManager
from injector import TextInjector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MikeWhisper")

class MikeWhisperApp:
    def __init__(self):
        logger.info("Initializing MikeWhisper MVP...")
        
        # Initialize components
        self.recorder = AudioRecorder()
        # Using base.en for better quality/speed balance in MVP
        self.transcriber = Transcriber(model_size="base.en")
        self.injector = TextInjector()
        
        self.processing_queue = queue.Queue()
        self.is_running = True
        
        # Start the processing thread
        self.processor_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.processor_thread.start()

    def _on_press(self):
        """Called when hotkey is held down."""
        # Use a non-blocking start if possible, or handle in recorder
        self.recorder.start_recording()

    def _on_release(self):
        """Called when hotkey is released."""
        audio_data = self.recorder.stop_recording()
        if audio_data.size > 0:
            logger.info("Audio captured, adding to processing queue...")
            self.processing_queue.put(audio_data)
        else:
            logger.warning("Captured audio was empty.")

    def _process_worker(self):
        """Background thread to handle transcription and injection."""
        while self.is_running:
            try:
                # Wait for audio data from the queue
                audio_data = self.processing_queue.get(timeout=1)
                
                logger.info("Processing transcription...")
                start_time = time.time()
                
                text = self.transcriber.transcribe(audio_data)
                
                if text:
                    logger.info(f"Final Text: {text}")
                    self.injector.inject(text)
                else:
                    logger.info("No text detected.")
                    
                duration = time.time() - start_time
                logger.info(f"Total processing time: {duration:.2f}s")
                
                self.processing_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in processing worker: {e}")

    def run(self):
        """Starts the application."""
        hotkey = HotkeyManager(
            on_press_callback=self._on_press,
            on_release_callback=self._on_release
        )
        
        logger.info("--- MikeWhisper is LIVE ---")
        logger.info("Press CTRL+SHIFT+SPACE to record.")
        logger.info("Press CTRL+C in this terminal to exit.")
        
        hotkey.start()
        
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.is_running = False
            hotkey.stop()

if __name__ == "__main__":
    app = MikeWhisperApp()
    app.run()
