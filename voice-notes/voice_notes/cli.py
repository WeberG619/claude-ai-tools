#!/usr/bin/env python3
"""
Voice Notes CLI - Convert audio recordings to structured meeting notes.

Usage:
    voice-notes input.wav                    # Basic transcription
    voice-notes input.mp3 -o notes.md        # Custom output file
    voice-notes input.wav --model medium     # Use larger model
    voice-notes input.wav --speak            # Speak summary after processing
    voice-notes input.wav --no-transcript    # Exclude full transcript from output
"""

import argparse
import subprocess
import sys
from pathlib import Path

from . import __version__
from .transcriber import Transcriber
from .note_formatter import NoteFormatter


# Path to the voice TTS script
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")


def speak_summary(text: str) -> bool:
    """
    Speak the summary using the voice-mcp speak.py script.

    Args:
        text: Text to speak

    Returns:
        True if successful, False otherwise
    """
    if not VOICE_SCRIPT.exists():
        print(f"Warning: Voice script not found at {VOICE_SCRIPT}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(VOICE_SCRIPT), text],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Warning: Voice summary timed out")
        return False
    except Exception as e:
        print(f"Warning: Could not speak summary: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="voice-notes",
        description="Convert audio recordings to structured meeting notes using OpenAI Whisper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  voice-notes meeting.wav                    # Transcribe and extract notes
  voice-notes meeting.mp3 -o meeting.md      # Save to custom file
  voice-notes meeting.wav --model small      # Use small model (faster)
  voice-notes meeting.wav --model medium     # Use medium model (more accurate)
  voice-notes meeting.wav --speak            # Speak summary when done
  voice-notes meeting.wav --language en      # Force English language
  voice-notes meeting.wav --no-transcript    # Don't include full transcript

Supported formats: .wav, .mp3, .m4a, .flac, .ogg, .webm
Available models: tiny, base, small, medium, large
        """
    )

    parser.add_argument(
        "audio",
        help="Path to audio file (.wav, .mp3, .m4a, .flac, .ogg, .webm)"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output markdown file path (default: <audio_name>_notes.md)"
    )

    parser.add_argument(
        "-m", "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model size (default: base). Larger = more accurate but slower."
    )

    parser.add_argument(
        "-l", "--language",
        help="Language code (e.g., 'en', 'es'). Auto-detected if not specified."
    )

    parser.add_argument(
        "--speak",
        action="store_true",
        help="Speak a summary after processing using voice-mcp"
    )

    parser.add_argument(
        "--no-transcript",
        action="store_true",
        help="Don't include full transcript in output (just extracted notes)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed progress during transcription"
    )

    parser.add_argument(
        "--timestamps",
        action="store_true",
        help="Include timestamps in the full transcript"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"voice-notes {__version__}"
    )

    args = parser.parse_args()

    # Validate input file
    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Error: Audio file not found: {args.audio}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = audio_path.parent / f"{audio_path.stem}_notes.md"

    print(f"Voice Notes v{__version__}")
    print(f"Input: {audio_path}")
    print(f"Output: {output_path}")
    print(f"Model: {args.model}")
    print()

    # Initialize transcriber
    try:
        transcriber = Transcriber(model_name=args.model)
    except Exception as e:
        print(f"Error initializing transcriber: {e}")
        sys.exit(1)

    # Transcribe
    print("Transcribing audio...")
    try:
        if args.timestamps:
            result = transcriber.transcribe(
                str(audio_path),
                language=args.language,
                verbose=args.verbose
            )
            transcription = result["text"]

            # Format with timestamps
            segments = result.get("segments", [])
            if segments:
                timestamped_lines = []
                for seg in segments:
                    start = seg.get("start", 0)
                    mins, secs = divmod(int(start), 60)
                    timestamped_lines.append(f"[{mins:02d}:{secs:02d}] {seg.get('text', '').strip()}")
                transcription_with_timestamps = "\n".join(timestamped_lines)
            else:
                transcription_with_timestamps = transcription
        else:
            result = transcriber.transcribe(
                str(audio_path),
                language=args.language,
                verbose=args.verbose
            )
            transcription = result["text"]
            transcription_with_timestamps = transcription

        print(f"Transcription complete. Language: {result.get('language', 'unknown')}")
        print(f"Words transcribed: {len(transcription.split())}")
        print()

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during transcription: {e}")
        sys.exit(1)

    # Format notes
    print("Extracting notes...")
    formatter = NoteFormatter(audio_filename=audio_path.name)

    key_points = formatter.extract_key_points(transcription)
    action_items = formatter.extract_action_items(transcription)
    attendees = formatter.extract_attendees(transcription)

    print(f"  Key points found: {len(key_points)}")
    print(f"  Action items found: {len(action_items)}")
    print(f"  Attendees mentioned: {len(attendees)}")
    print()

    # Generate markdown
    transcript_text = transcription_with_timestamps if args.timestamps else transcription
    markdown = formatter.format_markdown(
        transcription=transcript_text,
        key_points=key_points,
        action_items=action_items,
        attendees=attendees,
        include_full_transcript=not args.no_transcript
    )

    # Write output
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        print(f"Notes saved to: {output_path}")
    except Exception as e:
        print(f"Error writing output: {e}")
        sys.exit(1)

    # Speak summary if requested
    if args.speak:
        print()
        print("Speaking summary...")
        summary = formatter.generate_summary(transcription, key_points, action_items)
        success = speak_summary(summary)
        if success:
            print("Summary spoken.")
        else:
            print("Could not speak summary (voice-mcp may not be available)")

    print()
    print("Done!")

    # Print brief summary
    if key_points:
        print()
        print("Top key points:")
        for point in key_points[:3]:
            print(f"  • {point[:80]}{'...' if len(point) > 80 else ''}")

    if action_items:
        print()
        print("Top action items:")
        for item in action_items[:3]:
            print(f"  □ {item[:80]}{'...' if len(item) > 80 else ''}")


if __name__ == "__main__":
    main()
