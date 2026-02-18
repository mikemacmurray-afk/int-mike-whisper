import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.audio_recorder import AudioRecorder
from src.transcriber import Transcriber

def test_live_transcription():
    recorder = AudioRecorder()
    # Using 'tiny.en' for faster initial download and test
    transcriber = Transcriber(model_size="tiny.en")
    
    print("\n--- Live Transcription Test ---")
    print("Please Speak clearly for 3 seconds (try saying 'Hello Mike Whisper test')...")
    time.sleep(1)
    
    audio_data = recorder.capture_fixed_duration(duration=3)
    
    print("\nProcessing transcription...")
    start_time = time.time()
    text = transcriber.transcribe(audio_data)
    duration = time.time() - start_time
    
    print(f"\nResults:")
    print(f" - Transcribed Text: '{text}'")
    print(f" - Processing Time: {duration:.2f}s")
    
    if text:
        print("\n✅ SUCCESS: Transcription received!")
    else:
        print("\n❌ FAILED: No text transcribed. Ensure you spoke during the recording.")

if __name__ == "__main__":
    test_live_transcription()
