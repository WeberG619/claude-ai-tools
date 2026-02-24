#!/usr/bin/env python3
"""
Render Video 03: Checkpointing — "My AI Saves Its Own Brain."
Timeline visualization with checkpoint markers and state snapshots.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gfx_engine import *
from PIL import ImageDraw

BASE = Path(__file__).parent
AUDIO = BASE / "audio" / "full_narration.mp3"
OUT_LANDSCAPE = BASE / "final_landscape.mp4"
OUT_VERTICAL = BASE / "final_vertical.mp4"
THUMBNAIL = BASE / "thumbnail.png"

DURATION = 40.0
TOTAL_FRAMES = int(DURATION * FPS)

CAPTIONS = [
    (0.0,  4.0, "My AI saves its own brain."),
    (4.0,  4.0, "Sessions crash. Context fills up."),
    (8.0,  5.0, "After every phase — checkpoint."),
    (13.0, 5.0, "Files modified. Decisions made."),
    (18.0, 5.0, "New session? Full state restored."),
    (23.0, 5.0, "Nothing is ever lost."),
    (28.0, 6.0, "Resume from any checkpoint, any time."),
    (34.0, 6.0, "cadre-ai — github.com/WeberG619"),
]

# Task phases for the timeline
PHASES = [
    ("Orient", 2.0, CYAN),
    ("Investigate", 5.0, BLUE),
    ("Plan", 9.0, YELLOW),
    ("Execute", 14.0, GREEN),
    ("Verify", 20.0, MAGENTA),
]

# Checkpoint data cards
CHECKPOINT_DATA = [
    ("files_modified", ["src/auth.py", "tests/test_auth.py", "config.json"]),
    ("decisions", ["JWT over sessions", "Redis for tokens"]),
    ("next_action", "Implement refresh endpoint"),
]


def get_caption(t):
    for start, dur, text in CAPTIONS:
        if start <= t < start + dur:
            return text
    return None


def render_frame_fn(frame_idx, t):
    img = new_frame()
    draw = ImageDraw.Draw(img)
    draw_grid(draw, spacing=50)

    # === TITLE (0-3s) ===
    if t < 3.0:
        fade = min(1.0, t / 0.5) * max(0.0, 1.0 - (t - 2.0))
        c = tuple(int(v * fade) for v in WHITE)
        draw_big_text(draw, "My AI Saves Its Own Brain", 80, color=c, size=48)

    # === TIMELINE BAR (appears at 2s) ===
    if t >= 2.0:
        bar_y = 300
        bar_x1, bar_x2 = 160, W - 160
        bar_w = bar_x2 - bar_x1
        fade = min(1.0, (t - 2.0) / 1.0)

        # Background bar
        c_bg = tuple(int(v * fade) for v in (30, 30, 50))
        draw.rounded_rectangle([(bar_x1, bar_y - 4), (bar_x2, bar_y + 4)],
                               radius=4, fill=c_bg)

        # Phase markers and checkpoints
        for i, (name, phase_t, color) in enumerate(PHASES):
            # Position on bar
            frac = i / (len(PHASES) - 1)
            px = bar_x1 + int(bar_w * frac)

            if t < phase_t:
                continue

            age = t - phase_t
            scale = ease_in_out(min(1.0, age / 0.6))

            # Progress fill up to this point
            fill_x = bar_x1 + int(bar_w * frac)
            draw.rounded_rectangle([(bar_x1, bar_y - 4), (fill_x, bar_y + 4)],
                                   radius=4, fill=color)

            # Checkpoint diamond
            size = int(14 * scale)
            points = [(px, bar_y - size), (px + size, bar_y),
                      (px, bar_y + size), (px - size, bar_y)]
            draw.polygon(points, fill=color)

            # Phase label
            f_label = font(14, bold=True)
            tw = draw.textlength(name, font=f_label)
            draw.text((px - tw / 2, bar_y - 35), name, fill=color, font=f_label)

            # Checkpoint saved indicator
            if age > 1.0:
                f_sm = font(11)
                draw.text((px - 15, bar_y + 20), "SAVED", fill=DIM, font=f_sm)

            # Pulse effect on newest checkpoint
            if age < 2.0:
                pulse = math.sin(age * math.pi * 3) * 0.5 + 0.5
                pr = int(20 + pulse * 10)
                gc = tuple(int(v * pulse * 0.3) for v in color)
                draw.ellipse([(px - pr, bar_y - pr), (px + pr, bar_y + pr)], fill=gc)

    # === SESSION CRASH ANIMATION (8-10s) ===
    if 8.0 <= t < 10.0:
        crash_t = (t - 8.0) / 2.0
        # Red flash
        if crash_t < 0.3:
            flash = int(40 * (1 - crash_t / 0.3))
            draw.rectangle([(0, 0), (W, H)], fill=(flash, 0, 0))

        # "SESSION LOST" text
        if 0.3 <= crash_t < 1.5:
            draw_big_text(draw, "SESSION CRASHED", 500, color=RED, size=40)

    # === CHECKPOINT STATE CARDS (13-28s) ===
    if t >= 13.0:
        card_fade = min(1.0, (t - 13.0) / 1.0)

        # State snapshot card
        card_x = 120
        card_y = 420
        card_w = 500
        card_h = 280

        if card_fade > 0:
            draw_card(draw, card_x, card_y, card_w, card_h,
                      title="Checkpoint State", color=GREEN,
                      icon="S", subtitle="Phase 3 of 5")

            y_off = card_y + 75
            for key, val in CHECKPOINT_DATA:
                if t < 14.0 + CHECKPOINT_DATA.index((key, val)) * 2:
                    break
                f_key = font(14, bold=True, mono=True)
                f_val = font(13, mono=True)
                draw.text((card_x + 20, y_off), f"{key}:", fill=CYAN, font=f_key)
                if isinstance(val, list):
                    for item in val[:2]:
                        y_off += 22
                        draw.text((card_x + 40, y_off), item, fill=DIM, font=f_val)
                else:
                    y_off += 22
                    draw.text((card_x + 40, y_off), str(val), fill=DIM, font=f_val)
                y_off += 28

        # Resume card (appears at 18s)
        if t >= 18.0:
            resume_fade = min(1.0, (t - 18.0) / 1.0)
            rx = W - 620
            draw_card(draw, rx, card_y, card_w, card_h,
                      title="Resume Prompt", color=CYAN,
                      icon="R", subtitle="Full context restored")

            if t >= 19.0:
                ry = card_y + 75
                resume_lines = [
                    ("Continue:", WHITE),
                    ("  Implement refresh endpoint", CYAN),
                    ("  Files: src/auth.py +2 more", DIM),
                    ("  Decision: JWT over sessions", DIM),
                    ("  Phase: Execute (3/5)", GREEN),
                ]
                for text, color in resume_lines:
                    if t < 19.0 + resume_lines.index((text, color)) * 0.8:
                        break
                    f_line = font(14, mono=True)
                    draw.text((rx + 20, ry), text, fill=color, font=f_line)
                    ry += 24

    # === PROGRESS RINGS (appear at 23s) ===
    if t >= 23.0:
        ring_t = t - 23.0
        ring_progress = ease_in_out(min(1.0, ring_t / 3.0))

        rings = [
            (W // 2 - 250, 750, ring_progress * 0.6, "Orient", CYAN),
            (W // 2 - 125, 750, ring_progress * 0.8, "Investigate", BLUE),
            (W // 2,       750, ring_progress * 1.0, "Plan", YELLOW),
            (W // 2 + 125, 750, ring_progress * 0.4, "Execute", GREEN),
            (W // 2 + 250, 750, ring_progress * 0.2, "Verify", MAGENTA),
        ]
        for cx, cy, prog, label, color in rings:
            draw_progress_ring(draw, cx, cy, 35, prog, color=color, width=5)
            f_sm = font(10)
            tw = draw.textlength(label, font=f_sm)
            draw.text((cx - tw / 2, cy + 42), label, fill=DIM, font=f_sm)

    # Caption bar
    caption = get_caption(t)
    if caption:
        draw_caption(draw, caption)

    return img


def generate_thumbnail():
    img = render_frame_fn(0, 24.0)
    draw = ImageDraw.Draw(img)
    draw_big_text(draw, "My AI Saves Its Own Brain", 30, color=GREEN, size=48)
    draw_subtitle(draw, "Checkpoint & Resume System", 90, color=DIM, size=24)
    img.save(str(THUMBNAIL), quality=95)
    print(f"  Thumbnail: {THUMBNAIL}")


def main():
    print("=" * 50)
    print("Rendering Video 03: Checkpointing")
    print("=" * 50)

    print("\nGenerating thumbnail...")
    generate_thumbnail()

    print(f"\nRendering {DURATION}s @ {FPS}fps...")
    audio = str(AUDIO) if AUDIO.exists() else None
    render_to_mp4(render_frame_fn, TOTAL_FRAMES, OUT_LANDSCAPE, audio_path=audio)

    print("\nConverting to vertical...")
    make_vertical(OUT_LANDSCAPE, OUT_VERTICAL)

    print("\nDone!")


if __name__ == "__main__":
    main()
