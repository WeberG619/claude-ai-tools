#!/usr/bin/env python3
"""
Produce Video 01: Retry Ladder

Two-step process:
  Step 1: Record terminal demo → screen_recording.mp4 (use OBS or manual)
  Step 2: Compose final video — overlay voiceover + add captions + export

Usage:
  # After you have screen_recording.mp4:
  python3 produce.py compose

  # Or do everything (plays demo + records via ffmpeg):
  python3 produce.py record   # Records terminal via ffmpeg
  python3 produce.py compose  # Overlays audio + captions
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
AUDIO_DIR = BASE / "audio"
RECORDING = BASE / "screen_recording.mp4"
FINAL_LANDSCAPE = BASE / "final_landscape.mp4"
FINAL_VERTICAL = BASE / "final_vertical.mp4"
DEMO_SCRIPT = BASE / "demo_runner.py"

# Captions — burned in, timed to audio segments
# Format: (start_seconds, duration_seconds, text)
CAPTIONS = [
    (0.0, 5.0, "When my AI agent fails,\\nit doesn't just retry."),
    (5.0, 2.0, "It runs a strategy ladder."),
    (7.0, 5.0, "Strategy 1: QUICK-FIX\\nMinimal change. Two shots."),
    (12.0, 5.0, "Strategy 2: REFACTOR\\nRead more context. Different approach."),
    (17.0, 5.0, "Strategy 3: ALTERNATIVE\\nCompletely different solution."),
    (22.0, 6.0, "Strategy 4: ESCALATE\\nDetailed failure report."),
    (28.0, 5.0, "4 strategies. 5 max attempts.\\n15-minute hard timeout."),
    (33.0, 5.0, "It remembers what worked —\\nskips to it next time."),
    (38.0, 4.0, "cadre-ai — github.com/WeberG619"),
]


def record_terminal():
    """Record the terminal demo using script + ffmpeg."""
    print("Starting terminal recording...")
    print("The demo will play in your terminal. Recording via ffmpeg.")
    print()

    # Use Windows ffmpeg to capture screen, or just tell user to use OBS
    print("=" * 50)
    print("OPTION A: Use OBS")
    print("  1. Open OBS, select your terminal window")
    print("  2. Start recording")
    print("  3. Run: python3 demo_runner.py")
    print("  4. Stop recording")
    print(f"  5. Save as: {RECORDING}")
    print()
    print("OPTION B: Manual screen record")
    print("  Use Win+G (Game Bar) or any screen recorder")
    print(f"  Save as: {RECORDING}")
    print("=" * 50)
    print()
    print("After recording, run: python3 produce.py compose")


def compose():
    """Overlay voiceover + captions on the screen recording."""
    if not RECORDING.exists():
        print(f"ERROR: {RECORDING} not found.")
        print("Record the terminal demo first: python3 produce.py record")
        sys.exit(1)

    narration = AUDIO_DIR / "full_narration.mp3"
    if not narration.exists():
        print("ERROR: full_narration.mp3 not found. Run generate_audio.py first.")
        sys.exit(1)

    # Get video duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(RECORDING)],
        capture_output=True, text=True
    )
    video_duration = float(probe.stdout.strip())
    print(f"Video duration: {video_duration:.1f}s")

    # Build caption filter
    caption_filters = []
    for start, dur, text in CAPTIONS:
        end = start + dur
        # White text with dark background box, bottom of screen
        escaped_text = text.replace("'", "\\'")
        caption_filters.append(
            f"drawtext=text='{escaped_text}'"
            f":fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'"
            f":fontsize=28"
            f":fontcolor=white"
            f":borderw=2"
            f":bordercolor=black"
            f":x=(w-text_w)/2"
            f":y=h-th-60"
            f":enable='between(t,{start},{end})'"
        )

    filter_str = ",".join(caption_filters)

    # === Landscape version (16:9) ===
    print("\nComposing landscape (16:9)...")
    cmd_landscape = [
        "ffmpeg", "-y",
        "-i", str(RECORDING),
        "-i", str(narration),
        "-filter_complex",
        f"[0:v]{filter_str}[v];"
        f"[1:a]adelay=0|0[a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(FINAL_LANDSCAPE),
    ]
    result = subprocess.run(cmd_landscape, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  Saved: {FINAL_LANDSCAPE}")
    else:
        print(f"  ERROR: {result.stderr[-500:]}")
        return

    # === Vertical version (9:16 for Shorts/Reels) ===
    print("\nComposing vertical (9:16)...")
    # Crop center of landscape, scale to 1080x1920
    vertical_filter = (
        f"[0:v]crop=ih*9/16:ih,scale=1080:1920,{filter_str}[v];"
        f"[1:a]adelay=0|0[a]"
    )
    cmd_vertical = [
        "ffmpeg", "-y",
        "-i", str(RECORDING),
        "-i", str(narration),
        "-filter_complex", vertical_filter,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(FINAL_VERTICAL),
    ]
    result = subprocess.run(cmd_vertical, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  Saved: {FINAL_VERTICAL}")
    else:
        print(f"  Vertical crop failed (may need manual adjustment): {result.stderr[-300:]}")

    print("\nDone! Files:")
    print(f"  Landscape: {FINAL_LANDSCAPE}")
    print(f"  Vertical:  {FINAL_VERTICAL}")


def main():
    parser = argparse.ArgumentParser(description="Produce Video 01")
    parser.add_argument("action", choices=["record", "compose"],
                        help="'record' for instructions, 'compose' to build final video")
    args = parser.parse_args()

    if args.action == "record":
        record_terminal()
    elif args.action == "compose":
        compose()


if __name__ == "__main__":
    main()
