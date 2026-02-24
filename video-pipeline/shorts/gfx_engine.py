#!/usr/bin/env python3
"""
Graphics Engine for video shorts — animated diagrams, dashboards, flowing data.
Shared by all video render scripts.
"""

import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── FONTS ──────────────────────────────────────
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ── PALETTE ────────────────────────────────────
BG = (12, 12, 20)
BG_CARD = (22, 22, 35)
BG_CARD_LIGHT = (32, 32, 50)
CYAN = (0, 220, 255)
GREEN = (0, 255, 140)
RED = (255, 70, 70)
YELLOW = (255, 220, 60)
MAGENTA = (200, 100, 255)
BLUE = (80, 140, 255)
WHITE = (240, 240, 240)
DIM = (100, 100, 130)
ORANGE = (255, 160, 40)
GLOW_CYAN = (0, 180, 220, 60)
GLOW_GREEN = (0, 200, 120, 60)

W, H = 1920, 1080
FPS = 30


def font(size, bold=False, mono=False):
    if mono:
        return ImageFont.truetype(FONT_MONO_BOLD if bold else FONT_MONO, size)
    return ImageFont.truetype(FONT_SANS_BOLD if bold else FONT_SANS, size)


def new_frame():
    return Image.new("RGB", (W, H), BG)


def draw_grid(draw, spacing=60, color=(20, 20, 35)):
    """Subtle dot grid background."""
    for x in range(0, W, spacing):
        for y in range(0, H, spacing):
            draw.ellipse([(x-1, y-1), (x+1, y+1)], fill=color)


def draw_rounded_rect(draw, bbox, radius=16, fill=BG_CARD, outline=None, width=1):
    """Rounded rectangle."""
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)


def draw_card(draw, x, y, w, h, title="", color=CYAN, progress=None, subtitle="", status=None, icon=None):
    """Dashboard card with optional title, progress bar, status indicator."""
    # Card background
    draw_rounded_rect(draw, (x, y, x+w, y+h), radius=12, fill=BG_CARD, outline=(40, 40, 60), width=1)

    # Color accent line at top
    draw.rectangle([(x+1, y+1), (x+w-1, y+4)], fill=color)

    # Icon circle
    cx = x + 30
    if icon:
        draw.ellipse([(cx-12, y+22), (cx+12, y+46)], fill=color)
        f = font(14, bold=True)
        iw = draw.textlength(icon, font=f)
        draw.text((cx - iw/2, y+26), icon, fill=BG, font=f)
        cx += 30

    # Title
    if title:
        f = font(18, bold=True)
        draw.text((cx, y + 20), title, fill=WHITE, font=f)

    # Subtitle
    if subtitle:
        f = font(13)
        draw.text((cx, y + 46), subtitle, fill=DIM, font=f)

    # Progress bar
    if progress is not None:
        bar_y = y + h - 24
        bar_w = w - 30
        draw.rounded_rectangle([(x+15, bar_y), (x+15+bar_w, bar_y+8)], radius=4, fill=(30, 30, 50))
        filled = int(bar_w * min(progress, 1.0))
        if filled > 0:
            draw.rounded_rectangle([(x+15, bar_y), (x+15+filled, bar_y+8)], radius=4, fill=color)

    # Status dot
    if status:
        sx = x + w - 30
        sy = y + 28
        dot_color = GREEN if status == "ok" else RED if status == "fail" else YELLOW if status == "active" else DIM
        draw.ellipse([(sx-6, sy-6), (sx+6, sy+6)], fill=dot_color)


def draw_node(draw, cx, cy, radius=40, label="", color=CYAN, active=False, glow=False):
    """Circular node for architecture diagrams."""
    if glow:
        for r in range(radius+20, radius, -2):
            alpha_color = (*color[:3], max(0, 30 - (r - radius) * 3))
            # Approximate glow with lighter circles
            fade = max(0, 255 - (r - radius) * 15)
            gc = (color[0] * fade // 255, color[1] * fade // 255, color[2] * fade // 255)
            draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], fill=gc)

    fill = color if active else BG_CARD
    outline_c = color
    draw.ellipse([(cx-radius, cy-radius), (cx+radius, cy+radius)], fill=fill, outline=outline_c, width=2)

    if label:
        f = font(14 if len(label) > 6 else 16, bold=True)
        tw = draw.textlength(label, font=f)
        text_color = BG if active else color
        draw.text((cx - tw/2, cy - 8), label, fill=text_color, font=f)


def draw_connection(draw, x1, y1, x2, y2, color=DIM, width=2, animated_pos=None):
    """Line between two points with optional animated dot."""
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

    if animated_pos is not None:
        # Dot traveling along the line
        t = animated_pos % 1.0
        dx = x1 + (x2 - x1) * t
        dy = y1 + (y2 - y1) * t
        draw.ellipse([(dx-4, dy-4), (dx+4, dy+4)], fill=WHITE)


def draw_big_text(draw, text, y, color=WHITE, size=52):
    """Centered large text."""
    f = font(size, bold=True)
    tw = draw.textlength(text, font=f)
    draw.text(((W - tw) / 2, y), text, fill=color, font=f)


def draw_subtitle(draw, text, y, color=DIM, size=22):
    """Centered subtitle."""
    f = font(size)
    tw = draw.textlength(text, font=f)
    draw.text(((W - tw) / 2, y), text, fill=color, font=f)


def draw_caption(draw, text, color=WHITE):
    """Bottom caption bar."""
    bar_y = H - 90
    draw.rectangle([(0, bar_y), (W, H)], fill=(8, 8, 14))
    f = font(28, bold=True)
    tw = draw.textlength(text, font=f)
    draw.text(((W - tw) / 2, bar_y + 28), text, fill=color, font=f)


def draw_counter(draw, x, y, value, label, color=CYAN, size=48):
    """Big number with label underneath."""
    f = font(size, bold=True)
    tw = draw.textlength(str(value), font=f)
    draw.text((x - tw/2, y), str(value), fill=color, font=f)
    fl = font(16)
    lw = draw.textlength(label, font=fl)
    draw.text((x - lw/2, y + size + 5), label, fill=DIM, font=fl)


def draw_progress_ring(draw, cx, cy, radius, progress, color=CYAN, width=6):
    """Circular progress indicator."""
    # Background ring
    draw.arc([(cx-radius, cy-radius), (cx+radius, cy+radius)], 0, 360, fill=(30, 30, 50), width=width)
    # Progress arc
    angle = int(360 * min(progress, 1.0))
    if angle > 0:
        draw.arc([(cx-radius, cy-radius), (cx+radius, cy+radius)], -90, -90 + angle, fill=color, width=width)


def draw_terminal_line(draw, x, y, text, color=WHITE, mono_size=18):
    """Single terminal-style line."""
    f = font(mono_size, mono=True)
    draw.text((x, y), text, fill=color, font=f)


def ease_in_out(t):
    """Smooth easing function."""
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * min(max(t, 0), 1)


def _get_audio_duration(audio_path):
    """Get audio duration in seconds via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(audio_path)],
            capture_output=True, text=True)
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return None


def render_to_mp4(frame_generator, total_frames, output_path, audio_path=None):
    """Render frames to MP4 via FFmpeg pipe — single pass, same as video_01."""
    output_path = Path(output_path)

    # If audio exists, match frame count to audio duration
    if audio_path and Path(audio_path).exists():
        audio_dur = _get_audio_duration(audio_path)
        if audio_dur:
            total_frames = min(total_frames, int(audio_dur * FPS))
            print(f"  Audio: {audio_dur:.1f}s → rendering {total_frames} frames")

    # Single-pass: pipe raw video + audio input together (matches video_01 approach)
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24",
        "-r", str(FPS), "-i", "-",
    ]
    if audio_path and Path(audio_path).exists():
        cmd.extend(["-i", str(audio_path), "-c:a", "aac", "-b:a", "192k"])
    cmd.extend([
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-shortest",
        str(output_path),
    ])

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    for i in range(total_frames):
        frame = frame_generator(i, i / FPS)
        proc.stdin.write(frame.tobytes())
        if i % (FPS * 5) == 0:
            print(f"  {i/FPS:.0f}s / {total_frames/FPS:.0f}s")

    proc.stdin.close()
    proc.wait()

    if proc.returncode == 0 and output_path.exists():
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  Saved: {output_path} ({size_mb:.1f} MB)")
    else:
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        print(f"  ERROR (rc={proc.returncode}): {stderr[-300:]}")


def make_vertical(landscape_path, vertical_path):
    """Convert landscape to vertical 9:16."""
    subprocess.run([
        "ffmpeg", "-y", "-i", str(landscape_path),
        "-vf", "crop=608:1080:656:0,scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy", str(vertical_path)
    ], capture_output=True)
    if Path(vertical_path).exists():
        print(f"  Vertical: {vertical_path}")


ELEVENLABS_API_KEY = "sk_9b7b51c745285626934572da9c9920ef713fe6eb01fccfa1"
ELEVENLABS_VOICE_ID = "TX3LPaxmHKxFdv7VOQHJ"  # Liam - Energetic


def generate_audio(segments, output_dir):
    """Generate TTS audio segments + full narration via ElevenLabs."""
    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    def _generate_one(text, filepath):
        audio = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
        )
        with open(filepath, "wb") as f:
            for chunk in audio:
                f.write(chunk)

    # Individual segments
    for name, text in segments:
        f = out / f"{name}.mp3"
        _generate_one(text, f)
        print(f"  Generated: {f.name}")

    # Full narration (all segments with pauses)
    full_text = " ... ".join(t for _, t in segments)
    full_path = out / "full_narration.mp3"
    _generate_one(full_text, full_path)
    print(f"  Generated: full_narration.mp3")

    return full_path
