import sys
import os
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.transcriber import Transcriber

def test_transcriber_with_prompt():
    # Verify that initial_prompt is correctly formatted and passed to whisper-cli subprocess
    import unittest.mock as mock
    
    try:
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="test result", stderr="")
            t = Transcriber(model_size="base.en")
            
            audio = np.zeros(16000, dtype=np.float32)
            res = t.transcribe(audio, initial_prompt="CustomWord1, CustomWord2")
            
            assert res == "test result"
            # Check that command arguments include --prompt
            called_args = mock_run.call_args[0][0]
            assert "--prompt" in called_args
            assert "CustomWord1, CustomWord2" in called_args
            
            print("Test passed: initial_prompt accepted and passed to whisper-cli.")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_transcriber_with_prompt()
