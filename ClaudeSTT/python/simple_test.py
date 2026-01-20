"""
Very simple test - just record and transcribe
"""
import sounddevice as sd
import numpy as np
import time
from faster_whisper import WhisperModel

print("Simple Voice Test")
print("================")
print("This will record for 5 seconds and transcribe what you say.")
print("You don't need to say 'Claude' - just speak normally.")
print("\nPress Enter when ready...")
input()

# Record audio
print("Recording... speak now!")
recording = []
sample_rate = 16000

def callback(indata, frames, time, status):
    recording.append(indata.copy())
    volume = np.sqrt(np.mean(indata**2))
    if volume > 0.01:
        print("🎤", end='', flush=True)
    else:
        print(".", end='', flush=True)

with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
    time.sleep(5)

print("\n\nProcessing...")

# Convert and transcribe
audio_data = np.concatenate(recording, axis=0).flatten()
audio_float = audio_data.astype(np.float32) / 32768.0

print("Loading Whisper model...")
model = WhisperModel("base", device="cpu")

print("Transcribing...")
segments, info = model.transcribe(audio_float, language="en")
result = " ".join([segment.text for segment in segments]).strip()

print(f"\nYou said: '{result}'")

if result:
    print("✅ Transcription working!")
    if "claude" in result.lower():
        print("✅ And you said 'Claude'!")
else:
    print("❌ No transcription - check microphone")