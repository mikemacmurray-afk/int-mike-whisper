from faster_whisper import WhisperModel
import numpy as np
import logging
import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self, model_size="base.en", device=None, compute_type=None):
        """
        Initializes the Faster-Whisper model.
        
        model_size: "tiny.en", "base.en", "small.en", "medium.en", "large-v3"
        device: "cpu", "cuda" (defaults to auto-detect)
        compute_type: "float32", "int8", "float16", or None (auto-detect)
        """
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if compute_type is None:
            compute_type = "float16" if device == "cuda" else "int8"
            
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

        # Optimizations: greedy decoding (beam_size=1) and VAD filtering to skip silence
        segments, info = self.model.transcribe(
            audio_data, 
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        text = "".join([segment.text for segment in segments]).strip()
        logger.info(f"Transcription complete: '{text}' (Language: {info.language})")
        return text
