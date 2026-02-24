#!/usr/bin/env python3
"""
Render Video 05: Output Validation — "Prove It's Correct."
Contract schema visualization with pass/fail animations.
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
    (0.0,  4.0, "My AI proves its output is correct."),
    (4.0,  4.0, "Most AI ships broken results."),
    (8.0,  5.0, "Every output has a contract."),
    (13.0, 5.0, "Missing a field? Fails. TODO found? Fails."),
    (18.0, 5.0, "Failed? Automatic retry."),
    (23.0, 5.0, "Every result is validated before delivery."),
    (28.0, 6.0, "Four contract types. Zero broken outputs."),
    (34.0, 6.0, "cadre-ai — github.com/WeberG619"),
]

# Contract types
CONTRACTS = [
    ("code_change", CYAN, ["summary", "files_changed", "no TODO/FIXME"]),
    ("task_result", GREEN, ["status", "summary", "min 20 words"]),
    ("research", BLUE, ["sources", "summary", "min 200 words"]),
    ("bim_operation", MAGENTA, ["elements", "positions", "verified"]),
]

# Validation checks animation
CHECKS = [
    (13.0, "summary", "present", True),
    (14.0, "files_changed", "['auth.py', 'test.py']", True),
    (15.0, "TODO found?", "scanning...", False),
    (16.0, "FIXME found?", "scanning...", True),
    (17.0, "word count", "147 words", True),
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
    if t < 3.5:
        fade = min(1.0, t / 0.5) * max(0.0, 1.0 - (t - 2.5))
        c = tuple(int(v * fade) for v in WHITE)
        draw_big_text(draw, "Prove It's Correct.", 80, color=c, size=48)

    # === CONTRACT CARDS (appear 4-12s) ===
    if t >= 4.0:
        card_w = 380
        card_h = 180
        gap = 40
        start_x = (W - (card_w * 2 + gap)) // 2
        start_y = 100

        for i, (name, color, fields) in enumerate(CONTRACTS):
            appear_t = 4.0 + i * 1.5
            if t < appear_t:
                continue

            age = t - appear_t
            scale = ease_in_out(min(1.0, age / 0.5))

            col = i % 2
            row = i // 2
            cx = start_x + col * (card_w + gap)
            cy = start_y + row * (card_h + gap)

            cw = int(card_w * scale)
            ch = int(card_h * scale)
            if cw < 20 or ch < 20:
                continue

            # Highlight active contract
            active_contract = None
            if 13.0 <= t < 18.0:
                active_contract = 0  # code_change
            elif 23.0 <= t < 28.0:
                active_contract = i

            outline_c = color if (active_contract == i or age < 2.0) else (40, 40, 60)
            draw_rounded_rect(draw, (cx, cy, cx + cw, cy + ch),
                              radius=12, fill=BG_CARD, outline=outline_c, width=2)

            # Color accent
            draw.rectangle([(cx + 1, cy + 1), (cx + cw - 1, cy + 4)], fill=color)

            if scale > 0.7:
                # Title
                f_title = font(18, bold=True)
                draw.text((cx + 15, cy + 15), name, fill=color, font=f_title)

                # Fields
                y_off = cy + 45
                for field in fields:
                    f_field = font(13, mono=True)
                    draw.text((cx + 20, y_off), f"  {field}", fill=DIM, font=f_field)
                    y_off += 22

                    # Check marks for active contract
                    if active_contract == i and t >= 23.0:
                        check_t = t - 23.0
                        field_idx = fields.index(field)
                        if check_t > field_idx * 0.5:
                            draw.text((cx + cw - 35, y_off - 22), "OK",
                                      fill=GREEN, font=font(12, bold=True))

    # === VALIDATION ANIMATION (13-18s) ===
    if 13.0 <= t < 22.0:
        val_x = W // 2 - 300
        val_y = 520
        val_w = 600
        val_h = 280

        draw_rounded_rect(draw, (val_x, val_y, val_x + val_w, val_y + val_h),
                          radius=12, fill=BG_CARD, outline=CYAN, width=2)
        draw.rectangle([(val_x + 1, val_y + 1), (val_x + val_w - 1, val_y + 4)],
                       fill=CYAN)

        f_title = font(18, bold=True)
        draw.text((val_x + 15, val_y + 15), "Validating: code_change", fill=CYAN, font=f_title)

        check_y = val_y + 50
        for check_t, field, value, passes in CHECKS:
            if t < check_t:
                break

            age = t - check_t
            f_field = font(14, mono=True)
            f_val = font(14, mono=True)

            # Field name
            draw.text((val_x + 25, check_y), field, fill=WHITE, font=f_field)

            # Value
            draw.text((val_x + 220, check_y), value, fill=DIM, font=f_val)

            # Result (appears after 0.5s)
            if age > 0.5:
                if passes:
                    draw.text((val_x + val_w - 60, check_y), "PASS",
                              fill=GREEN, font=font(14, bold=True))
                else:
                    draw.text((val_x + val_w - 60, check_y), "FAIL",
                              fill=RED, font=font(14, bold=True))

                    # Red flash on fail
                    if age < 1.0:
                        flash = int(20 * (1.0 - age + 0.5))
                        draw.rectangle([(val_x, check_y - 2),
                                        (val_x + val_w, check_y + 20)],
                                       fill=(flash, 0, 0))

            check_y += 38

        # Overall result
        if t >= 17.5:
            result_fade = min(1.0, (t - 17.5) / 0.5)
            # Has a failure (TODO check)
            c = tuple(int(v * result_fade) for v in RED)
            f_result = font(20, bold=True)
            draw.text((val_x + 15, val_y + val_h - 40),
                      "VALIDATION FAILED — retrying...", fill=c, font=f_result)

    # === RETRY + PASS (18-23s) ===
    if 18.0 <= t < 23.0:
        retry_t = t - 18.0

        rx = W // 2 - 300
        ry = 520
        rw = 600
        rh = 120

        draw_rounded_rect(draw, (rx, ry, rx + rw, ry + rh),
                          radius=12, fill=BG_CARD, outline=YELLOW, width=2)

        f_title = font(18, bold=True)
        draw.text((rx + 15, ry + 15), "Retry #1 — Validating...", fill=YELLOW, font=f_title)

        if retry_t > 2.0:
            # Progress bar
            prog = min(1.0, (retry_t - 2.0) / 2.0)
            bar_y = ry + 55
            bar_w = rw - 30
            draw.rounded_rectangle([(rx + 15, bar_y), (rx + 15 + bar_w, bar_y + 8)],
                                   radius=4, fill=(30, 30, 50))
            filled = int(bar_w * prog)
            draw.rounded_rectangle([(rx + 15, bar_y), (rx + 15 + filled, bar_y + 8)],
                                   radius=4, fill=GREEN)

        if retry_t > 4.0:
            draw.text((rx + 15, ry + 80), "ALL CHECKS PASSED",
                      fill=GREEN, font=font(20, bold=True))

    # === FINAL STATS (28s+) ===
    if t >= 28.0:
        fade = min(1.0, (t - 28.0) / 1.0)
        stats_y = H - 200

        stats = [
            (W // 2 - 300, "4", "Contract Types", CYAN),
            (W // 2 - 100, "0", "Broken Outputs", GREEN),
            (W // 2 + 100, "2", "Max Retries", YELLOW),
            (W // 2 + 300, "100%", "Validated", MAGENTA),
        ]
        for sx, val, label, color in stats:
            c = tuple(int(v * fade) for v in color)
            d = tuple(int(v * fade) for v in DIM)
            f_big = font(36, bold=True)
            tw = draw.textlength(val, font=f_big)
            draw.text((sx - tw / 2, stats_y), val, fill=c, font=f_big)
            f_sm = font(13)
            lw = draw.textlength(label, font=f_sm)
            draw.text((sx - lw / 2, stats_y + 42), label, fill=d, font=f_sm)

    # Caption bar
    caption = get_caption(t)
    if caption:
        draw_caption(draw, caption)

    return img


def generate_thumbnail():
    img = render_frame_fn(0, 24.0)
    draw = ImageDraw.Draw(img)
    draw_big_text(draw, "Prove It's Correct.", 30, color=MAGENTA, size=48)
    draw_subtitle(draw, "AI Output Validation Contracts", 90, color=DIM, size=24)
    img.save(str(THUMBNAIL), quality=95)
    print(f"  Thumbnail: {THUMBNAIL}")


def main():
    print("=" * 50)
    print("Rendering Video 05: Output Validation")
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
