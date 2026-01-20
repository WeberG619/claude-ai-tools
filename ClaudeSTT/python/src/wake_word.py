import numpy as np
import struct
import pvporcupine
from typing import List, Optional, Callable
import logging
import os

logger = logging.getLogger(__name__)

class WakeWordDetector:
    def __init__(
        self,
        wake_words: List[str] = ["claude"],
        sensitivities: Optional[List[float]] = None,
        access_key: Optional[str] = None,
        model_path: Optional[str] = None
    ):
        self.wake_words = [w.lower() for w in wake_words]
        self.access_key = access_key or os.environ.get("PORCUPINE_ACCESS_KEY")
        self.porcupine = None
        self.frame_length = 512  # Default frame length
        self.sample_rate = 16000  # Default sample rate
        
        if not self.access_key:
            logger.warning("No Porcupine access key provided. Wake word detection disabled.")
            return
            
        try:
            keywords = []
            for word in self.wake_words:
                if word in pvporcupine.KEYWORDS:
                    keywords.append(word)
                else:
                    logger.warning(f"Wake word '{word}' not available in Porcupine. Skipping.")
                    
            if not keywords:
                logger.warning("No valid wake words found. Using 'computer' as default.")
                keywords = ["computer"]
                
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=keywords,
                sensitivities=sensitivities or [0.5] * len(keywords),
                model_path=model_path
            )
            
            self.frame_length = self.porcupine.frame_length
            self.sample_rate = self.porcupine.sample_rate
            
            logger.info(f"Wake word detector initialized with keywords: {keywords}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            self.porcupine = None
            
    def process_audio(self, audio_chunk: np.ndarray) -> Optional[int]:
        if not self.porcupine:
            return None
            
        if len(audio_chunk) != self.frame_length:
            return None
            
        try:
            pcm = struct.unpack_from("h" * self.frame_length, audio_chunk.tobytes())
            keyword_index = self.porcupine.process(pcm)
            
            if keyword_index >= 0:
                logger.info(f"Wake word detected: {self.wake_words[keyword_index]}")
                return keyword_index
                
        except Exception as e:
            logger.error(f"Error processing audio for wake word: {e}")
            
        return None
        
    def delete(self):
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
            
    def __del__(self):
        self.delete()


class SimpleWakeWordDetector:
    def __init__(
        self,
        wake_word: str = "claude",
        threshold: float = 0.5,
        sample_rate: int = 16000
    ):
        self.wake_word = wake_word.lower()
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.audio_buffer = np.array([], dtype=np.int16)
        self.buffer_duration = 2.0
        self.max_buffer_size = int(self.buffer_duration * self.sample_rate)
        
    def process_audio(self, audio_chunk: np.ndarray, transcription: str) -> bool:
        self.audio_buffer = np.concatenate([self.audio_buffer, audio_chunk])
        
        if len(self.audio_buffer) > self.max_buffer_size:
            self.audio_buffer = self.audio_buffer[-self.max_buffer_size:]
            
        if transcription:
            transcription_lower = transcription.lower().strip()
            
            if self.wake_word in transcription_lower:
                logger.info(f"Wake word '{self.wake_word}' detected in transcription: {transcription}")
                self.audio_buffer = np.array([], dtype=np.int16)
                return True
                
            if transcription_lower.startswith("hey") and self.wake_word in transcription_lower:
                logger.info(f"Wake phrase 'hey {self.wake_word}' detected")
                self.audio_buffer = np.array([], dtype=np.int16)
                return True
                
        return False
        
    def reset(self):
        self.audio_buffer = np.array([], dtype=np.int16)