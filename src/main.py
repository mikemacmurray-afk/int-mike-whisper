import sys
import os
import time
import logging
import threading
import queue
import requests

# Add src to path if needed for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_recorder import AudioRecorder
from transcriber import Transcriber
from hotkeys import HotkeyManager
from injector import TextInjector
from brain_dispatcher import dispatch_to_daily_brain

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
        self.active_mode = "cursor"
        
        # Start the processing thread
        self.processor_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.processor_thread.start()

    def _on_press(self, mode="cursor"):
        """Called when hotkey is held down."""
        self.active_mode = mode
        logger.info(f"Hotkey pressed, recording started (Mode: {mode})...")
        self.recorder.start_recording()

    def _on_release(self, mode=None):
        """Called when hotkey is released."""
        target_mode = mode or self.active_mode or "cursor"
        audio_data = self.recorder.stop_recording()
        if audio_data.size > 0:
            logger.info(f"Audio captured ({target_mode}), adding to processing queue...")
            self.processing_queue.put((audio_data, target_mode))
        else:
            logger.warning("Captured audio was empty.")

    def _process_worker(self):
        """Background thread to handle transcription and injection or dispatch."""
        while self.is_running:
            try:
                # Wait for audio data from the queue
                item = self.processing_queue.get(timeout=1)
                if isinstance(item, tuple):
                    audio_data, mode = item
                else:
                    audio_data, mode = item, "cursor"
                
                logger.info(f"Processing transcription ({mode})...")
                start_time = time.time()
                
                text = self.transcriber.transcribe(audio_data)
                
                if text:
                    logger.info(f"Final Text: {text}")
                    if mode == "brain":
                        logger.info("Dispatching transcribed text to Daily Brain...")
                        dispatch_to_daily_brain(text)
                    else:
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

    def run(self, hotkey_cursor=None, hotkey_brain=None):
        """Starts the application."""
        hotkey = HotkeyManager(
            on_press_callback=self._on_press,
            on_release_callback=self._on_release,
            hotkey_cursor=hotkey_cursor,
            hotkey_brain=hotkey_brain,
        )
        
        logger.info("--- MikeWhisper is LIVE ---")
        logger.info(f"Hotkey A: [{hotkey.hotkey_cursor_str}] -> Cursor Dictation")
        logger.info(f"Hotkey B: [{hotkey.hotkey_brain_str}] -> Daily Brain Voice Logging")
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
    import argparse
    parser = argparse.ArgumentParser(description="MikeWhisper Voice Dictation & Daily Brain Integration")
    parser.add_argument("--hotkey-cursor", help="Key combination for cursor dictation (e.g. 'Ctrl+Space')")
    parser.add_argument("--hotkey-brain", help="Key combination for Daily Brain (e.g. 'Fn+Space' or 'Ctrl+Alt+Space')")
    args = parser.parse_args()

    app = MikeWhisperApp()
    app.run(hotkey_cursor=args.hotkey_cursor, hotkey_brain=args.hotkey_brain)
