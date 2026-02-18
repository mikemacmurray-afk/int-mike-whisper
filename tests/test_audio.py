import sys
import os
import numpy as np
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.audio_recorder import AudioRecorder

def test_audio_capture():
    recorder = AudioRecorder()
    
    print("\n--- Audio Diagnostic Test ---")
    print("Please Speak for 3 seconds when recording starts...")
    time.sleep(1)
    
    audio_data = recorder.capture_fixed_duration(duration=3)
    
    # Calculate stats
    max_amplitude = np.max(np.abs(audio_data))
    rms = np.sqrt(np.mean(audio_data**2))
    
    print(f"\nResults:")
    print(f" - Data Points: {len(audio_data)}")
    print(f" - Max Amplitude: {max_amplitude:.4f}")
    print(f" - RMS (Volume): {rms:.4f}")
    
    if max_amplitude > 0.01:
        print("\n✅ SUCCESS: Audio captured and it's not silent!")
    elif max_amplitude > 0:
        print("\n⚠️ WARNING: Audio captured but it is very quiet. Check your mic gain.")
    else:
        print("\n❌ FAILED: Silence detected. Check your default microphone settings.")

if __name__ == "__main__":
    test_audio_capture()
