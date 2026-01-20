#!/usr/bin/env python3
"""
Create Premium YouTube Video with:
- Extended intro with brand animation
- Visual slides between segments
- Animated bullet points and key takeaways
- Smooth crossfade transitions
- Professional lower thirds
- Background music
- Extended outro with call-to-action
"""

import subprocess
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
SEGMENTS_DIR = BASE_DIR / "video_segments"
ASSETS_DIR = BASE_DIR / "assets"
TEMP_DIR = ASSETS_DIR / "premium_temp"
OUTPUT_FILE = BASE_DIR / "AI_System_Overview_PREMIUM.mp4"

TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Extended segment info with visual content
SEGMENTS = [
    {
        "file": "01_intro.mp4",
        "title": "INTRODUCTION",
        "subtitle": "AI-Powered Professional Software Automation",
        "visual_points": [
            "AI Assistant That Controls Software",
            "Automates Repetitive Tasks",
            "Learns From Every Interaction"
        ]
    },
    {
        "file": "02_problem.mp4",
        "title": "THE PROBLEM",
        "subtitle": "Challenges in Professional Software",
        "visual_points": [
            "Hours on Repetitive Tasks",
            "Manual Data Entry & Copying",
            "Constant Application Switching"
        ]
    },
    {
        "file": "03_solution.mp4",
        "title": "THE SOLUTION",
        "subtitle": "Model Context Protocol (MCP)",
        "visual_points": [
            "Direct Software Connection",
            "AI Sees Your Project",
            "Takes Actions For You"
        ]
    },
    {
        "file": "04_how_it_works.mp4",
        "title": "HOW IT WORKS",
        "subtitle": "Natural Language to Action",
        "visual_points": [
            "Speak Naturally to AI",
            "AI Understands & Plans",
            "Executes Commands Automatically"
        ]
    },
    {
        "file": "05_features_memory.mp4",
        "title": "PERSISTENT MEMORY",
        "subtitle": "AI That Learns & Remembers",
        "visual_points": [
            "Remembers Your Preferences",
            "Recalls Past Decisions",
            "Never Repeats Mistakes"
        ]
    },
    {
        "file": "06_features_voice.mp4",
        "title": "VOICE FEEDBACK",
        "subtitle": "Audio Status Updates",
        "visual_points": [
            "Spoken Task Summaries",
            "Real-Time Progress Updates",
            "Hands-Free Notifications"
        ]
    },
    {
        "file": "07_features_automation.mp4",
        "title": "AUTOMATION PIPELINES",
        "subtitle": "Repeatable Workflows",
        "visual_points": [
            "Define Steps Once",
            "Execute Consistently",
            "Hours Become Minutes"
        ]
    },
    {
        "file": "08_applications.mp4",
        "title": "APPLICATIONS",
        "subtitle": "Beyond BIM & CAD",
        "visual_points": [
            "Engineering & Design Tools",
            "Project Management Systems",
            "Any API-Enabled Software"
        ]
    },
    {
        "file": "09_benefits.mp4",
        "title": "THE BENEFITS",
        "subtitle": "Measurable Results",
        "visual_points": [
            "50%+ Productivity Increase",
            "Dramatically Reduced Errors",
            "Focus on High-Value Work"
        ]
    },
    {
        "file": "10_closing.mp4",
        "title": "GET STARTED",
        "subtitle": "The Future of Professional Software",
        "visual_points": [
            "AI That Amplifies You",
            "Transform Your Workflow",
            "Links in Description"
        ]
    },
]

TRANSITION_DURATION = 1.0

def get_video_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def create_extended_intro():
    """Create 8-second animated intro"""
    intro = TEMP_DIR / "intro.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0d1117:s=1280x720:d=8:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "8",
        "-vf", (
            # Animated accent line
            "drawbox=x='(w-600)/2':y='(h/2)-2':w='min(t*150,600)':h=4:color=0x00d4ff:t=fill,"
            # Main title fade in
            "drawtext=text='AI-POWERED':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=72:fontcolor=white:"
            "x=(w-text_w)/2:y=(h-text_h)/2-80:"
            "alpha='if(lt(t,1),t,1)',"
            # Second line
            "drawtext=text='AUTOMATION SYSTEM':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=72:fontcolor=0x00d4ff:"
            "x=(w-text_w)/2:y=(h-text_h)/2+10:"
            "alpha='if(lt(t,1.5),(t-0.5),1)',"
            # Tagline
            "drawtext=text='Professional Software Integration':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=28:fontcolor=0x888888:"
            "x=(w-text_w)/2:y=(h-text_h)/2+110:"
            "alpha='if(lt(t,2),(t-1),1)',"
            # Brand
            "drawtext=text='BIM OPS STUDIO':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=20:fontcolor=0x555555:"
            "x=(w-text_w)/2:y=h-60:"
            "alpha='if(lt(t,2.5),(t-1.5),1)',"
            # Fade out at end
            "fade=t=out:st=7:d=1"
        ),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-pix_fmt", "yuv420p", "-r", "25",
        str(intro)
    ]

    print("Creating extended intro animation...")
    subprocess.run(cmd, capture_output=True, text=True)
    return intro

def create_visual_slide(points, title, index):
    """Create animated visual slide with bullet points"""
    slide = TEMP_DIR / f"slide_{index:02d}.mp4"

    # Build filter for animated bullet points
    y_start = 280
    y_spacing = 80

    filter_parts = [
        # Background
        "drawbox=x=0:y=0:w=iw:h=ih:color=0x0d1117:t=fill",
        # Section indicator
        f"drawtext=text='SECTION {index+1}':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "fontsize=16:fontcolor=0x00d4ff:x=60:y=60",
        # Title
        f"drawtext=text='{title}':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "fontsize=42:fontcolor=white:x=60:y=120:"
        "alpha='if(lt(t,0.5),t*2,1)'",
        # Accent line under title
        "drawbox=x=60:y=180:w=200:h=3:color=0x00d4ff:t=fill",
        # Key takeaways label
        "drawtext=text='KEY TAKEAWAYS':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "fontsize=14:fontcolor=0x666666:x=60:y=220:"
        "alpha='if(lt(t,0.8),(t-0.3)*2,1)'"
    ]

    # Add each bullet point with staggered animation
    for i, point in enumerate(points):
        delay = 0.5 + (i * 0.4)
        y_pos = y_start + (i * y_spacing)

        # Bullet circle
        filter_parts.append(
            f"drawtext=text='●':"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"fontsize=20:fontcolor=0x00d4ff:x=60:y={y_pos}:"
            f"alpha='if(lt(t,{delay}),0,if(lt(t,{delay+0.3}),(t-{delay})*3.33,1))'"
        )

        # Point text
        filter_parts.append(
            f"drawtext=text='{point}':"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"fontsize=28:fontcolor=white:x=100:y={y_pos}:"
            f"alpha='if(lt(t,{delay}),0,if(lt(t,{delay+0.3}),(t-{delay})*3.33,1))'"
        )

    # Fade out
    filter_parts.append("fade=t=in:st=0:d=0.5,fade=t=out:st=3.5:d=0.5")

    filter_str = ",".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0d1117:s=1280x720:d=4:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "4",
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-pix_fmt", "yuv420p", "-r", "25",
        str(slide)
    ]

    subprocess.run(cmd, capture_output=True, text=True)
    return slide

def create_extended_outro():
    """Create 10-second outro with call-to-action"""
    outro = TEMP_DIR / "outro.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0d1117:s=1280x720:d=10:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "10",
        "-vf", (
            # Fade in
            "fade=t=in:st=0:d=1,"
            # Thank you
            "drawtext=text='THANK YOU FOR WATCHING':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=48:fontcolor=white:"
            "x=(w-text_w)/2:y=150:"
            "alpha='if(lt(t,1),t,1)',"
            # Divider
            "drawbox=x=(w-400)/2:y=230:w=400:h=2:color=0x00d4ff:t=fill,"
            # CTA 1
            "drawtext=text='SUBSCRIBE for more AI automation content':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=26:fontcolor=0x00d4ff:"
            "x=(w-text_w)/2:y=280:"
            "alpha='if(lt(t,2),(t-1),1)',"
            # CTA 2
            "drawtext=text='LIKE this video if you found it valuable':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=26:fontcolor=white:"
            "x=(w-text_w)/2:y=340:"
            "alpha='if(lt(t,2.5),(t-1.5),1)',"
            # CTA 3
            "drawtext=text='COMMENT your questions below':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=26:fontcolor=white:"
            "x=(w-text_w)/2:y=400:"
            "alpha='if(lt(t,3),(t-2),1)',"
            # Links info
            "drawtext=text='Links and resources in the description':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=20:fontcolor=0x666666:"
            "x=(w-text_w)/2:y=480:"
            "alpha='if(lt(t,4),(t-3),1)',"
            # Brand
            "drawtext=text='BIM OPS STUDIO':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=28:fontcolor=0x00d4ff:"
            "x=(w-text_w)/2:y=560:"
            "alpha='if(lt(t,5),(t-4),1)',"
            # Fade out
            "fade=t=out:st=9:d=1"
        ),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-pix_fmt", "yuv420p", "-r", "25",
        str(outro)
    ]

    print("Creating extended outro with CTA...")
    subprocess.run(cmd, capture_output=True, text=True)
    return outro

def add_lower_third(input_file, output_file, index, title, subtitle):
    """Add professional lower third"""
    filter_complex = (
        f"drawbox=x='if(lt(t,0.5),-450+t*900,0)':y=ih-95:w=420:h=95:"
        f"color=0x0d1117@0.9:t=fill,"
        f"drawbox=x='if(lt(t,0.5),-450+t*900,0)':y=ih-95:w=4:h=95:"
        f"color=0x00d4ff:t=fill,"
        f"drawtext=text='{index+1:02d}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize=32:fontcolor=0x00d4ff:"
        f"x=18:y=h-80:alpha='if(lt(t,0.6),t/0.6,1)',"
        f"drawtext=text='{title}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize=24:fontcolor=white:"
        f"x=65:y=h-82:alpha='if(lt(t,0.7),t/0.7,1)',"
        f"drawtext=text='{subtitle}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"fontsize=16:fontcolor=0x888888:"
        f"x=65:y=h-50:alpha='if(lt(t,0.9),(t-0.2)/0.7,1)'"
    )

    cmd = [
        "ffmpeg", "-y", "-i", str(input_file),
        "-vf", filter_complex,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        str(output_file)
    ]

    subprocess.run(cmd, capture_output=True, text=True)
    return output_file

def crossfade_videos(video1, video2, output, fade_dur=TRANSITION_DURATION):
    """Smooth crossfade between videos"""
    dur1 = get_video_duration(video1)
    offset = dur1 - fade_dur

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video1), "-i", str(video2),
        "-filter_complex", (
            f"[0:v][1:v]xfade=transition=fade:duration={fade_dur}:offset={offset}[v];"
            f"[0:a][1:a]acrossfade=d={fade_dur}[a]"
        ),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
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
            f"[1:a]volume=0.10,afade=t=in:st=0:d=5,afade=t=out:st={duration-5}:d=5[music];"
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[aout]"
        ),
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(output_file)
    ]

    print("Adding background music...")
    subprocess.run(cmd, capture_output=True, text=True)
    return output_file

def create_premium_video():
    """Create the complete premium video"""
    print("=" * 70)
    print("CREATING PREMIUM YOUTUBE VIDEO")
    print("=" * 70)
    print()

    # Build sequence list
    sequence = []

    # 1. Extended intro
    intro = create_extended_intro()
    sequence.append(intro)

    # 2. Process each segment with visual slides
    print("Processing segments with visual slides...")
    for i, seg in enumerate(SEGMENTS):
        # Add visual slide before segment (except first)
        if i > 0:
            print(f"  Creating visual slide {i}...")
            slide = create_visual_slide(
                SEGMENTS[i-1]["visual_points"],
                SEGMENTS[i-1]["title"],
                i-1
            )
            sequence.append(slide)

        # Add segment with lower third
        print(f"  Processing segment {i+1}: {seg['title']}...")
        input_file = SEGMENTS_DIR / seg["file"]
        output_file = TEMP_DIR / f"seg_{i:02d}.mp4"
        add_lower_third(input_file, output_file, i, seg["title"], seg["subtitle"])
        sequence.append(output_file)

    # Add final visual slide
    print("  Creating final visual slide...")
    final_slide = create_visual_slide(
        SEGMENTS[-1]["visual_points"],
        SEGMENTS[-1]["title"],
        len(SEGMENTS)-1
    )
    sequence.append(final_slide)

    # 3. Extended outro
    outro = create_extended_outro()
    sequence.append(outro)

    # 4. Chain all with crossfades
    print()
    print(f"Creating smooth transitions ({len(sequence)} clips)...")
    current = sequence[0]

    for i, next_clip in enumerate(sequence[1:], 1):
        next_output = TEMP_DIR / f"chain_{i:02d}.mp4"
        print(f"  Crossfading clip {i}/{len(sequence)-1}...")
        crossfade_videos(current, next_clip, next_output)

        # Cleanup previous chain file
        if i > 1:
            prev = TEMP_DIR / f"chain_{i-1:02d}.mp4"
            if prev.exists():
                prev.unlink()

        current = next_output

    # 5. Add background music
    print()
    add_background_music(current, OUTPUT_FILE)

    # Cleanup
    print("Cleaning up...")
    for f in TEMP_DIR.glob("*.mp4"):
        try:
            f.unlink()
        except:
            pass

    print()
    print("=" * 70)
    print("PREMIUM VIDEO COMPLETE!")
    print("=" * 70)

    duration = get_video_duration(OUTPUT_FILE)
    mins = int(duration // 60)
    secs = int(duration % 60)
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)

    print(f"Output: {OUTPUT_FILE}")
    print(f"Duration: {mins}:{secs:02d}")
    print(f"Size: {size_mb:.1f} MB")
    print()
    print("Features included:")
    print("  ✓ Extended animated intro (8 seconds)")
    print("  ✓ Visual slides with animated bullet points")
    print("  ✓ Professional lower third graphics")
    print("  ✓ Smooth crossfade transitions")
    print("  ✓ Extended outro with call-to-action")
    print("  ✓ Subtle background music")

    return OUTPUT_FILE

if __name__ == "__main__":
    create_premium_video()
