#!/usr/bin/env python3
"""
assemble_illustrated.py — Illustrated Scene Video Pipeline

Generates DALL-E 3 scene illustrations, animates them with Sora 2
image-to-video, adds captions and branded intro/outro, merges with
ElevenLabs narration audio.

Usage:
  python3 assemble_illustrated.py                # Generate + assemble Video 01
  python3 assemble_illustrated.py --video 2      # Specific video
  python3 assemble_illustrated.py --skip-gen     # Skip image generation (use cached)
  python3 assemble_illustrated.py --all          # All videos
"""

import os
import subprocess
import sys
import time
import io
import requests
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# Load .env
load_dotenv(Path(__file__).parent / ".env")

# Reuse branded renderers
from assemble_runway import (
    render_intro, render_outro, get_duration,
    W, H, FPS, INTRO_DURATION, OUTRO_DURATION, BASE,
    FONT_BOLD, FONT_REGULAR, CYAN, WHITE, DIM, BG,
    _font, _draw_grid_dots, _scale_color, _render_frames_to_video,
)

# ── CONFIG ────────────────────────────────────────────────────────────────────

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

# Visual style prefix for DALL-E 3 scene generation
STYLE_PREFIX = (
    "Dark futuristic tech environment, professional digital illustration, "
    "cinematic composition, volumetric lighting, neon cyan and blue accents, "
    "depth of field, moody atmosphere, 16:9 aspect ratio, "
    "no text no words no letters no watermarks"
)

SORA_MODEL = "sora-2"
SORA_CLIP_SECONDS = 8   # Sora supports 4, 8, or 12
SORA_SIZE = "1280x720"


# ── VIDEO DEFINITIONS ────────────────────────────────────────────────────────
# Each segment: (key, audio_file, scene_prompt, motion_prompt, caption_lines)
# scene_prompt  → DALL-E 3 (still image)
# motion_prompt → Sora 2 (animate the still)

VIDEO_01 = {
    "dir": "video_01_retry_ladder",
    "title": "Retry Ladder",
    "segments": [
        ("hook", "01_hook.mp3",
         "A lone AI agent standing before a massive wall of cascading red holographic error messages in a dark futuristic command center, the agent glowing with determination, red warning lights reflecting off dark metallic surfaces",
         "Subtle cinematic motion: holographic error messages flicker and scroll down the wall, volumetric light rays shift slowly, ambient particles drift through the air, the AI agent pulses with soft glowing energy. Slow camera push-in.",
         ["When my AI agent fails,", "it doesn't just retry."]),

        ("intro", "02_intro.mp3",
         "A glowing ladder made of pure cyan light materializing in dark space, each rung representing a different strategy level, the ladder ascending through layers of holographic code, dramatic upward perspective",
         "A glowing cyan stairway of light materializes step by step in a dark tech environment, holographic particles float gently, soft volumetric lighting, smooth upward camera tilt.",
         ["It runs a strategy ladder."]),

        ("quickfix", "03_quickfix.mp3",
         "A precision robotic arm performing delicate micro-surgery on a glowing circuit board, tiny sparks of cyan light, surgical tools hovering, a small targeted repair on a massive system, dark background with blue rim lighting",
         "The robotic arm performs precise micro-repairs, tiny sparks fly with each touch, circuit pathways light up as connections are restored, subtle camera orbit around the repair site.",
         ["Quick Fix — minimal change.", "Two shots at it."]),

        ("refactor", "04_refactor.mp3",
         "Holographic blueprints of code architecture being deconstructed and rebuilt in mid-air, floating code blocks rearranging themselves into a better structure, purple and blue energy connections forming new patterns, wide cinematic shot",
         "Code blocks float apart and reassemble into new patterns, purple and blue energy connections dissolve and reform, the architecture transforms smoothly, holographic blueprints rotate.",
         ["That fails?", "Read more context. Refactor."]),

        ("alternative", "05_alternative.mp3",
         "A dramatic crossroads in a dark digital landscape with multiple glowing pathways branching in different directions, one path blazing bright green while others fade, a bold new direction being chosen, particles streaming along the bright path",
         "Camera tracks along the bright green pathway as it blazes forward, other paths dim and fade, particles stream rapidly along the chosen route, dramatic lighting shift from red to green.",
         ["Still failing?", "Completely different strategy."]),

        ("escalate", "06_escalate.mp3",
         "An AI agent generating a detailed holographic failure report, data visualizations and diagnostic panels floating around it, amber and orange warning displays, a thorough analysis being compiled for human review",
         "Holographic data panels appear one by one in a dark futuristic space, information populating across floating screens, soft amber and orange glow, gentle camera orbit.",
         ["Nothing works?", "Detailed failure report."]),

        ("result", "07_result.mp3",
         "Four glowing vertical bars of increasing height arranged left to right in a dark futuristic environment, each bar a different color (cyan, blue, purple, green), the tallest rightmost bar blazing bright green with a pulsing halo of success, abstract holographic energy connections between the bars, dramatic volumetric lighting, purely abstract visualization with absolutely no text no words no letters no numbers no labels no watermarks",
         "The four bars illuminate one by one from left to right, each pulsing with energy as it activates, the final green bar blazes brightest with a spreading halo, energy arcs flow between bars, subtle camera pull-back.",
         ["4 strategies. 5 max attempts.", "15 minute timeout."]),

        ("memory", "08_memory.mp3",
         "Glowing data streams spiraling into a vast crystalline memory vault, knowledge being permanently stored as luminous orbs in a dark neural archive, the vault stretching into infinity, cyan and gold light",
         "Glowing data orbs spiral smoothly into the crystalline vault, each orb finding its place on the shelves, the archive extends deeper into infinity, cyan and gold light pulses rhythmically.",
         ["Logs every attempt.", "Skips to what worked next time."]),

        ("cta", "09_cta.mp3",
         "The CADRE-AI system fully operational, a beautiful holographic hub with five interconnected subsystems all pulsing with activity, viewed from above like a constellation, dark space with cyan glow, epic wide shot",
         "All five subsystems pulse with synchronized activity, data flows between them in smooth arcs of light, the constellation slowly rotates, epic scale revealed with slow camera pull-back.",
         ["CADRE-AI", "Link in bio."]),
    ],
}

VIDEOS = {1: VIDEO_01}


# ── IMAGE GENERATION ─────────────────────────────────────────────────────────

def generate_scene_image(prompt, output_path):
    """Generate a scene illustration via DALL-E 3."""
    if output_path.exists() and output_path.stat().st_size > 50000:
        print(f"    Cached: {output_path.name}")
        return True

    client = OpenAI(api_key=OPENAI_KEY)
    full_prompt = f"{prompt}. {STYLE_PREFIX}"

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1792x1024",
            quality="hd",
            n=1,
        )
        url = response.data[0].url

        img_data = requests.get(url, timeout=30).content
        with open(output_path, "wb") as f:
            f.write(img_data)

        print(f"    Generated: {output_path.name} ({len(img_data) // 1024} KB)")
        return True

    except Exception as e:
        print(f"    ERROR generating {output_path.name}: {e}")
        return False


# ── SORA 2 ANIMATION ────────────────────────────────────────────────────────

def animate_scene_sora(img_path, motion_prompt, output_path):
    """Animate a still image using Sora 2 image-to-video."""
    if output_path.exists() and output_path.stat().st_size > 100000:
        print(f"    Cached: {output_path.name}")
        return True

    client = OpenAI(api_key=OPENAI_KEY)

    # Resize to match Sora output size
    sora_w, sora_h = [int(x) for x in SORA_SIZE.split("x")]
    img = Image.open(img_path).convert("RGB").resize((sora_w, sora_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    try:
        video = client.videos.create(
            model=SORA_MODEL,
            prompt=motion_prompt,
            input_reference=(img_path.name, buf, "image/png"),
            seconds=SORA_CLIP_SECONDS,
            size=SORA_SIZE,
        )
        print(f"    Submitted: {output_path.stem} -> {video.id}")

        # Poll for completion
        while video.status in ("queued", "in_progress"):
            time.sleep(10)
            video = client.videos.retrieve(video.id)

        if video.status == "completed":
            content = client.videos.download_content(video.id)
            with open(output_path, "wb") as f:
                for chunk in content.iter_bytes():
                    f.write(chunk)
            print(f"    Animated: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
            return True
        else:
            print(f"    FAILED: {output_path.stem} - {video.status}")
            if hasattr(video, "error"):
                print(f"      {video.error}")
            return False

    except Exception as e:
        print(f"    ERROR animating {output_path.stem}: {e}")
        return False


def trim_and_scale_clip(clip_path, duration, output_path):
    """Trim Sora clip to exact duration and scale to 1920x1080 for assembly."""
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(clip_path),
        "-t", f"{duration:.3f}",
        "-vf", f"scale={W}:{H}:flags=lanczos",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(output_path),
    ], capture_output=True, text=True)
    return r.returncode == 0 and output_path.exists()


CAPTION_DELAY = 0.3  # seconds before first caption line appears

def burn_caption_overlay(video_path, caption_lines, output_path, seg_duration=None):
    """Burn caption text + watermark onto video using FFmpeg drawtext.
    Caption lines are staggered across the segment to match speech pace."""
    filters = []

    # Watermark top-right (always visible)
    wm_filter = (
        f"drawtext=text='CADRE-AI':fontsize=20:fontcolor=0x00FFD0@0.3"
        f":x=w-tw-30:y=20:fontfile='{FONT_BOLD}'"
    )
    filters.append(wm_filter)

    # Caption lines centered near bottom — staggered to match speech
    active = [l for l in caption_lines if l.strip()]
    if active:
        line_h = 48
        total_h = line_h * len(active)
        base_y = H - 110 - total_h

        # Stagger lines: distribute evenly across segment duration
        # Line 1 at CAPTION_DELAY, line 2 at ~halfway, etc.
        dur = seg_duration or 4.0
        if len(active) == 1:
            line_delays = [CAPTION_DELAY]
        else:
            # Spread lines across the speaking time
            # Leave buffer at start and don't use the very end
            usable = dur - CAPTION_DELAY - 0.5  # 0.5s buffer at end
            spacing = usable / len(active)
            line_delays = [CAPTION_DELAY + i * spacing for i in range(len(active))]

        for i, line in enumerate(active):
            # FFmpeg drawtext escaping: replace ' with right-quote (avoids
            # filter-string leak when subprocess passes -vf without shell),
            # escape colons and backslashes for the drawtext parser.
            escaped = (
                line.replace("\\", "\\\\")
                    .replace("'", "\u2019")   # ' → Unicode right single quote
                    .replace(":", "\\:")
                    .replace('"', '\\"')
            )
            y = base_y + i * line_h
            delay = line_delays[i]
            txt_filter = (
                f"drawtext=text='{escaped}':fontsize=38"
                f":fontcolor=white:x=(w-tw)/2:y={y}:fontfile='{FONT_BOLD}'"
                f":shadowcolor=black:shadowx=3:shadowy=3"
                f":enable='gte(t\\,{delay:.2f})'"
            )
            filters.append(txt_filter)

    vf = ",".join(filters)
    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(output_path),
    ], capture_output=True, text=True)

    if r.returncode != 0:
        print(f"    Caption burn error: {r.stderr[-300:]}")
        return False
    return True


def burn_caption_overlay_vertical(video_path, segments, seg_durations, output_path,
                                   vw, vh, intro_dur=2.0):
    """Burn all segment captions onto a vertical (post-crop) video in one pass.

    Calculates absolute timestamps from intro_dur + cumulative segment durations
    so each caption appears at the right moment in the final timeline.
    """
    filters = []

    # Watermark top-right (always visible)
    wm_filter = (
        f"drawtext=text='CADRE-AI':fontsize=24:fontcolor=0x00FFD0@0.3"
        f":x=w-tw-20:y=16:fontfile='{FONT_BOLD}'"
    )
    filters.append(wm_filter)

    # Walk segments, accumulate time offset
    t_offset = intro_dur
    for seg_i, (key, audio_file, scene_prompt, motion_prompt, captions) in enumerate(segments):
        dur = seg_durations[seg_i]
        active = [l for l in captions if l.strip()]
        if active:
            line_h = 56  # larger for vertical (1080px wide)
            total_h = line_h * len(active)
            base_y = vh - 180 - total_h  # more room from bottom on vertical

            if len(active) == 1:
                line_delays = [CAPTION_DELAY]
            else:
                usable = dur - CAPTION_DELAY - 0.5
                spacing = usable / len(active)
                line_delays = [CAPTION_DELAY + j * spacing for j in range(len(active))]

            for j, line in enumerate(active):
                escaped = (
                    line.replace("\\", "\\\\")
                        .replace("'", "\u2019")
                        .replace(":", "\\:")
                        .replace('"', '\\"')
                )
                y = base_y + j * line_h
                abs_start = t_offset + line_delays[j]
                abs_end = t_offset + dur
                txt_filter = (
                    f"drawtext=text='{escaped}':fontsize=44"
                    f":fontcolor=white:x=(w-tw)/2:y={y}:fontfile='{FONT_BOLD}'"
                    f":shadowcolor=black:shadowx=3:shadowy=3"
                    f":enable='between(t\\,{abs_start:.2f}\\,{abs_end:.2f})'"
                )
                filters.append(txt_filter)

        t_offset += dur

    vf = ",".join(filters)
    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        str(output_path),
    ], capture_output=True, text=True)

    if r.returncode != 0:
        print(f"    Vertical caption burn error: {r.stderr[-300:]}")
        return False
    return True


# ── MAIN ASSEMBLY ────────────────────────────────────────────────────────────

def assemble_video(video_num, video_config, skip_gen=False):
    """Full illustrated-scene assembly pipeline using Sora 2 animation."""
    vdir = BASE / video_config["dir"]
    work = vdir / "_work_illustrated"
    scenes_dir = vdir / "scenes"
    audio_dir = vdir / "audio"
    work.mkdir(exist_ok=True)
    scenes_dir.mkdir(exist_ok=True)

    segments = video_config["segments"]
    title = video_config["title"]

    print(f"\n{'=' * 60}")
    print(f"  ILLUSTRATED: Video {video_num:02d} — {title}")
    print(f"{'=' * 60}")

    # ── 1. Generate scene images (DALL-E 3) ──
    print(f"\n[1/7] Generating {len(segments)} scene illustrations...")
    scene_images = []
    for key, audio_file, scene_prompt, motion_prompt, captions in segments:
        img_path = scenes_dir / f"{key}.png"
        if not skip_gen:
            ok = generate_scene_image(scene_prompt, img_path)
            if not ok:
                print(f"    FATAL: Could not generate {key}")
                return False
            time.sleep(0.5)
        else:
            if not img_path.exists():
                print(f"    MISSING: {img_path.name} (run without --skip-gen)")
                return False
            print(f"    Cached: {img_path.name}")
        scene_images.append(img_path)

    # ── 2. Animate scenes (Sora 2) ──
    print(f"\n[2/7] Animating scenes with Sora 2...")
    animated_clips = []
    for i, (key, audio_file, scene_prompt, motion_prompt, captions) in enumerate(segments):
        clip_path = scenes_dir / f"{key}_animated.mp4"
        if not skip_gen:
            ok = animate_scene_sora(scene_images[i], motion_prompt, clip_path)
            if not ok:
                print(f"    WARNING: {key} animation failed, will use still image fallback")
                clip_path = None
        else:
            if not clip_path.exists():
                print(f"    MISSING: {clip_path.name}")
                clip_path = None
            else:
                print(f"    Cached: {clip_path.name}")
        animated_clips.append(clip_path)

    # ── 3. Get audio durations ──
    print(f"\n[3/7] Measuring audio segments...")
    seg_durations = []
    for key, audio_file, scene_prompt, motion_prompt, captions in segments:
        audio_path = audio_dir / audio_file
        dur = get_duration(audio_path) if audio_path.exists() else 3.0
        seg_durations.append(dur)
        print(f"    {key:12s} {dur:.1f}s")

    # ── 4. Trim clips to audio duration ──
    # We keep uncaptioned trimmed segments for vertical (captions burned after crop)
    # and burn landscape captions separately for the landscape output.
    print(f"\n[4/7] Trimming + captioning segments...")
    segment_paths_captioned = []   # landscape: captions burned at 1920x1080
    segment_paths_trimmed = []     # uncaptioned: used for vertical pipeline
    for i, (key, audio_file, scene_prompt, motion_prompt, captions) in enumerate(segments):
        dur = seg_durations[i]
        trimmed = work / f"trimmed_{i:02d}_{key}.mp4"
        captioned = work / f"seg_{i:02d}_{key}.mp4"

        if animated_clips[i]:
            # Trim Sora clip to exact audio duration + scale to 1920x1080
            ok = trim_and_scale_clip(animated_clips[i], dur, trimmed)
        else:
            # Fallback: still image with FFmpeg zoompan
            ok = subprocess.run([
                "ffmpeg", "-y", "-loop", "1",
                "-i", str(scene_images[i]),
                "-t", f"{dur:.3f}",
                "-vf", f"scale={W}:{H}:flags=lanczos,zoompan=z='1+0.001*in':d={int(dur*FPS)}:s={W}x{H}:fps={FPS}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-an",
                str(trimmed),
            ], capture_output=True, text=True).returncode == 0

        if not ok or not trimmed.exists():
            print(f"    {key:12s} TRIM FAIL")
            continue

        segment_paths_trimmed.append(trimmed)

        # Burn captions for landscape (pass duration so lines are staggered)
        ok = burn_caption_overlay(trimmed, captions, captioned, seg_duration=dur)
        if ok and captioned.exists():
            segment_paths_captioned.append(captioned)
            print(f"    {key:12s} {dur:.1f}s  OK")
        else:
            segment_paths_captioned.append(trimmed)
            print(f"    {key:12s} {dur:.1f}s  (no captions)")

    if not segment_paths_captioned:
        print("  No segments. Aborting.")
        return False

    # ── 5. Assemble with intro/outro ──
    print(f"\n[5/7] Assembling with intro/outro...")

    intro_path = work / "intro.mp4"
    outro_path = work / "outro.mp4"
    render_intro(intro_path)
    render_outro(outro_path)

    # Landscape assembly (captioned segments)
    concat_file = work / "concat.txt"
    with open(concat_file, "w") as f:
        f.write(f"file '{intro_path}'\n")
        for p in segment_paths_captioned:
            f.write(f"file '{p}'\n")
        f.write(f"file '{outro_path}'\n")

    video_only = work / "video_assembled.mp4"
    r = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(video_only),
    ], capture_output=True, text=True)

    if r.returncode != 0:
        print(f"    Concat error: {r.stderr[-300:]}")
        return False

    total_dur = get_duration(video_only)
    print(f"    Video assembled: {total_dur:.1f}s")

    # Uncaptioned assembly (for vertical — captions burned after crop)
    concat_nocap = work / "concat_nocap.txt"
    with open(concat_nocap, "w") as f:
        f.write(f"file '{intro_path}'\n")
        for p in segment_paths_trimmed:
            f.write(f"file '{p}'\n")
        f.write(f"file '{outro_path}'\n")

    video_nocap = work / "video_assembled_nocap.mp4"
    r = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_nocap),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(video_nocap),
    ], capture_output=True, text=True)

    if r.returncode != 0:
        print(f"    Uncaptioned concat error: {r.stderr[-300:]}")
        return False

    # ── 6. Build audio and merge ──
    print(f"\n[6/7] Audio + merge...")
    narration = audio_dir / "full_narration.mp3"
    if not narration.exists():
        print(f"    ERROR: {narration} not found")
        return False

    # Audio: [intro silence] + [narration] + [outro silence]
    combined_audio = work / "combined_audio.aac"
    r = subprocess.run([
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
    ], capture_output=True, text=True)

    if r.returncode != 0:
        print(f"    Audio error: {r.stderr[-300:]}")
        return False

    output_landscape = vdir / "illustrated_landscape.mp4"
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_only),
        "-i", str(combined_audio),
        "-c:v", "copy", "-c:a", "copy",
        "-shortest",
        str(output_landscape),
    ], capture_output=True, text=True)

    if not output_landscape.exists():
        print(f"    Merge error: {r.stderr[-300:]}")
        return False

    mb = output_landscape.stat().st_size / 1024 / 1024
    dur = get_duration(output_landscape)
    print(f"    Landscape: {output_landscape.name} ({mb:.1f} MB, {dur:.1f}s)")

    # ── 7. Vertical crop + captions at vertical resolution ──
    # Crop uncaptioned video first, then burn captions at 1080px width so
    # text isn't clipped by the center crop.
    print(f"\n[7/7] Vertical (9:16)...")

    # 7a. Merge uncaptioned video with audio
    vert_nocap_merged = work / "vert_nocap_merged.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_nocap),
        "-i", str(combined_audio),
        "-c:v", "copy", "-c:a", "copy", "-shortest",
        str(vert_nocap_merged),
    ], capture_output=True)

    # 7b. Crop center 608px from 1920 wide → scale to 1080x1920
    vert_cropped = work / "vert_cropped.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(vert_nocap_merged),
        "-vf", "crop=608:1080:656:0,scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        str(vert_cropped),
    ], capture_output=True)

    # 7c. Burn captions onto vertical at 1080px width
    output_vertical = vdir / "illustrated_vertical.mp4"
    vert_w, vert_h = 1080, 1920
    ok = burn_caption_overlay_vertical(
        vert_cropped, segments, seg_durations,
        output_vertical, vert_w, vert_h,
        intro_dur=INTRO_DURATION,
    )

    if output_vertical.exists():
        mb_v = output_vertical.stat().st_size / 1024 / 1024
        print(f"    Vertical: {output_vertical.name} ({mb_v:.1f} MB)")

    print(f"\n{'=' * 60}")
    print(f"  DONE: Video {video_num:02d} — {title}")
    print(f"  {output_landscape}")
    if output_vertical.exists():
        print(f"  {output_vertical}")
    print(f"{'=' * 60}")
    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    if not OPENAI_KEY:
        print("ERROR: OPENAI_API_KEY not set. Add it to shorts/.env")
        sys.exit(1)

    video_num = 1
    skip_gen = "--skip-gen" in sys.argv

    if "--video" in sys.argv:
        i = sys.argv.index("--video")
        video_num = int(sys.argv[i + 1])

    if "--all" in sys.argv:
        for num in sorted(VIDEOS):
            assemble_video(num, VIDEOS[num], skip_gen)
    elif video_num in VIDEOS:
        assemble_video(video_num, VIDEOS[video_num], skip_gen)
    else:
        print(f"Video {video_num} not configured. Available: {sorted(VIDEOS.keys())}")


if __name__ == "__main__":
    main()
