"""
Terminal-integrated STT that captures voice commands and returns them as text
"""
import sys
import time
import logging
from src.realtime_stt import RealtimeSTT

# Configure minimal logging
logging.basicConfig(level=logging.WARNING, format='%(message)s')

class TerminalSTT:
    def __init__(self, wake_word="claude", timeout=30):
        self.wake_word = wake_word
        self.timeout = timeout
        self.last_transcription = None
        self.is_listening = False
        
        self.stt = RealtimeSTT(
            model_size="base",
            device="cpu",
            language="en",
            wake_word=wake_word,
            use_wake_word=True,
            vad_enabled=True,
            on_transcription=self._on_transcription,
            on_wake_word=self._on_wake_word,
            on_start_recording=self._on_start_recording,
            on_stop_recording=self._on_stop_recording
        )
        
    def _on_transcription(self, text):
        self.last_transcription = text
        self.is_listening = False
        
    def _on_wake_word(self):
        self.is_listening = True
        print("Listening...", end='', flush=True)
        
    def _on_start_recording(self):
        pass
        
    def _on_stop_recording(self):
        print(" Processing...", end='', flush=True)
        
    def get_command(self, prompt=None):
        """Get a single voice command and return it"""
        if prompt:
            print(prompt)
            
        self.last_transcription = None
        self.stt.start()
        
        start_time = time.time()
        try:
            while self.last_transcription is None and (time.time() - start_time) < self.timeout:
                time.sleep(0.1)
                
            return self.last_transcription
            
        finally:
            self.stt.stop()
            print()  # New line after command
            
    def listen_continuous(self):
        """Listen continuously and print commands"""
        print(f"Say '{self.wake_word}' followed by your command. Press Ctrl+C to stop.")
        
        self.stt.on_transcription = lambda text: print(f"\nCommand: {text}")
        self.stt.start()
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stt.stop()

# Command-line usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Terminal STT")
    parser.add_argument("--wake-word", default="claude", help="Wake word to use")
    parser.add_argument("--continuous", action="store_true", help="Listen continuously")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    terminal_stt = TerminalSTT(wake_word=args.wake_word, timeout=args.timeout)
    
    if args.continuous:
        terminal_stt.listen_continuous()
    else:
        # Single command mode
        command = terminal_stt.get_command(f"Say '{args.wake_word}' followed by your command:")
        if command:
            print(f"You said: {command}")
        else:
            print("No command received")