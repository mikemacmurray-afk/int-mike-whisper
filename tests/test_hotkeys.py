import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.hotkeys import HotkeyManager

def test_hotkeys():
    print("\n--- Global Hotkey Test ---")
    print("Hold down 'CTRL + SHIFT + SPACE' to activate.")
    print("Release to deactivate.")
    print("Press CTRL+C in this terminal to exit test.")
    
    def on_press():
        print(">>> [ACTIVE] Recording... <<<", end="\r")

    def on_release():
        print("\n--- [INACTIVE] Stopped. ---")

    manager = HotkeyManager(on_press_callback=on_press, on_release_callback=on_release)
    manager.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop()
        print("\nTest finished.")

if __name__ == "__main__":
    test_hotkeys()
