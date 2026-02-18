from pynput import keyboard
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HotkeyManager:
    def __init__(self, on_press_callback=None, on_release_callback=None):
        self.on_press_callback = on_press_callback
        self.on_release_callback = on_release_callback
        self.listener = None
        
        # Default hotkey: <ctrl>+<shift>+<space>
        self.combination = {
            keyboard.Key.ctrl_l,
            keyboard.Key.shift,
            keyboard.Key.space
        }
        # Can also use a string for convenience if we wanted to use keyboard.GlobalHotKeys
        self.current_keys = set()
        self.is_active = False

    def _on_press(self, key):
        if key in self.combination or (hasattr(key, 'char') and key.char == ' '): # Handle Space specifically
            # Map canonical keys if needed
            actual_key = key
            if key == keyboard.Key.space:
                actual_key = keyboard.Key.space
            
            self.current_keys.add(actual_key)
            
            # Check if all keys in combination are pressed
            if all(k in self.current_keys for k in self.combination):
                if not self.is_active:
                    self.is_active = True
                    logger.info("Hotkey Activation: Start")
                    if self.on_press_callback:
                        self.on_press_callback()

    def _on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)
            
        # If any of the keys are released, stop the activation
        if self.is_active:
            if not all(k in self.current_keys for k in self.combination):
                self.is_active = False
                logger.info("Hotkey Activation: Stop")
                if self.on_release_callback:
                    self.on_release_callback()

    def start(self):
        """Starts the global keyboard listener in a non-blocking way."""
        logger.info("Starting global hotkey listener (Ctrl+Shift+Space)...")
        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self.listener.start()

    def stop(self):
        """Stops the listener."""
        if self.listener:
            self.listener.stop()
            logger.info("Hotkey listener stopped.")

# Alternative simpler implementation using pynput.keyboard.GlobalHotKeys
class SimpleHotkeyManager:
    def __init__(self, hotkey_str="<ctrl>+<shift>+<space>", on_activate=None):
        self.hotkey_str = hotkey_str
        self.on_activate = on_activate
        self.listener = None

    def start(self):
        logger.info(f"Starting simple hotkey listener for {self.hotkey_str}...")
        self.listener = keyboard.GlobalHotKeys({
            self.hotkey_str: self.on_activate
        })
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
