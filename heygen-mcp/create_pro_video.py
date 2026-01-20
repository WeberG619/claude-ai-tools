#!/usr/bin/env python3
"""
Create Professional YouTube Video with:
- Smooth crossfade transitions
- Title card intro with fade
- Background music
- Lower third overlays
- No visible cuts or breaks
"""

import subprocess
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
SEGMENTS_DIR = BASE_DIR / "video_segments"
ASSETS_DIR = BASE_DIR / "assets"
TEMP_DIR = ASSETS_DIR / "temp"
OUTPUT_FILE = BASE_DIR / "AI_System_Overview_PRO.mp4"

# Ensure temp directory exists
TEMP_DIR.mkdir(parents=True, exist_ok=True)

SEGMENTS = [
    {"file": "01_intro.mp4", "title": "INTRODUCTION", "subtitle": "AI-Powered Professional Software Automation"},
    {"file": "02_problem.mp4", "title": "THE PROBLEM", "subtitle": "Challenges in Professional Software"},
    {"file": "03_solution.mp4", "title": "THE SOLUTION", "subtitle": "Model Context Protocol (MCP)"},
    {"file": "04_how_it_works.mp4", "title": "HOW IT WORKS", "subtitle": "Natural Language to Action"},
    {"file": "05_features_memory.mp4", "title": "PERSISTENT MEMORY", "subtitle": "AI That Learns & Remembers"},
    {"file": "06_features_voice.mp4", "title": "VOICE FEEDBACK", "subtitle": "Audio Status Updates"},
    {"file": "07_features_automation.mp4", "title": "AUTOMATION PIPELINES", "subtitle": "Repeatable Workflows"},
    {"file": "08_applications.mp4", "title": "APPLICATIONS", "subtitle": "Beyond BIM & CAD"},
    {"file": "09_benefits.mp4", "title": "THE BENEFITS", "subtitle": "Measurable Results"},
    {"file": "10_closing.mp4", "title": "GET STARTED", "subtitle": "The Future of Professional Software"},
]

TRANSITION_DURATION = 0.8  # Smooth crossfade duration

def get_video_duration(file_path):
    """Get video duration in seconds"""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def create_title_card():
    """Create a smooth fade-in title card"""
    title_card = TEMP_DIR / "title_card.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1280x720:d=5:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", "5",
        "-vf", (
            "drawtext=text='AI-POWERED AUTOMATION':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=56:fontcolor=white:"
            "x=(w-text_w)/2:y=(h-text_h)/2-50:"
            "alpha='if(lt(t,1),t,if(lt(t,4),1,5-t))',"
            "drawtext=text='Professional Software Integration':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=28:fontcolor=0x00d4ff:"
            "x=(w-text_w)/2:y=(h-text_h)/2+20:"
            "alpha='if(lt(t,1.2),t/1.2,if(lt(t,3.8),1,(5-t)/1.2))',"
            "drawtext=text='Transforming How Professionals Work':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=20:fontcolor=0x888888:"
            "x=(w-text_w)/2:y=(h-text_h)/2+70:"
            "alpha='if(lt(t,1.5),t/1.5,if(lt(t,3.5),1,(5-t)/1.5))'"
        ),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-r", "25",
        str(title_card)
    ]

    print("Creating title card with fade...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return title_card

def add_lower_third(input_file, output_file, index, title, subtitle):
    """Add animated lower third overlay"""

    # Lower third with slide-in animation
    filter_complex = (
        # Background bar slides in from left
        f"drawbox=x='if(lt(t,0.5),-400+t*800,0)':y=ih-100:w=450:h=100:"
        f"color=0x1a1a2e@0.85:t=fill,"
        # Accent line
        f"drawbox=x='if(lt(t,0.5),-400+t*800,0)':y=ih-100:w=5:h=100:"
        f"color=0x00d4ff:t=fill,"
        # Section number with fade in
        f"drawtext=text='{index+1:02d}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize=36:fontcolor=0x00d4ff:"
        f"x=20:y=h-85:"
        f"alpha='if(lt(t,0.6),t/0.6,1)',"
        # Title with fade in
        f"drawtext=text='{title}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize=28:fontcolor=white:"
        f"x=75:y=h-90:"
        f"alpha='if(lt(t,0.7),t/0.7,1)',"
        # Subtitle with delayed fade in
        f"drawtext=text='{subtitle}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"fontsize=18:fontcolor=0xaaaaaa:"
        f"x=75:y=h-55:"
        f"alpha='if(lt(t,0.9),(t-0.2)/0.7,1)'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-vf", filter_complex,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        str(output_file)
    ]

    print(f"  Adding lower third to segment {index+1}: {title}...")
    subprocess.run(cmd, capture_output=True, text=True)
    return output_file

def crossfade_two_videos(video1, video2, output, fade_duration=TRANSITION_DURATION):
    """Crossfade two videos together"""
    dur1 = get_video_duration(video1)
    offset = dur1 - fade_duration

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video1),
        "-i", str(video2),
        "-filter_complex", (
            f"[0:v][1:v]xfade=transition=fade:duration={fade_duration}:offset={offset}[v];"
            f"[0:a][1:a]acrossfade=d={fade_duration}[a]"
        ),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        str(output)
    ]

    subprocess.run(cmd, capture_output=True, text=True)
    return output

def add_background_music(video_file, output_file):
    """Add subtle background music"""
    music_file = ASSETS_DIR / "background_music.mp3"
    duration = get_video_duration(video_file)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_file),
        "-stream_loop", "-1", "-i", str(music_file),
        "-t", str(duration),
        "-filter_complex", (
            f"[1:a]volume=0.12,afade=t=in:st=0:d=4,afade=t=out:st={duration-4}:d=4[music];"
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[aout]"
        ),
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(output_file)
    ]

    print("Adding background music...")
    subprocess.run(cmd, capture_output=True, text=True)
    return output_file

def create_professional_video():
    """Create the complete professional video"""
    print("=" * 60)
    print("CREATING PROFESSIONAL YOUTUBE VIDEO")
    print("=" * 60)
    print()

    # Step 1: Create title card
    title_card = create_title_card()

    # Step 2: Add lower thirds to all segments
    print("Adding lower third overlays...")
    overlay_files = []
    for i, seg in enumerate(SEGMENTS):
        input_file = SEGMENTS_DIR / seg["file"]
        output_file = TEMP_DIR / f"overlay_{i:02d}.mp4"
        add_lower_third(input_file, output_file, i, seg["title"], seg["subtitle"])
        overlay_files.append(output_file)

    # Step 3: Chain crossfade all videos together
    print()
    print("Creating smooth crossfade transitions...")

    # Start with title card
    current = title_card

    for i, overlay_file in enumerate(overlay_files):
        next_output = TEMP_DIR / f"chain_{i:02d}.mp4"
        print(f"  Crossfading segment {i+1}/10...")
        crossfade_two_videos(current, overlay_file, next_output)

        # Clean up previous temp file (except title card on first iteration)
        if i > 0:
            prev_chain = TEMP_DIR / f"chain_{i-1:02d}.mp4"
            if prev_chain.exists():
                prev_chain.unlink()

        current = next_output

    # Step 4: Add background music
    print()
    video_no_music = current
    add_background_music(video_no_music, OUTPUT_FILE)

    # Cleanup
    print("Cleaning up temporary files...")
    for f in TEMP_DIR.glob("*.mp4"):
        f.unlink()

    print()
    print("=" * 60)
    print("PROFESSIONAL VIDEO COMPLETE!")
    print("=" * 60)

    duration = get_video_duration(OUTPUT_FILE)
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)

    print(f"Output: {OUTPUT_FILE}")
    print(f"Duration: {int(duration // 60)}:{int(duration % 60):02d}")
    print(f"Size: {size_mb:.1f} MB")
    print()
    print("Features:")
    print("  - Animated title card intro")
    print("  - Smooth crossfade transitions")
    print("  - Professional lower third graphics")
    print("  - Subtle background music")

    return OUTPUT_FILE

if __name__ == "__main__":
    create_professional_video()
