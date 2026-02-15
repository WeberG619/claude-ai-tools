#!/usr/bin/env python3
"""
Voice Assistant for Claude Code
- Wake word detection ("Hey Claude" or custom)
- Continuous speech-to-text
- Voice responses via Edge TTS
- Sends commands to Claude Code
"""

import asyncio
import subprocess
import sys
import os
import json
import tempfile
import threading
import queue
import time
from datetime import datetime
from pathlib import Path

# Add voice MCP to path
sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/voice-mcp/src')

try:
    import speech_recognition as sr
    import edge_tts
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install speechrecognition edge-tts pyaudio")
    sys.exit(1)

# Configuration
WAKE_WORDS = ["hey claude", "hey cloud", "a]claude", "claude", "okay claude"]
VOICE = "en-US-AndrewNeural"
VOICE_RATE = "+5%"
AUDIO_DIR = Path("/mnt/d/.playwright-mcp/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# State
listening_for_command = False
should_exit = False

def speak(text: str, rate: str = VOICE_RATE):
    """Speak text using Edge TTS"""
    async def _speak():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audio_file = AUDIO_DIR / f"assistant_{timestamp}.mp3"

        communicate = edge_tts.Communicate(text, VOICE, rate=rate)
        await communicate.save(str(audio_file))

        win_path = str(audio_file).replace("/mnt/d", "D:")

        # Play via PowerShell
        play_script = f'''
        Add-Type -AssemblyName PresentationCore
        $player = New-Object System.Windows.Media.MediaPlayer
        $player.Open("{win_path}")
        Start-Sleep -Milliseconds 300
        $player.Play()
        while ($player.NaturalDuration.HasTimeSpan -eq $false) {{
            Start-Sleep -Milliseconds 100
        }}
        $duration = $player.NaturalDuration.TimeSpan.TotalSeconds
        Start-Sleep -Seconds ($duration + 0.5)
        $player.Close()
        '''

        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", play_script],
            capture_output=True
        )

    asyncio.run(_speak())

def send_to_claude(command: str) -> str:
    """Send command to Claude Code and get response"""
    # Write command to a file that Claude Code can read
    command_file = Path("/mnt/d/_CLAUDE-TOOLS/voice-assistant/pending_command.txt")
    command_file.write_text(command)

    # For now, we'll use a simpler approach - just run claude in print mode
    # This gives us the response directly
    try:
        result = subprocess.run(
            ["claude", "-p", command],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/mnt/d"
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "I'm still thinking about that. Give me a moment."
    except Exception as e:
        return f"I encountered an error: {str(e)}"

def check_wake_word(text: str) -> bool:
    """Check if text contains wake word"""
    text_lower = text.lower().strip()
    for wake_word in WAKE_WORDS:
        if wake_word in text_lower:
            return True
    return False

def extract_command(text: str) -> str:
    """Extract command after wake word"""
    text_lower = text.lower()
    for wake_word in WAKE_WORDS:
        if wake_word in text_lower:
            # Get everything after the wake word
            idx = text_lower.find(wake_word)
            command = text[idx + len(wake_word):].strip()
            # Remove common filler words at start
            for filler in ["can you", "please", "could you", "would you"]:
                if command.lower().startswith(filler):
                    command = command[len(filler):].strip()
            return command
    return text

class VoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.listening = False
        self.wake_word_detected = False
        self.command_queue = queue.Queue()

        # Adjust for ambient noise
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    def find_microphone(self):
        """Find available microphone"""
        print("Looking for microphone...")

        # List available microphones
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"  [{i}] {name}")

        # Try to use default
        try:
            self.microphone = sr.Microphone()
            print("Using default microphone")
            return True
        except Exception as e:
            print(f"Could not access microphone: {e}")
            return False

    def listen_for_wake_word(self):
        """Continuously listen for wake word"""
        print("\n🎤 Listening for 'Hey Claude'...")

        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

            while not should_exit:
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)

                    try:
                        text = self.recognizer.recognize_google(audio)
                        print(f"Heard: {text}")

                        if check_wake_word(text):
                            command = extract_command(text)
                            if command:
                                self.command_queue.put(command)
                            else:
                                # Just wake word, wait for command
                                speak("Yes?")
                                self.listen_for_command()

                    except sr.UnknownValueError:
                        pass  # Couldn't understand audio
                    except sr.RequestError as e:
                        print(f"Speech recognition error: {e}")

                except sr.WaitTimeoutError:
                    pass  # No speech detected, continue listening
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(1)

    def listen_for_command(self):
        """Listen for a command after wake word"""
        print("🎯 Listening for command...")

        with self.microphone as source:
            try:
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)
                text = self.recognizer.recognize_google(audio)
                print(f"Command: {text}")
                self.command_queue.put(text)
            except sr.WaitTimeoutError:
                speak("I didn't hear anything. Say Hey Claude when you're ready.")
            except sr.UnknownValueError:
                speak("I didn't catch that. Can you repeat?")
            except Exception as e:
                print(f"Error listening for command: {e}")

    def process_commands(self):
        """Process commands from queue"""
        while not should_exit:
            try:
                command = self.command_queue.get(timeout=1)
                print(f"\n📝 Processing: {command}")

                # Check for exit commands
                if any(x in command.lower() for x in ["goodbye", "exit", "quit", "stop listening"]):
                    speak("Goodbye Weber. I'll be here when you need me.")
                    global should_exit
                    should_exit = True
                    break

                # Send to Claude and get response
                speak("Let me work on that.")
                response = send_to_claude(command)

                # Speak the response (truncate if too long)
                if len(response) > 500:
                    # Summarize long responses
                    summary_prompt = f"Summarize this in 2-3 sentences for spoken delivery: {response[:2000]}"
                    response = send_to_claude(summary_prompt)

                speak(response)
                print(f"✅ Responded")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing command: {e}")
                speak("I ran into an issue. Let me try again.")

    def run(self):
        """Main run loop"""
        print("=" * 50)
        print("🤖 Claude Voice Assistant")
        print("=" * 50)
        print("\nSay 'Hey Claude' followed by your command")
        print("Say 'Goodbye' to exit")
        print()

        if not self.find_microphone():
            print("No microphone found. Exiting.")
            return

        speak("Voice assistant ready. Say Hey Claude when you need me.")

        # Start command processor in background
        processor_thread = threading.Thread(target=self.process_commands, daemon=True)
        processor_thread.start()

        # Listen for wake word in main thread
        try:
            self.listen_for_wake_word()
        except KeyboardInterrupt:
            print("\nStopping...")
            speak("Stopping voice assistant.")

        print("Voice assistant stopped.")

def main():
    assistant = VoiceAssistant()
    assistant.run()

if __name__ == "__main__":
    main()
