from faster_whisper import WhisperModel
import numpy as np
import logging
import ctranslate2

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
            try:
                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception as e:
                logger.warning(f"Error checking CUDA devices via ctranslate2: {e}. Defaulting to cpu.")
                device = "cpu"
        
        # Resolve model path
        import sys
        import os
        
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        local_model_path = os.path.join(base_path, "models", model_size)
        
        if os.path.exists(local_model_path) and os.path.isdir(local_model_path):
            logger.info(f"Loading Whisper model from bundled local path: {local_model_path}")
            model_to_load = local_model_path
        else:
            logger.info(f"Local model path not found at {local_model_path}. Fetching '{model_size}' from Hugging Face...")
            model_to_load = model_size

        if compute_type is None:
            compute_type = "float16" if device == "cuda" else "int8"
            
        logger.info(f"Initializing Whisper model '{model_size}' on '{device}' ({compute_type})...")
        try:
            self.model = WhisperModel(
                model_to_load, 
                device=device, 
                compute_type=compute_type,
                cpu_threads=4 # Limit CPU threads to reduce system load during transcription
            )
        except Exception as e:
            if device == "cuda":
                logger.warning(f"Failed to initialize Whisper on CUDA: {e}. Falling back to CPU.")
                device = "cpu"
                compute_type = "int8"
                logger.info(f"Re-initializing Whisper model '{model_size}' on '{device}' ({compute_type})...")
                self.model = WhisperModel(
                    model_to_load,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=4
                )
            else:
                raise e

    def transcribe(self, audio_data, initial_prompt=None):
        """
        Transcribes the provided audio data (numpy array).
        Returns the stitched together text.
        """
        if audio_data.size < 8000: # Discard if less than 500ms
            return ""

        # faster-whisper expects a 1D float32 array
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()

        # Input is already pre-gated by VAD, so no need for vad_filter here.
        segments, info = self.model.transcribe(
            audio_data, 
            beam_size=1,
            initial_prompt=initial_prompt
        )
        
        text = "".join([segment.text for segment in segments]).strip()
        logger.info(f"Transcription complete: '{text}' (Language: {info.language})")
        return text
