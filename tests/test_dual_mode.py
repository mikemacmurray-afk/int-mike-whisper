import sys
import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pynput import keyboard

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from hotkeys import HotkeyManager
from brain_dispatcher import dispatch_to_daily_brain

class TestDualModeIntegration(unittest.TestCase):

    def test_hotkey_manager_cursor_activation(self):
        press_calls = []
        release_calls = []

        def on_press(mode="cursor"):
            press_calls.append(mode)

        def on_release(mode="cursor"):
            release_calls.append(mode)

        manager = HotkeyManager(
            on_press_callback=on_press,
            on_release_callback=on_release,
            hotkey_cursor="Ctrl+Shift+Space",
            hotkey_brain="Ctrl+Alt+Space"
        )

        # Simulate pressing Ctrl + Shift + Space
        manager._on_press(keyboard.Key.ctrl_l)
        manager._on_press(keyboard.Key.shift)
        self.assertFalse(manager.is_active)

        manager._on_press(keyboard.Key.space)
        self.assertTrue(manager.is_active)
        self.assertEqual(manager.active_mode, "cursor")
        self.assertEqual(press_calls, ["cursor"])

        # Release space
        manager._on_release(keyboard.Key.space)
        self.assertFalse(manager.is_active)
        self.assertIsNone(manager.active_mode)
        self.assertEqual(release_calls, ["cursor"])

    def test_hotkey_manager_brain_activation(self):
        press_calls = []
        release_calls = []

        def on_press(mode):
            press_calls.append(mode)

        def on_release(mode):
            release_calls.append(mode)

        manager = HotkeyManager(
            on_press_callback=on_press,
            on_release_callback=on_release,
            hotkey_cursor="Ctrl+Shift+Space",
            hotkey_brain="Ctrl+Alt+Space"
        )

        # Simulate pressing Ctrl + Alt + Space
        manager._on_press(keyboard.Key.ctrl_l)
        manager._on_press(keyboard.Key.alt_l)
        self.assertFalse(manager.is_active)

        manager._on_press(keyboard.Key.space)
        self.assertTrue(manager.is_active)
        self.assertEqual(manager.active_mode, "brain")
        self.assertEqual(press_calls, ["brain"])

        # Release space
        manager._on_release(keyboard.Key.space)
        self.assertFalse(manager.is_active)
        self.assertIsNone(manager.active_mode)
        self.assertEqual(release_calls, ["brain"])

    def test_hotkey_backward_compatibility_zero_arg_callbacks(self):
        called = {"press": 0, "release": 0}

        def on_press():
            called["press"] += 1

        def on_release():
            called["release"] += 1

        manager = HotkeyManager(
            on_press_callback=on_press,
            on_release_callback=on_release
        )

        manager._on_press(keyboard.Key.ctrl)
        manager._on_press(keyboard.Key.space)
        self.assertEqual(called["press"], 1)

        manager._on_release(keyboard.Key.space)
        self.assertEqual(called["release"], 1)

    @patch("requests.post")
    def test_dispatch_to_daily_brain_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        dispatch_to_daily_brain("Fix login bug in auth controller")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("localhost:4321/api/inbox", args[0])
        self.assertEqual(kwargs["json"]["source"], "whisper_voice")
        self.assertEqual(kwargs["json"]["raw_text"], "Fix login bug in auth controller")

    @patch("requests.post")
    def test_dispatch_to_daily_brain_offline_buffering(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as tmp:
            tmp_queue_path = tmp.name

        try:
            with patch("brain_dispatcher.OFFLINE_QUEUE_PATH", tmp_queue_path):
                dispatch_to_daily_brain("Offline voice note for ticket #42")

            with open(tmp_queue_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertEqual(entry["source"], "whisper_voice")
            self.assertEqual(entry["raw_text"], "Offline voice note for ticket #42")
            self.assertIn("timestamp", entry)
        finally:
            if os.path.exists(tmp_queue_path):
                os.remove(tmp_queue_path)

    def test_hotkey_manager_custom_ctrl_space_and_fn_space(self):
        press_calls = []
        release_calls = []

        def on_press(mode):
            press_calls.append(mode)

        def on_release(mode):
            release_calls.append(mode)

        manager = HotkeyManager(
            on_press_callback=on_press,
            on_release_callback=on_release,
            hotkey_cursor="Ctrl+Space",
            hotkey_brain="Fn+Space"
        )

        # Test Ctrl+Space -> cursor
        manager._on_press(keyboard.Key.ctrl_l)
        manager._on_press(keyboard.Key.space)
        self.assertTrue(manager.is_active)
        self.assertEqual(manager.active_mode, "cursor")
        self.assertEqual(press_calls, ["cursor"])
        manager._on_release(keyboard.Key.space)
        self.assertFalse(manager.is_active)
        self.assertEqual(release_calls, ["cursor"])

        # Test Fn+Space -> brain
        fn_key = MagicMock()
        fn_key.name = "fn"
        manager._on_press(fn_key)
        manager._on_press(keyboard.Key.space)
        self.assertTrue(manager.is_active)
        self.assertEqual(manager.active_mode, "brain")
        self.assertEqual(press_calls, ["cursor", "brain"])
        manager._on_release(keyboard.Key.space)
        self.assertFalse(manager.is_active)
        self.assertEqual(release_calls, ["cursor", "brain"])

    def test_natural_language_hotkey_parsing(self):
        from hotkeys import parse_hotkey
        
        # Test "control in space"
        combo1 = parse_hotkey("control in space")
        self.assertIn(keyboard.Key.ctrl, combo1)
        self.assertIn(keyboard.Key.space, combo1)

        # Test "function and space"
        combo2 = parse_hotkey("function and space")
        self.assertIn("fn", combo2)
        self.assertIn(keyboard.Key.space, combo2)

        # Test "F2+Space"
        combo3 = parse_hotkey("F2+Space")
        self.assertIn(keyboard.Key.f2, combo3)
        self.assertIn(keyboard.Key.space, combo3)

if __name__ == "__main__":
    unittest.main()
