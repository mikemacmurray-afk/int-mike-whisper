import keyboard
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextInjector:
    def __init__(self, delay=0.1):
        """
        delay: Small delay before typing to ensure OS context is correct.
        """
        self.delay = delay

    def inject(self, text):
        """
        Types the text directly at the cursor position.
        """
        if not text:
            return

        logger.info(f"Injecting text: '{text[:20]}...'")
        
        # Small sleep helps if the user just released a key
        time.sleep(self.delay)
        
        try:
            # keyboard.write is effective on Windows for direct injection
            keyboard.write(text)
        except Exception as e:
            logger.error(f"Failed to inject text: {e}")

    def inject_via_clipboard(self, text):
        """
        Alternative: Copy to clipboard and paste. 
        Useful for complex characters or if direct typing is slow.
        """
        # This would require pyperclip or similar, leaving as placeholder 
        # for Phase 1. Basic 'keyboard.write' is the MVP target.
        pass
