import sounddevice as sd
import numpy as np
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamingSileroVAD:
    def __init__(self, threshold=0.5):
        from faster_whisper.vad import get_vad_model
        # get_vad_model caching protects from reloading
        self.model = get_vad_model()
        self.threshold = threshold
        self.reset_states()

    def reset_states(self):
        self.h = np.zeros((1, 1, 128), dtype="float32")
        self.c = np.zeros((1, 1, 128), dtype="float32")
        self.context = np.zeros((1, 64), dtype="float32")

    def process_chunk(self, audio_chunk: np.ndarray) -> float:
        """Processes exactly 512 samples and returns speech probability."""
        if len(audio_chunk) < 512:
            return 0.0
        batched_audio = np.concatenate([self.context[0], audio_chunk]).reshape(1, 576).astype(np.float32)
        self.context[0] = audio_chunk[-64:]
        
        output, self.h, self.c = self.model.session.run(
            None,
            {"input": batched_audio, "h": self.h, "c": self.c},
        )
        return output[0][0]

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording_buffer = []
        self.ring_buffer = []  # To keep last pre-speech context
        self.is_recording = False
        
        self.blocksize = 1536 # Multiple of 512 for Silero VAD (96ms)
        self.vad = StreamingSileroVAD(threshold=0.5)
        self.silence_timeout = 2.0
        self.last_speech_time = 0
        self.timeout_triggered = False
        self.speech_detected_since_last_poll = False
        
        # Initialize the stream but don't start it yet
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.blocksize,
            callback=self._audio_callback,
            dtype='float32'
        )

    def _audio_callback(self, indata, frames, time_info, status):
        """This is called by sounddevice for every audio chunk."""
        if status:
            logger.warning(f"Audio Stream Status: {status}")
        if not self.is_recording:
            return
            
        audio_data = indata[:, 0].copy()
        
        # Check VAD in 512-sample chunks
        is_speech = False
        for i in range(0, len(audio_data), 512):
            chunk = audio_data[i:i+512]
            if len(chunk) == 512:
                prob = self.vad.process_chunk(chunk)
                if prob > self.vad.threshold:
                    is_speech = True
                    break
                    
        current_time = time.time()
        
        if is_speech:
            self.last_speech_time = current_time
            self.speech_detected_since_last_poll = True
            
            # Attach context from right before speech started
            if self.ring_buffer:
                self.recording_buffer.extend(self.ring_buffer)
                self.ring_buffer = []
                
            self.recording_buffer.append(audio_data)
        else:
            # Silence: retain small ring buffer to prevent harsh cuts
            self.ring_buffer = [audio_data]
            
            # Silence Timeout Check
            if current_time - self.last_speech_time > self.silence_timeout:
                self.timeout_triggered = True

    def start_recording(self):
        """Starts capturing audio into the buffer."""
        self.recording_buffer = []
        self.ring_buffer = []
        self.is_recording = True
        self.timeout_triggered = False
        self.speech_detected_since_last_poll = False
        self.vad.reset_states()
        self.last_speech_time = time.time()
        
        if not self.stream.active:
            self.stream.start()
        logger.info("Started recording audio...")

    def get_current_buffer(self):
        """Returns the current accumulated audio data without stopping."""
        if not self.recording_buffer:
            return np.array([], dtype=np.float32)
        # Combine current chunks
        return np.concatenate(list(self.recording_buffer), axis=0)

    def stop_recording(self):
        """Stops capturing and returns the accumulated audio data."""
        self.is_recording = False
        logger.info("Stopped recording audio.")
        
        if not self.recording_buffer:
            return np.array([], dtype=np.float32)
            
        data = np.concatenate(self.recording_buffer, axis=0)
        self.recording_buffer = []
        self.ring_buffer = []
        return data

    def capture_fixed_duration(self, duration=3):
        """Records for a fixed duration and returns the result."""
        logger.info(f"Recording for {duration} seconds...")
        recording = sd.rec(int(duration * self.sample_rate), 
                           samplerate=self.sample_rate, 
                           channels=self.channels, 
                           dtype='float32')
        sd.wait()
        return recording

    def __del__(self):
        if hasattr(self, 'stream') and self.stream:
            self.stream.stop()
            self.stream.close()
