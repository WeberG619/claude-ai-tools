#!/usr/bin/env python3
"""
Create Final YouTube Video with:
- Title card intro
- Background music
- Text overlays for each segment
- Lower third graphics
"""

import subprocess
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
SEGMENTS_DIR = BASE_DIR / "video_segments"
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_FILE = BASE_DIR / "AI_System_Overview_FINAL.mp4"

# Segment info with timestamps and overlay text
SEGMENTS = [
    {
        "file": "01_intro.mp4",
        "title": "INTRODUCTION",
        "subtitle": "AI-Powered Professional Software Automation",
        "key_points": ["AI Assistant", "Software Control", "Task Automation"]
    },
    {
        "file": "02_problem.mp4",
        "title": "THE PROBLEM",
        "subtitle": "Challenges in Professional Software",
        "key_points": ["Repetitive Tasks", "Manual Data Entry", "Context Switching"]
    },
    {
        "file": "03_solution.mp4",
        "title": "THE SOLUTION",
        "subtitle": "Model Context Protocol (MCP)",
        "key_points": ["AI Bridge Technology", "Direct Software Control", "Intelligent Automation"]
    },
    {
        "file": "04_how_it_works.mp4",
        "title": "HOW IT WORKS",
        "subtitle": "Natural Language to Action",
        "key_points": ["Natural Language Input", "Software Integration", "Automated Execution"]
    },
    {
        "file": "05_features_memory.mp4",
        "title": "PERSISTENT MEMORY",
        "subtitle": "AI That Learns & Remembers",
        "key_points": ["Session Memory", "Preference Learning", "Error Prevention"]
    },
    {
        "file": "06_features_voice.mp4",
        "title": "VOICE FEEDBACK",
        "subtitle": "Audio Status Updates",
        "key_points": ["Task Summaries", "Progress Reports", "Hands-Free Updates"]
    },
    {
        "file": "07_features_automation.mp4",
        "title": "AUTOMATION PIPELINES",
        "subtitle": "Repeatable Workflows",
        "key_points": ["One-Time Setup", "Consistent Execution", "Hours to Minutes"]
    },
    {
        "file": "08_applications.mp4",
        "title": "APPLICATIONS",
        "subtitle": "Beyond BIM & CAD",
        "key_points": ["Engineering Tools", "Design Applications", "Any API-Enabled Software"]
    },
    {
        "file": "09_benefits.mp4",
        "title": "THE BENEFITS",
        "subtitle": "Measurable Results",
        "key_points": ["50%+ Productivity Gain", "Reduced Errors", "Focus on High-Value Work"]
    },
    {
        "file": "10_closing.mp4",
        "title": "GET STARTED",
        "subtitle": "The Future of Professional Software",
        "key_points": ["AI Amplification", "Transform Your Workflow", "Links Below"]
    }
]

def get_video_duration(file_path):
    """Get video duration in seconds"""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def create_title_card():
    """Create a 4-second title card intro"""
    title_card = ASSETS_DIR / "title_card.mp4"

    # Create title card with ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1280x720:d=4",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", "4",
        "-vf", (
            "drawtext=text='AI-POWERED AUTOMATION':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-40,"
            "drawtext=text='Professional Software Integration':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=30:fontcolor=0x00d4ff:x=(w-text_w)/2:y=(h-text_h)/2+40,"
            "drawtext=text='BIM OPS STUDIO':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=24:fontcolor=0x888888:x=(w-text_w)/2:y=h-80,"
            "fade=t=in:st=0:d=1,fade=t=out:st=3:d=1"
        ),
        "-c:v", "libx264", "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        str(title_card)
    ]

    print("Creating title card...")
    subprocess.run(cmd, capture_output=True)
    return title_card

def add_overlays_to_segment(segment_info, index):
    """Add text overlays to a single segment"""
    input_file = SEGMENTS_DIR / segment_info["file"]
    output_file = SEGMENTS_DIR / f"overlay_{index:02d}.mp4"

    title = segment_info["title"]
    subtitle = segment_info["subtitle"]

    # Lower third style overlay
    filter_complex = (
        # Semi-transparent background bar at bottom
        f"drawbox=x=0:y=ih-120:w=iw:h=120:color=black@0.7:t=fill,"
        # Section number
        f"drawtext=text='{index+1:02d}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize=48:fontcolor=0x00d4ff:x=30:y=h-100,"
        # Title
        f"drawtext=text='{title}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize=36:fontcolor=white:x=100:y=h-105,"
        # Subtitle
        f"drawtext=text='{subtitle}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"fontsize=22:fontcolor=0xaaaaaa:x=100:y=h-60"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-vf", filter_complex,
        "-c:v", "libx264", "-c:a", "copy",
        "-preset", "fast",
        "-crf", "23",
        str(output_file)
    ]

    print(f"Adding overlays to segment {index+1}: {title}...")
    subprocess.run(cmd, capture_output=True)
    return output_file

def create_concat_with_overlays():
    """Create all overlay segments and concat list"""
    overlay_files = []

    # Create title card first
    title_card = create_title_card()
    overlay_files.append(title_card)

    # Add overlays to each segment
    for i, segment in enumerate(SEGMENTS):
        overlay_file = add_overlays_to_segment(segment, i)
        overlay_files.append(overlay_file)

    # Create concat list
    concat_list = ASSETS_DIR / "final_concat.txt"
    with open(concat_list, 'w') as f:
        for file in overlay_files:
            f.write(f"file '{file}'\n")

    return concat_list

def concat_videos(concat_list, output_no_music):
    """Concatenate all videos"""
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_no_music)
    ]

    print("Concatenating all segments...")
    subprocess.run(cmd, capture_output=True)
    return output_no_music

def add_background_music(video_file, output_file):
    """Add background music mixed with original audio"""
    music_file = ASSETS_DIR / "background_music.mp3"

    # Get video duration
    duration = get_video_duration(video_file)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_file),
        "-stream_loop", "-1", "-i", str(music_file),
        "-t", str(duration),
        "-filter_complex", (
            "[1:a]volume=0.15,afade=t=in:st=0:d=3,afade=t=out:st=" +
            str(duration - 3) + ":d=3[music];"
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        ),
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(output_file)
    ]

    print("Adding background music...")
    subprocess.run(cmd, capture_output=True)
    return output_file

def create_final_video():
    """Main function to create the complete video"""
    print("=" * 60)
    print("CREATING FINAL YOUTUBE VIDEO")
    print("=" * 60)

    # Step 1: Create segments with overlays
    concat_list = create_concat_with_overlays()

    # Step 2: Concatenate all segments
    temp_video = ASSETS_DIR / "temp_no_music.mp4"
    concat_videos(concat_list, temp_video)

    # Step 3: Add background music
    final_video = add_background_music(temp_video, OUTPUT_FILE)

    # Cleanup temp file
    if temp_video.exists():
        temp_video.unlink()

    print("=" * 60)
    print(f"COMPLETE! Final video: {OUTPUT_FILE}")
    print("=" * 60)

    # Get final video info
    duration = get_video_duration(OUTPUT_FILE)
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"Duration: {int(duration // 60)}:{int(duration % 60):02d}")
    print(f"Size: {size_mb:.1f} MB")

    return OUTPUT_FILE

if __name__ == "__main__":
    create_final_video()
