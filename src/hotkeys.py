from pynput import keyboard
import logging
import threading
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_key(key):
    """Maps various OS key representations to standardized key tokens."""
    if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        return keyboard.Key.ctrl
    if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
        return keyboard.Key.shift
    if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
        return keyboard.Key.alt
    if key in (keyboard.Key.cmd, keyboard.Key.cmd_r):
        return keyboard.Key.cmd
    if key == keyboard.Key.space or (hasattr(key, 'char') and key.char == ' '):
        return keyboard.Key.space
    # Check for Fn key representation
    if hasattr(key, 'name') and key.name and key.name.lower() in ('fn', 'function'):
        return 'fn'
    if hasattr(key, 'char') and key.char and key.char.lower() in ('fn', 'function'):
        return 'fn'
    return key

def parse_hotkey(spec):
    """
    Parses a hotkey specification string or set into a normalized set of keys.
    Examples:
        'Ctrl+Space' -> {Key.ctrl, Key.space}
        'control in space' -> {Key.ctrl, Key.space}
        'function and space' -> {'fn', Key.space}
        'Fn+Space' -> {'fn', Key.space}
        'Ctrl+Shift+Space' -> {Key.ctrl, Key.shift, Key.space}
        'Alt+Space' -> {Key.alt, Key.space}
        'F2+Space' -> {Key.f2, Key.space}
    """
    if spec is None:
        return set()
    if isinstance(spec, (set, list, tuple)):
        return {normalize_key(k) for k in spec}
    
    if not isinstance(spec, str):
        return set()

    clean_spec = spec.replace("<", "").replace(">", "").strip()
    clean_spec = clean_spec.replace(" in ", "+").replace(" and ", "+").replace("&", "+")
    tokens = [t.strip().lower() for t in clean_spec.split("+") if t.strip()]
    
    result = set()
    for token in tokens:
        if token in ("ctrl", "control", "ctrl_l", "ctrl_r"):
            result.add(keyboard.Key.ctrl)
        elif token in ("shift", "shift_l", "shift_r"):
            result.add(keyboard.Key.shift)
        elif token in ("alt", "alt_l", "alt_r", "alt_gr", "option"):
            result.add(keyboard.Key.alt)
        elif token in ("win", "windows", "cmd", "command", "super"):
            result.add(keyboard.Key.cmd)
        elif token in ("space", "spacebar", " "):
            result.add(keyboard.Key.space)
        elif token in ("fn", "function"):
            result.add("fn")
        elif hasattr(keyboard.Key, token):
            result.add(getattr(keyboard.Key, token))
        else:
            result.add(keyboard.KeyCode(char=token))
            
    return result

class HotkeyManager:
    def __init__(
        self,
        on_press_callback=None,
        on_release_callback=None,
        on_press_brain_callback=None,
        on_release_brain_callback=None,
        hotkey_cursor=None,
        hotkey_brain=None,
        combination_cursor=None,
        combination_brain=None,
    ):
        self.on_press_callback = on_press_callback
        self.on_release_callback = on_release_callback
        self.on_press_brain_callback = on_press_brain_callback
        self.on_release_brain_callback = on_release_brain_callback
        self.listener = None
        
        cfg = load_config()
        self.hotkey_cursor_str = hotkey_cursor or cfg.get("hotkey_cursor", "Ctrl+Space")
        self.hotkey_brain_str = hotkey_brain or cfg.get("hotkey_brain", "Fn+Space")
        
        # Hotkey A: Normal Cursor Dictation (Default: Ctrl+Space)
        if combination_cursor is not None:
            self.combination_cursor = {normalize_key(k) for k in combination_cursor}
        else:
            self.combination_cursor = parse_hotkey(self.hotkey_cursor_str)
            
        # Hotkey B: Daily Brain Dispatch (Default: Fn+Space)
        if combination_brain is not None:
            self.combination_brain = {normalize_key(k) for k in combination_brain}
        else:
            self.combination_brain = parse_hotkey(self.hotkey_brain_str)

        # Default hotkey combination for backward compatibility
        self.combination = self.combination_cursor
        
        self.raw_keys = set()
        self.current_keys = set()
        self.is_active = False
        self.active_mode = None  # "cursor" or "brain"

    def _normalize_key(self, key):
        return normalize_key(key)

    def _invoke_callback(self, callback, mode):
        if not callback:
            return
        try:
            callback(mode)
        except TypeError:
            callback()

    def _on_press(self, key):
        self.raw_keys.add(key)
        self.current_keys = {self._normalize_key(k) for k in self.raw_keys}

        if not self.is_active:
            # Check Hotkey B (Daily Brain)
            if self.combination_brain and all(k in self.current_keys for k in self.combination_brain):
                self.is_active = True
                self.active_mode = "brain"
                logger.info(f"Hotkey Activation: Start (Hotkey B: {self.hotkey_brain_str} -> Daily Brain)")
                cb = self.on_press_brain_callback or self.on_press_callback
                self._invoke_callback(cb, "brain")
            # Check Hotkey A (Cursor Dictation)
            elif self.combination_cursor and all(k in self.current_keys for k in self.combination_cursor):
                self.is_active = True
                self.active_mode = "cursor"
                logger.info(f"Hotkey Activation: Start (Hotkey A: {self.hotkey_cursor_str} -> Cursor)")
                self._invoke_callback(self.on_press_callback, "cursor")

    def _on_release(self, key):
        self.raw_keys.discard(key)
        self.current_keys = {self._normalize_key(k) for k in self.raw_keys}

        if self.is_active:
            target_combo = self.combination_brain if self.active_mode == "brain" else self.combination_cursor
            if not all(k in self.current_keys for k in target_combo):
                prev_mode = self.active_mode
                self.is_active = False
                self.active_mode = None
                logger.info(f"Hotkey Activation: Stop ({prev_mode})")
                if prev_mode == "brain":
                    cb = self.on_release_brain_callback or self.on_release_callback
                    self._invoke_callback(cb, "brain")
                else:
                    self._invoke_callback(self.on_release_callback, "cursor")

    def start(self):
        """Starts the global keyboard listener in a non-blocking way."""
        logger.info(f"Starting global hotkey listener ({self.hotkey_cursor_str} for Cursor, {self.hotkey_brain_str} for Daily Brain)...")
        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self.listener.start()

    def stop(self):
        """Stops the listener."""
        if self.listener:
            self.listener.stop()
            logger.info("Hotkey listener stopped.")

# Alternative simpler implementation using pynput.keyboard.GlobalHotKeys
class SimpleHotkeyManager:
    def __init__(
        self,
        hotkey_str=None,
        on_activate=None,
        brain_hotkey_str=None,
        on_activate_brain=None,
    ):
        cfg = load_config()
        self.hotkey_str = hotkey_str or cfg.get("hotkey_cursor", "<ctrl>+<space>")
        self.on_activate = on_activate
        self.brain_hotkey_str = brain_hotkey_str or cfg.get("hotkey_brain", "<ctrl>+<alt>+<space>")
        self.on_activate_brain = on_activate_brain
        self.listener = None

    def start(self):
        logger.info(f"Starting simple hotkey listener ({self.hotkey_str}, {self.brain_hotkey_str})...")
        bindings = {}
        if self.on_activate:
            bindings[self.hotkey_str] = self.on_activate
        if self.on_activate_brain:
            bindings[self.brain_hotkey_str] = self.on_activate_brain
        self.listener = keyboard.GlobalHotKeys(bindings)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
