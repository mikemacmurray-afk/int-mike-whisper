import sys
import os
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.transcriber import Transcriber

def test_transcriber_initialization_and_transcribe():
    print("Initializing transcriber with base.en to test compute_type auto-detection...")
    transcriber = Transcriber(model_size="base.en")
    
    # Create empty audio buffer (1 second of silence at 16kHz)
    dummy_audio = np.zeros(16000, dtype=np.float32)
    
    print("Testing transcription with dummy audio to evaluate vad_filter and beam_size...")
    text = transcriber.transcribe(dummy_audio)
    
    print(f"Resulting text: '{text}'")
    assert text == "" # VAD filter should prevent any text from being transcribed from silence
    print("✅ SUCCESS: Transcriber initialized and transcribed without errors.")

if __name__ == "__main__":
    test_transcriber_initialization_and_transcribe()
