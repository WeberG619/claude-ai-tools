"""
Audio transcription module using OpenAI Whisper.
"""

import os
from pathlib import Path
from typing import Optional

import whisper


class Transcriber:
    """Handles audio transcription using OpenAI Whisper."""

    SUPPORTED_FORMATS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}
    AVAILABLE_MODELS = ['tiny', 'base', 'small', 'medium', 'large']

    def __init__(self, model_name: str = "base"):
        """
        Initialize the transcriber with a Whisper model.

        Args:
            model_name: Whisper model size. Options: tiny, base, small, medium, large
                       Larger models are more accurate but slower.
        """
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Model must be one of: {self.AVAILABLE_MODELS}")

        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy-load the Whisper model."""
        if self._model is None:
            print(f"Loading Whisper model '{self.model_name}'...")
            self._model = whisper.load_model(self.model_name)
            print("Model loaded.")
        return self._model

    def validate_audio_file(self, audio_path: str) -> Path:
        """
        Validate that the audio file exists and is a supported format.

        Args:
            audio_path: Path to the audio file

        Returns:
            Path object for the validated file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {path.suffix}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        return path

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        verbose: bool = False
    ) -> dict:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file (.wav, .mp3, etc.)
            language: Optional language code (e.g., 'en', 'es').
                     If None, Whisper auto-detects.
            verbose: If True, print transcription progress

        Returns:
            Dictionary containing:
                - text: Full transcription text
                - segments: List of timestamped segments
                - language: Detected/specified language
        """
        path = self.validate_audio_file(audio_path)

        if verbose:
            print(f"Transcribing: {path.name}")

        # Transcribe with Whisper
        options = {"verbose": verbose}
        if language:
            options["language"] = language

        result = self.model.transcribe(str(path), **options)

        return {
            "text": result["text"].strip(),
            "segments": result.get("segments", []),
            "language": result.get("language", language or "unknown")
        }

    def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> list:
        """
        Transcribe and return text with timestamps.

        Args:
            audio_path: Path to the audio file
            language: Optional language code

        Returns:
            List of dicts with 'start', 'end', and 'text' keys
        """
        result = self.transcribe(audio_path, language)

        timestamps = []
        for segment in result.get("segments", []):
            timestamps.append({
                "start": segment.get("start", 0),
                "end": segment.get("end", 0),
                "text": segment.get("text", "").strip()
            })

        return timestamps
