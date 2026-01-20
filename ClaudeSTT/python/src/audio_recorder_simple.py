import sounddevice as sd
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
        
        self.stream = None
        self.recording = False
        self.audio_queue = queue.Queue()
        self.callback_queue = queue.Queue()
        
        self._callback_thread = None
        
    def start_recording(self, callback: Optional[Callable[[np.ndarray], None]] = None):
        if self.recording:
            return
            
        self.recording = True
        
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            audio_chunk = indata[:, 0].astype(self.dtype) if self.channels == 1 else indata.astype(self.dtype)
            self.audio_queue.put(audio_chunk.copy())
            self.callback_queue.put(audio_chunk.copy())
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            device=self.device_index,
            channels=self.channels,
            dtype=self.dtype,
            callback=audio_callback
        )
        
        self.stream.start()
        
        if callback:
            self._callback_thread = threading.Thread(target=self._process_callbacks, args=(callback,))
            self._callback_thread.daemon = True
            self._callback_thread.start()
            
        logger.info("Audio recording started")
        
    def stop_recording(self):
        if not self.recording:
            return
            
        self.recording = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        if self._callback_thread:
            self._callback_thread.join(timeout=1.0)
            
        while not self.audio_queue.empty():
            self.audio_queue.get()
            
        while not self.callback_queue.empty():
            self.callback_queue.get()
            
        logger.info("Audio recording stopped")
        
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
            
    def list_devices(self):
        """List available audio devices"""
        return sd.query_devices()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_recording()