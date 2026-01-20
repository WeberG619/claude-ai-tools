#!/usr/bin/env python
"""
Clean voice CLI that only outputs the transcribed command
"""
import sys
import time
import logging
import json
from src.realtime_stt import RealtimeSTT

# Suppress all logging output
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)

class VoiceCLI:
    def __init__(self, wake_word="claude", timeout=30):
        self.wake_word = wake_word
        self.timeout = timeout
        self.result = None
        self.activated = False
        
    def get_command(self):
        """Get a single voice command and return only the text"""
        stt = RealtimeSTT(
            model_size="base",
            device="cpu",
            language="en",
            wake_word=self.wake_word,
            use_wake_word=True,
            vad_enabled=True,
            on_transcription=self._on_transcription,
            on_wake_word=self._on_wake_word
        )
        
        # Suppress model loading output
        import io
        import contextlib
        
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            stt.start()
            
            start_time = time.time()
            while self.result is None and (time.time() - start_time) < self.timeout:
                time.sleep(0.1)
                
            stt.stop()
        
        return self.result
        
    def _on_transcription(self, text):
        if self.activated:
            self.result = text.strip()
            self.activated = False
            
    def _on_wake_word(self):
        self.activated = True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--wake-word", default="claude")
    
    args = parser.parse_args()
    
    cli = VoiceCLI(wake_word=args.wake_word, timeout=args.timeout)
    result = cli.get_command()
    
    if result:
        if args.json:
            print(json.dumps({"command": result, "success": True}))
        else:
            print(result)
    else:
        if args.json:
            print(json.dumps({"command": None, "success": False}))
        # Don't print anything in text mode for null results