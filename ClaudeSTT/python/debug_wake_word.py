"""
Debug wake word detection
"""
import sounddevice as sd
import numpy as np
import time
from faster_whisper import WhisperModel
import re

def test_wake_word_variations():
    """Test different wake word patterns"""
    print("Wake Word Debug Test")
    print("===================")
    print("Say 'Claude hello' and we'll see what gets transcribed...")
    print("\nPress Enter when ready...")
    input()

    # Record audio
    print("Recording for 5 seconds... say 'Claude hello'!")
    recording = []
    sample_rate = 16000

    def callback(indata, frames, time, status):
        recording.append(indata.copy())

    with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
        time.sleep(5)

    print("Processing...")

    # Transcribe
    audio_data = np.concatenate(recording, axis=0).flatten()
    audio_float = audio_data.astype(np.float32) / 32768.0

    model = WhisperModel("base", device="cpu")
    segments, info = model.transcribe(audio_float, language="en")
    result = " ".join([segment.text for segment in segments]).strip()

    print(f"\nTranscribed: '{result}'")
    print(f"Length: {len(result)} characters")
    
    # Test different wake word patterns
    wake_patterns = [
        r'\bclaude\b',           # Exact word
        r'claude',               # Anywhere in text
        r'\bclod\b',            # Common mishearing
        r'\bclaud\b',           # Without 'e'
        r'\bcloud\b',           # Another mishearing
        r'\bglad\b',            # Similar sound
        r'\bclot\b',            # Phonetic variation
    ]
    
    result_lower = result.lower()
    print(f"\nTesting wake word patterns on: '{result_lower}'")
    
    for pattern in wake_patterns:
        if re.search(pattern, result_lower):
            print(f"✅ Found pattern: {pattern}")
            return True
        else:
            print(f"❌ No match: {pattern}")
    
    # Check for similar sounding words
    words = result_lower.split()
    print(f"\nIndividual words: {words}")
    
    for word in words:
        # Calculate simple similarity to "claude"
        if len(word) >= 3:
            if word.startswith('cl') or word.startswith('gl'):
                print(f"🤔 Possible match: '{word}' (starts with cl/gl)")
            if 'lau' in word or 'lou' in word:
                print(f"🤔 Possible match: '{word}' (contains lau/lou)")
    
    return False

def create_flexible_wake_word_detector():
    """Create a more flexible wake word detector"""
    
    class FlexibleWakeWordDetector:
        def __init__(self, wake_word="claude"):
            self.wake_word = wake_word.lower()
            
        def detect(self, text):
            """Detect wake word with fuzzy matching"""
            if not text:
                return False
                
            text_lower = text.lower().strip()
            
            # Exact match
            if self.wake_word in text_lower:
                return True
                
            # Common misheard variations
            variations = [
                'clod', 'claud', 'cloud', 'glad', 'clot', 
                'claw', 'clear', 'close', 'cloth'
            ]
            
            words = text_lower.split()
            for word in words:
                if word in variations:
                    return True
                    
                # Fuzzy matching - if word starts with 'cl' and has similar length
                if (word.startswith('cl') or word.startswith('gl')) and 3 <= len(word) <= 6:
                    return True
                    
            return False
    
    return FlexibleWakeWordDetector()

if __name__ == "__main__":
    success = test_wake_word_variations()
    
    if not success:
        print(f"\n💡 Wake word 'claude' not detected clearly.")
        print("This could be due to:")
        print("- Pronunciation differences")
        print("- Background noise")
        print("- Microphone sensitivity")
        print("- Whisper transcription variations")
        
        print(f"\n🔧 Try speaking:")
        print("- Slower and clearer")
        print("- Closer to microphone") 
        print("- In a quieter environment")
        print("- Use 'Hey Claude' instead")
    else:
        print(f"\n✅ Wake word detection working!")