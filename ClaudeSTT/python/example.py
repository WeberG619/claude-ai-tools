import logging
import time
import sys
from src.realtime_stt import RealtimeSTT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def on_transcription(text):
    print(f"\n📝 Final transcription: {text}")
    
def on_wake_word():
    print("\n🎯 Wake word detected!")
    
def on_start_recording():
    print("🎤 Recording started...")
    
def on_stop_recording():
    print("🛑 Recording stopped.")

def main():
    print("Claude STT - Real-time Speech-to-Text")
    print("=====================================")
    print("Say 'Claude' or 'Hey Claude' to activate")
    print("Press Ctrl+C to stop\n")
    
    stt = RealtimeSTT(
        model_size="base",
        device="cpu",
        language="en",
        wake_word="claude",
        use_wake_word=True,
        vad_enabled=True,
        on_transcription=on_transcription,
        on_wake_word=on_wake_word,
        on_start_recording=on_start_recording,
        on_stop_recording=on_stop_recording
    )
    
    try:
        with stt:
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        
if __name__ == "__main__":
    main()