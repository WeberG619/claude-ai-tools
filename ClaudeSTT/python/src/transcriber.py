import numpy as np
from faster_whisper import WhisperModel
import queue
import threading
import time
from typing import Callable, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
        initial_prompt: Optional[str] = None,
        vad_filter: bool = True,
        vad_parameters: Optional[Dict[str, Any]] = None
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.initial_prompt = initial_prompt
        self.vad_filter = vad_filter
        self.vad_parameters = vad_parameters or {
            "threshold": 0.5,
            "min_speech_duration_ms": 250,
            "max_speech_duration_s": float("inf"),
            "min_silence_duration_ms": 2000,
            "speech_pad_ms": 400
        }
        
        logger.info(f"Loading Whisper model '{model_size}' on {device}")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.transcribing = False
        self._transcription_thread = None
        
    def start(self, callback: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        if self.transcribing:
            return
            
        self.transcribing = True
        self._transcription_thread = threading.Thread(
            target=self._transcription_worker,
            args=(callback,)
        )
        self._transcription_thread.daemon = True
        self._transcription_thread.start()
        logger.info("Transcriber started")
        
    def stop(self):
        if not self.transcribing:
            return
            
        self.transcribing = False
        
        if self._transcription_thread:
            self._transcription_thread.join(timeout=5.0)
            
        while not self.audio_queue.empty():
            self.audio_queue.get()
            
        while not self.result_queue.empty():
            self.result_queue.get()
            
        logger.info("Transcriber stopped")
        
    def transcribe_audio(self, audio: np.ndarray) -> Optional[str]:
        if len(audio) == 0:
            return None
            
        try:
            audio_float = audio.astype(np.float32) / 32768.0
            
            segments, info = self.model.transcribe(
                audio_float,
                language=self.language,
                initial_prompt=self.initial_prompt,
                vad_filter=self.vad_filter,
                vad_parameters=self.vad_parameters,
                without_timestamps=True
            )
            
            transcription = " ".join([segment.text for segment in segments]).strip()
            
            return transcription if transcription else None
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
            
    def add_audio(self, audio_chunk: np.ndarray):
        self.audio_queue.put(audio_chunk)
        
    def _transcription_worker(self, callback: Optional[Callable[[str, Dict[str, Any]], None]]):
        audio_buffer = np.array([], dtype=np.int16)
        min_audio_length = int(0.5 * 16000)
        max_audio_length = int(30 * 16000)
        
        while self.transcribing:
            try:
                audio_chunk = self.audio_queue.get(timeout=0.1)
                audio_buffer = np.concatenate([audio_buffer, audio_chunk])
                
                if len(audio_buffer) >= min_audio_length:
                    if len(audio_buffer) > max_audio_length:
                        audio_to_transcribe = audio_buffer[:max_audio_length]
                        audio_buffer = audio_buffer[max_audio_length:]
                    else:
                        audio_to_transcribe = audio_buffer
                        audio_buffer = np.array([], dtype=np.int16)
                        
                    transcription = self.transcribe_audio(audio_to_transcribe)
                    
                    if transcription:
                        result = {
                            "text": transcription,
                            "timestamp": time.time(),
                            "audio_length": len(audio_to_transcribe) / 16000
                        }
                        
                        self.result_queue.put(result)
                        
                        if callback:
                            callback(transcription, result)
                            
            except queue.Empty:
                if len(audio_buffer) >= min_audio_length:
                    transcription = self.transcribe_audio(audio_buffer)
                    
                    if transcription:
                        result = {
                            "text": transcription,
                            "timestamp": time.time(),
                            "audio_length": len(audio_buffer) / 16000
                        }
                        
                        self.result_queue.put(result)
                        
                        if callback:
                            callback(transcription, result)
                            
                    audio_buffer = np.array([], dtype=np.int16)
                    
            except Exception as e:
                logger.error(f"Error in transcription worker: {e}")
                
    def get_result(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None