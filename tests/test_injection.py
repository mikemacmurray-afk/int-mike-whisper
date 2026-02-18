import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.injector import TextInjector

def test_injection():
    injector = TextInjector()
    
    print("\n--- Text Injection Test ---")
    print("Switch focus to a Notepad or text field NOW.")
    print("Injection will start in 3 seconds...")
    
    for i in range(3, 0, -1):
        print(f"{i}...", end="\r")
        time.sleep(1)
    
    test_text = "Hello! This text was injected by MikeWhisper's injector module."
    injector.inject(test_text)
    
    print("\nInjection command sent. Check your active window.")

if __name__ == "__main__":
    test_injection()
