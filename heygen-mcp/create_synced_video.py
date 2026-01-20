#!/usr/bin/env python3
"""
Create Final Video - Preserving Audio/Video Sync
Uses careful encoding to maintain lip sync from HeyGen
"""

import subprocess
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
SEGMENTS_DIR = BASE_DIR / "video_segments"
ASSETS_DIR = BASE_DIR / "assets"
TEMP_DIR = ASSETS_DIR / "synced_temp"
OUTPUT_FILE = BASE_DIR / "AI_System_Overview_SYNCED.mp4"

TEMP_DIR.mkdir(parents=True, exist_ok=True)

SEGMENTS = [
    {"file": "01_intro.mp4", "title": "INTRODUCTION", "subtitle": "AI-Powered Automation"},
    {"file": "02_problem.mp4", "title": "THE PROBLEM", "subtitle": "Professional Software Challenges"},
    {"file": "03_solution.mp4", "title": "THE SOLUTION", "subtitle": "Model Context Protocol"},
    {"file": "04_how_it_works.mp4", "title": "HOW IT WORKS", "subtitle": "Natural Language to Action"},
    {"file": "05_features_memory.mp4", "title": "PERSISTENT MEMORY", "subtitle": "AI That Remembers"},
    {"file": "06_features_voice.mp4", "title": "VOICE FEEDBACK", "subtitle": "Audio Updates"},
    {"file": "07_features_automation.mp4", "title": "AUTOMATION", "subtitle": "Repeatable Workflows"},
    {"file": "08_applications.mp4", "title": "APPLICATIONS", "subtitle": "Beyond BIM & CAD"},
    {"file": "09_benefits.mp4", "title": "THE BENEFITS", "subtitle": "Measurable Results"},
    {"file": "10_closing.mp4", "title": "GET STARTED", "subtitle": "Transform Your Workflow"},
]

def get_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def add_overlay_sync_safe(input_file, output_file, index, title, subtitle):
    """Add overlay while preserving exact sync using vsync passthrough"""

    filter_str = (
        f"drawbox=x=0:y=ih-80:w=380:h=80:color=0x000000@0.75:t=fill,"
        f"drawbox=x=0:y=ih-80:w=4:h=80:color=0x00d4ff:t=fill,"
        f"drawtext=text='{index+1:02d}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize=28:fontcolor=0x00d4ff:x=15:y=h-65,"
        f"drawtext=text='{title}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize=22:fontcolor=white:x=55:y=h-68,"
        f"drawtext=text='{subtitle}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"fontsize=14:fontcolor=0xaaaaaa:x=55:y=h-40"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-vf", filter_str,
        "-c:v", "libx264",
        "-preset", "slow",  # Better quality
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",  # Match original sample rate
        "-vsync", "cfr",  # Constant frame rate for sync
        "-async", "1",  # Audio sync
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_file)
    ]

    print(f"  Processing {index+1}: {title}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    Warning: {result.stderr[:200]}")
    return output_file

def create_title_card():
    """Create simple title card"""
    title_card = TEMP_DIR / "title.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x111111:s=1280x720:d=5:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", "5",
        "-vf", (
            "drawtext=text='AI-POWERED AUTOMATION':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=54:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-40,"
            "drawtext=text='Professional Software Integration':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=26:fontcolor=0x00d4ff:x=(w-text_w)/2:y=(h-text_h)/2+30,"
            "fade=t=in:st=0:d=1,fade=t=out:st=4:d=1"
        ),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-pix_fmt", "yuv420p",
        str(title_card)
    ]

    print("Creating title card...")
    subprocess.run(cmd, capture_output=True)
    return title_card

def create_outro():
    """Create outro card"""
    outro = TEMP_DIR / "outro.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x111111:s=1280x720:d=8:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", "8",
        "-vf", (
            "fade=t=in:st=0:d=1,"
            "drawtext=text='THANKS FOR WATCHING':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=44:fontcolor=white:x=(w-text_w)/2:y=180,"
            "drawtext=text='SUBSCRIBE | LIKE | COMMENT':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=28:fontcolor=0x00d4ff:x=(w-text_w)/2:y=300,"
            "drawtext=text='Links in description':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=20:fontcolor=0x888888:x=(w-text_w)/2:y=380,"
            "drawtext=text='BIM OPS STUDIO':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=24:fontcolor=0x00d4ff:x=(w-text_w)/2:y=500,"
            "fade=t=out:st=7:d=1"
        ),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-pix_fmt", "yuv420p",
        str(outro)
    ]

    print("Creating outro...")
    subprocess.run(cmd, capture_output=True)
    return outro

def concat_with_sync(file_list, output_file):
    """Concatenate using concat demuxer for perfect sync"""

    # Create concat file
    concat_file = TEMP_DIR / "concat.txt"
    with open(concat_file, 'w') as f:
        for file in file_list:
            f.write(f"file '{file}'\n")

    # Use concat demuxer (stream copy where possible)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-vsync", "cfr",
        "-async", "1",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_file)
    ]

    print("Concatenating with sync preservation...")
    subprocess.run(cmd, capture_output=True)
    return output_file

def add_music(video_file, output_file):
    """Add background music at low volume"""
    music_file = ASSETS_DIR / "background_music.mp3"
    duration = get_duration(video_file)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_file),
        "-stream_loop", "-1",
        "-i", str(music_file),
        "-t", str(duration),
        "-filter_complex", (
            f"[1:a]volume=0.08,afade=t=in:st=0:d=3,afade=t=out:st={duration-3}:d=3[music];"
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        ),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",  # Don't re-encode video
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_file)
    ]

    print("Adding background music (preserving video stream)...")
    subprocess.run(cmd, capture_output=True)
    return output_file

def main():
    print("=" * 60)
    print("CREATING SYNC-SAFE VIDEO")
    print("=" * 60)
    print()

    # Create title and outro
    title = create_title_card()
    outro = create_outro()

    # Process segments with overlays
    print("Adding overlays to segments...")
    processed = []
    processed.append(title)

    for i, seg in enumerate(SEGMENTS):
        input_file = SEGMENTS_DIR / seg["file"]
        output_file = TEMP_DIR / f"seg_{i:02d}.mp4"
        add_overlay_sync_safe(input_file, output_file, i, seg["title"], seg["subtitle"])
        processed.append(output_file)

    processed.append(outro)

    # Concatenate all
    print()
    temp_concat = TEMP_DIR / "concat_temp.mp4"
    concat_with_sync(processed, temp_concat)

    # Add music (video stream copy to preserve sync)
    print()
    add_music(temp_concat, OUTPUT_FILE)

    # Cleanup
    print("Cleaning up...")
    for f in TEMP_DIR.glob("*"):
        try:
            f.unlink()
        except:
            pass

    print()
    print("=" * 60)
    print("COMPLETE!")
    print("=" * 60)

    duration = get_duration(OUTPUT_FILE)
    size = OUTPUT_FILE.stat().st_size / (1024*1024)

    print(f"Output: {OUTPUT_FILE}")
    print(f"Duration: {int(duration//60)}:{int(duration%60):02d}")
    print(f"Size: {size:.1f} MB")
    print()
    print("Sync-safe features:")
    print("  - Constant frame rate encoding")
    print("  - Audio sync flags enabled")
    print("  - Video stream copy for music pass")
    print("  - Matched audio sample rates")

if __name__ == "__main__":
    main()
