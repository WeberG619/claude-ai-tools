#!/usr/bin/env python3
"""
Final Video with Visual Slides - Sync Safe
Adds animated bullet point slides while preserving lip sync
"""

import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
SEGMENTS_DIR = BASE_DIR / "video_segments"
ASSETS_DIR = BASE_DIR / "assets"
TEMP_DIR = ASSETS_DIR / "final_temp"
OUTPUT_FILE = BASE_DIR / "AI_System_Overview_FINAL.mp4"

TEMP_DIR.mkdir(parents=True, exist_ok=True)

SEGMENTS = [
    {
        "file": "01_intro.mp4",
        "title": "INTRODUCTION",
        "subtitle": "AI-Powered Automation",
        "points": ["AI Assistant That Controls Software", "Automates Repetitive Tasks", "Learns From Every Interaction"]
    },
    {
        "file": "02_problem.mp4",
        "title": "THE PROBLEM",
        "subtitle": "Professional Software Challenges",
        "points": ["Hours on Repetitive Tasks", "Manual Data Entry", "Constant App Switching"]
    },
    {
        "file": "03_solution.mp4",
        "title": "THE SOLUTION",
        "subtitle": "Model Context Protocol",
        "points": ["Direct Software Connection", "AI Sees Your Project", "Takes Actions For You"]
    },
    {
        "file": "04_how_it_works.mp4",
        "title": "HOW IT WORKS",
        "subtitle": "Natural Language to Action",
        "points": ["Speak Naturally to AI", "AI Understands & Plans", "Executes Automatically"]
    },
    {
        "file": "05_features_memory.mp4",
        "title": "PERSISTENT MEMORY",
        "subtitle": "AI That Remembers",
        "points": ["Remembers Preferences", "Recalls Past Decisions", "Never Repeats Mistakes"]
    },
    {
        "file": "06_features_voice.mp4",
        "title": "VOICE FEEDBACK",
        "subtitle": "Audio Updates",
        "points": ["Spoken Task Summaries", "Real-Time Progress", "Hands-Free Updates"]
    },
    {
        "file": "07_features_automation.mp4",
        "title": "AUTOMATION",
        "subtitle": "Repeatable Workflows",
        "points": ["Define Steps Once", "Consistent Execution", "Hours to Minutes"]
    },
    {
        "file": "08_applications.mp4",
        "title": "APPLICATIONS",
        "subtitle": "Beyond BIM & CAD",
        "points": ["Engineering Tools", "Design Applications", "Any API-Enabled Software"]
    },
    {
        "file": "09_benefits.mp4",
        "title": "THE BENEFITS",
        "subtitle": "Measurable Results",
        "points": ["50%+ Productivity Gain", "Reduced Errors", "Focus on High-Value Work"]
    },
    {
        "file": "10_closing.mp4",
        "title": "GET STARTED",
        "subtitle": "Transform Your Workflow",
        "points": ["AI That Amplifies You", "Transform Your Workflow", "Links in Description"]
    },
]

def get_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def create_title_card():
    """Create animated title card"""
    output = TEMP_DIR / "00_title.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0a0a12:s=1280x720:d=6:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "6",
        "-vf", (
            "drawbox=x=340:y=358:w='min(t*150,600)':h=4:color=0x00d4ff:t=fill,"
            "drawtext=text='AI-POWERED':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=64:fontcolor=white:x=(w-text_w)/2:y=260:"
            "alpha='if(lt(t,1),t,1)',"
            "drawtext=text='AUTOMATION SYSTEM':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=64:fontcolor=0x00d4ff:x=(w-text_w)/2:y=380:"
            "alpha='if(lt(t,1.5),(t-0.5),1)',"
            "drawtext=text='Professional Software Integration':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=24:fontcolor=0x888888:x=(w-text_w)/2:y=480:"
            "alpha='if(lt(t,2),(t-1),1)',"
            "fade=t=in:st=0:d=0.5,fade=t=out:st=5:d=1"
        ),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-vsync", "cfr", "-pix_fmt", "yuv420p",
        str(output)
    ]

    print("Creating title card...")
    subprocess.run(cmd, capture_output=True)
    return output

def create_visual_slide(points, title, section_num, output_name):
    """Create animated bullet point slide"""
    output = TEMP_DIR / output_name

    # Build animated bullet points
    y_base = 300
    y_gap = 70

    filter_parts = [
        "drawbox=x=0:y=0:w=iw:h=ih:color=0x0a0a12:t=fill",
        f"drawtext=text='SECTION {section_num}':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "fontsize=14:fontcolor=0x00d4ff:x=80:y=100",
        f"drawtext=text='{title}':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "fontsize=38:fontcolor=white:x=80:y=140:"
        "alpha='if(lt(t,0.5),t*2,1)'",
        "drawbox=x=80:y=200:w=180:h=3:color=0x00d4ff:t=fill",
        "drawtext=text='KEY POINTS':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "fontsize=12:fontcolor=0x666666:x=80:y=230"
    ]

    for i, point in enumerate(points):
        delay = 0.6 + (i * 0.35)
        y = y_base + (i * y_gap)

        # Bullet
        filter_parts.append(
            f"drawtext=text='▸':"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"fontsize=24:fontcolor=0x00d4ff:x=80:y={y}:"
            f"alpha='if(lt(t,{delay}),0,if(lt(t,{delay+0.25}),(t-{delay})*4,1))'"
        )
        # Text
        filter_parts.append(
            f"drawtext=text='{point}':"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"fontsize=26:fontcolor=white:x=115:y={y}:"
            f"alpha='if(lt(t,{delay}),0,if(lt(t,{delay+0.25}),(t-{delay})*4,1))'"
        )

    filter_parts.append("fade=t=in:st=0:d=0.3,fade=t=out:st=3.2:d=0.3")
    filter_str = ",".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0a0a12:s=1280x720:d=3.5:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "3.5",
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-vsync", "cfr", "-pix_fmt", "yuv420p",
        str(output)
    ]

    subprocess.run(cmd, capture_output=True)
    return output

def add_lower_third(input_file, output_file, index, title, subtitle):
    """Add lower third overlay - sync safe"""

    filter_str = (
        f"drawbox=x=0:y=ih-80:w=380:h=80:color=0x0a0a12@0.85:t=fill,"
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
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-vsync", "cfr", "-async", "1",
        "-pix_fmt", "yuv420p",
        str(output_file)
    ]

    subprocess.run(cmd, capture_output=True)
    return output_file

def create_outro():
    """Create outro with CTA"""
    output = TEMP_DIR / "99_outro.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0a0a12:s=1280x720:d=8:r=25",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "8",
        "-vf", (
            "fade=t=in:st=0:d=0.5,"
            "drawtext=text='THANKS FOR WATCHING':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=42:fontcolor=white:x=(w-text_w)/2:y=200,"
            "drawbox=x=440:y=270:w=400:h=3:color=0x00d4ff:t=fill,"
            "drawtext=text='▸ SUBSCRIBE for more AI content':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=24:fontcolor=0x00d4ff:x=(w-text_w)/2:y=320:"
            "alpha='if(lt(t,1.5),(t-0.5),1)',"
            "drawtext=text='▸ LIKE if this was helpful':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=24:fontcolor=white:x=(w-text_w)/2:y=370:"
            "alpha='if(lt(t,2),(t-1),1)',"
            "drawtext=text='▸ COMMENT your questions':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=24:fontcolor=white:x=(w-text_w)/2:y=420:"
            "alpha='if(lt(t,2.5),(t-1.5),1)',"
            "drawtext=text='Links and resources in description':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            "fontsize=18:fontcolor=0x666666:x=(w-text_w)/2:y=500:"
            "alpha='if(lt(t,3),(t-2),1)',"
            "drawtext=text='BIM OPS STUDIO':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "fontsize=26:fontcolor=0x00d4ff:x=(w-text_w)/2:y=580:"
            "alpha='if(lt(t,3.5),(t-2.5),1)',"
            "fade=t=out:st=7:d=1"
        ),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-vsync", "cfr", "-pix_fmt", "yuv420p",
        str(output)
    ]

    print("Creating outro...")
    subprocess.run(cmd, capture_output=True)
    return output

def concat_all(file_list, output):
    """Concatenate with sync preservation"""
    concat_file = TEMP_DIR / "concat.txt"
    with open(concat_file, 'w') as f:
        for file in file_list:
            f.write(f"file '{file}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-vsync", "cfr", "-async", "1",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output)
    ]

    print("Concatenating all clips...")
    subprocess.run(cmd, capture_output=True)
    return output

def add_music(video, output):
    """Add background music"""
    music = ASSETS_DIR / "background_music.mp3"
    duration = get_duration(video)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-t", str(duration),
        "-filter_complex", (
            f"[1:a]volume=0.08,afade=t=in:st=0:d=4,afade=t=out:st={duration-4}:d=4[music];"
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        ),
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(output)
    ]

    print("Adding background music...")
    subprocess.run(cmd, capture_output=True)
    return output

def main():
    print("=" * 60)
    print("CREATING FINAL VIDEO WITH VISUAL SLIDES")
    print("=" * 60)
    print()

    all_clips = []

    # Title card
    title = create_title_card()
    all_clips.append(title)

    # Process each segment with slide before it
    print("Creating visual slides and processing segments...")
    for i, seg in enumerate(SEGMENTS):
        # Visual slide (except before first segment)
        if i > 0:
            print(f"  Creating slide for section {i}...")
            prev = SEGMENTS[i-1]
            slide = create_visual_slide(prev["points"], prev["title"], i, f"slide_{i:02d}.mp4")
            all_clips.append(slide)

        # Segment with lower third
        print(f"  Processing segment {i+1}: {seg['title']}...")
        input_file = SEGMENTS_DIR / seg["file"]
        output_file = TEMP_DIR / f"seg_{i:02d}.mp4"
        add_lower_third(input_file, output_file, i, seg["title"], seg["subtitle"])
        all_clips.append(output_file)

    # Final slide for last segment
    print("  Creating final slide...")
    last = SEGMENTS[-1]
    final_slide = create_visual_slide(last["points"], last["title"], 10, "slide_final.mp4")
    all_clips.append(final_slide)

    # Outro
    outro = create_outro()
    all_clips.append(outro)

    # Concatenate
    print()
    temp_video = TEMP_DIR / "temp_concat.mp4"
    concat_all(all_clips, temp_video)

    # Add music
    print()
    add_music(temp_video, OUTPUT_FILE)

    # Cleanup
    print("Cleaning up...")
    for f in TEMP_DIR.glob("*"):
        try:
            f.unlink()
        except:
            pass

    print()
    print("=" * 60)
    print("FINAL VIDEO COMPLETE!")
    print("=" * 60)

    duration = get_duration(OUTPUT_FILE)
    size = OUTPUT_FILE.stat().st_size / (1024*1024)

    print(f"Output: {OUTPUT_FILE}")
    print(f"Duration: {int(duration//60)}:{int(duration%60):02d}")
    print(f"Size: {size:.1f} MB")
    print()
    print("Features:")
    print("  ✓ Animated title intro")
    print("  ✓ Visual slides with bullet points")
    print("  ✓ Professional lower thirds")
    print("  ✓ Extended outro with CTA")
    print("  ✓ Background music")
    print("  ✓ Lip sync preserved")

if __name__ == "__main__":
    main()
