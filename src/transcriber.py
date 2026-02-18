from faster_whisper import WhisperModel
import numpy as np
import logging
import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self, model_size="base.en", device=None, compute_type="float32"):
        """
        Initializes the Faster-Whisper model.
        
        model_size: "tiny.en", "base.en", "small.en", "medium.en", "large-v3"
        device: "cpu", "cuda" (defaults to auto-detect)
        compute_type: "float32", "int8", "float16" (float16 requires CUDA)
        """
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Adjust compute type for CPU if needed
        if device == "cpu" and compute_type == "float16":
            compute_type = "float32"
            
        logger.info(f"Initializing Whisper model '{model_size}' on '{device}' ({compute_type})...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_data):
        """
        Transcribes the provided audio data (numpy array).
        Returns the stitched together text.
        """
        if audio_data.size == 0:
            return ""

        # faster-whisper expects a 1D float32 array
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()

        segments, info = self.model.transcribe(audio_data, beam_size=5)
        
        text = "".join([segment.text for segment in segments]).strip()
        logger.info(f"Transcription complete: '{text}' (Language: {info.language})")
        return text
