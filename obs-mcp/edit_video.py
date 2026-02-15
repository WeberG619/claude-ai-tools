#!/usr/bin/env python3
"""
Video editor for the AI Demo showcase — Take 6.
- Natural pace preserved (NO speed changes)
- Gaussian blur on Telegram contacts and old messages (live section)
- Gaussian blur on Telegram screenshot in PowerPoint slide
- Fade to black at end
"""
import subprocess
import os
import sys
import time

SRC = "/mnt/d/_CLAUDE-TOOLS/video-pipeline/recordings/2026-02-13 13-50-20.mp4"
OUT_DIR = "/mnt/d/_CLAUDE-TOOLS/video-pipeline/edited"
FINAL = f"{OUT_DIR}/AI_Assistant_Demo_Final.mp4"

os.makedirs(OUT_DIR, exist_ok=True)

# Video properties
DURATION = 795.0
FADE_DUR = 3.0
FADE_START = DURATION - FADE_DUR  # 792.0

# ============================================================
# BLUR REGION 1: Live Telegram — Left contacts panel
# Active during: 313s-348s (Telegram Desktop visible)
# Covers: Leslie HAGEN, Tony Monty, Botfather, User Info, Steeve Wolf, Telegram
# Keeps: "Weber Assistant" header + Search bar
# ============================================================
TG_START = 313
TG_END = 348
B1_X, B1_Y, B1_W, B1_H = 160, 250, 740, 1050

# ============================================================
# BLUR REGION 2: Live Telegram — Old chat messages
# Active during: 313s-348s
# Covers: Take 3, Take 4 (x2), Take 5 (1:39 PM), voice msg, Processing
# Keeps: Final "LIVE DEMO — Take 5" at 1:55 PM + chat header
# ============================================================
B2_X, B2_Y, B2_W, B2_H = 910, 130, 1000, 850

# ============================================================
# BLUR REGION 3: PowerPoint — Embedded Telegram screenshot
# Active during: 558s-633s (PPT slide 6 visible)
# Covers: Entire embedded screenshot (contacts + messages + profile)
# Keeps: Slide title "Live: Telegram Message Sent" + subtitle
# ============================================================
PPT_START = 558
PPT_END = 633
B3_X, B3_Y, B3_W, B3_H = 500, 350, 1520, 650

# Gaussian blur strength
SIGMA = 30

# ============================================================
# BUILD FILTER
# ============================================================
filter_complex = (
    # Split video into 4 streams for blur compositing
    "[0:v]split=4[base][crop1][crop2][crop3];"
    # Region 1: Crop left contacts and blur
    f"[crop1]crop={B1_W}:{B1_H}:{B1_X}:{B1_Y},gblur=sigma={SIGMA}[blur1];"
    # Region 2: Crop old messages and blur
    f"[crop2]crop={B2_W}:{B2_H}:{B2_X}:{B2_Y},gblur=sigma={SIGMA}[blur2];"
    # Region 3: Crop PPT Telegram screenshot and blur
    f"[crop3]crop={B3_W}:{B3_H}:{B3_X}:{B3_Y},gblur=sigma={SIGMA}[blur3];"
    # Overlay Region 1 (live Telegram contacts)
    f"[base][blur1]overlay={B1_X}:{B1_Y}:enable='between(t,{TG_START},{TG_END})'[tmp1];"
    # Overlay Region 2 (live Telegram messages)
    f"[tmp1][blur2]overlay={B2_X}:{B2_Y}:enable='between(t,{TG_START},{TG_END})'[tmp2];"
    # Overlay Region 3 (PPT Telegram screenshot)
    f"[tmp2][blur3]overlay={B3_X}:{B3_Y}:enable='between(t,{PPT_START},{PPT_END})'[tmp3];"
    # Fade to black at the end
    f"[tmp3]fade=t=out:st={FADE_START}:d={FADE_DUR}[vout];"
    # Audio fade to silence at the end
    f"[0:a]afade=t=out:st={FADE_START}:d={FADE_DUR}[aout]"
)

cmd = (
    f'ffmpeg -y -i "{SRC}" '
    f"-filter_complex \"{filter_complex}\" "
    f'-map "[vout]" -map "[aout]" '
    f'-c:v libx264 -preset veryfast -crf 23 '
    f'-c:a aac -b:a 128k '
    f'-pix_fmt yuv420p -movflags +faststart '
    f'"{FINAL}"'
)

# ============================================================
# RUN
# ============================================================
print("=" * 60)
print("VIDEO EDIT — AI ASSISTANT DEMO (Take 6) v2")
print("=" * 60)
print(f"Source:  {SRC}")
print(f"Output:  {FINAL}")
print(f"Blur 1:  Live Telegram contacts ({TG_START}s-{TG_END}s)")
print(f"Blur 2:  Live Telegram old messages ({TG_START}s-{TG_END}s)")
print(f"Blur 3:  PPT Telegram screenshot ({PPT_START}s-{PPT_END}s)")
print(f"Fade:    {FADE_DUR}s fade to black at end")
print(f"Pace:    Natural (no speed changes)")
print()
print("Encoding full video... this may take several minutes.")
print()

start_time = time.time()

r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)

elapsed = time.time() - start_time

if r.returncode != 0:
    print(f"ERROR (exit code {r.returncode}):")
    print(r.stderr[-1000:])
    sys.exit(1)

# Get final stats
r2 = subprocess.run(
    f'ffprobe -v error -show_entries format=duration,size -of csv=p=0 "{FINAL}"',
    shell=True, capture_output=True, text=True
)

if r2.stdout.strip():
    parts = r2.stdout.strip().split(',')
    dur = float(parts[0])
    size = int(parts[1]) / (1024 * 1024)
    print()
    print("=" * 60)
    print("EDIT COMPLETE")
    print(f"  Duration:  {int(dur//60)}m {int(dur%60)}s")
    print(f"  Size:      {size:.1f} MB")
    print(f"  Encode:    {int(elapsed//60)}m {int(elapsed%60)}s")
    print(f"  Output:    {FINAL}")
    print("=" * 60)
else:
    print("WARNING: Could not read final file stats")
    print(f"  Encode time: {int(elapsed//60)}m {int(elapsed%60)}s")
    print(f"  Output: {FINAL}")
