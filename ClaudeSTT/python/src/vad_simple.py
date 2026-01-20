import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class VoiceActivityDetector:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        energy_threshold: float = 0.01,
        speech_threshold: float = 0.3,
        silence_threshold: float = 0.1
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.energy_threshold = energy_threshold
        self.speech_threshold = speech_threshold
        self.silence_threshold = silence_threshold
        
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False
        
    def calculate_energy(self, audio_chunk: np.ndarray) -> float:
        """Calculate RMS energy of audio chunk"""
        return np.sqrt(np.mean(audio_chunk.astype(float)**2)) / 32768.0
        
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Simple energy-based speech detection"""
        energy = self.calculate_energy(audio_chunk)
        return energy > self.energy_threshold
        
    def process_audio(self, audio_chunk: np.ndarray) -> Tuple[bool, bool]:
        """
        Process audio chunk and return (is_speech, state_changed)
        """
        is_speech = self.is_speech(audio_chunk)
        state_changed = False
        
        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
            
            if not self.is_speaking and self.speech_frames > 3:
                self.is_speaking = True
                state_changed = True
                logger.debug("Speech started")
        else:
            self.silence_frames += 1
            self.speech_frames = 0
            
            if self.is_speaking and self.silence_frames > 20:
                self.is_speaking = False
                state_changed = True
                logger.debug("Speech ended")
                
        return self.is_speaking, state_changed
        
    def reset(self):
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False