#!/usr/bin/env python3
"""
Claude Voice Service - System Tray Version
Runs silently in background, shows icon in system tray
Double-click tray icon to toggle listening

INSTALL: pip install SpeechRecognition pyaudio edge-tts pystray pillow
"""

import subprocess
import sys
import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path

# Check platform
if sys.platform != "win32":
    print("This script must run on Windows")
    sys.exit(1)

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pystray", "pillow"], check=True)
    import pystray
    from PIL import Image, ImageDraw

try:
    import speech_recognition as sr
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "SpeechRecognition", "pyaudio"], check=True)
    import speech_recognition as sr

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

# Global state
listening = True
running = True
mic_index = None

def log(msg):
    """Log message to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def create_icon(color):
    """Create a simple icon"""
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Draw a microphone shape
    if color == "green":
        fill = (0, 200, 0, 255)
    elif color == "red":
        fill = (200, 0, 0, 255)
    else:
        fill = (100, 100, 100, 255)

    # Mic body
    draw.ellipse([20, 10, 44, 40], fill=fill)
    draw.rectangle([20, 25, 44, 45], fill=fill)

    # Mic stand
    draw.arc([15, 30, 49, 55], 0, 180, fill=fill, width=3)
    draw.line([32, 55, 32, 60], fill=fill, width=3)
    draw.line([22, 60, 42, 60], fill=fill, width=3)

    return image

def speak(text, rate=VOICE_RATE):
    """Speak text using Edge TTS via WSL - NATURAL VOICE ONLY, no fallback"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audio_file = AUDIO_DIR / f"voice_{timestamp}.mp3"
        wsl_audio_path = f"/mnt/d/.playwright-mcp/audio/voice_{timestamp}.mp3"

        # Clean text for shell
        safe_text = text.replace("'", "'").replace('"', "'").replace('`', "'")
        safe_text = safe_text.replace('\n', ' ').replace('\r', '')

        # Generate audio with edge-tts via WSL (natural voice)
        result = subprocess.run([
            "wsl", "bash", "-c",
            f"/home/weber/.local/bin/edge-tts --voice {VOICE} --rate '{rate}' --text '{safe_text}' --write-media '{wsl_audio_path}'"
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
    """Get microphone index"""
    global mic_index

    if MIC_INDEX_FILE.exists():
        try:
            mic_index = int(MIC_INDEX_FILE.read_text().strip())
            return mic_index
        except:
            pass

    mics = sr.Microphone.list_microphone_names()
    log(f"Available microphones: {len(mics)}")

    preferred = ["c920", "webcam", "usb", "logitech", "blue", "yeti"]

    for i, name in enumerate(mics):
        log(f"  [{i}] {name}")
        for keyword in preferred:
            if keyword in name.lower():
                mic_index = i
                MIC_INDEX_FILE.write_text(str(i))
                return i

    mic_index = 1 if len(mics) > 1 else 0
    return mic_index

def listen_once(timeout=5):
    """Listen for speech"""
    try:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        idx = get_mic_index()

        with sr.Microphone(device_index=idx) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)

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
    """Check for wake word"""
    if not text:
        return False
    text_lower = text.lower()
    return any(w in text_lower for w in WAKE_WORDS)

def extract_command(text):
    """Extract command after wake word"""
    if not text:
        return ""
    text_lower = text.lower()
    for word in WAKE_WORDS:
        if word in text_lower:
            idx = text_lower.find(word)
            return text[idx + len(word):].strip()
    return text

def send_to_claude(command):
    """Send command to Claude Code"""
    try:
        log(f"Sending to Claude: {command}")

        COMMAND_FILE.write_text(json.dumps({
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }))

        result = subprocess.run(
            ["wsl", "bash", "-c", f"cd /mnt/d && claude -p '{command}'"],
            capture_output=True,
            text=True,
            timeout=120
        )

        response = result.stdout.strip()
        if not response:
            response = "I processed your request but didn't get a text response."

        RESPONSE_FILE.write_text(json.dumps({
            "command": command,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }))

        log(f"Response: {response[:100]}...")
        return response

    except subprocess.TimeoutExpired:
        return "That's taking longer than expected. I'm still working on it."
    except Exception as e:
        log(f"Claude error: {e}")
        return f"I encountered an error: {str(e)}"

def voice_loop():
    """Main voice listening loop"""
    global listening, running

    log("Voice loop starting...")
    speak("Voice service ready. Say Hey Claude when you need me.")

    while running:
        if not listening:
            time.sleep(0.5)
            continue

        try:
            text = listen_once(timeout=5)

            if text and check_wake_word(text):
                command = extract_command(text)

                if not command or len(command) < 3:
                    speak("Yes?")
                    command = listen_once(timeout=15)

                if command and len(command) >= 3:
                    cmd_lower = command.lower()

                    if any(x in cmd_lower for x in ["goodbye", "exit", "quit", "stop listening"]):
                        speak("Goodbye. I'll be here when you need me.")
                        continue

                    log(f"Processing: {command}")
                    speak("Let me work on that.")

                    response = send_to_claude(command)

                    if len(response) > 500:
                        summary_cmd = f"Summarize this in 2-3 sentences for spoken delivery: {response[:1500]}"
                        response = send_to_claude(summary_cmd)

                    speak(response)

        except Exception as e:
            log(f"Loop error: {e}")
            time.sleep(1)

    log("Voice loop stopped")

def toggle_listening(icon, item):
    """Toggle listening on/off"""
    global listening
    listening = not listening
    status = "Listening" if listening else "Paused"
    log(f"Status: {status}")
    icon.icon = create_icon("green" if listening else "red")
    icon.title = f"Claude Voice - {status}"

def quit_app(icon, item):
    """Quit the application"""
    global running
    running = False
    speak("Voice service stopping.")
    icon.stop()

def setup_tray(icon):
    """Setup after tray icon visible"""
    icon.visible = True

    # Start voice loop in thread
    voice_thread = threading.Thread(target=voice_loop, daemon=True)
    voice_thread.start()

def main():
    """Main entry point"""
    log("=" * 50)
    log("Claude Voice Service (Tray) Starting")
    log("=" * 50)

    # Create system tray icon
    menu = pystray.Menu(
        pystray.MenuItem("Toggle Listening", toggle_listening, default=True),
        pystray.MenuItem("Quit", quit_app)
    )

    icon = pystray.Icon(
        "claude_voice",
        create_icon("green"),
        "Claude Voice - Listening",
        menu
    )

    icon.run(setup_tray)

if __name__ == "__main__":
    main()
