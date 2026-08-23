import os
import sys
import wave
import logging
import tempfile
import subprocess
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self, model_size="base.en", device=None, compute_type=None):
        """
        Initializes the Transcriber by resolving paths to the whisper-cli executable and the GGUF model.
        """
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        # Resolve whisper-cli.exe path
        self.whisper_exe = os.path.join(base_path, "src", "bin", "whisper-cli.exe")
        if not os.path.exists(self.whisper_exe):
            self.whisper_exe = os.path.join(base_path, "whisper-cli.exe")
            
        # Map model size parameter to GGUF filename
        gguf_name = "ggml-base.en.bin"
        if "tiny" in model_size:
            gguf_name = "ggml-tiny.en.bin"
        elif "small" in model_size:
            gguf_name = "ggml-small.en.bin"
        elif "medium" in model_size:
            gguf_name = "ggml-medium.en.bin"
            
        self.model_path = os.path.join(base_path, "models", gguf_name)
        
        # Fall back to ggml-base.en.bin if the requested model size doesn't exist locally
        if not os.path.exists(self.model_path):
            self.model_path = os.path.join(base_path, "models", "ggml-base.en.bin")
            
        logger.info(f"Transcriber initialized with executable: {self.whisper_exe}")
        logger.info(f"Transcriber initialized with model: {self.model_path}")

    def transcribe(self, audio_data, initial_prompt=None):
        """
        Transcribes the provided audio data (numpy array) using the whisper-cli executable.
        Returns the clean transcribed text.
        """
        if audio_data.size < 8000:  # Discard if less than 500ms
            return ""

        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()

        # Create temporary file to write WAV input
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav_path = f.name
            
        try:
            # Convert float32 array to 16-bit PCM
            pcm_data = (audio_data * 32767.0).clip(-32768.0, 32767.0).astype(np.int16)
            
            # Write mono 16kHz PCM WAV file
            with wave.open(temp_wav_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(pcm_data.tobytes())
                
            # Build command args
            cmd = [
                self.whisper_exe,
                "-m", self.model_path,
                "-f", temp_wav_path,
                "-nt",  # No timestamps
                "-np",  # No print progress / debug logs
                "-t", "4",  # Use 4 threads
            ]
            
            if initial_prompt:
                cmd.extend(["--prompt", initial_prompt])
                
            logger.info(f"Executing whisper-cli: {' '.join(cmd)}")
            
            # Run subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            
            if result.returncode != 0:
                logger.error(f"whisper-cli failed with exit code {result.returncode}. Stderr: {result.stderr}")
                return ""
                
            text = result.stdout.strip()
            # Clean up newlines or formatting
            text = " ".join([line.strip() for line in text.split("\n") if line.strip()]).strip()
            
            logger.info(f"Transcription complete: '{text}'")
            return text
            
        except Exception as e:
            logger.error(f"Error during transcription subprocess call: {e}")
            return ""
            
        finally:
            if os.path.exists(temp_wav_path):
                os.remove(temp_wav_path)
