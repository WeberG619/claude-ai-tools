#!/usr/bin/env python3
"""
Generate a professional promotional video for Upwork Project Catalog listing:
"Custom Revit C# Plugin Development" by Weber Gouin / BIM Ops Studio.

Creates slideshow-style frames with Pillow, assembles with ffmpeg.
Output: 1920x1080 MP4, 30fps, ~40 seconds, H.264.
"""

import os
import sys
import math
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

# ── Configuration ──────────────────────────────────────────────────────────
W, H = 1920, 1080
FPS = 30
SLIDE_DURATION = 7          # seconds per slide
TRANSITION_FRAMES = 20      # cross-fade frames between slides
NUM_SLIDES = 6

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Palette
BG_TOP = (15, 15, 35)       # #0f0f23
BG_BOT = (26, 26, 62)       # #1a1a3e
ACCENT = (70, 130, 255)     # bright blue
WHITE = (255, 255, 255)
LIGHT = (200, 210, 230)
DIM = (140, 150, 170)
GREEN = (80, 220, 130)
GOLD = (255, 200, 60)
PILL_BG = (40, 45, 75)
DIVIDER = (50, 55, 90)

OUTPUT_PATH = "/mnt/d/_CLAUDE-TOOLS/revit-plugin-promo.mp4"


# ── Helpers ────────────────────────────────────────────────────────────────
def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def gradient_bg():
    """Create a vertical-gradient background image."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return img


def text_size(draw, text, fnt):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered(draw, y, text, fnt, fill=WHITE):
    tw, th = text_size(draw, text, fnt)
    draw.text(((W - tw) // 2, y), text, font=fnt, fill=fill)
    return th


def draw_pill(draw, cx, cy, text, fnt, fill_bg=PILL_BG, fill_text=WHITE):
    """Draw a rounded-rectangle pill centered at (cx, cy)."""
    tw, th = text_size(draw, text, fnt)
    pad_x, pad_y = 24, 12
    x0 = cx - tw // 2 - pad_x
    y0 = cy - th // 2 - pad_y
    x1 = cx + tw // 2 + pad_x
    y1 = cy + th // 2 + pad_y
    draw.rounded_rectangle([x0, y0, x1, y1], radius=22, fill=fill_bg, outline=ACCENT, width=2)
    draw.text((cx - tw // 2, cy - th // 2), text, font=fnt, fill=fill_text)
    return x1 - x0  # width of pill


def draw_horizontal_line(draw, y, color=DIVIDER, margin=300):
    draw.line([(margin, y), (W - margin, y)], fill=color, width=2)


def ease_in_out(t):
    """Smooth ease-in-out for 0..1."""
    return t * t * (3 - 2 * t)


# ── Slide Builders ─────────────────────────────────────────────────────────
# Each returns a list of (image, count) tuples where count = number of frames
# to hold that image.  For animated reveals we produce multiple sub-frames.

def slide_title():
    """Slide 1: Title."""
    frames = []
    total_frames = SLIDE_DURATION * FPS
    reveal_steps = 25  # frames for text to appear

    for step in range(reveal_steps):
        img = gradient_bg()
        draw = ImageDraw.Draw(img)
        alpha = ease_in_out(step / (reveal_steps - 1))

        # decorative top line
        line_w = int(400 * alpha)
        draw.line([(W // 2 - line_w, 230), (W // 2 + line_w, 230)], fill=ACCENT, width=3)

        # Title
        title_color = tuple(int(c * alpha) for c in WHITE)
        draw_centered(draw, 270, "Custom Revit Plugin", font(72, bold=True), fill=title_color)
        draw_centered(draw, 360, "Development", font(72, bold=True), fill=title_color)

        # Subtitle
        sub_alpha = max(0, (step - 8) / (reveal_steps - 9)) if step > 8 else 0
        sub_alpha = ease_in_out(min(1, sub_alpha))
        sub_color = tuple(int(c * sub_alpha) for c in ACCENT)
        draw_centered(draw, 470, "C# / .NET  |  Revit API  |  BIM Automation", font(36), fill=sub_color)

        # Author
        auth_alpha = max(0, (step - 14) / (reveal_steps - 15)) if step > 14 else 0
        auth_alpha = ease_in_out(min(1, auth_alpha))
        auth_color = tuple(int(c * auth_alpha) for c in DIM)
        draw_centered(draw, 700, "by Weber Gouin", font(30), fill=auth_color)

        # decorative bottom line
        draw.line([(W // 2 - line_w, 770), (W // 2 + line_w, 770)], fill=ACCENT, width=3)

        frames.append(img)

    # Hold the final frame
    hold = total_frames - reveal_steps
    if hold > 0:
        frames.extend([frames[-1]] * hold)
    return frames


def slide_services():
    """Slide 2: What I Build."""
    items = [
        "Custom Revit Add-ins",
        "Workflow Automation",
        "Family & Parameter Management",
        "AI Integration (LLM + Revit)",
        "Dynamo Scripts & Custom Nodes",
    ]
    frames = []
    total_frames = SLIDE_DURATION * FPS
    frames_per_item = 18

    for reveal in range(len(items) + 1):
        # Build frame showing `reveal` items
        img = gradient_bg()
        draw = ImageDraw.Draw(img)

        # Header
        draw_centered(draw, 120, "What I Build", font(56, bold=True), fill=ACCENT)
        draw_horizontal_line(draw, 200, margin=600)

        y = 260
        for i, item in enumerate(items):
            if i < reveal:
                alpha = 1.0
            elif i == reveal:
                alpha = 0.0  # will animate below
            else:
                break
            color = tuple(int(c * alpha) for c in WHITE)
            bullet_color = tuple(int(c * alpha) for c in GREEN)
            # bullet
            draw.text((500, y), ">", font=font(34, bold=True), fill=bullet_color)
            draw.text((550, y), item, font=font(34), fill=color)
            y += 75

        if reveal < len(items):
            # animate current item appearing
            sub_frames = []
            for s in range(frames_per_item):
                img2 = img.copy()
                draw2 = ImageDraw.Draw(img2)
                a = ease_in_out(s / (frames_per_item - 1))
                c = tuple(int(v * a) for v in WHITE)
                bc = tuple(int(v * a) for v in GREEN)
                draw2.text((500, y), ">", font=font(34, bold=True), fill=bc)
                draw2.text((550, y), items[reveal], font=font(34), fill=c)
                sub_frames.append(img2)
            frames.extend(sub_frames)
        else:
            # All items shown, hold
            remaining = total_frames - len(frames)
            if remaining > 0:
                frames.extend([img] * remaining)

    # Pad if needed
    while len(frames) < total_frames:
        frames.append(frames[-1])
    return frames[:total_frames]


def slide_tech():
    """Slide 3: Tech Stack."""
    tags = ["C#", ".NET", "Revit API", "WPF / XAML", "Python", "Dynamo", "Named Pipes", "Git"]
    frames = []
    total_frames = SLIDE_DURATION * FPS
    reveal_steps = 30

    for step in range(reveal_steps):
        img = gradient_bg()
        draw = ImageDraw.Draw(img)

        draw_centered(draw, 120, "Tech Stack", font(56, bold=True), fill=ACCENT)
        draw_horizontal_line(draw, 200, margin=600)

        fnt = font(30, bold=True)
        # Calculate pill layout (two rows)
        row1 = tags[:4]
        row2 = tags[4:]

        progress = ease_in_out(step / (reveal_steps - 1))
        visible_count = int(progress * len(tags) + 0.5)

        def draw_tag_row(tag_list, cy, start_idx):
            # Measure total width
            pill_spacing = 30
            widths = []
            for t in tag_list:
                tw, _ = text_size(draw, t, fnt)
                widths.append(tw + 48)  # pill padding
            total_w = sum(widths) + pill_spacing * (len(tag_list) - 1)
            x = (W - total_w) // 2

            for i, t in enumerate(tag_list):
                idx = start_idx + i
                if idx < visible_count:
                    cx = x + widths[i] // 2
                    draw_pill(draw, cx, cy, t, fnt)
                x += widths[i] + pill_spacing

        draw_tag_row(row1, 340, 0)
        draw_tag_row(row2, 440, 4)

        # Version line
        if progress > 0.7:
            va = ease_in_out(min(1, (progress - 0.7) / 0.3))
            vc = tuple(int(v * va) for v in GOLD)
            draw_centered(draw, 560, "Revit 2024  |  2025  |  2026", font(32, bold=True), fill=vc)

        frames.append(img)

    hold = total_frames - reveal_steps
    if hold > 0:
        frames.extend([frames[-1]] * hold)
    return frames[:total_frames]


def slide_pricing():
    """Slide 4: Service Tiers."""
    tiers = [
        ("Starter", "$300", "5 days", "Small tool or script"),
        ("Standard", "$750", "14 days", "Full add-in with UI"),
        ("Advanced", "$1,500", "30 days", "Complex multi-feature plugin"),
    ]
    frames = []
    total_frames = SLIDE_DURATION * FPS
    reveal_steps = 30
    col_w = 440
    start_x = (W - col_w * 3 - 60) // 2

    for step in range(reveal_steps):
        img = gradient_bg()
        draw = ImageDraw.Draw(img)

        draw_centered(draw, 100, "Service Tiers", font(56, bold=True), fill=ACCENT)
        draw_horizontal_line(draw, 180, margin=600)

        progress = ease_in_out(step / (reveal_steps - 1))
        visible_cols = progress * 3

        for i, (name, price, duration, desc) in enumerate(tiers):
            if i > visible_cols:
                break
            col_alpha = min(1.0, visible_cols - i)
            cx = start_x + i * (col_w + 30) + col_w // 2

            # Card background
            card_color = (int(35 * col_alpha), int(40 * col_alpha), int(70 * col_alpha))
            rx0 = cx - col_w // 2
            ry0 = 230
            rx1 = cx + col_w // 2
            ry1 = 780
            draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=18, fill=card_color,
                                   outline=tuple(int(c * col_alpha) for c in ACCENT), width=2)

            nc = tuple(int(c * col_alpha) for c in WHITE)
            pc = tuple(int(c * col_alpha) for c in GOLD)
            dc = tuple(int(c * col_alpha) for c in DIM)
            desc_c = tuple(int(c * col_alpha) for c in LIGHT)

            # Tier name
            tw, _ = text_size(draw, name, font(36, bold=True))
            draw.text((cx - tw // 2, 280), name, font=font(36, bold=True), fill=nc)

            # Divider
            draw.line([(rx0 + 40, 340), (rx1 - 40, 340)],
                      fill=tuple(int(c * col_alpha) for c in DIVIDER), width=2)

            # Price
            tw, _ = text_size(draw, price, font(52, bold=True))
            draw.text((cx - tw // 2, 380), price, font=font(52, bold=True), fill=pc)

            # Duration
            tw, _ = text_size(draw, duration, font(28))
            draw.text((cx - tw // 2, 460), duration, font=font(28), fill=dc)

            # Description
            tw, _ = text_size(draw, desc, font(24))
            draw.text((cx - tw // 2, 530), desc, font=font(24), fill=desc_c)

            # Highlight middle card
            if i == 1 and col_alpha > 0.8:
                badge_text = "POPULAR"
                btw, bth = text_size(draw, badge_text, font(18, bold=True))
                bx = cx - btw // 2 - 12
                by = ry0 - 16
                draw.rounded_rectangle([bx, by, bx + btw + 24, by + bth + 10], radius=10,
                                       fill=ACCENT)
                draw.text((bx + 12, by + 5), badge_text, font=font(18, bold=True), fill=WHITE)

        frames.append(img)

    hold = total_frames - reveal_steps
    if hold > 0:
        frames.extend([frames[-1]] * hold)
    return frames[:total_frames]


def slide_deliverables():
    """Slide 5: What You Get."""
    items = [
        "Complete source code (C# project)",
        "Compiled DLL / installer",
        "Technical documentation",
        "Multi-version support (2024-2026)",
        "Post-delivery support included",
    ]
    frames = []
    total_frames = SLIDE_DURATION * FPS
    frames_per_item = 16

    for reveal in range(len(items) + 1):
        img = gradient_bg()
        draw = ImageDraw.Draw(img)

        draw_centered(draw, 120, "What You Get", font(56, bold=True), fill=ACCENT)
        draw_horizontal_line(draw, 200, margin=600)

        y = 280
        for i in range(min(reveal, len(items))):
            draw.text((480, y), "\u2713", font=font(36, bold=True), fill=GREEN)
            draw.text((540, y), items[i], font=font(32), fill=WHITE)
            y += 80

        if reveal < len(items):
            sub_frames = []
            for s in range(frames_per_item):
                img2 = img.copy()
                draw2 = ImageDraw.Draw(img2)
                a = ease_in_out(s / (frames_per_item - 1))
                gc = tuple(int(v * a) for v in GREEN)
                tc = tuple(int(v * a) for v in WHITE)
                draw2.text((480, y), "\u2713", font=font(36, bold=True), fill=gc)
                draw2.text((540, y), items[reveal], font=font(32), fill=tc)
                sub_frames.append(img2)
            frames.extend(sub_frames)
        else:
            remaining = total_frames - len(frames)
            if remaining > 0:
                frames.extend([img] * remaining)

    while len(frames) < total_frames:
        frames.append(frames[-1])
    return frames[:total_frames]


def slide_cta():
    """Slide 6: Call to Action."""
    frames = []
    total_frames = SLIDE_DURATION * FPS
    reveal_steps = 30

    for step in range(reveal_steps):
        img = gradient_bg()
        draw = ImageDraw.Draw(img)
        p = ease_in_out(step / (reveal_steps - 1))

        # Decorative lines
        lw = int(350 * p)
        draw.line([(W // 2 - lw, 240), (W // 2 + lw, 240)], fill=ACCENT, width=3)
        draw.line([(W // 2 - lw, 750), (W // 2 + lw, 750)], fill=ACCENT, width=3)

        c1 = tuple(int(v * p) for v in WHITE)
        c2 = tuple(int(v * min(1, max(0, (p - 0.3) / 0.7))) for v in ACCENT)
        c3 = tuple(int(v * min(1, max(0, (p - 0.5) / 0.5))) for v in DIM)
        c4 = tuple(int(v * min(1, max(0, (p - 0.6) / 0.4))) for v in GOLD)

        draw_centered(draw, 300, "Ready to automate your", font(48, bold=True), fill=c1)
        draw_centered(draw, 370, "Revit workflow?", font(48, bold=True), fill=c1)

        # Button-style CTA
        if p > 0.3:
            btn_a = min(1, (p - 0.3) / 0.4)
            btn_text = "Let's discuss your project"
            btw, bth = text_size(draw, btn_text, font(34, bold=True))
            bx = (W - btw) // 2 - 40
            by = 480
            draw.rounded_rectangle([bx, by, bx + btw + 80, by + bth + 30], radius=16,
                                   fill=tuple(int(v * btn_a) for v in ACCENT),
                                   outline=tuple(int(v * btn_a) for v in WHITE), width=2)
            draw.text(((W - btw) // 2, by + 15), btn_text, font=font(34, bold=True),
                      fill=tuple(int(v * btn_a) for v in WHITE))

        draw_centered(draw, 620, "BIM Ops Studio", font(32, bold=True), fill=c4)
        draw_centered(draw, 670, "Weber Gouin", font(28), fill=c3)

        frames.append(img)

    hold = total_frames - reveal_steps
    if hold > 0:
        frames.extend([frames[-1]] * hold)
    return frames[:total_frames]


def crossfade(frames_a, frames_b, n):
    """Generate n cross-fade frames from last frame of A to first frame of B."""
    a = frames_a[-1]
    b = frames_b[0]
    result = []
    for i in range(n):
        t = i / (n - 1)
        blended = Image.blend(a, b, t)
        result.append(blended)
    return result


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    print("Generating slide frames...")

    slide_funcs = [slide_title, slide_services, slide_tech, slide_pricing,
                   slide_deliverables, slide_cta]
    all_slides = []
    for i, func in enumerate(slide_funcs):
        print(f"  Slide {i + 1}/{len(slide_funcs)}: {func.__doc__.strip()}")
        all_slides.append(func())

    # Assemble with cross-fades
    print("Assembling with cross-fade transitions...")
    final_frames = list(all_slides[0])
    for i in range(1, len(all_slides)):
        fade = crossfade(all_slides[i - 1], all_slides[i], TRANSITION_FRAMES)
        final_frames.extend(fade)
        final_frames.extend(all_slides[i])

    total_secs = len(final_frames) / FPS
    print(f"Total frames: {len(final_frames)} ({total_secs:.1f}s at {FPS}fps)")

    # Write frames to temp dir
    tmpdir = tempfile.mkdtemp(prefix="revit_promo_")
    print(f"Writing frames to {tmpdir} ...")
    for idx, frame in enumerate(final_frames):
        frame.save(os.path.join(tmpdir, f"frame_{idx:05d}.png"))
        if (idx + 1) % 200 == 0:
            print(f"  {idx + 1}/{len(final_frames)} frames written")

    print(f"  {len(final_frames)}/{len(final_frames)} frames written")

    # Encode with ffmpeg
    print("Encoding video with ffmpeg (H.264)...")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(tmpdir, "frame_%05d.png"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUTPUT_PATH,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg STDERR:", result.stderr[-2000:])
        sys.exit(1)

    # Verify output
    size_bytes = os.path.getsize(OUTPUT_PATH)
    size_mb = size_bytes / (1024 * 1024)
    print(f"\nVideo saved: {OUTPUT_PATH}")
    print(f"File size: {size_mb:.2f} MB")
    print(f"Duration: {total_secs:.1f}s")
    print(f"Resolution: {W}x{H} @ {FPS}fps")

    # Cleanup temp frames
    print("Cleaning up temporary frames...")
    shutil.rmtree(tmpdir)
    print("Done!")


if __name__ == "__main__":
    main()
