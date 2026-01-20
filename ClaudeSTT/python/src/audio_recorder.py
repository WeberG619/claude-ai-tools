import pyaudio
import numpy as np
import threading
import queue
import time
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)

class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        channels: int = 1,
        dtype: np.dtype = np.int16,
        device_index: Optional[int] = None
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.dtype = dtype
        self.device_index = device_index
        
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        self.audio_queue = queue.Queue()
        self.callback_queue = queue.Queue()
        
        self._recording_thread = None
        self._callback_thread = None
        
    def start_recording(self, callback: Optional[Callable[[np.ndarray], None]] = None):
        if self.recording:
            return
            
        self.recording = True
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk_size
        )
        
        self._recording_thread = threading.Thread(target=self._record_audio)
        self._recording_thread.daemon = True
        self._recording_thread.start()
        
        if callback:
            self._callback_thread = threading.Thread(target=self._process_callbacks, args=(callback,))
            self._callback_thread.daemon = True
            self._callback_thread.start()
            
        logger.info("Audio recording started")
        
    def stop_recording(self):
        if not self.recording:
            return
            
        self.recording = False
        
        if self._recording_thread:
            self._recording_thread.join(timeout=1.0)
            
        if self._callback_thread:
            self._callback_thread.join(timeout=1.0)
            
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        while not self.audio_queue.empty():
            self.audio_queue.get()
            
        while not self.callback_queue.empty():
            self.callback_queue.get()
            
        logger.info("Audio recording stopped")
        
    def _record_audio(self):
        while self.recording:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_chunk = np.frombuffer(data, dtype=self.dtype)
                
                self.audio_queue.put(audio_chunk)
                self.callback_queue.put(audio_chunk)
                
            except Exception as e:
                logger.error(f"Error recording audio: {e}")
                time.sleep(0.01)
                
    def _process_callbacks(self, callback: Callable[[np.ndarray], None]):
        while self.recording:
            try:
                audio_chunk = self.callback_queue.get(timeout=0.1)
                callback(audio_chunk)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")
                
    def get_audio_chunk(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def clear_queue(self):
        while not self.audio_queue.empty():
            self.audio_queue.get()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_recording()
        self.audio.terminate()