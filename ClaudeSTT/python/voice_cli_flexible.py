#!/usr/bin/env python
"""
Voice CLI with flexible wake word detection
"""
import sys
import time
import logging
import json
import contextlib
import io
from src.realtime_stt import RealtimeSTT
from src.wake_word_flexible import FlexibleWakeWordDetector

# Suppress logging
logging.basicConfig(level=logging.CRITICAL)

class FlexibleVoiceCLI:
    def __init__(self, wake_word="claude", timeout=30):
        self.wake_word = wake_word
        self.timeout = timeout
        self.result = None
        self.wake_detector = FlexibleWakeWordDetector(wake_word=wake_word)
        self.activated = False
        
    def get_command(self):
        """Get voice command with flexible wake word detection"""
        
        # Suppress output during STT initialization
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            stt = RealtimeSTT(
                model_size="base",
                device="cpu", 
                language="en",
                wake_word=self.wake_word,
                use_wake_word=False,  # We'll handle wake word ourselves
                vad_enabled=True,
                on_transcription=self._on_transcription
            )
            
            stt.start()
            
        start_time = time.time()
        while self.result is None and (time.time() - start_time) < self.timeout:
            time.sleep(0.1)
            
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            stt.stop()
        
        return self.result
        
    def _on_transcription(self, text):
        """Handle transcription and check for wake word"""
        if not text:
            return
            
        # Check if wake word is detected
        if self.wake_detector._detect_wake_word(text):
            # Extract command after wake word
            command = self._extract_command(text)
            if command:
                self.result = command
        elif self.activated:
            # If already activated, any speech is the command
            self.result = text.strip()
            
    def _extract_command(self, text: str) -> str:
        """Extract command from text containing wake word"""
        text_lower = text.lower()
        
        # Find wake word variations and extract what comes after
        variations = ['claude', 'clod', 'claud', 'cloud', 'glad', 'clot']
        
        for variation in variations:
            if variation in text_lower:
                # Find position and extract remainder
                pos = text_lower.find(variation)
                after_wake = text[pos + len(variation):].strip()
                
                # Remove common filler words at the start
                fillers = ['please', 'could you', 'can you', 'would you']
                for filler in fillers:
                    if after_wake.lower().startswith(filler):
                        after_wake = after_wake[len(filler):].strip()
                        
                return after_wake
                
        # If no specific variation found, return whole text (fallback)
        return text.strip()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--wake-word", default="claude")
    
    args = parser.parse_args()
    
    cli = FlexibleVoiceCLI(wake_word=args.wake_word, timeout=args.timeout)
    result = cli.get_command()
    
    if result:
        if args.json:
            print(json.dumps({"command": result, "success": True}))
        else:
            print(result)
    else:
        if args.json:
            print(json.dumps({"command": None, "success": False}))