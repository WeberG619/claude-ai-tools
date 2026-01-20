import sounddevice as sd
import numpy as np
import time

print("Audio Device Test")
print("=================\n")

# List audio devices
print("Available audio devices:")
devices = sd.query_devices()
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"{i}: {device['name']} (Input channels: {device['max_input_channels']})")

print("\n" + "="*50 + "\n")

# Test recording
print("Testing audio recording for 3 seconds...")
print("Please speak into your microphone...\n")

duration = 3  # seconds
sample_rate = 16000
recording = []

def callback(indata, frames, time, status):
    if status:
        print(f"Status: {status}")
    recording.append(indata.copy())
    
    # Calculate and display volume level
    volume = np.sqrt(np.mean(indata**2))
    bar_length = int(volume * 100)
    bar = '█' * min(bar_length, 50)
    print(f"\rVolume: |{bar:<50}|", end='', flush=True)

try:
    with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
        print("Recording started...")
        time.sleep(duration)
        print("\n\nRecording finished!")
        
    # Analyze recording
    audio_data = np.concatenate(recording, axis=0)
    print(f"\nRecorded {len(audio_data) / sample_rate:.2f} seconds of audio")
    print(f"Average volume: {np.sqrt(np.mean(audio_data**2)):.4f}")
    print(f"Max volume: {np.max(np.abs(audio_data)):.4f}")
    
    if np.max(np.abs(audio_data)) < 0.001:
        print("\n⚠️  WARNING: No audio detected! Check your microphone.")
    else:
        print("\n✅ Audio recording is working properly!")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check that your microphone is connected")
    print("2. Check Windows sound settings")
    print("3. Make sure no other application is using the microphone")