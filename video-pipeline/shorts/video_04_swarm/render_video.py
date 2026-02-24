#!/usr/bin/env python3
"""
Render Video 04: Swarm Engine — "One Task. Five Agents."
Fan-out animation: central task splits into parallel workers, results merge back.
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
    (0.0,  4.0, "One task. Five AI agents."),
    (4.0,  4.0, "Big tasks are slow with one agent."),
    (8.0,  5.0, "Decompose into independent pieces."),
    (13.0, 5.0, "Dispatch to parallel workers."),
    (18.0, 5.0, "Each result validated against a contract."),
    (23.0, 5.0, "Merge back. Deduplicated. Quality-checked."),
    (28.0, 6.0, "10x faster. Same quality."),
    (34.0, 6.0, "cadre-ai — github.com/WeberG619"),
]

# Worker positions (fan-out from center)
WORKERS = [
    (W // 2 - 500, H // 2, "Worker 1", "Review auth.py", CYAN),
    (W // 2 - 250, H // 2 - 180, "Worker 2", "Review api.py", BLUE),
    (W // 2,       H // 2 - 280, "Worker 3", "Review db.py", GREEN),
    (W // 2 + 250, H // 2 - 180, "Worker 4", "Review cache.py", YELLOW),
    (W // 2 + 500, H // 2, "Worker 5", "Review utils.py", MAGENTA),
]

TASK_POS = (W // 2, 120)
MERGE_POS = (W // 2, H - 200)


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
        draw_big_text(draw, "One Task. Five Agents.", 60, color=c, size=48)

    # === CENTRAL TASK NODE (appears at 3s) ===
    if t >= 3.0:
        age = t - 3.0
        scale = ease_in_out(min(1.0, age / 0.6))
        tx, ty = TASK_POS
        r = int(55 * scale)

        # Task card instead of just node
        draw_card(draw, tx - 180, ty - 20, 360, 80,
                  title="Review 5 API endpoints", color=WHITE,
                  icon="T", subtitle="Security audit")

    # === DECOMPOSITION LINES (8-12s) ===
    if t >= 8.0:
        decomp_t = min(1.0, (t - 8.0) / 3.0)
        tx, ty = TASK_POS[0], TASK_POS[1] + 60

        for i, (wx, wy, name, desc, color) in enumerate(WORKERS):
            # Staggered appearance
            worker_delay = i * 0.4
            worker_t = max(0, decomp_t - worker_delay / 3.0)
            if worker_t <= 0:
                continue

            # Line from task to worker
            lx = int(lerp(tx, wx, ease_in_out(min(1.0, worker_t * 2))))
            ly = int(lerp(ty, wy - 45, ease_in_out(min(1.0, worker_t * 2))))
            line_c = tuple(int(v * 0.4) for v in color)
            draw.line([(tx, ty), (lx, ly)], fill=line_c, width=2)

            # Animated data packet
            if worker_t < 0.8:
                pt = worker_t / 0.8
                px = lerp(tx, wx, pt)
                py = lerp(ty, wy - 45, pt)
                draw.ellipse([(px - 5, py - 5), (px + 5, py + 5)], fill=color)

    # === WORKER NODES (appear at 9s, staggered) ===
    if t >= 9.0:
        for i, (wx, wy, name, desc, color) in enumerate(WORKERS):
            appear_t = 9.0 + i * 0.5
            if t < appear_t:
                continue

            age = t - appear_t
            scale = ease_in_out(min(1.0, age / 0.5))

            # Worker card
            cw = int(280 * scale)
            ch = int(110 * scale)
            if cw > 20 and ch > 20:
                draw_card(draw, wx - cw // 2, wy - ch // 2, cw, ch,
                          title=name, color=color,
                          subtitle=desc if scale > 0.8 else "")

            # Progress bar inside card (13s+)
            if t >= 13.0 and scale > 0.9:
                prog_t = (t - 13.0) / 8.0  # 8 seconds to complete
                # Each worker finishes at different rate
                rates = [1.0, 0.9, 1.1, 0.85, 0.95]
                prog = min(1.0, prog_t * rates[i])

                bar_y = wy + ch // 2 - 20
                bar_x = wx - cw // 2 + 15
                bar_w = cw - 30
                if bar_w > 10:
                    draw.rounded_rectangle(
                        [(bar_x, bar_y), (bar_x + bar_w, bar_y + 6)],
                        radius=3, fill=(30, 30, 50))
                    filled = int(bar_w * prog)
                    if filled > 0:
                        draw.rounded_rectangle(
                            [(bar_x, bar_y), (bar_x + filled, bar_y + 6)],
                            radius=3, fill=color)

                # Check mark when done
                if prog >= 1.0:
                    f_check = font(20, bold=True)
                    draw.text((wx + cw // 2 - 35, wy - ch // 2 + 10),
                              "OK", fill=GREEN, font=f_check)

            # Spinning indicator while working
            if 13.0 <= t < 21.0:
                rates = [1.0, 0.9, 1.1, 0.85, 0.95]
                prog_t = (t - 13.0) / 8.0
                if prog_t * rates[i] < 1.0:
                    angle = t * 4 + i * 1.2
                    sx = wx + cw // 2 - 25 + math.cos(angle) * 6
                    sy = wy - ch // 2 + 20 + math.sin(angle) * 6
                    draw.ellipse([(sx - 3, sy - 3), (sx + 3, sy + 3)], fill=color)

    # === MERGE NODE (appears at 23s) ===
    if t >= 23.0:
        age = t - 23.0
        scale = ease_in_out(min(1.0, age / 0.8))
        mx, my = MERGE_POS
        r = int(50 * scale)

        # Lines from workers to merge
        if t >= 24.0:
            merge_t = min(1.0, (t - 24.0) / 2.0)
            for i, (wx, wy, name, desc, color) in enumerate(WORKERS):
                wy_bottom = wy + 55
                lx = int(lerp(wx, mx, merge_t))
                ly = int(lerp(wy_bottom, my - 50, merge_t))
                line_c = tuple(int(v * 0.4) for v in color)
                draw.line([(wx, wy_bottom), (lx, ly)], fill=line_c, width=2)

                # Data packet traveling
                if merge_t < 0.8:
                    pt = merge_t / 0.8
                    px = lerp(wx, mx, pt)
                    py = lerp(wy_bottom, my - 50, pt)
                    draw.ellipse([(px - 4, py - 4), (px + 4, py + 4)], fill=color)

        # Merge card
        draw_card(draw, mx - 200, my - 40, 400, 90,
                  title="MERGED RESULT", color=GREEN,
                  icon="M", subtitle="Deduplicated. Validated.")

    # === RESULT STATS (28s+) ===
    if t >= 28.0:
        fade = min(1.0, (t - 28.0) / 1.0)
        stats_y = H - 160
        stats = [
            (W // 2 - 300, "5", "Workers"),
            (W // 2 - 100, "8.2s", "Total Time"),
            (W // 2 + 100, "41s", "Sequential"),
            (W // 2 + 300, "5x", "Speedup"),
        ]
        for sx, val, label in stats:
            c = tuple(int(v * fade) for v in CYAN)
            d = tuple(int(v * fade) for v in DIM)
            f_big = font(32, bold=True)
            tw = draw.textlength(val, font=f_big)
            draw.text((sx - tw / 2, stats_y), val, fill=c, font=f_big)
            f_sm = font(13)
            lw = draw.textlength(label, font=f_sm)
            draw.text((sx - lw / 2, stats_y + 38), label, fill=d, font=f_sm)

    # Caption bar
    caption = get_caption(t)
    if caption:
        draw_caption(draw, caption)

    return img


def generate_thumbnail():
    img = render_frame_fn(0, 20.0)
    draw = ImageDraw.Draw(img)
    draw_big_text(draw, "One Task. Five Agents.", 30, color=BLUE, size=48)
    draw_subtitle(draw, "Parallel AI Swarm Engine", 90, color=DIM, size=24)
    img.save(str(THUMBNAIL), quality=95)
    print(f"  Thumbnail: {THUMBNAIL}")


def main():
    print("=" * 50)
    print("Rendering Video 04: Swarm Engine")
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
