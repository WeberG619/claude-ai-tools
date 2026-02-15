#!/usr/bin/env python3
"""
Quick Voice Listener - Single command capture
Returns the spoken text to stdout for use in scripts
"""

import speech_recognition as sr
import sys

def listen_once(timeout=10, phrase_limit=15):
    """Listen for one phrase and return it"""
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    try:
        with sr.Microphone() as source:
            print("🎤 Listening...", file=sys.stderr)
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

            text = recognizer.recognize_google(audio)
            print(text)
            return text

    except sr.WaitTimeoutError:
        print("No speech detected", file=sys.stderr)
        return None
    except sr.UnknownValueError:
        print("Could not understand audio", file=sys.stderr)
        return None
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    result = listen_once()
    sys.exit(0 if result else 1)
