"""
Voice recognition diagnostic tool
"""
import sounddevice as sd
import numpy as np
import time
import sys

def test_microphone():
    """Test if microphone is working"""
    print("🎤 Testing microphone...")
    print("Speak for 3 seconds:")
    
    recording = []
    sample_rate = 16000
    
    def callback(indata, frames, time, status):
        recording.append(indata.copy())
        volume = np.sqrt(np.mean(indata**2))
        bar = '█' * min(int(volume * 50), 20)
        print(f"\r   Volume: |{bar:<20}|", end='', flush=True)
    
    try:
        with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
            time.sleep(3)
        
        print("\n")
        audio_data = np.concatenate(recording, axis=0)
        max_vol = np.max(np.abs(audio_data))
        avg_vol = np.sqrt(np.mean(audio_data**2))
        
        print(f"   Max volume: {max_vol:.4f}")
        print(f"   Avg volume: {avg_vol:.4f}")
        
        if max_vol < 0.001:
            print("   ❌ No audio detected!")
            return False
        elif max_vol < 0.01:
            print("   ⚠️  Very quiet - speak louder")
            return False
        else:
            print("   ✅ Microphone working!")
            return True
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_whisper():
    """Test if Whisper model loads"""
    print("\n🤖 Testing Whisper model...")
    try:
        from faster_whisper import WhisperModel
        print("   Loading model...")
        model = WhisperModel("base", device="cpu")
        print("   ✅ Whisper model loaded!")
        return True
    except Exception as e:
        print(f"   ❌ Error loading Whisper: {e}")
        return False

def test_transcription():
    """Test actual transcription"""
    print("\n🎯 Testing transcription...")
    print("Say something clearly (no wake word needed):")
    
    try:
        import sounddevice as sd
        from faster_whisper import WhisperModel
        
        # Record audio
        recording = []
        sample_rate = 16000
        duration = 5
        
        def callback(indata, frames, time, status):
            recording.append(indata.copy())
        
        with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
            for i in range(duration, 0, -1):
                print(f"\r   Recording... {i} seconds left", end='', flush=True)
                time.sleep(1)
        
        print("\n   Processing audio...")
        
        # Convert to format for Whisper
        audio_data = np.concatenate(recording, axis=0).flatten()
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        # Transcribe
        model = WhisperModel("base", device="cpu")
        segments, info = model.transcribe(audio_float, language="en")
        
        result = " ".join([segment.text for segment in segments]).strip()
        
        if result:
            print(f"   ✅ Transcribed: '{result}'")
            return True
        else:
            print("   ❌ No transcription result")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_wake_word():
    """Test wake word detection in transcription"""
    print("\n🔍 Testing wake word detection...")
    print("Say 'Claude hello world' clearly:")
    
    try:
        # Use the same code as test_transcription but check for wake word
        import sounddevice as sd
        from faster_whisper import WhisperModel
        
        recording = []
        sample_rate = 16000
        duration = 5
        
        def callback(indata, frames, time, status):
            recording.append(indata.copy())
        
        with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
            for i in range(duration, 0, -1):
                print(f"\r   Recording... {i} seconds left", end='', flush=True)
                time.sleep(1)
        
        print("\n   Processing...")
        
        audio_data = np.concatenate(recording, axis=0).flatten()
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        model = WhisperModel("base", device="cpu")
        segments, info = model.transcribe(audio_float, language="en")
        result = " ".join([segment.text for segment in segments]).strip()
        
        print(f"   Transcribed: '{result}'")
        
        if "claude" in result.lower():
            print("   ✅ Wake word detected!")
            return True
        else:
            print("   ❌ Wake word 'claude' not found in transcription")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("Voice Recognition Diagnostics")
    print("=" * 40)
    
    tests = [
        ("Microphone", test_microphone),
        ("Whisper Model", test_whisper),
        ("Transcription", test_transcription),
        ("Wake Word", test_wake_word)
    ]
    
    results = {}
    
    for name, test_func in tests:
        results[name] = test_func()
        if not results[name]:
            print(f"\n❌ {name} test failed - stopping here")
            break
        time.sleep(1)
    
    print("\n" + "=" * 40)
    print("DIAGNOSTIC SUMMARY:")
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    if all(results.values()):
        print("\n🎉 All tests passed! Voice recognition should work.")
        print("\nTry running: .\v.ps1 -Execute")
    else:
        print("\n🔧 Some tests failed. Check the issues above.")

if __name__ == "__main__":
    main()