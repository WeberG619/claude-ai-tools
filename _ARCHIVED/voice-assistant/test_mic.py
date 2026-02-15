"""Quick microphone test - run on Windows"""
import speech_recognition as sr

print("Testing microphone...")
print("Available microphones:")
for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"  [{i}] {name}")

# Use the C920 webcam mic (index 1)
recognizer = sr.Recognizer()
recognizer.energy_threshold = 300

print("\nSay something (you have 5 seconds)...")

try:
    with sr.Microphone(device_index=1) as source:  # C920 webcam
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)

    print("Processing...")
    text = recognizer.recognize_google(audio)
    print(f"You said: {text}")

except sr.WaitTimeoutError:
    print("No speech detected")
except sr.UnknownValueError:
    print("Could not understand audio")
except Exception as e:
    print(f"Error: {e}")
