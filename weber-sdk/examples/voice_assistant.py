"""
Voice Assistant Examples using Weber SDK.

Uses Edge TTS for speech and OpenAI Whisper for transcription.
"""

import asyncio
from weber_sdk import Weber


async def voice_basics():
    """Basic voice operations."""
    async with Weber() as w:
        # Speak text
        await w.voice.speak("Hello, this is Weber SDK speaking!")

        # Use different voice
        await w.voice.speak(
            "This is Jenny's voice.",
            voice="en-US-JennyNeural"
        )


async def voice_listen():
    """Listen for voice input."""
    async with Weber() as w:
        # Listen and transcribe
        print("Listening for voice input...")
        text = await w.voice.listen(max_duration=5)
        print(f"You said: {text}")


async def voice_conversation():
    """Have a voice conversation."""
    async with Weber() as w:
        # Ask a question and get voice response
        response = await w.voice.conversation(
            prompt="What would you like me to help you with?",
            max_duration=10
        )
        print(f"User responded: {response}")

        # Reply based on response
        await w.voice.speak(f"You said: {response}. Let me help you with that.")


async def voice_notification():
    """Use voice for notifications."""
    async with Weber() as w:
        # Announce something
        await w.voice.speak("Build completed successfully!")

        # Warning
        await w.voice.speak(
            "Warning: Memory usage is at 85 percent.",
            voice="en-US-GuyNeural"
        )


async def interactive_loop():
    """Interactive voice assistant loop."""
    async with Weber() as w:
        await w.voice.speak("Hello! I'm your voice assistant. Say 'quit' to exit.")

        while True:
            response = await w.voice.conversation(
                prompt="How can I help you?",
                max_duration=10
            )

            if "quit" in response.lower() or "exit" in response.lower():
                await w.voice.speak("Goodbye!")
                break

            # Echo back (in a real app, you'd process the command)
            await w.voice.speak(f"I heard: {response}")


if __name__ == "__main__":
    print("=== Voice Basics ===")
    asyncio.run(voice_basics())

    # Uncomment to run other examples
    # print("\n=== Voice Listen ===")
    # asyncio.run(voice_listen())

    # print("\n=== Voice Conversation ===")
    # asyncio.run(voice_conversation())

    # print("\n=== Interactive Loop ===")
    # asyncio.run(interactive_loop())
