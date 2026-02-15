#!/usr/bin/env python3
"""
Narrator Module for Revit Recorder

Uses Microsoft Edge TTS (Andrew voice) to generate narration
audio from the narration scripts.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional
import json

try:
    import edge_tts
except ImportError:
    print("edge-tts not installed. Run: pip install edge-tts")
    sys.exit(1)

# Paths
BASE_DIR = Path(__file__).parent
RECORDINGS_DIR = BASE_DIR / "recordings"
AUDIO_DIR = BASE_DIR / "recordings" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Voice configuration
VOICES = {
    "andrew": "en-US-AndrewNeural",  # Warm, professional male voice
    "guy": "en-US-GuyNeural",        # Friendly male voice
    "jenny": "en-US-JennyNeural",    # Clear female voice
    "aria": "en-US-AriaNeural",      # Engaging female voice
}

DEFAULT_VOICE = "andrew"


async def text_to_speech(
    text: str,
    output_file: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz"
) -> bool:
    """
    Convert text to speech using Edge TTS.

    Args:
        text: Text to convert
        output_file: Output MP3 file path
        voice: Voice name (andrew, guy, jenny, aria)
        rate: Speech rate adjustment (e.g., "+10%", "-5%")
        pitch: Pitch adjustment (e.g., "+5Hz", "-10Hz")

    Returns:
        True if successful
    """
    try:
        voice_id = VOICES.get(voice.lower(), VOICES[DEFAULT_VOICE])

        communicate = edge_tts.Communicate(
            text,
            voice_id,
            rate=rate,
            pitch=pitch
        )

        await communicate.save(output_file)
        return True

    except Exception as e:
        print(f"TTS Error: {e}")
        return False


async def generate_narration_audio(
    script_file: str,
    voice: str = DEFAULT_VOICE,
    output_dir: Optional[str] = None
) -> dict:
    """
    Generate narration audio from a script file.

    The script file should have lines like:
    [timestamp] Description text

    Each line becomes a separate audio file for easier editing.
    """
    script_path = Path(script_file)
    if not script_path.exists():
        return {"success": False, "error": "Script file not found"}

    output_path = Path(output_dir) if output_dir else AUDIO_DIR
    output_path.mkdir(parents=True, exist_ok=True)

    with open(script_path) as f:
        script_content = f.read()

    lines = script_content.strip().split("\n")
    audio_files = []
    errors = []

    # Track section for naming
    session_name = script_path.stem

    for i, line in enumerate(lines):
        line = line.strip()

        # Skip empty lines, comments, and headers
        if not line or line.startswith("#") or line.startswith("##"):
            continue

        # Extract text (remove timestamp if present)
        if line.startswith("["):
            # Format: [timestamp] text
            if "]" in line:
                text = line.split("]", 1)[1].strip()
            else:
                text = line
        else:
            text = line

        if not text or text.startswith("Parameters:"):
            continue

        # Generate audio filename
        audio_file = output_path / f"{session_name}_line_{i:04d}.mp3"

        success = await text_to_speech(
            text=text,
            output_file=str(audio_file),
            voice=voice
        )

        if success:
            audio_files.append({
                "line_number": i,
                "text": text[:100],
                "audio_file": str(audio_file)
            })
        else:
            errors.append(f"Line {i}: Failed to generate audio")

    return {
        "success": True,
        "audio_files": audio_files,
        "total_generated": len(audio_files),
        "errors": errors if errors else None
    }


async def speak_text(text: str, voice: str = DEFAULT_VOICE) -> dict:
    """
    Immediately speak text using Edge TTS (for live narration).
    Saves to temp file and plays it.
    """
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_file = f.name

        success = await text_to_speech(text, temp_file, voice)

        if success:
            # Play the audio
            if sys.platform == "win32":
                import subprocess
                # Use Windows Media Player for playback
                subprocess.Popen(
                    ['powershell.exe', '-Command', f'(New-Object Media.SoundPlayer "{temp_file}").PlaySync()'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            return {"success": True, "audio_file": temp_file}
        else:
            return {"success": False, "error": "TTS generation failed"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_voices() -> dict:
    """List available Edge TTS voices."""
    try:
        voices = await edge_tts.list_voices()
        english_voices = [v for v in voices if v["Locale"].startswith("en-")]

        return {
            "success": True,
            "recommended": VOICES,
            "all_english": [
                {"name": v["ShortName"], "gender": v["Gender"], "locale": v["Locale"]}
                for v in english_voices[:20]
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate narration audio from scripts")
    parser.add_argument("action", choices=["speak", "generate", "voices"])
    parser.add_argument("--text", help="Text to speak (for speak action)")
    parser.add_argument("--script", help="Script file path (for generate action)")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Voice name")
    parser.add_argument("--output", help="Output directory for generated audio")

    args = parser.parse_args()

    if args.action == "speak":
        if not args.text:
            print("--text is required for speak action")
            sys.exit(1)
        result = asyncio.run(speak_text(args.text, args.voice))
        print(json.dumps(result, indent=2))

    elif args.action == "generate":
        if not args.script:
            print("--script is required for generate action")
            sys.exit(1)
        result = asyncio.run(generate_narration_audio(args.script, args.voice, args.output))
        print(json.dumps(result, indent=2))

    elif args.action == "voices":
        result = asyncio.run(list_voices())
        print(json.dumps(result, indent=2))
