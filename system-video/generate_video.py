#!/usr/bin/env python3
"""
Video Generator for Claude Workflow System Overview
Creates slide images, generates narration audio, and combines into MP4 video.
"""

import json
import asyncio
import subprocess
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import edge_tts

# Configuration
PROJECT_DIR = Path(__file__).parent
SLIDES_DIR = PROJECT_DIR / "slides"
AUDIO_DIR = PROJECT_DIR / "audio"
OUTPUT_DIR = PROJECT_DIR / "output"
SCRIPT_FILE = PROJECT_DIR / "video_script.json"

# Video settings
WIDTH = 1920
HEIGHT = 1080
BG_COLOR = (20, 25, 35)  # Dark blue-gray
TITLE_COLOR = (100, 200, 255)  # Cyan
SUBTITLE_COLOR = (180, 180, 180)  # Light gray
BULLET_COLOR = (220, 220, 220)  # White-ish
ACCENT_COLOR = (80, 180, 120)  # Green accent

# Voice setting
VOICE = "en-US-AndrewNeural"  # Andrew voice


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default if needed."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]

    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    # Fallback to default
    return ImageFont.load_default()


def create_slide(slide_data: dict, slide_num: int, total_slides: int) -> Image.Image:
    """Create a single slide image."""
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Fonts
    title_font = get_font(72, bold=True)
    subtitle_font = get_font(36)
    bullet_font = get_font(32)
    small_font = get_font(24)

    # Draw gradient overlay at top
    for i in range(200):
        alpha = int(255 * (1 - i / 200) * 0.3)
        draw.rectangle([(0, i), (WIDTH, i + 1)], fill=(ACCENT_COLOR[0], ACCENT_COLOR[1], ACCENT_COLOR[2]))

    # Title
    title = slide_data.get('title', '')
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((WIDTH - title_width) // 2, 120), title, font=title_font, fill=TITLE_COLOR)

    # Subtitle
    subtitle = slide_data.get('subtitle', '')
    if subtitle:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        draw.text(((WIDTH - sub_width) // 2, 210), subtitle, font=subtitle_font, fill=SUBTITLE_COLOR)

    # Bullets
    bullets = slide_data.get('bullets', [])
    y_pos = 320
    for bullet in bullets:
        # Bullet point
        draw.ellipse([(140, y_pos + 12), (156, y_pos + 28)], fill=ACCENT_COLOR)
        # Text
        draw.text((180, y_pos), bullet, font=bullet_font, fill=BULLET_COLOR)
        y_pos += 60

    # Slide number
    slide_text = f"{slide_num} / {total_slides}"
    draw.text((WIDTH - 120, HEIGHT - 50), slide_text, font=small_font, fill=SUBTITLE_COLOR)

    # Bottom accent line
    draw.rectangle([(100, HEIGHT - 80), (WIDTH - 100, HEIGHT - 78)], fill=ACCENT_COLOR)

    # Logo/branding area
    draw.text((100, HEIGHT - 50), "Claude Workflow System", font=small_font, fill=SUBTITLE_COLOR)

    return img


async def generate_audio(text: str, output_path: Path) -> float:
    """Generate audio narration using Edge TTS. Returns duration in seconds."""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(output_path))

    # Get duration using ffprobe
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(output_path)
    ], capture_output=True, text=True)

    duration = float(result.stdout.strip()) if result.stdout.strip() else 10.0
    return duration


def combine_video(slides_info: list, output_path: Path):
    """Combine slides and audio into final video using FFmpeg."""

    # Create concat file for ffmpeg
    concat_file = PROJECT_DIR / "concat.txt"

    with open(concat_file, 'w') as f:
        for info in slides_info:
            # Each slide needs to be shown for the duration of its audio
            f.write(f"file '{info['image']}'\n")
            f.write(f"duration {info['duration']}\n")
        # Repeat last frame (ffmpeg requirement)
        f.write(f"file '{slides_info[-1]['image']}'\n")

    # First, create video from images
    video_only = PROJECT_DIR / "video_only.mp4"
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
        '-vf', 'scale=1920:1080,format=yuv420p',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        str(video_only)
    ], check=True)

    # Concatenate all audio files
    audio_concat = PROJECT_DIR / "audio_concat.txt"
    with open(audio_concat, 'w') as f:
        for info in slides_info:
            f.write(f"file '{info['audio']}'\n")

    audio_combined = PROJECT_DIR / "audio_combined.mp3"
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(audio_concat),
        '-c:a', 'libmp3lame', '-q:a', '2',
        str(audio_combined)
    ], check=True)

    # Combine video and audio
    subprocess.run([
        'ffmpeg', '-y', '-i', str(video_only), '-i', str(audio_combined),
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        str(output_path)
    ], check=True)

    # Cleanup temp files
    concat_file.unlink()
    audio_concat.unlink()
    video_only.unlink()
    audio_combined.unlink()

    print(f"\n✓ Video created: {output_path}")


async def main():
    """Main video generation process."""
    print("=" * 60)
    print("Claude Workflow System - Video Generator")
    print("=" * 60)

    # Load script
    with open(SCRIPT_FILE, 'r') as f:
        script = json.load(f)

    slides = script['slides']
    total_slides = len(slides)

    print(f"\nProcessing {total_slides} slides...")

    slides_info = []

    for i, slide in enumerate(slides, 1):
        slide_id = slide['id']
        print(f"\n[{i}/{total_slides}] Slide: {slide['title']}")

        # Create slide image
        print("  → Creating image...")
        img = create_slide(slide, i, total_slides)
        img_path = SLIDES_DIR / f"slide_{slide_id:02d}.png"
        img.save(img_path, 'PNG')

        # Generate audio
        print("  → Generating narration...")
        audio_path = AUDIO_DIR / f"audio_{slide_id:02d}.mp3"
        duration = await generate_audio(slide['narration'], audio_path)
        print(f"  → Duration: {duration:.1f}s")

        slides_info.append({
            'id': slide_id,
            'image': str(img_path),
            'audio': str(audio_path),
            'duration': duration
        })

    # Calculate total duration
    total_duration = sum(info['duration'] for info in slides_info)
    print(f"\n{'=' * 60}")
    print(f"Total video duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
    print(f"{'=' * 60}")

    # Combine into video
    print("\nCombining into final video...")
    output_path = OUTPUT_DIR / "claude_workflow_system_overview.mp4"
    combine_video(slides_info, output_path)

    print(f"\n{'=' * 60}")
    print(f"VIDEO COMPLETE!")
    print(f"{'=' * 60}")
    print(f"\nFile: {output_path}")
    print(f"Size: {output_path.stat().st_size / (1024*1024):.1f} MB")
    print(f"Duration: {total_duration/60:.1f} minutes")
    print(f"\nReady for YouTube upload!")


if __name__ == "__main__":
    asyncio.run(main())
