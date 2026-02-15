"""
Voice service wrapper for voice-input-mcp.

Provides typed methods for voice input and output.
"""

from typing import Literal

from weber_sdk.services.base import BaseService


VoiceType = Literal[
    "en-US-AndrewNeural",
    "en-US-GuyNeural",
    "en-US-JennyNeural",
]


class VoiceService(BaseService):
    """
    Voice service for speech input and output.

    Available voices:
    - en-US-AndrewNeural (default, natural male voice)
    - en-US-GuyNeural
    - en-US-JennyNeural
    """

    async def speak(
        self,
        text: str,
        voice: VoiceType = "en-US-AndrewNeural",
    ) -> str:
        """
        Speak text out loud using Edge TTS.

        Args:
            text: Text to speak
            voice: Voice to use (default: AndrewNeural)

        Returns:
            Confirmation message
        """
        result = await self.call("voice_speak", text=text, voice=voice)
        return str(result) if result else "Spoke text"

    async def listen(
        self,
        max_duration: float = 10.0,
        prompt: str | None = None,
    ) -> str:
        """
        Listen for voice input and transcribe it.

        Args:
            max_duration: Maximum recording duration in seconds
            prompt: Optional prompt to speak before listening

        Returns:
            Transcribed text
        """
        kwargs: dict = {"max_duration": max_duration}
        if prompt:
            kwargs["prompt"] = prompt

        result = await self.call("voice_listen", **kwargs)
        return str(result) if result else ""

    async def conversation(
        self,
        prompt: str,
        max_duration: float = 10.0,
    ) -> str:
        """
        Have a voice conversation - speak a prompt, then listen for response.

        Args:
            prompt: What to say before listening
            max_duration: Max listen duration in seconds

        Returns:
            Transcribed response
        """
        result = await self.call(
            "voice_conversation",
            prompt=prompt,
            max_duration=max_duration,
        )
        return str(result) if result else ""

    # Synchronous convenience methods
    def speak_sync(
        self,
        text: str,
        voice: VoiceType = "en-US-AndrewNeural",
    ) -> str:
        """Synchronous version of speak()."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.speak(text, voice))

    def listen_sync(
        self,
        max_duration: float = 10.0,
        prompt: str | None = None,
    ) -> str:
        """Synchronous version of listen()."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.listen(max_duration, prompt)
        )
