#!/usr/bin/env python3
"""
Claude Voice Service - Background service for voice interaction
Runs on Windows, bridges to Claude Code in WSL
Uses Google Speech Recognition (free, reliable)

INSTALL: pip install SpeechRecognition pyaudio edge-tts
"""

import subprocess
import sys
import os
import json
import time
import threading
import queue
from datetime import datetime
from pathlib import Path

# Paths
AUDIO_DIR = Path(r"D:\.playwright-mcp\audio")
COMMAND_FILE = Path(r"D:\_CLAUDE-TOOLS\voice-assistant\voice_command.json")
RESPONSE_FILE = Path(r"D:\_CLAUDE-TOOLS\voice-assistant\voice_response.json")
LOG_FILE = Path(r"D:\_CLAUDE-TOOLS\voice-assistant\voice_service.log")
MIC_INDEX_FILE = Path(r"D:\_CLAUDE-TOOLS\voice-assistant\mic_index.txt")

AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Configuration
WAKE_WORDS = ["hey claude", "hey cloud", "claude", "okay claude", "a claude", "hey claud"]
VOICE = "en-US-AndrewNeural"
VOICE_RATE = "+5%"
MIC_INDEX = None  # Auto-detect or read from file

def log(msg):
    """Log message to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def speak(text, rate=VOICE_RATE):
    """Speak text using Edge TTS via WSL - NATURAL VOICE ONLY, no fallback"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audio_file = AUDIO_DIR / f"voice_{timestamp}.mp3"
        wsl_audio_path = f"/mnt/d/.playwright-mcp/audio/voice_{timestamp}.mp3"

        # Clean text for shell - remove problematic characters
        safe_text = text.replace("'", "").replace('"', "").replace('`', "")
        safe_text = safe_text.replace('\n', ' ').replace('\r', ' ')
        safe_text = safe_text.replace('$', '').replace('\\', '')
        safe_text = ' '.join(safe_text.split())  # normalize whitespace

        # Generate audio with edge-tts via WSL (natural voice)
        result = subprocess.run([
            "wsl", "bash", "-c",
            f'/home/weber/.local/bin/edge-tts --voice {VOICE} --text "{safe_text}" --write-media "{wsl_audio_path}"'
        ], capture_output=True, timeout=30)

        if result.returncode != 0:
            log(f"Edge TTS error: {result.stderr.decode()}")
            return

        # Play audio using PowerShell
        play_script = f'''
        Add-Type -AssemblyName PresentationCore
        $player = New-Object System.Windows.Media.MediaPlayer
        $player.Open("{audio_file}")
        Start-Sleep -Milliseconds 300
        $player.Play()
        while ($player.NaturalDuration.HasTimeSpan -eq $false) {{
            Start-Sleep -Milliseconds 100
        }}
        $duration = $player.NaturalDuration.TimeSpan.TotalSeconds
        Start-Sleep -Seconds ($duration + 0.5)
        $player.Close()
        '''

        subprocess.run(["powershell", "-Command", play_script], capture_output=True, timeout=60)
        log(f"Spoke: {text[:50]}...")

    except Exception as e:
        log(f"Speech error: {e}")

def get_mic_index():
    """Get microphone index - from file or auto-detect"""
    global MIC_INDEX

    # Try to read from saved file
    if MIC_INDEX_FILE.exists():
        try:
            MIC_INDEX = int(MIC_INDEX_FILE.read_text().strip())
            return MIC_INDEX
        except:
            pass

    # Auto-detect: look for webcam or USB mic
    import speech_recognition as sr
    mics = sr.Microphone.list_microphone_names()
    log(f"Available microphones: {len(mics)}")

    preferred_keywords = ["c920", "webcam", "usb", "logitech", "blue", "yeti"]

    for i, name in enumerate(mics):
        log(f"  [{i}] {name}")
        name_lower = name.lower()
        for keyword in preferred_keywords:
            if keyword in name_lower:
                log(f"Selected mic [{i}]: {name}")
                MIC_INDEX = i
                MIC_INDEX_FILE.write_text(str(i))
                return i

    # Default to index 1 (often the first real mic after system devices)
    if len(mics) > 1:
        MIC_INDEX = 1
    else:
        MIC_INDEX = 0

    log(f"Using default mic index: {MIC_INDEX}")
    return MIC_INDEX

def listen_once(timeout=10):
    """Listen for speech using Python speech_recognition with Windows audio"""
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        mic_idx = get_mic_index()

        # Use specified microphone
        with sr.Microphone(device_index=mic_idx) as source:
            log("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)

        # Use Google Speech Recognition
        text = recognizer.recognize_google(audio)
        log(f"Heard: {text}")
        return text

    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        log(f"Listen error: {e}")
        return None

def check_wake_word(text):
    """Check if text contains wake word"""
    if not text:
        return False
    text_lower = text.lower()
    for wake_word in WAKE_WORDS:
        if wake_word in text_lower:
            return True
    return False

def extract_command(text):
    """Extract command after wake word"""
    if not text:
        return ""
    text_lower = text.lower()
    for wake_word in WAKE_WORDS:
        if wake_word in text_lower:
            idx = text_lower.find(wake_word)
            return text[idx + len(wake_word):].strip()
    return text

def send_to_claude(command):
    """Send command to Claude Code and get response"""
    try:
        log(f"Sending to Claude: {command}")

        # Write command to file for any listening Claude session
        COMMAND_FILE.write_text(json.dumps({
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }))

        # Also run claude directly for immediate response
        result = subprocess.run(
            ["wsl", "bash", "-c", f"cd /mnt/d && claude -p '{command}'"],
            capture_output=True,
            text=True,
            timeout=120
        )

        response = result.stdout.strip()
        if not response:
            response = "I processed your request but didn't get a text response."

        # Write response to file
        RESPONSE_FILE.write_text(json.dumps({
            "command": command,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }))

        log(f"Claude response: {response[:100]}...")
        return response

    except subprocess.TimeoutExpired:
        return "That's taking longer than expected. I'm still working on it."
    except Exception as e:
        log(f"Claude error: {e}")
        return f"I encountered an error: {str(e)}"

def main_loop():
    """Main voice service loop"""
    log("=" * 50)
    log("Claude Voice Service Starting")
    log("=" * 50)

    speak("Voice service ready. Say Hey Claude when you need me.")

    running = True
    while running:
        try:
            # Listen for wake word
            text = listen_once(timeout=5)

            if text and check_wake_word(text):
                command = extract_command(text)

                if not command or len(command) < 3:
                    speak("Yes?")
                    log("Waiting for command...")
                    command = listen_once(timeout=15)

                if command and len(command) >= 3:
                    # Check for exit
                    cmd_lower = command.lower()
                    if any(x in cmd_lower for x in ["goodbye", "exit", "quit", "stop listening"]):
                        speak("Goodbye Weber. I'll be here when you need me.")
                        running = False
                        break

                    log(f"Processing: {command}")
                    speak("Let me work on that.")

                    # Get response from Claude
                    response = send_to_claude(command)

                    # Summarize long responses
                    if len(response) > 500:
                        summary_cmd = f"Summarize this in 2-3 sentences for spoken delivery: {response[:1500]}"
                        response = send_to_claude(summary_cmd)

                    speak(response)
                    log("Done")

        except KeyboardInterrupt:
            log("Interrupted by user")
            speak("Stopping voice service.")
            break
        except Exception as e:
            log(f"Error in main loop: {e}")
            time.sleep(1)

    log("Voice service stopped")

if __name__ == "__main__":
    # Check if running on Windows
    if sys.platform != "win32":
        print("This script must run on Windows, not WSL")
        print("Run: python voice_service.py")
        sys.exit(1)

    main_loop()
