#!/usr/bin/env python3
"""
assemble_pro.py — Hybrid Video Assembly: Pillow Animations + Runway Transitions

Uses Pillow terminal/dashboard animations as primary content.
Runway clips used only as brief 0.5s visual transition cuts (Video 01 only).
Branded intro/outro wrapping.

Usage:
  python3 assemble_pro.py                    # Assemble Video 01
  python3 assemble_pro.py --video 2          # Assemble specific video
  python3 assemble_pro.py --all              # Assemble all 6 videos
"""

import subprocess
import sys
from pathlib import Path

# Reuse branded renderers from assemble_runway.py
from assemble_runway import (
    render_intro, render_outro, get_duration,
    W, H, FPS, INTRO_DURATION, OUTRO_DURATION, BASE,
)

# ── CONFIG ────────────────────────────────────────────────────────────────────

CUT_DURATION = 0.5          # seconds per Runway transition cut
MIN_RENDER_SIZE_MB = 5      # Pillow render must exceed this to be considered valid
RENDER_TIMEOUT = 600        # max seconds for render_video.py

# ── VIDEO DEFINITIONS ────────────────────────────────────────────────────────

VIDEOS = {
    1: {
        "dir": "video_01_retry_ladder",
        "title": "Retry Ladder",
        "runway_cuts": [
            # (cut_point_seconds, clip_filename)
            (5.0,  "clip_00.mp4"),   # hook → intro boundary
            (7.0,  "clip_01.mp4"),   # intro → quickfix
            (12.0, "clip_02.mp4"),   # quickfix → refactor
            (17.0, "clip_03.mp4"),   # refactor → alternative
            (33.0, "clip_04.mp4"),   # result → memory
        ],
    },
    2: {"dir": "video_02_architecture", "title": "Architecture",  "runway_cuts": []},
    3: {"dir": "video_03_checkpoint",   "title": "Checkpoints",   "runway_cuts": []},
    4: {"dir": "video_04_swarm",        "title": "Swarm Engine",  "runway_cuts": []},
    5: {"dir": "video_05_validator",    "title": "Validator",      "runway_cuts": []},
    6: {"dir": "video_06_full_system",  "title": "Full System",   "runway_cuts": []},
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def run(cmd, desc=""):
    """Run FFmpeg command, print errors, return success bool."""
    if desc:
        print(f"    {desc}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    ERROR: {r.stderr[-400:]}")
        return False
    return True


def ensure_pillow_render(vdir):
    """Run render_video.py if output doesn't exist or is a stub (<5 MB)."""
    landscape = vdir / "final_landscape.mp4"
    render_script = vdir / "render_video.py"

    if landscape.exists():
        size_mb = landscape.stat().st_size / 1024 / 1024
        if size_mb >= MIN_RENDER_SIZE_MB:
            print(f"    Already rendered ({size_mb:.1f} MB), skipping.")
            return landscape
        else:
            print(f"    Stub render ({size_mb:.1f} MB), re-rendering...")

    if not render_script.exists():
        print(f"    ERROR: No render_video.py in {vdir.name}")
        return None

    print(f"    Running render_video.py (this takes 1-3 min)...")
    try:
        r = subprocess.run(
            [sys.executable, str(render_script)],
            cwd=str(vdir),
            capture_output=True, text=True,
            timeout=RENDER_TIMEOUT,
        )
        # Print render output for progress visibility
        if r.stdout:
            for line in r.stdout.strip().split("\n")[-5:]:
                print(f"      {line}")
        if r.returncode != 0:
            print(f"    Render failed: {r.stderr[-300:]}")
            return None
    except subprocess.TimeoutExpired:
        print(f"    Render timed out after {RENDER_TIMEOUT}s")
        return None

    if landscape.exists():
        size_mb = landscape.stat().st_size / 1024 / 1024
        print(f"    Rendered: {size_mb:.1f} MB")
        return landscape

    print("    ERROR: render_video.py produced no output")
    return None


# ── RUNWAY CUT INSERTION ─────────────────────────────────────────────────────

def insert_runway_cuts(pillow_silent, runway_cuts, clip_dir, work):
    """
    Replace 0.5s at each cut point with a Runway clip.
    Total duration stays the same — these are replacements, not insertions.
    Returns path to content video with cuts spliced in.
    """
    if not runway_cuts:
        return pillow_silent

    pillow_dur = get_duration(pillow_silent)
    cuts = sorted(runway_cuts, key=lambda c: c[0])

    segments = []
    seg_idx = 0
    prev_end = 0.0

    for cut_time, clip_file in cuts:
        clip_path = clip_dir / clip_file
        if not clip_path.exists():
            print(f"    SKIP cut at {cut_time:.1f}s: {clip_file} not found")
            continue

        # Pillow segment before this cut
        if cut_time > prev_end:
            seg_path = work / f"pseg_{seg_idx:02d}.mp4"
            ok = run([
                "ffmpeg", "-y",
                "-ss", f"{prev_end:.3f}",
                "-t", f"{cut_time - prev_end:.3f}",
                "-i", str(pillow_silent),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-an",
                str(seg_path),
            ], f"Pillow [{prev_end:.1f}s – {cut_time:.1f}s]")
            if ok and seg_path.exists():
                segments.append(seg_path)
                seg_idx += 1

        # Runway transition clip (0.5s, scaled to 1920x1080)
        runway_seg = work / f"rseg_{seg_idx:02d}.mp4"
        ok = run([
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-t", f"{CUT_DURATION:.3f}",
            "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(runway_seg),
        ], f"Runway cut @ {cut_time:.1f}s → {clip_file}")
        if ok and runway_seg.exists():
            segments.append(runway_seg)
            seg_idx += 1

        prev_end = cut_time + CUT_DURATION

    # Final Pillow segment (after last cut to end)
    if prev_end < pillow_dur:
        seg_path = work / f"pseg_{seg_idx:02d}.mp4"
        ok = run([
            "ffmpeg", "-y",
            "-ss", f"{prev_end:.3f}",
            "-i", str(pillow_silent),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(seg_path),
        ], f"Pillow [{prev_end:.1f}s – end]")
        if ok and seg_path.exists():
            segments.append(seg_path)

    if not segments:
        return pillow_silent

    # Concat all segments
    concat_file = work / "cuts_concat.txt"
    with open(concat_file, "w") as f:
        for p in segments:
            f.write(f"file '{p}'\n")

    content = work / "content.mp4"
    ok = run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(content),
    ], "Concatenating Pillow + Runway segments...")

    if ok and content.exists():
        return content
    return pillow_silent


# ── MAIN ASSEMBLY ────────────────────────────────────────────────────────────

def assemble_video(video_num, video_config):
    """Full hybrid assembly pipeline for one video."""
    vdir = BASE / video_config["dir"]
    work = vdir / "_work_pro"
    work.mkdir(exist_ok=True)
    clip_dir = vdir / "runway_clips"
    audio_dir = vdir / "audio"

    has_cuts = bool(video_config.get("runway_cuts"))
    mode = "HYBRID (Pillow + Runway)" if has_cuts else "PILLOW ONLY"

    print(f"\n{'=' * 60}")
    print(f"  Video {video_num:02d}: {video_config['title']}  [{mode}]")
    print(f"{'=' * 60}")

    # ── 1. Ensure Pillow render exists ──
    print("\n[1/6] Pillow render...")
    pillow_video = ensure_pillow_render(vdir)
    if not pillow_video:
        print("  ABORT: No Pillow render available.")
        return False

    pillow_dur = get_duration(pillow_video)
    print(f"    Duration: {pillow_dur:.1f}s")

    # ── 2. Strip audio from Pillow video ──
    print("\n[2/6] Strip audio...")
    pillow_silent = work / "pillow_silent.mp4"
    if not run([
        "ffmpeg", "-y",
        "-i", str(pillow_video),
        "-c:v", "copy", "-an",
        str(pillow_silent),
    ], "Extracting silent video track..."):
        return False

    # ── 3. Insert Runway transition cuts ──
    runway_cuts = video_config.get("runway_cuts", [])
    if runway_cuts:
        print(f"\n[3/6] Inserting {len(runway_cuts)} Runway cuts...")
        content = insert_runway_cuts(pillow_silent, runway_cuts, clip_dir, work)
    else:
        print("\n[3/6] No Runway cuts — using Pillow directly.")
        content = pillow_silent

    content_dur = get_duration(content)
    print(f"    Content: {content_dur:.1f}s")

    # ── 4. Wrap with intro/outro ──
    print("\n[4/6] Intro/outro...")
    intro_path = work / "intro.mp4"
    outro_path = work / "outro.mp4"

    if not render_intro(intro_path):
        return False
    if not render_outro(outro_path):
        return False

    concat_file = work / "final_concat.txt"
    with open(concat_file, "w") as f:
        f.write(f"file '{intro_path}'\n")
        f.write(f"file '{content}'\n")
        f.write(f"file '{outro_path}'\n")

    video_only = work / "video_assembled.mp4"
    if not run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(video_only),
    ], "Intro + content + outro..."):
        return False

    total_video_dur = get_duration(video_only)
    print(f"    Assembled: {total_video_dur:.1f}s")

    # ── 5. Build audio and merge ──
    print("\n[5/6] Audio + merge...")
    narration = audio_dir / "full_narration.mp3"
    if not narration.exists():
        print(f"    ERROR: {narration} not found")
        return False

    # Audio: [intro silence] + [narration] + [outro silence]
    combined_audio = work / "combined_audio.aac"
    if not run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-t", str(INTRO_DURATION),
        "-i", "anullsrc=r=44100:cl=stereo",
        "-i", str(narration),
        "-f", "lavfi", "-t", str(OUTRO_DURATION),
        "-i", "anullsrc=r=44100:cl=stereo",
        "-filter_complex",
        "[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a0];"
        "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a1];"
        "[2:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a2];"
        "[a0][a1][a2]concat=n=3:v=0:a=1[outa]",
        "-map", "[outa]",
        "-c:a", "aac", "-b:a", "192k",
        str(combined_audio),
    ], "Building audio: silence + narration + silence..."):
        return False

    # Merge video + audio
    output_landscape = vdir / "hybrid_landscape.mp4"
    if not run([
        "ffmpeg", "-y",
        "-i", str(video_only),
        "-i", str(combined_audio),
        "-c:v", "copy", "-c:a", "copy",
        "-shortest",
        str(output_landscape),
    ], "Merging video + audio..."):
        return False

    if not output_landscape.exists():
        print("    ERROR: No output produced")
        return False

    mb = output_landscape.stat().st_size / 1024 / 1024
    dur = get_duration(output_landscape)
    print(f"    Landscape: {output_landscape.name} ({mb:.1f} MB, {dur:.1f}s)")

    # ── 6. Vertical crop ──
    print("\n[6/6] Vertical (9:16)...")
    output_vertical = vdir / "hybrid_vertical.mp4"
    run([
        "ffmpeg", "-y", "-i", str(output_landscape),
        "-vf", "crop=608:1080:656:0,scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy",
        str(output_vertical),
    ], "Center-crop to 1080x1920...")

    if output_vertical.exists():
        mb_v = output_vertical.stat().st_size / 1024 / 1024
        print(f"    Vertical: {output_vertical.name} ({mb_v:.1f} MB)")

    print(f"\n{'=' * 60}")
    print(f"  DONE: Video {video_num:02d} — {video_config['title']}")
    print(f"  {output_landscape}")
    if output_vertical.exists():
        print(f"  {output_vertical}")
    print(f"{'=' * 60}")
    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    video_num = 1

    if "--video" in sys.argv:
        i = sys.argv.index("--video")
        video_num = int(sys.argv[i + 1])

    if "--all" in sys.argv:
        results = {}
        for num in sorted(VIDEOS):
            ok = assemble_video(num, VIDEOS[num])
            results[num] = "OK" if ok else "FAIL"
        print(f"\n{'=' * 60}")
        print("  SUMMARY")
        print(f"{'=' * 60}")
        for num, status in results.items():
            v = VIDEOS[num]
            print(f"  Video {num:02d} ({v['title']:15s}): {status}")
        print(f"{'=' * 60}")
    elif video_num in VIDEOS:
        assemble_video(video_num, VIDEOS[video_num])
    else:
        print(f"Video {video_num} not configured. Available: {sorted(VIDEOS.keys())}")


if __name__ == "__main__":
    main()
