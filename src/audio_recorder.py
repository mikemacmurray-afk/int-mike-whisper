import sounddevice as sd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording_buffer = []
        self.is_recording = False
        
        # Initialize the stream but don't start it yet
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            dtype='float32'
        )

    def _audio_callback(self, indata, frames, time, status):
        """This is called by sounddevice for every audio chunk."""
        if status:
            logger.warning(f"Audio Stream Status: {status}")
        if self.is_recording:
            self.recording_buffer.append(indata.copy())

    def start_recording(self):
        """Starts capturing audio into the buffer."""
        self.recording_buffer = []
        self.is_recording = True
        if not self.stream.active:
            self.stream.start()
        logger.info("Started recording audio...")

    def stop_recording(self):
        """Stops capturing and returns the accumulated audio data."""
        self.is_recording = False
        logger.info("Stopped recording audio.")
        
        if not self.recording_buffer:
            return np.array([], dtype=np.float32)
            
        data = np.concatenate(self.recording_buffer, axis=0)
        self.recording_buffer = []
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
