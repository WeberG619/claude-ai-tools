#!/usr/bin/env python3
"""
Full pipeline: Record demo + Post-production + Upload
=====================================================
Runs from WSL, orchestrates:
1. Start FFmpeg recording on Windows (Revit monitor)
2. Run demo_revit_video.py (real speed)
3. Stop recording
4. Post-production: title card + narration overlay
5. Upload to YouTube

Usage:
    python3 record_and_produce.py [--skip-record] [--skip-upload]
"""

import subprocess
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()

# Paths
VIDEO_PIPELINE = Path(__file__).parent
RECORDINGS_DIR = VIDEO_PIPELINE / "recordings"
AUDIO_DIR = VIDEO_PIPELINE / "audio"
NARRATION_SCRIPT = VIDEO_PIPELINE / "narration_script.txt"
DEMO_SCRIPT = VIDEO_PIPELINE / "demo_revit_video.py"
FFMPEG_WIN = r"C:\Program Files\ffmpeg-2025-03-20-git-76f09ab647-full_build\bin\ffmpeg.exe"
FFMPEG_WSL = "/mnt/c/Program Files/ffmpeg-2025-03-20-git-76f09ab647-full_build/bin/ffmpeg.exe"
FFMPEG_NATIVE = "ffmpeg"  # Native WSL ffmpeg for post-production (can access WSL fonts)
SYSTEM_STATE = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
UPLOADER = Path("/mnt/d/_CLAUDE-TOOLS/youtube-uploader/upload.py")

# OBS WebSocket config (OBS runs on Windows, connect via host IP from WSL)
OBS_PORT = 4455
OBS_PASSWORD = "2GwO1bvUqSIy3V2X"
OBS_SCENE = "Screen 2"  # Center monitor where Revit runs

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


def _get_obs_host():
    """Get Windows host IP for OBS WebSocket connection from WSL."""
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                if line.startswith("nameserver"):
                    return line.split()[1]
    except Exception:
        pass
    return "172.24.224.1"


def _get_obs_client():
    """Create an OBS WebSocket client."""
    import obsws_python as obs
    host = _get_obs_host()
    return obs.ReqClient(host=host, port=OBS_PORT, password=OBS_PASSWORD, timeout=10)


def start_recording(monitor_info=None):
    """Start OBS recording on the center monitor (Screen 2)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"demo_recording_{timestamp}.mp4"
    output_path_wsl = str(RECORDINGS_DIR / output_file)

    try:
        cl = _get_obs_client()

        # Ensure correct scene (center monitor where Revit runs)
        cl.set_current_program_scene(OBS_SCENE)
        time.sleep(0.5)

        # Set recording folder to our recordings directory
        rec_dir = r"D:\_CLAUDE-TOOLS\video-pipeline\recordings"
        try:
            cl.set_record_directory(rec_dir)
        except Exception:
            # Fallback: set via profile parameter (OBS <31.2 doesn't have SetRecordDirectory)
            cl.set_profile_parameter("SimpleOutput", "FilePath", rec_dir)

        # Start recording
        cl.start_record()
        time.sleep(1)

        # Verify recording started
        status = cl.get_record_status()
        if status.output_active:
            print(f"  OBS recording started (scene: {OBS_SCENE})")
        else:
            print(f"  WARNING: OBS recording may not have started")

        print(f"  Output dir: {rec_dir}")
        cl.disconnect()

    except Exception as e:
        print(f"  ERROR starting OBS recording: {e}")
        print(f"  Falling back to FFmpeg gdigrab...")
        return _start_recording_ffmpeg(monitor_info)

    return {
        "method": "obs",
        "output_file": output_file,
        "output_path_wsl": output_path_wsl,
        "start_time": timestamp,
    }


def stop_recording(rec_info):
    """Stop recording (OBS or FFmpeg)."""
    method = rec_info.get("method", "ffmpeg")

    if method == "obs":
        _stop_recording_obs(rec_info)
    else:
        _stop_recording_ffmpeg(rec_info)


def _stop_recording_obs(rec_info):
    """Stop OBS recording and locate the output file."""
    try:
        cl = _get_obs_client()

        # Get the output path before stopping
        status = cl.get_record_status()
        if not status.output_active:
            print("  OBS was not recording")
            cl.disconnect()
            return

        result = cl.stop_record()
        obs_output = getattr(result, "output_path", "")
        print(f"  OBS recording stopped")
        cl.disconnect()

        # Wait for OBS to finalize the file
        time.sleep(3)

        # OBS returns the Windows path (e.g. D:/_CLAUDE-TOOLS/...)
        # Convert to WSL path
        if obs_output:
            wsl_path = obs_output.replace("D:/", "/mnt/d/").replace("D:\\", "/mnt/d/").replace("\\", "/")
            rec_info["output_path_wsl"] = wsl_path
            print(f"  Output: {wsl_path}")

            if Path(wsl_path).exists():
                size_mb = Path(wsl_path).stat().st_size / (1024 * 1024)
                print(f"  Size: {size_mb:.1f} MB")
            else:
                print(f"  WARNING: File not found at {wsl_path}")
                # Fallback: find newest mp4
                rec_dir = Path("/mnt/d/_CLAUDE-TOOLS/video-pipeline/recordings")
                mp4s = sorted(rec_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
                if mp4s:
                    rec_info["output_path_wsl"] = str(mp4s[0])
                    print(f"  Found: {mp4s[0].name}")
        else:
            print("  WARNING: OBS did not return output path, searching...")
            rec_dir = Path("/mnt/d/_CLAUDE-TOOLS/video-pipeline/recordings")
            mp4s = sorted(rec_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if mp4s:
                rec_info["output_path_wsl"] = str(mp4s[0])
                print(f"  Found: {mp4s[0].name}")

    except Exception as e:
        print(f"  Error stopping OBS recording: {e}")


def _start_recording_ffmpeg(monitor_info):
    """Fallback: Start FFmpeg gdigrab recording."""
    if not monitor_info:
        monitor_info = {"index": 1, "x": -2560, "y": 0, "width": 2560, "height": 1440}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"demo_recording_{timestamp}.mp4"
    output_path_wsl = str(RECORDINGS_DIR / output_file)
    output_path_win = f"D:\\_CLAUDE-TOOLS\\video-pipeline\\recordings\\{output_file}"

    x = monitor_info["x"]
    y = monitor_info["y"]
    w = monitor_info["width"]
    h = monitor_info["height"]

    ps_cmd = (
        f"$p = Start-Process -FilePath '{FFMPEG_WIN}' "
        f"-ArgumentList '-f gdigrab -framerate 15 -offset_x {x} -offset_y {y} "
        f"-video_size {w}x{h} -i desktop "
        f"-c:v libx264 -crf 20 -preset ultrafast -pix_fmt yuv420p "
        f"-y \"{output_path_win}\"' "
        f"-PassThru -WindowStyle Hidden; "
        f"$p.Id"
    )

    result = _run_ps(ps_cmd, timeout=30)

    pid = None
    if result.returncode == 0 and result.stdout.strip():
        try:
            pid = int(result.stdout.strip().split('\n')[-1])
        except ValueError:
            pass

    if pid:
        print(f"  FFmpeg recording started (PID: {pid})")
    else:
        print(f"  WARNING: Could not get FFmpeg PID")

    return {
        "method": "ffmpeg",
        "pid": pid,
        "output_file": output_file,
        "output_path_win": output_path_win,
        "output_path_wsl": output_path_wsl,
    }


def _stop_recording_ffmpeg(rec_info):
    """Fallback: Stop FFmpeg recording."""
    pid = rec_info.get("pid")
    if not pid:
        _run_ps("Stop-Process -Name ffmpeg -Force -ErrorAction SilentlyContinue", timeout=10)
        time.sleep(3)
        return

    try:
        _run_ps(f"taskkill /PID {pid}", timeout=10)
        print(f"  Sent graceful stop to PID {pid}")
        time.sleep(8)

        check = _run_ps(
            f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id",
            timeout=5
        )
        if check.stdout.strip():
            _run_ps(f"Stop-Process -Id {pid} -Force", timeout=10)
            time.sleep(3)
        else:
            print(f"  Recording stopped and finalized")
    except Exception as e:
        print(f"  Error stopping recording: {e}")
        _run_ps("Stop-Process -Name ffmpeg -Force -ErrorAction SilentlyContinue", timeout=10)
    time.sleep(3)


def run_demo():
    """Run the demo script with real pauses."""
    print("\n  Running demo script (real speed)...")
    result = subprocess.run(
        [sys.executable, str(DEMO_SCRIPT), "--verbose"],
        capture_output=False,
        timeout=1800  # 30 minute max
    )
    return result.returncode == 0


def parse_narration_timestamps():
    """Parse narration_script.txt to get timestamp → audio file mapping."""
    entries = []
    with open(NARRATION_SCRIPT) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line or not line.startswith("["):
                continue
            # Parse [M:SS] text
            bracket_end = line.index("]")
            time_str = line[1:bracket_end]
            parts = time_str.split(":")
            seconds = int(parts[0]) * 60 + int(parts[1])
            text = line[bracket_end+2:]

            audio_file = AUDIO_DIR / f"narration_script_line_{i:04d}.mp3"
            if audio_file.exists():
                entries.append({
                    "timestamp": seconds,
                    "text": text,
                    "audio_file": str(audio_file),
                })
    return entries


def create_title_card():
    """Create a title card image using FFmpeg."""
    title_path = RECORDINGS_DIR / "title_card.png"

    # Use FFmpeg to generate a title card with text
    ffmpeg_cmd = [
        FFMPEG_NATIVE,
        "-f", "lavfi",
        "-i", f"color=c=0x1a1a2e:s=2560x1440:d=1",
        "-vf", (
            "drawtext=text='AI Builds a Real Building in Revit'"
            ":fontsize=72:fontcolor=white:x=(w-text_w)/2:y=h/3"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            "drawtext=text='1700 West Sheffield Road - Avon Park, FL'"
            ":fontsize=42:fontcolor=0xcccccc:x=(w-text_w)/2:y=h/3+100"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            "drawtext=text='BIM Ops Studio'"
            ":fontsize=48:fontcolor=0x00b4d8:x=(w-text_w)/2:y=2*h/3"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ),
        "-frames:v", "1",
        "-y",
        str(title_path)
    ]

    subprocess.run(ffmpeg_cmd, capture_output=True, timeout=30)
    print(f"  Title card: {title_path}")
    return str(title_path)


def create_end_card():
    """Create an end card."""
    end_path = RECORDINGS_DIR / "end_card.png"

    ffmpeg_cmd = [
        FFMPEG_NATIVE,
        "-f", "lavfi",
        "-i", "color=c=0x1a1a2e:s=2560x1440:d=1",
        "-vf", (
            "drawtext=text='BIM Ops Studio'"
            ":fontsize=72:fontcolor=0x00b4d8:x=(w-text_w)/2:y=h/3"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            "drawtext=text='AI-Powered Revit Automation'"
            ":fontsize=42:fontcolor=white:x=(w-text_w)/2:y=h/3+100"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            "drawtext=text='Subscribe & Follow on LinkedIn'"
            ":fontsize=36:fontcolor=0xcccccc:x=(w-text_w)/2:y=2*h/3"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        "-frames:v", "1",
        "-y",
        str(end_path)
    ]

    subprocess.run(ffmpeg_cmd, capture_output=True, timeout=30)
    print(f"  End card: {end_path}")
    return str(end_path)


def post_production(raw_video_path):
    """Assemble final video with title card, narration, and end card."""
    print("\n" + "="*60)
    print("POST-PRODUCTION")
    print("="*60)

    final_output = RECORDINGS_DIR / "AI_Builds_Real_Building_Revit_FINAL.mp4"
    title_card = create_title_card()
    end_card = create_end_card()

    # Step 1: Create title card video (5 seconds)
    title_video = str(RECORDINGS_DIR / "title_card_video.mp4")
    subprocess.run([
        FFMPEG_NATIVE,
        "-loop", "1", "-i", title_card,
        "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p",
        "-vf", "fps=30", "-y", title_video
    ], capture_output=True, timeout=30)
    print("  Title card video created (5s)")

    # Step 2: Create end card video (8 seconds)
    end_video = str(RECORDINGS_DIR / "end_card_video.mp4")
    subprocess.run([
        FFMPEG_NATIVE,
        "-loop", "1", "-i", end_card,
        "-c:v", "libx264", "-t", "8", "-pix_fmt", "yuv420p",
        "-vf", "fps=30", "-y", end_video
    ], capture_output=True, timeout=30)
    print("  End card video created (8s)")

    # Step 3: Build narration audio track
    narration_entries = parse_narration_timestamps()
    narration_track = str(RECORDINGS_DIR / "narration_combined.mp3")

    if narration_entries:
        # Get the duration of the raw video using ffprobe (fast, no decoding)
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", raw_video_path
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15)
        total_duration = 200  # default
        if probe.returncode == 0 and probe.stdout.strip():
            try:
                total_duration = float(probe.stdout.strip())
            except ValueError:
                pass
        print(f"  Raw video duration: {total_duration:.1f}s")

        # Build filter_complex for mixing narration clips at correct timestamps
        # Offset by 5s for title card
        inputs = []
        filter_parts = []
        for i, entry in enumerate(narration_entries):
            inputs.extend(["-i", entry["audio_file"]])
            delay_ms = (entry["timestamp"] + 5) * 1000  # +5 for title card
            filter_parts.append(f"[{i}]adelay={delay_ms}|{delay_ms}[a{i}]")

        mix_inputs = "".join(f"[a{i}]" for i in range(len(narration_entries)))
        filter_parts.append(f"{mix_inputs}amix=inputs={len(narration_entries)}:duration=longest[aout]")

        filter_str = ";".join(filter_parts)

        narration_cmd = [FFMPEG_NATIVE] + inputs + [
            "-filter_complex", filter_str,
            "-map", "[aout]",
            "-ac", "2", "-ar", "44100",
            "-y", narration_track
        ]

        result = subprocess.run(narration_cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            print(f"  Narration track created ({len(narration_entries)} clips)")
        else:
            print(f"  Warning: Narration mix failed, continuing without narration")
            narration_track = None
    else:
        narration_track = None

    # Step 4: Concatenate title + raw video + end card
    concat_list = str(RECORDINGS_DIR / "concat_list.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{title_video}'\n")
        f.write(f"file '{raw_video_path}'\n")
        f.write(f"file '{end_video}'\n")

    concat_video = str(RECORDINGS_DIR / "concat_no_audio.mp4")
    subprocess.run([
        FFMPEG_NATIVE,
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-y", concat_video
    ], capture_output=True, timeout=600)
    print("  Videos concatenated (title + demo + end)")

    # Step 5: Add narration audio to the concatenated video
    if narration_track and Path(narration_track).exists():
        subprocess.run([
            FFMPEG_NATIVE,
            "-i", concat_video,
            "-i", narration_track,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-y", str(final_output)
        ], capture_output=True, timeout=600)
        print(f"  Final video with narration: {final_output}")
    else:
        # Just rename the concat video
        import shutil
        shutil.copy2(concat_video, str(final_output))
        print(f"  Final video (no narration): {final_output}")

    # Verify
    if final_output.exists():
        size_mb = final_output.stat().st_size / (1024 * 1024)
        print(f"  Final video size: {size_mb:.1f} MB")
        return str(final_output)
    else:
        print("  ERROR: Final video not created!")
        return None


def create_thumbnail():
    """Create a YouTube thumbnail."""
    thumb_path = RECORDINGS_DIR / "thumbnail.png"

    ffmpeg_cmd = [
        FFMPEG_NATIVE,
        "-f", "lavfi",
        "-i", "color=c=0x0f0f23:s=1280x720:d=1",
        "-vf", (
            "drawtext=text='AI Built This House'"
            ":fontsize=64:fontcolor=white:x=(w-text_w)/2:y=h/4"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            "drawtext=text='in 3 Minutes'"
            ":fontsize=56:fontcolor=0x00b4d8:x=(w-text_w)/2:y=h/4+80"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            "drawtext=text='Zero Human Interaction'"
            ":fontsize=36:fontcolor=0xff6b6b:x=(w-text_w)/2:y=2*h/3"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            "drawtext=text='BIM Ops Studio'"
            ":fontsize=28:fontcolor=0x888888:x=(w-text_w)/2:y=2*h/3+60"
            ":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        "-frames:v", "1",
        "-y",
        str(thumb_path)
    ]

    subprocess.run(ffmpeg_cmd, capture_output=True, timeout=30)
    print(f"  Thumbnail: {thumb_path}")
    return str(thumb_path)


def upload_to_youtube(video_path, thumbnail_path):
    """Upload to YouTube."""
    print("\n" + "="*60)
    print("YOUTUBE UPLOAD")
    print("="*60)

    title = "AI Builds a Real House in Revit - Zero Human Interaction | BIM Ops Studio"
    description = """Watch as Claude AI autonomously controls Autodesk Revit 2026 to recreate a real single-family residence from scratch.

This is 1700 West Sheffield Road in Avon Park, Florida - a 3-bedroom, 2-bath home with a 2-car garage. Every wall, door, window, and room was extracted from the original Revit project and recreated programmatically through the Revit API.

No mouse clicks. No manual drafting. Just AI talking directly to the Revit API.

What's different in Take 2:
- Correct 8" CMU exterior wall type (not Generic)
- Each door uses its exact family type (garage, sliding, pocket, bifold, flush panel)
- 14 windows placed on exterior walls with correct sill heights
- Wall corners joined for clean intersections
- Project's own ARKY titleblock (not Autodesk default)
- Room and door tags added

CHAPTERS:
0:00 - Title Card
0:05 - Introduction
0:17 - The Challenge
0:29 - Phase 1: Blank Canvas
0:40 - Phase 2: CMU Exterior Walls
1:15 - Walls Appearing in Real Time
1:35 - Phase 3: Interior Partitions
2:05 - Room Layout Taking Shape
2:35 - Phase 4: Wall Joining
2:55 - Phase 5: Door Placement (Exact Types)
3:25 - Doors Snapping to Host Walls
3:55 - Phase 6: Windows
4:20 - Phase 7: Room Assignment
4:35 - Room Names & Numbers
5:00 - Phase 8: Tagging
5:15 - Phase 9: Views & Sheet
5:40 - Phase 10: The 3D Reveal
5:55 - About BIM Ops Studio

Built with:
- Autodesk Revit 2026.2
- RevitMCPBridge (custom Revit API bridge)
- Claude AI (Anthropic)
- Python automation

BIM Ops Studio - AI-Powered BIM Automation
LinkedIn: https://www.linkedin.com/company/bim-ops-studio
GitHub: https://github.com/bimopsstudio

#Revit #BIM #AI #Automation #Architecture #MCP #RevitAPI #ClaudeAI #BIMOpsStudio #Windows #Doors
"""

    tags = [
        "Revit", "BIM", "AI", "automation", "Revit API", "MCP",
        "Claude AI", "BIM Ops Studio", "architecture", "construction",
        "Autodesk", "RevitMCPBridge", "autonomous", "floor plan",
        "residential", "single family", "Avon Park"
    ]

    cmd = [
        sys.executable, str(UPLOADER),
        video_path,
        "--title", title,
        "--description", description,
        "--tags"] + tags + [
        "--privacy", "unlisted",
        "--category", "28",
    ]
    if thumbnail_path and Path(thumbnail_path).exists():
        cmd.extend(["--thumbnail", thumbnail_path])

    print(f"  Uploading: {Path(video_path).name}")
    print(f"  Title: {title[:60]}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode == 0:
        print(f"  Upload successful!")
        print(f"  Output: {result.stdout}")
        return True
    else:
        print(f"  Upload failed: {result.stderr[:500]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Record and produce Revit demo video")
    parser.add_argument("--skip-record", action="store_true", help="Skip recording, use existing raw video")
    parser.add_argument("--skip-upload", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--raw-video", type=str, help="Path to existing raw video (with --skip-record)")
    args = parser.parse_args()

    print("\n" + "#"*60)
    print("# REVIT DEMO VIDEO - FULL PIPELINE")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60)

    raw_video_path = None

    # ===== STEP 1: RECORD =====
    if not args.skip_record:
        print("\n" + "="*60)
        print("STEP 1: RECORDING")
        print("="*60)

        print(f"  Using OBS Studio (scene: {OBS_SCENE}) for recording")

        # Start recording
        rec_info = start_recording()
        raw_video_path = rec_info["output_path_wsl"]

        # Wait for FFmpeg to initialize
        time.sleep(3)

        # Run the demo
        print("\n  === DEMO STARTING ===")
        demo_success = run_demo()
        print(f"  === DEMO {'COMPLETE' if demo_success else 'FAILED'} ===")

        # Wait a moment for dramatic effect
        time.sleep(5)

        # Stop recording
        stop_recording(rec_info)

        # OBS may update the output path — use the latest from rec_info
        raw_video_path = rec_info.get("output_path_wsl", raw_video_path)

        if not Path(raw_video_path).exists():
            # Fallback: find newest mp4 in recordings dir
            mp4s = sorted(RECORDINGS_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if mp4s:
                raw_video_path = str(mp4s[0])
                print(f"  Found recording: {raw_video_path}")
            else:
                print("  ERROR: Recording file not found!")
                sys.exit(1)

        size_mb = Path(raw_video_path).stat().st_size / (1024 * 1024)
        print(f"  Raw recording: {raw_video_path} ({size_mb:.1f} MB)")
    else:
        raw_video_path = args.raw_video
        if not raw_video_path:
            # Find most recent recording
            recs = sorted(RECORDINGS_DIR.glob("demo_recording_*.mp4"))
            if recs:
                raw_video_path = str(recs[-1])
            else:
                print("ERROR: No raw video found. Run without --skip-record")
                sys.exit(1)
        print(f"  Using existing recording: {raw_video_path}")

    # ===== STEP 2: POST-PRODUCTION =====
    final_video = post_production(raw_video_path)
    if not final_video:
        print("ERROR: Post-production failed")
        sys.exit(1)

    # ===== STEP 3: THUMBNAIL =====
    print("\n" + "="*60)
    print("THUMBNAIL")
    print("="*60)
    thumbnail = create_thumbnail()

    # ===== STEP 4: UPLOAD =====
    if not args.skip_upload:
        upload_to_youtube(final_video, thumbnail)
    else:
        print("\n  Skipping upload (--skip-upload)")

    print("\n" + "#"*60)
    print("# PIPELINE COMPLETE")
    print("#"*60)
    print(f"  Raw video: {raw_video_path}")
    print(f"  Final video: {final_video}")
    print(f"  Thumbnail: {thumbnail}")


if __name__ == "__main__":
    main()
