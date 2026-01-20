import logging
import time
import sys
from src.realtime_stt import RealtimeSTT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress Porcupine warnings
logging.getLogger('src.wake_word').setLevel(logging.ERROR)

def on_transcription(text):
    print(f"\n📝 You said: {text}")
    
    # Simple command processing
    text_lower = text.lower()
    if "stop" in text_lower or "exit" in text_lower:
        print("Goodbye!")
        return False
    elif "hello" in text_lower:
        print("👋 Hello there!")
    elif "time" in text_lower:
        print(f"🕐 Current time: {time.strftime('%H:%M:%S')}")
    elif "help" in text_lower:
        print("Available commands: hello, time, stop/exit")
    
    return True

def on_wake_word():
    print("\n🎯 Listening! Speak now...")
    
def on_start_recording():
    print("🎤 Recording...")
    
def on_stop_recording():
    print("⏸️  Processing...")

def main():
    print("Claude STT - Simple Example")
    print("===========================")
    print("\nThis example uses transcription-based wake word detection.")
    print("Say 'Claude' or 'Hey Claude' to activate, then speak your command.")
    print("Say 'stop' or 'exit' to quit.\n")
    
    # Create STT with simple configuration
    stt = RealtimeSTT(
        model_size="base",  # Use smallest model for faster response
        device="cpu",       # Force CPU to avoid CUDA issues
        language="en",
        wake_word="claude",
        use_wake_word=True,
        vad_enabled=True,   # Use voice activity detection
        on_transcription=on_transcription,
        on_wake_word=on_wake_word,
        on_start_recording=on_start_recording,
        on_stop_recording=on_stop_recording
    )
    
    try:
        # Start the STT service
        stt.start()
        
        # Keep running until interrupted
        print("Ready! Say 'Claude' to start...")
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        stt.stop()
        
if __name__ == "__main__":
    main()