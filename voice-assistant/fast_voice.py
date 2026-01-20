#!/usr/bin/env python3
"""
Fast Claude Voice Assistant
Uses Google Speech Recognition + streaming Claude + Edge TTS via WSL
Optimized for low-latency natural conversation on Windows.
"""

import os
import sys
import subprocess
import time
import threading
from datetime import datetime
from pathlib import Path

# Check platform
if sys.platform != "win32":
    print("This script must run on Windows, not WSL")
    sys.exit(1)

# Paths
AUDIO_DIR = Path(r"D:\.playwright-mcp\audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Import speech recognition
try:
    import speech_recognition as sr
except ImportError:
    print("Installing SpeechRecognition...")
    subprocess.run([sys.executable, "-m", "pip", "install", "SpeechRecognition", "pyaudio"], check=True)
    import speech_recognition as sr

# Import anthropic
try:
    import anthropic
except ImportError:
    print("Installing anthropic...")
    subprocess.run([sys.executable, "-m", "pip", "install", "anthropic"], check=True)
    import anthropic

# Set API key
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    key_file = Path(r"D:\_CLAUDE-TOOLS\voice-assistant\anthropic_key.txt")
    if key_file.exists():
        ANTHROPIC_API_KEY = key_file.read_text().strip()
    else:
        print(f"Please create {key_file} with your API key")
        sys.exit(1)

os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

# Configuration
WAKE_WORDS = ["claude", "hey claude", "okay claude", "hey claud", "hey cloud"]
VOICE = "en-US-AndrewNeural"  # Natural male voice
MODEL = "claude-sonnet-4-20250514"  # Fast model
MAX_HISTORY = 10

# Global state
conversation_history = []
is_speaking = False
mic_index = None
conversation_mode = False  # True = no wake word needed for follow-ups
conversation_timeout = 15  # Seconds to wait for follow-up without wake word

def log(msg):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {msg}", flush=True)

def get_mic_index():
    """Find preferred microphone"""
    global mic_index
    if mic_index is not None:
        return mic_index

    mics = sr.Microphone.list_microphone_names()
    preferred = ["c920", "webcam", "usb", "logitech"]

    for i, name in enumerate(mics):
        for keyword in preferred:
            if keyword in name.lower():
                log(f"Using mic [{i}]: {name}")
                mic_index = i
                return i

    mic_index = 1 if len(mics) > 1 else 0
    log(f"Using default mic: {mic_index}")
    return mic_index

def speak_sync(text):
    """Speak text using Edge TTS via WSL - synchronous, waits until done"""
    global is_speaking
    is_speaking = True

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
        audio_file = AUDIO_DIR / f"voice_{timestamp}.mp3"
        wsl_audio_path = f"/mnt/d/.playwright-mcp/audio/voice_{timestamp}.mp3"

        # Clean text for shell
        safe_text = text.replace("'", "").replace('"', "").replace('`', "")
        safe_text = safe_text.replace('\n', ' ').replace('\r', '')
        safe_text = safe_text.replace('$', '').replace('\\', '')
        safe_text = ' '.join(safe_text.split())

        if not safe_text:
            return

        # Generate audio with edge-tts via WSL
        result = subprocess.run([
            "wsl", "bash", "-c",
            f'/home/weber/.local/bin/edge-tts --voice {VOICE} --text "{safe_text}" --write-media "{wsl_audio_path}"'
        ], capture_output=True, timeout=30)

        if result.returncode != 0 or not audio_file.exists():
            log(f"TTS failed: {result.stderr.decode()}")
            return

        # Play audio with PowerShell MediaPlayer
        play_script = f'''
        Add-Type -AssemblyName PresentationCore
        $player = New-Object System.Windows.Media.MediaPlayer
        $player.Open("{audio_file}")
        Start-Sleep -Milliseconds 200
        $player.Play()
        while ($player.NaturalDuration.HasTimeSpan -eq $false) {{
            Start-Sleep -Milliseconds 50
        }}
        $duration = $player.NaturalDuration.TimeSpan.TotalSeconds
        Start-Sleep -Seconds ($duration + 0.3)
        $player.Close()
        '''

        subprocess.run(["powershell", "-Command", play_script], capture_output=True, timeout=60)

    except Exception as e:
        log(f"Speech error: {e}")
    finally:
        is_speaking = False

def listen(timeout=5):
    """Listen for speech using Google Speech Recognition"""
    try:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 400
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.6  # Faster response

        idx = get_mic_index()

        with sr.Microphone(device_index=idx) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)

        # Use Google Speech Recognition
        text = recognizer.recognize_google(audio)
        return text

    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        log(f"Listen error: {e}")
        return None

def check_wake_word(text):
    """Check if text starts with wake word"""
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

def get_response_streaming(user_message):
    """Get streaming response from Claude API"""
    global conversation_history

    # Add to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    # Trim history
    if len(conversation_history) > MAX_HISTORY * 2:
        conversation_history = conversation_history[-MAX_HISTORY * 2:]

    # System prompt for voice
    system = """You are Claude, a helpful voice assistant having a natural spoken conversation.
Keep responses brief and conversational - 1-3 sentences unless detail is needed.
Never use markdown, bullet points, or formatting - just natural speech.
Respond as if talking to a friend."""

    client = anthropic.Anthropic()

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=250,
            system=system,
            messages=conversation_history
        ) as stream:
            full_response = []
            buffer = ""

            for text in stream.text_stream:
                buffer += text
                full_response.append(text)

                # Stream out complete sentences
                for sep in [". ", "! ", "? ", "\n"]:
                    if sep in buffer:
                        parts = buffer.split(sep, 1)
                        sentence = parts[0] + sep.strip()
                        buffer = parts[1] if len(parts) > 1 else ""
                        yield sentence

            # Yield remaining text
            if buffer.strip():
                yield buffer.strip()

            # Save to history
            conversation_history.append({
                "role": "assistant",
                "content": "".join(full_response)
            })

    except Exception as e:
        log(f"API error: {e}")
        yield f"Sorry, I had an error: {str(e)}"

def respond_streaming(user_message):
    """Get Claude response and speak it with streaming"""
    log(f"Getting response for: {user_message[:50]}...")

    start = time.time()
    first_chunk = True

    for sentence in get_response_streaming(user_message):
        if first_chunk:
            latency = time.time() - start
            log(f"First response in {latency:.2f}s")
            first_chunk = False

        if sentence:
            log(f"Speaking: {sentence[:40]}...")
            speak_sync(sentence)

def main():
    """Main conversation loop"""
    global conversation_mode

    log("=" * 50)
    log("Claude Fast Voice Assistant")
    log("=" * 50)
    log(f"Model: {MODEL}")
    log(f"Voice: {VOICE}")
    log("=" * 50)

    # Initial greeting
    speak_sync("Voice assistant ready. Say Claude to start.")
    log("Listening for wake word...")

    last_interaction = 0

    while True:
        try:
            # Determine timeout - shorter in conversation mode
            timeout = conversation_timeout if conversation_mode else 5

            # Listen for speech
            text = listen(timeout=timeout)

            # Check if conversation mode should expire
            if conversation_mode and (time.time() - last_interaction) > conversation_timeout:
                conversation_mode = False
                log("Conversation mode timeout - need wake word")

            if not text:
                continue

            log(f"Heard: {text}")

            # In conversation mode OR has wake word
            should_respond = conversation_mode or check_wake_word(text)

            if should_respond:
                # Extract command (remove wake word if present)
                if check_wake_word(text):
                    command = extract_command(text)
                else:
                    command = text  # In conversation mode, use full text

                # If just wake word, prompt for command
                if not command or len(command) < 3:
                    speak_sync("Yes?")
                    log("Waiting for command...")
                    command = listen(timeout=10)

                if command and len(command) >= 3:
                    # Check for exit
                    if any(x in command.lower() for x in ["goodbye", "exit", "quit", "stop"]):
                        speak_sync("Goodbye! Talk to you later.")
                        conversation_mode = False
                        break

                    log(f"Processing: {command}")
                    respond_streaming(command)

                    # Enable conversation mode - no wake word needed for follow-ups
                    conversation_mode = True
                    last_interaction = time.time()
                    log(f"Done - conversation mode active for {conversation_timeout}s")

        except KeyboardInterrupt:
            log("Interrupted")
            speak_sync("Stopping.")
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(1)

    log("Stopped")

if __name__ == "__main__":
    main()
