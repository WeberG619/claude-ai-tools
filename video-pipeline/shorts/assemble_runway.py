#!/usr/bin/env python3
"""
assemble_runway.py — Polished Video Assembly with Pillow Overlays + Runway Clips

Generates professional videos with:
- Branded intro/outro cards with fade transitions
- Styled caption boxes (2-line max, rounded semi-transparent background)
- Strategy labels with colored accent bars
- Subtle persistent watermark
- Per-segment clip trimming matched to audio duration

Usage:
  python3 assemble_runway.py                    # Assemble Video 01
  python3 assemble_runway.py --video 2          # Assemble specific video
  python3 assemble_runway.py --all              # Assemble all configured videos
"""

import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE = Path("/mnt/d/_CLAUDE-TOOLS/video-pipeline/shorts")
W, H = 1920, 1080
FPS = 30

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Brand colors
CYAN = (0, 220, 255)
WHITE = (255, 255, 255)
DIM = (140, 140, 160)
BG = (10, 10, 16)

STRATEGY_COLORS = {
    "QUICK FIX":   (0, 220, 255),
    "REFACTOR":    (80, 140, 255),
    "ALTERNATIVE": (200, 100, 255),
    "ESCALATE":    (255, 160, 40),
}

INTRO_DURATION = 2.0   # seconds
OUTRO_DURATION = 3.0   # seconds

# ── VIDEO DEFINITIONS ─────────────────────────────────────────────────────────
# Each segment: (key, audio_file, clip_index, [caption_lines], strategy_label)

VIDEO_01 = {
    "dir": "video_01_retry_ladder",
    "segments": [
        ("hook",        "01_hook.mp3",        0, ["When my AI agent fails,", "it doesn't just retry."],        None),
        ("intro",       "02_intro.mp3",       0, ["It runs a strategy ladder."],                               None),
        ("quickfix",    "03_quickfix.mp3",    1, ["Quick Fix \u2014 minimal change.", "Two shots at it."],            "STRATEGY 1 \u2014 QUICK FIX"),
        ("refactor",    "04_refactor.mp3",    1, ["That fails?", "Read more context. Refactor."],              "STRATEGY 2 \u2014 REFACTOR"),
        ("alternative", "05_alternative.mp3", 2, ["Still failing?", "Completely different strategy."],         "STRATEGY 3 \u2014 ALTERNATIVE"),
        ("escalate",    "06_escalate.mp3",    3, ["Nothing works?", "Detailed failure report."],               "STRATEGY 4 \u2014 ESCALATE"),
        ("result",      "07_result.mp3",      3, ["4 strategies. 5 max attempts.", "15 minute timeout."],      None),
        ("memory",      "08_memory.mp3",      4, ["Logs every attempt.", "Skips to what worked next time."],   None),
        ("cta",         "09_cta.mp3",         4, ["CADRE-AI", "Link in bio."],                                 None),
    ],
}

VIDEO_02 = {
    "dir": "video_02_architecture",
    "segments": [
        ("hook",       "01_hook.mp3",       0, ["Five systems. Zero dependencies.", "All running on one machine."],   None),
        ("board",      "02_board.mp3",      0, ["The task board tracks", "every operation across sessions."],         "TASK BOARD"),
        ("retry",      "03_retry.mp3",      0, ["Adaptive retry escalates", "strategies when something fails."],     "ADAPTIVE RETRY"),
        ("checkpoint", "04_checkpoint.mp3", 0, ["Checkpoints save agent state.", "Nothing is ever lost."],            "CHECKPOINTS"),
        ("validator",  "05_validator.mp3",  0, ["Output contracts validate", "every result before delivery."],        "VALIDATOR"),
        ("swarm",      "06_swarm.mp3",      0, ["The swarm engine fans out", "parallel workers for big tasks."],     "SWARM ENGINE"),
        ("cta",        "07_cta.mp3",        0, ["All open source.", "CADRE-AI \u2014 Link in bio."],                         None),
    ],
}

VIDEOS = {1: VIDEO_01, 2: VIDEO_02}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_duration(path):
    """Get media file duration in seconds via ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True)
        return float(r.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def _font(path, size):
    return ImageFont.truetype(path, size)


def _draw_grid_dots(draw, spacing=60, color=(22, 22, 32)):
    """Subtle dot grid for branded cards."""
    for x in range(0, W, spacing):
        for y in range(0, H, spacing):
            draw.ellipse([(x - 1, y - 1), (x + 1, y + 1)], fill=color)


def _scale_color(color, factor):
    """Scale RGB color brightness by factor (0.0-1.0)."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)


# ── OVERLAY GENERATION ────────────────────────────────────────────────────────

def make_overlay(caption_lines, strategy_label=None):
    """
    Generate a transparent 1920x1080 RGBA overlay with:
    - Caption box (bottom-center, rounded, 60% black bg)
    - Watermark (top-right, 25% opacity)
    - Strategy label (top-left, colored accent bar) — optional
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Watermark (top-right) ──
    wm_font = _font(FONT_BOLD, 20)
    wm_text = "CADRE-AI"
    wm_w = draw.textlength(wm_text, font=wm_font)
    draw.text((W - wm_w - 30, 20), wm_text, fill=(*CYAN, 64), font=wm_font)

    # ── Strategy Label (top-left) ──
    if strategy_label:
        parts = strategy_label.split(" \u2014 ")
        strategy_name = parts[-1] if len(parts) > 1 else strategy_label
        color = STRATEGY_COLORS.get(strategy_name, CYAN)

        lbl_font = _font(FONT_BOLD, 22)
        lbl_w = draw.textlength(strategy_label, font=lbl_font)

        # Pill background
        pill_right = 36 + lbl_w + 20
        draw.rounded_rectangle(
            [(20, 18), (pill_right, 58)],
            radius=10,
            fill=(0, 0, 0, 153),
        )
        # Color accent bar (left edge)
        draw.rectangle([(20, 18), (27, 58)], fill=(*color, 255))
        # Label text
        draw.text((36, 24), strategy_label, fill=(255, 255, 255, 230), font=lbl_font)

    # ── Caption Box (bottom-center) ──
    active_lines = [l for l in caption_lines if l.strip()]
    if not active_lines:
        return img

    cap_font = _font(FONT_BOLD, 36)

    # Measure lines
    widths, heights = [], []
    for line in active_lines:
        bbox = draw.textbbox((0, 0), line, font=cap_font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])

    max_w = max(widths)
    line_h = max(heights) if heights else 40
    line_gap = 8

    pad_x, pad_y = 28, 18
    box_w = min(max_w + pad_x * 2, int(W * 0.8))
    box_h = line_h * len(active_lines) + line_gap * (len(active_lines) - 1) + pad_y * 2
    box_x = (W - box_w) // 2
    box_y = H - 90 - box_h

    # Rounded background
    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=16,
        fill=(0, 0, 0, 153),
    )

    # Text lines (centered, white with black stroke)
    y = box_y + pad_y
    for i, line in enumerate(active_lines):
        tw = widths[i]
        tx = (W - tw) // 2
        # Black outline (8-direction)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2),
                       (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            draw.text((tx + dx, y + dy), line, fill=(0, 0, 0, 255), font=cap_font)
        # White fill
        draw.text((tx, y), line, fill=(255, 255, 255, 255), font=cap_font)
        y += line_h + line_gap

    return img


# ── INTRO / OUTRO RENDERING ──────────────────────────────────────────────────

def _render_frames_to_video(frame_fn, total_frames, output_path):
    """Pipe Pillow RGB frames to FFmpeg, producing a silent video."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24",
        "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(output_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    for i in range(total_frames):
        frame = frame_fn(i, total_frames)
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        err = proc.stderr.read().decode()[-300:]
        print(f"    Frame render error: {err}")
        return False
    return True


def render_intro(output_path):
    """2-second branded intro: dark bg, CADRE-AI title, subtitle, accent line."""
    total = int(INTRO_DURATION * FPS)
    title_font = _font(FONT_BOLD, 72)
    sub_font = _font(FONT_REGULAR, 28)

    def frame_fn(i, total_frames):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        _draw_grid_dots(draw)

        # Fade in over first 0.8s
        alpha = min(1.0, t / 0.8)

        # "CADRE-AI"
        title = "CADRE-AI"
        tw = draw.textlength(title, font=title_font)
        tx = (W - tw) / 2
        ty = H / 2 - 50
        draw.text((tx, ty), title, fill=_scale_color(CYAN, alpha), font=title_font)

        # Accent line
        line_w = int(320 * alpha)
        lx = (W - line_w) // 2
        ly = int(ty) + 78
        draw.rectangle([(lx, ly), (lx + line_w, ly + 3)],
                       fill=_scale_color(CYAN, alpha))

        # Subtitle
        sub = "Autonomous Agent System"
        sw = draw.textlength(sub, font=sub_font)
        sx = (W - sw) / 2
        sy = ly + 18
        draw.text((sx, sy), sub, fill=_scale_color(DIM, alpha), font=sub_font)

        return img

    ok = _render_frames_to_video(frame_fn, total, output_path)
    if ok:
        print(f"  Intro rendered: {output_path.name}")
    return ok


def render_outro(output_path):
    """3-second branded outro: CADRE-AI, GitHub URL, tagline, fade to black."""
    total = int(OUTRO_DURATION * FPS)
    title_font = _font(FONT_BOLD, 72)
    url_font = _font(FONT_REGULAR, 28)
    tag_font = _font(FONT_REGULAR, 22)

    def frame_fn(i, total_frames):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        _draw_grid_dots(draw)

        fade_in = min(1.0, t / 0.6)
        fade_out = max(0.0, min(1.0, (OUTRO_DURATION - t) / 0.8))
        b = fade_in * fade_out

        # "CADRE-AI"
        title = "CADRE-AI"
        tw = draw.textlength(title, font=title_font)
        tx = (W - tw) / 2
        ty = H / 2 - 70
        draw.text((tx, ty), title, fill=_scale_color(CYAN, b), font=title_font)

        # Accent line
        line_w = int(320 * b)
        lx = (W - line_w) // 2
        ly = int(ty) + 78
        draw.rectangle([(lx, ly), (lx + line_w, ly + 3)],
                       fill=_scale_color(CYAN, b))

        # URL
        url = "github.com/WeberG619"
        uw = draw.textlength(url, font=url_font)
        ux = (W - uw) / 2
        uy = ly + 22
        draw.text((ux, uy), url, fill=_scale_color(WHITE, b), font=url_font)

        # Tagline
        tag = "Open Source  |  Link in Bio"
        tgw = draw.textlength(tag, font=tag_font)
        tgx = (W - tgw) / 2
        tgy = uy + 48
        draw.text((tgx, tgy), tag, fill=_scale_color(DIM, b), font=tag_font)

        return img

    ok = _render_frames_to_video(frame_fn, total, output_path)
    if ok:
        print(f"  Outro rendered: {output_path.name}")
    return ok


# ── SEGMENT RENDERING ────────────────────────────────────────────────────────

def render_segment(clip_path, clip_offset, duration, overlay_img, output_path):
    """
    Trim Runway clip from clip_offset for duration seconds,
    scale to 1920x1080, composite the RGBA overlay, output silent video.
    """
    overlay_png = output_path.with_suffix(".overlay.png")
    overlay_img.save(str(overlay_png))

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{clip_offset:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(clip_path),
        "-i", str(overlay_png),
        "-filter_complex",
        f"[0:v]scale={W}:{H}:flags=lanczos,fps={FPS}[base];[base][1:v]overlay=0:0[outv]",
        "-map", "[outv]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    overlay_png.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"    ERROR rendering {output_path.name}: {result.stderr[-200:]}")
        return False
    return True


# ── MAIN ASSEMBLY ─────────────────────────────────────────────────────────────

def assemble_video(video_config):
    """Full assembly pipeline for one video."""
    vdir = BASE / video_config["dir"]
    clip_dir = vdir / "runway_clips"
    audio_dir = vdir / "audio"
    work = vdir / "_work"
    work.mkdir(exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"  ASSEMBLING: {video_config['dir']}")
    print(f"{'=' * 60}")

    # ── 1. Intro ──
    print("\n[1/6] Intro card...")
    intro_path = work / "intro.mp4"
    if not render_intro(intro_path):
        return

    # ── 2. Content segments ──
    print("\n[2/6] Content segments...")
    clip_offsets = {}   # clip_index → current time offset within that clip
    segment_paths = []

    for idx, (key, audio_file, clip_idx, captions, strategy) in enumerate(video_config["segments"]):
        clip_path = clip_dir / f"clip_{clip_idx:02d}.mp4"
        audio_path = audio_dir / audio_file

        if not clip_path.exists():
            print(f"    SKIP {key}: clip not found")
            continue
        if not audio_path.exists():
            print(f"    SKIP {key}: audio not found")
            continue

        dur = get_duration(audio_path)
        clip_len = get_duration(clip_path)
        offset = clip_offsets.get(clip_idx, 0.0)

        # Wrap offset if it would exceed clip length
        if clip_len > 0 and offset + dur > clip_len:
            offset = 0.0

        overlay = make_overlay(captions, strategy)
        seg_path = work / f"seg_{idx:02d}_{key}.mp4"
        print(f"    {key:12s}  clip_{clip_idx:02d} [{offset:5.1f}s\u2013{offset + dur:5.1f}s]  {dur:.1f}s"
              + (f"  \u2502 {strategy}" if strategy else ""))

        if render_segment(clip_path, offset, dur, overlay, seg_path):
            segment_paths.append(seg_path)

        clip_offsets[clip_idx] = offset + dur

    if not segment_paths:
        print("  No segments rendered. Aborting.")
        return

    # ── 3. Outro ──
    print("\n[3/6] Outro card...")
    outro_path = work / "outro.mp4"
    if not render_outro(outro_path):
        return

    # ── 4. Concat all video parts ──
    print("\n[4/6] Concatenating video...")
    all_parts = [intro_path] + segment_paths + [outro_path]
    concat_list = work / "concat.txt"
    with open(concat_list, "w") as f:
        for p in all_parts:
            f.write(f"file '{p}'\n")

    video_only = work / "video_only.mp4"
    # Re-encode concat for guaranteed compatibility
    r = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(video_only),
    ], capture_output=True, text=True)

    if r.returncode != 0:
        print(f"    Concat error: {r.stderr[-300:]}")
        return

    video_dur = get_duration(video_only)
    print(f"  Video assembled: {video_dur:.1f}s")

    # ── 5. Build audio track and merge ──
    print("\n[5/6] Building audio and merging...")

    # Collect all audio segment files
    seg_audio_files = []
    for key, audio_file, _, _, _ in video_config["segments"]:
        ap = audio_dir / audio_file
        if ap.exists():
            seg_audio_files.append(ap)

    # Build FFmpeg filter concat: silence + segments + silence
    # Use filter_complex concat to handle mixed formats reliably
    inputs = []
    filter_parts = []
    n = 0

    # Intro silence
    inputs.extend(["-f", "lavfi", "-t", str(INTRO_DURATION),
                   "-i", "anullsrc=r=44100:cl=stereo"])
    filter_parts.append(f"[{n}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{n}]")
    n += 1

    # Segment audio files
    for ap in seg_audio_files:
        inputs.extend(["-i", str(ap)])
        filter_parts.append(f"[{n}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{n}]")
        n += 1

    # Outro silence
    inputs.extend(["-f", "lavfi", "-t", str(OUTRO_DURATION),
                   "-i", "anullsrc=r=44100:cl=stereo"])
    filter_parts.append(f"[{n}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{n}]")
    n += 1

    # Concat all audio streams
    stream_labels = "".join(f"[a{i}]" for i in range(n))
    filter_parts.append(f"{stream_labels}concat=n={n}:v=0:a=1[outa]")
    filter_str = ";".join(filter_parts)

    combined_audio = work / "combined_audio.aac"
    subprocess.run([
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[outa]",
        "-c:a", "aac", "-b:a", "192k",
        str(combined_audio),
    ], capture_output=True)

    # Merge video + audio
    output_landscape = vdir / "final_landscape.mp4"
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_only),
        "-i", str(combined_audio),
        "-c:v", "copy", "-c:a", "copy",
        "-shortest",
        str(output_landscape),
    ], capture_output=True, text=True)

    if not output_landscape.exists():
        print(f"    Merge failed: {r.stderr[-300:]}")
        return

    mb = output_landscape.stat().st_size / 1024 / 1024
    dur = get_duration(output_landscape)
    print(f"  Landscape: {output_landscape} ({mb:.1f} MB, {dur:.1f}s)")

    # ── 6. Vertical crop ──
    print("\n[6/6] Creating vertical version...")
    output_vertical = vdir / "final_vertical.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(output_landscape),
        "-vf", "crop=608:1080:656:0,scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy",
        str(output_vertical),
    ], capture_output=True)

    if output_vertical.exists():
        mb = output_vertical.stat().st_size / 1024 / 1024
        print(f"  Vertical:  {output_vertical} ({mb:.1f} MB)")

    print(f"\n  Work dir:  {work}")
    print(f"\n{'=' * 60}")
    print(f"  DONE: {video_config['dir']}")
    print(f"{'=' * 60}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    video_num = 1

    if "--video" in sys.argv:
        i = sys.argv.index("--video")
        video_num = int(sys.argv[i + 1])

    if "--all" in sys.argv:
        for num in sorted(VIDEOS):
            assemble_video(VIDEOS[num])
    elif video_num in VIDEOS:
        assemble_video(VIDEOS[video_num])
    else:
        print(f"Video {video_num} not configured. Available: {sorted(VIDEOS.keys())}")


if __name__ == "__main__":
    main()
