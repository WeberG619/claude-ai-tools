#!/usr/bin/env python3
"""
Render Video 01: Retry Ladder — fully programmatic, no screen capture needed.
Draws terminal text frame-by-frame with Pillow, pipes to FFmpeg, overlays voiceover.

Outputs:
  final_landscape.mp4  (1920x1080, 16:9)
  final_vertical.mp4   (1080x1920, 9:16)
  thumbnail.png        (1920x1080)

Run in background — no monitor takeover.
"""

import subprocess
import struct
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── CONFIG ────────────────────────────────────────
BASE = Path(__file__).parent
AUDIO = BASE / "audio" / "full_narration.mp3"
OUT_LANDSCAPE = BASE / "final_landscape.mp4"
OUT_VERTICAL = BASE / "final_vertical.mp4"
THUMBNAIL = BASE / "thumbnail.png"

WIDTH, HEIGHT = 1920, 1080
FPS = 30
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 22
LINE_HEIGHT = 30
MARGIN_X = 60
MARGIN_Y = 50
CAPTION_FONT_SIZE = 32

# Terminal colors (RGB)
COLORS = {
    "bg":       (18, 18, 24),
    "white":    (220, 220, 220),
    "dim":      (120, 120, 140),
    "red":      (255, 85, 85),
    "green":    (80, 250, 123),
    "yellow":   (241, 250, 140),
    "blue":     (100, 149, 237),
    "magenta":  (189, 147, 249),
    "cyan":     (139, 233, 253),
    "bold_white": (255, 255, 255),
}

# ── TIMELINE ──────────────────────────────────────
# (time_seconds, lines_to_add)
# Each line: (color_name, text, bold)

EVENTS = [
    # Hook: 0-5s
    (0.0, [("dim", "weber@claude-code ~ $", False)]),
    (0.5, [("white", "python3 adaptive-retry/retry_engine.py", False)]),
    (1.5, [("white", "", False)]),
    (1.6, [("bold_white", "╔══════════════════════════════════════════════════╗", True)]),
    (1.7, [("bold_white", "║   ADAPTIVE RETRY ENGINE  —  Strategy Ladder     ║", True)]),
    (1.8, [("bold_white", "╚══════════════════════════════════════════════════╝", True)]),
    (2.0, [("white", "", False)]),
    (2.2, [("red", "ERROR: msbuild failed — CS0246: type 'ErrorCode' not found", True)]),

    # Intro: 5-7s
    (5.0, [("white", "", False)]),
    (5.2, [("cyan", "Engaging retry ladder...", False)]),

    # Quick-fix attempt 1: 7-9.5s
    (7.0, [("white", "", False)]),
    (7.1, [("yellow", "━━━ Strategy 1: QUICK-FIX (attempt 1/2) ━━━", False)]),
    (7.3, [("dim", "  → Fix the specific error. Minimal change.", False)]),
    (8.0, [("dim", "  Adding missing using directive...", False)]),
    (8.8, [("red", "  ✗ FAIL — CS0246: type 'ErrorCode' not found", False)]),

    # Quick-fix attempt 2: 9.5-12s
    (9.5, [("white", "", False)]),
    (9.6, [("yellow", "━━━ Strategy 1: QUICK-FIX (attempt 2/2) ━━━", False)]),
    (9.8, [("dim", "  → Fix the specific error. Minimal change.", False)]),
    (10.3, [("dim", "  Creating ErrorCode enum in namespace...", False)]),
    (11.0, [("red", "  ✗ FAIL — CS0103: 'PipeRetryWrapper' does not exist", False)]),

    # Refactor: 12-17s
    (12.0, [("white", "", False)]),
    (12.1, [("blue", "━━━ Strategy 2: REFACTOR (attempt 1/1) ━━━", False)]),
    (12.3, [("dim", "  → Read more context. Refactor the approach.", False)]),
    (13.0, [("dim", "  Reading 4 additional source files...", False)]),
    (14.0, [("dim", "  Restructuring error handling pattern...", False)]),
    (15.5, [("red", "  ✗ FAIL — CS0029: cannot convert 'ErrorResult' to 'string'", False)]),

    # Alternative: 17-22s
    (17.0, [("white", "", False)]),
    (17.1, [("magenta", "━━━ Strategy 3: ALTERNATIVE (attempt 1/1) ━━━", True)]),
    (17.3, [("dim", "  → Completely different approach.", False)]),
    (18.0, [("dim", "  Bypassing custom error types...", False)]),
    (18.8, [("dim", "  Using built-in Exception pattern with error codes...", False)]),
    (19.8, [("dim", "  Building...", False)]),
    (20.8, [("green", "  ✓ BUILD SUCCEEDED", True)]),

    # Result: 22-33s
    (22.0, [("white", "", False)]),
    (22.1, [("green", "══════════════════════════════════════════════════", False)]),
    (22.2, [("green", "  RESOLVED on strategy 'alternative' (attempt 4/5)", True)]),
    (22.3, [("green", "══════════════════════════════════════════════════", False)]),
    (23.0, [("white", "", False)]),
    (23.1, [("dim", "  Retry Summary:", False)]),
    (23.5, [("red", "  [FAIL] quick-fix   #1 — CS0246: type not found", False)]),
    (23.8, [("red", "  [FAIL] quick-fix   #2 — PipeRetryWrapper missing", False)]),
    (24.1, [("red", "  [FAIL] refactor    #3 — cannot convert ErrorResult", False)]),
    (24.4, [("green", "  [ OK ] alternative #4 — build succeeded", False)]),

    # Memory: 33-38s
    (33.0, [("white", "", False)]),
    (33.2, [("cyan", "Storing to memory...", False)]),
    (34.0, [("dim", '  → "refactor strategy failed for MSBuild CS0246,', False)]),
    (34.1, [("dim", '     alternative succeeded with built-in Exception pattern"', False)]),
    (35.5, [("white", "", False)]),
    (35.7, [("cyan", "Next time this error occurs → skip to 'alternative'", False)]),

    # CTA: 38-42s
    (38.0, [("white", "", False)]),
    (38.5, [("bold_white", "github.com/WeberG619/cadre-ai", True)]),
]

# Captions (bottom of screen)
CAPTIONS = [
    (0.0, 5.0, "When my AI agent fails, it doesn't just retry."),
    (5.0, 2.0, "It runs a strategy ladder."),
    (7.0, 5.0, "Strategy 1: QUICK-FIX — Minimal change. Two shots."),
    (12.0, 5.0, "Strategy 2: REFACTOR — Read more context."),
    (17.0, 5.0, "Strategy 3: ALTERNATIVE — Completely different."),
    (22.0, 6.0, "If nothing works — detailed failure report."),
    (28.0, 5.0, "4 strategies. 5 max attempts. 15-min timeout."),
    (33.0, 5.0, "It remembers what worked — skips to it next time."),
    (38.0, 4.0, "cadre-ai — Link in bio"),
]

TOTAL_DURATION = 42.0

# ── RENDERING ─────────────────────────────────────

def load_fonts():
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, FONT_SIZE)
    font_caption = ImageFont.truetype(FONT_BOLD_PATH, CAPTION_FONT_SIZE)
    return font, font_bold, font_caption


def get_active_caption(t):
    for start, dur, text in CAPTIONS:
        if start <= t < start + dur:
            return text
    return None


def render_frame(t, lines, font, font_bold, font_caption):
    """Render a single frame at time t."""
    img = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # Draw terminal lines
    y = MARGIN_Y
    visible_start = max(0, len(lines) - ((HEIGHT - 200) // LINE_HEIGHT))
    for color_name, text, bold in lines[visible_start:]:
        if y > HEIGHT - 150:
            break
        color = COLORS.get(color_name, COLORS["white"])
        f = font_bold if bold else font
        draw.text((MARGIN_X, y), text, fill=color, font=f)
        y += LINE_HEIGHT

    # Draw caption bar (bottom)
    caption = get_active_caption(t)
    if caption:
        # Dark semi-transparent bar
        bar_y = HEIGHT - 100
        draw.rectangle([(0, bar_y), (WIDTH, HEIGHT)], fill=(10, 10, 15))
        # Centered caption text
        bbox = draw.textbbox((0, 0), caption, font=font_caption)
        tw = bbox[2] - bbox[0]
        tx = (WIDTH - tw) // 2
        # Text shadow
        draw.text((tx + 2, bar_y + 32), caption, fill=(0, 0, 0), font=font_caption)
        draw.text((tx, bar_y + 30), caption, fill=(255, 255, 255), font=font_caption)

    # Subtle top bar
    draw.rectangle([(0, 0), (WIDTH, 36)], fill=(30, 30, 40))
    title_font = ImageFont.truetype(FONT_PATH, 14)
    draw.text((MARGIN_X, 10), "weber@claude-code — adaptive-retry", fill=(100, 100, 120), font=title_font)

    return img


def generate_thumbnail(lines, font, font_bold, font_caption):
    """Generate a thumbnail from the 'BUILD SUCCEEDED' moment."""
    # Use frame at ~21s (build succeeded visible)
    thumb_lines = []
    for evt_time, evt_lines in EVENTS:
        if evt_time <= 24.5:
            thumb_lines.extend(evt_lines)
    img = render_frame(22.0, thumb_lines, font, font_bold, font_caption)

    # Add overlay title
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(FONT_BOLD_PATH, 64)
    subtitle_font = ImageFont.truetype(FONT_BOLD_PATH, 36)

    # Title
    title = "AI Agent Strategy Ladder"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    tx = (WIDTH - tw) // 2
    # Background rectangle
    draw.rectangle([(tx - 30, 180), (tx + tw + 30, 270)], fill=(18, 18, 24, 200))
    draw.text((tx + 3, 193), title, fill=(0, 0, 0), font=title_font)
    draw.text((tx, 190), title, fill=(139, 233, 253), font=title_font)

    img.save(str(THUMBNAIL), quality=95)
    print(f"  Thumbnail: {THUMBNAIL}")


def render_to_pipe(pipe, font, font_bold, font_caption):
    """Render all frames and write raw RGB to pipe."""
    total_frames = int(TOTAL_DURATION * FPS)
    lines = []
    event_idx = 0

    for frame_num in range(total_frames):
        t = frame_num / FPS

        # Add events that should appear by this time
        while event_idx < len(EVENTS) and EVENTS[event_idx][0] <= t:
            _, new_lines = EVENTS[event_idx]
            lines.extend(new_lines)
            event_idx += 1

        img = render_frame(t, lines, font, font_bold, font_caption)
        pipe.write(img.tobytes())

        if frame_num % (FPS * 5) == 0:
            print(f"  Rendering: {t:.0f}s / {TOTAL_DURATION:.0f}s")


def main():
    print("=" * 50)
    print("Rendering Video 01: Retry Ladder")
    print("=" * 50)

    font, font_bold, font_caption = load_fonts()

    # Generate thumbnail
    print("\nGenerating thumbnail...")
    thumb_lines = []
    for evt_time, evt_lines in EVENTS:
        if evt_time <= 24.5:
            thumb_lines.extend(evt_lines)
    generate_thumbnail(thumb_lines, font, font_bold, font_caption)

    # ── LANDSCAPE (1920x1080) ──
    print(f"\nRendering landscape {WIDTH}x{HEIGHT} @ {FPS}fps...")
    landscape_raw = BASE / "_temp_landscape.mp4"

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", str(AUDIO),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(OUT_LANDSCAPE),
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    render_to_pipe(proc.stdin, font, font_bold, font_caption)
    proc.stdin.close()
    proc.wait()
    stderr = proc.stderr.read() if proc.stderr else b""

    if proc.returncode == 0:
        size_mb = OUT_LANDSCAPE.stat().st_size / 1024 / 1024
        print(f"  Landscape saved: {OUT_LANDSCAPE} ({size_mb:.1f} MB)")
    else:
        print(f"  ERROR: {stderr.decode()[-500:]}")
        return

    # ── VERTICAL (1080x1920) — crop + rescale from landscape ──
    print("\nConverting to vertical (9:16)...")
    ffmpeg_vert = [
        "ffmpeg", "-y",
        "-i", str(OUT_LANDSCAPE),
        "-vf", "crop=608:1080:656:0,scale=1080:1920:flags=lanczos",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "copy",
        str(OUT_VERTICAL),
    ]
    result = subprocess.run(ffmpeg_vert, capture_output=True, text=True)
    if result.returncode == 0:
        size_mb = OUT_VERTICAL.stat().st_size / 1024 / 1024
        print(f"  Vertical saved: {OUT_VERTICAL} ({size_mb:.1f} MB)")
    else:
        print(f"  Vertical error: {result.stderr[-300:]}")

    print("\n" + "=" * 50)
    print("DONE!")
    print(f"  Landscape:  {OUT_LANDSCAPE}")
    print(f"  Vertical:   {OUT_VERTICAL}")
    print(f"  Thumbnail:  {THUMBNAIL}")
    print("=" * 50)


if __name__ == "__main__":
    main()
