import numpy as np
import re
from typing import List, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class FlexibleWakeWordDetector:
    def __init__(
        self,
        wake_word: str = "claude",
        sample_rate: int = 16000,
        sensitivity: float = 0.7  # Lower = more sensitive
    ):
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        self.sensitivity = sensitivity
        self.audio_buffer = np.array([], dtype=np.int16)
        self.buffer_duration = 3.0  # Keep 3 seconds of audio
        self.max_buffer_size = int(self.buffer_duration * self.sample_rate)
        
        # Common variations and mishearings of "claude"
        self.variations = [
            'claude', 'clod', 'claud', 'cloud', 'glad', 'clot',
            'claw', 'clear', 'close', 'cloth', 'clawed', 'crowded'
        ]
        
        logger.info(f"Flexible wake word detector initialized for '{wake_word}'")
        
    def process_audio(self, audio_chunk: np.ndarray, transcription: str) -> bool:
        """Process audio and check for wake word in transcription"""
        # Add to buffer
        self.audio_buffer = np.concatenate([self.audio_buffer, audio_chunk])
        
        # Trim buffer
        if len(self.audio_buffer) > self.max_buffer_size:
            self.audio_buffer = self.audio_buffer[-self.max_buffer_size:]
            
        # Check transcription for wake word
        if transcription:
            if self._detect_wake_word(transcription):
                logger.info(f"Wake word detected in: '{transcription}'")
                self.audio_buffer = np.array([], dtype=np.int16)  # Clear buffer
                return True
                
        return False
        
    def _detect_wake_word(self, text: str) -> bool:
        """Flexible wake word detection"""
        if not text:
            return False
            
        text_lower = text.lower().strip()
        words = re.findall(r'\b\w+\b', text_lower)
        
        # Method 1: Exact variations
        for variation in self.variations:
            if variation in text_lower:
                logger.debug(f"Exact match found: '{variation}' in '{text_lower}'")
                return True
                
        # Method 2: Fuzzy matching for individual words
        for word in words:
            if self._fuzzy_match(word, self.wake_word):
                logger.debug(f"Fuzzy match: '{word}' matches '{self.wake_word}'")
                return True
                
        # Method 3: Phonetic similarity
        for word in words:
            if self._phonetic_similarity(word, self.wake_word):
                logger.debug(f"Phonetic match: '{word}' sounds like '{self.wake_word}'")
                return True
                
        return False
        
    def _fuzzy_match(self, word: str, target: str) -> bool:
        """Simple fuzzy matching"""
        if len(word) < 3:
            return False
            
        # Must start with similar sound
        if not (word.startswith('cl') or word.startswith('gl') or word.startswith('cr')):
            return False
            
        # Similar length
        if abs(len(word) - len(target)) > 2:
            return False
            
        # Calculate similarity (simple character overlap)
        common_chars = sum(1 for c in word if c in target)
        similarity = common_chars / max(len(word), len(target))
        
        return similarity >= self.sensitivity
        
    def _phonetic_similarity(self, word: str, target: str) -> bool:
        """Check phonetic similarity"""
        # Simplified phonetic rules for "claude"
        phonetic_patterns = [
            r'^cl.{1,3}d?$',    # cl + 1-3 chars + optional d
            r'^gl.{1,3}d?$',    # gl + 1-3 chars + optional d  
            r'^cr.{1,3}d?$',    # cr + 1-3 chars + optional d
        ]
        
        for pattern in phonetic_patterns:
            if re.match(pattern, word) and len(word) >= 3:
                return True
                
        return False
        
    def reset(self):
        """Reset the detector"""
        self.audio_buffer = np.array([], dtype=np.int16)