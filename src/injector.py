import keyboard
import time
import logging
import pyperclip

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
        Injects text via the clipboard (Copy + Paste).
        This method is much more reliable for preserving newlines (bullet points)
        and paragraphs compared to simulated typing.
        """
        if not text:
            return

        logger.info(f"Injecting formatted text: '{text[:20]}...'")
        
        # Small sleep helps if the user just released a hotkey
        time.sleep(self.delay)
        
        try:
            # 1. Save original clipboard content (Optional, but let's keep it simple for now)
            # 2. Set new content
            pyperclip.copy(text)
            
            # 3. Trigger Ctrl+V
            # We use a small delay between key presses for OS stability
            keyboard.press('ctrl')
            keyboard.press('v')
            time.sleep(0.05)
            keyboard.release('v')
            keyboard.release('ctrl')
            
            # Small footer sleep to ensure paste is registered before clipboard changes
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Failed to inject text via clipboard: {e}")
            # Fallback to direct typing if clipboard fails
            try:
                keyboard.write(text)
            except:
                pass
