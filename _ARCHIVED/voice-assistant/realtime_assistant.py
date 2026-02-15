#!/usr/bin/env python3
"""
Claude Real-Time Voice Assistant
Low-latency streaming conversation using RealtimeSTT + RealtimeTTS + Claude API

This provides natural, fluid conversation like OpenAI's voice mode.
"""

import os
import sys
import threading
import queue
from datetime import datetime

# Check platform
if sys.platform != "win32":
    print("This script must run on Windows, not WSL")
    sys.exit(1)

# Set API key from environment or file
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    key_file = r"D:\_CLAUDE-TOOLS\voice-assistant\anthropic_key.txt"
    if os.path.exists(key_file):
        with open(key_file) as f:
            ANTHROPIC_API_KEY = f.read().strip()

if not ANTHROPIC_API_KEY:
    print("Please set ANTHROPIC_API_KEY environment variable")
    print(f"Or create file: {key_file}")
    sys.exit(1)

os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

# Import after setting up environment
try:
    from RealtimeSTT import AudioToTextRecorder
    from RealtimeTTS import TextToAudioStream, EdgeEngine
    import anthropic
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install RealtimeSTT RealtimeTTS anthropic")
    sys.exit(1)

# Configuration
WAKE_WORDS = ["claude", "hey claude", "okay claude"]
VOICE = "en-US-AndrewNeural"  # Natural male voice
MODEL = "claude-sonnet-4-20250514"  # Fast model for conversation

# Conversation history for context
conversation_history = []
MAX_HISTORY = 10

def log(msg):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

class RealtimeVoiceAssistant:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.tts_engine = None
        self.tts_stream = None
        self.recorder = None
        self.is_speaking = False
        self.response_queue = queue.Queue()

    def setup_tts(self):
        """Initialize text-to-speech with Edge (natural voice)"""
        log("Setting up TTS...")
        self.tts_engine = EdgeEngine()
        self.tts_engine.set_voice(VOICE)  # Set natural voice
        self.tts_stream = TextToAudioStream(self.tts_engine)
        log("TTS ready")

    def setup_stt(self):
        """Initialize speech-to-text with wake word detection"""
        log("Setting up STT...")
        self.recorder = AudioToTextRecorder(
            wake_words=WAKE_WORDS,
            wake_word_activation_delay=0.3,
            post_speech_silence_duration=0.6,
            min_length_of_recording=0.5,
            enable_realtime_transcription=True,
            realtime_processing_pause=0.1,
            on_wakeword_detected=self.on_wake_word,
            spinner=False,
        )
        log("STT ready - listening for wake word")

    def on_wake_word(self):
        """Called when wake word detected"""
        log("Wake word detected!")
        # Play a quick acknowledgment sound or say "yes?"
        self.speak_quick("Yes?")

    def speak_quick(self, text):
        """Quick speech without streaming (for short responses)"""
        if self.tts_stream:
            self.tts_stream.feed(text)
            self.tts_stream.play()

    def speak_streaming(self, text_generator):
        """Stream speech as text is generated"""
        self.is_speaking = True
        try:
            for chunk in text_generator:
                if chunk:
                    self.tts_stream.feed(chunk)
            self.tts_stream.play()
        finally:
            self.is_speaking = False

    def get_claude_response_streaming(self, user_message):
        """Get streaming response from Claude"""
        # Add to history
        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Keep history manageable
        if len(conversation_history) > MAX_HISTORY * 2:
            conversation_history[:] = conversation_history[-MAX_HISTORY * 2:]

        # System prompt for conversational assistant
        system = """You are Claude, a helpful voice assistant. Keep responses concise and conversational -
you're having a spoken conversation, not writing an essay.
Respond naturally as if talking to a friend.
Keep most responses to 1-3 sentences unless the topic requires more detail.
Never use markdown, bullet points, or formatting - just natural speech."""

        try:
            with self.client.messages.stream(
                model=MODEL,
                max_tokens=300,  # Keep responses short for conversation
                system=system,
                messages=conversation_history
            ) as stream:
                full_response = ""
                for text in stream.text_stream:
                    full_response += text
                    yield text

                # Save assistant response to history
                conversation_history.append({
                    "role": "assistant",
                    "content": full_response
                })

        except Exception as e:
            log(f"Claude API error: {e}")
            yield f"Sorry, I had trouble processing that. {str(e)}"

    def process_speech(self, text):
        """Process recognized speech and respond"""
        if not text or len(text.strip()) < 2:
            return

        text = text.strip()
        log(f"You said: {text}")

        # Check for exit commands
        if any(x in text.lower() for x in ["goodbye", "stop", "exit", "quit"]):
            self.speak_quick("Goodbye! Talk to you later.")
            return "EXIT"

        # Get and speak response with streaming
        log("Responding...")
        response_gen = self.get_claude_response_streaming(text)
        self.speak_streaming(response_gen)
        log("Done")
        return None

    def run(self):
        """Main loop"""
        log("=" * 50)
        log("Claude Real-Time Voice Assistant")
        log("=" * 50)

        try:
            self.setup_tts()
            self.setup_stt()

            self.speak_quick("Voice assistant ready. Say Claude when you need me.")

            log("Listening... Say 'Claude' to activate")

            while True:
                # This blocks until speech is detected after wake word
                text = self.recorder.text()

                if text:
                    result = self.process_speech(text)
                    if result == "EXIT":
                        break

        except KeyboardInterrupt:
            log("Interrupted")
        except Exception as e:
            log(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.recorder:
                self.recorder.stop()
            log("Stopped")

def main():
    assistant = RealtimeVoiceAssistant()
    assistant.run()

if __name__ == "__main__":
    main()
