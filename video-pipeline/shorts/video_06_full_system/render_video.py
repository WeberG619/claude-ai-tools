#!/usr/bin/env python3
"""
Render Video 06: Full System Showcase — "The Complete Agent System."
Dashboard view showing all 5 systems working together in a live flow.
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

DURATION = 48.0
TOTAL_FRAMES = int(DURATION * FPS)

CAPTIONS = [
    (0.0,  5.0, "A real engineering system for AI agents."),
    (5.0,  4.0, "Task comes in. Board picks it up."),
    (9.0,  5.0, "Agent works. Checkpoints after every phase."),
    (14.0, 5.0, "Something fails? Retry ladder kicks in."),
    (19.0, 5.0, "Too big? Swarm fans out."),
    (24.0, 5.0, "Every output validated."),
    (29.0, 5.0, "Remembers everything. Gets smarter."),
    (34.0, 5.0, "5 systems. Fully integrated."),
    (39.0, 9.0, "cadre-ai — github.com/WeberG619"),
]

# Dashboard layout
DASH_MARGIN = 40
DASH_GAP = 20


def get_caption(t):
    for start, dur, text in CAPTIONS:
        if start <= t < start + dur:
            return text
    return None


def draw_mini_graph(draw, x, y, w, h, data, color, t_offset=0):
    """Draw a small line graph."""
    if len(data) < 2:
        return
    pts = []
    for i, v in enumerate(data):
        px = x + int(w * i / (len(data) - 1))
        py = y + h - int(h * v)
        pts.append((px, py))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=2)


def draw_log_line(draw, x, y, timestamp, message, status_color, t):
    """Animated log line with typing effect."""
    f_ts = font(12, mono=True)
    f_msg = font(13, mono=True)
    draw.text((x, y), timestamp, fill=DIM, font=f_ts)
    draw.text((x + 90, y), message, fill=status_color, font=f_msg)


def render_frame_fn(frame_idx, t):
    img = new_frame()
    draw = ImageDraw.Draw(img)

    # Subtle grid
    draw_grid(draw, spacing=60, color=(16, 16, 28))

    # === TOP BAR ===
    draw.rectangle([(0, 0), (W, 50)], fill=(18, 18, 28))
    f_title = font(16, bold=True)
    draw.text((DASH_MARGIN, 14), "CADRE-AI  SYSTEM DASHBOARD", fill=CYAN, font=f_title)

    # Live clock
    f_clock = font(14, mono=True)
    clock_text = f"SESSION: {int(t)}s"
    tw = draw.textlength(clock_text, font=f_clock)
    draw.text((W - tw - DASH_MARGIN, 16), clock_text, fill=DIM, font=f_clock)

    # Status dots
    systems = ["Board", "Retry", "Checkpoint", "Validator", "Swarm"]
    sys_colors = [CYAN, YELLOW, GREEN, MAGENTA, BLUE]
    for i, (name, color) in enumerate(zip(systems, sys_colors)):
        sx = 400 + i * 130
        active = t > 5.0 + i * 5
        dot_c = color if active else (40, 40, 50)
        draw.ellipse([(sx, 18), (sx + 12, 30)], fill=dot_c)
        draw.text((sx + 18, 16), name, fill=dot_c, font=font(12))

    # === TASK BOARD PANEL (left) ===
    panel_y = 65
    panel_h = 440
    left_w = 450

    draw_rounded_rect(draw, (DASH_MARGIN, panel_y, DASH_MARGIN + left_w, panel_y + panel_h),
                      radius=10, fill=BG_CARD, outline=(35, 35, 55))
    draw.rectangle([(DASH_MARGIN + 1, panel_y + 1), (DASH_MARGIN + left_w - 1, panel_y + 4)],
                   fill=CYAN)
    draw.text((DASH_MARGIN + 15, panel_y + 12), "TASK BOARD", fill=CYAN, font=font(14, bold=True))

    # Task entries
    tasks = [
        ("Review API endpoints", "active", GREEN, 5.0),
        ("Fix auth regression", "pending", YELLOW, 9.0),
        ("Update documentation", "done", DIM, 14.0),
        ("Security audit", "active", CYAN, 19.0),
        ("Deploy staging", "pending", YELLOW, 29.0),
    ]
    ty = panel_y + 40
    for title, status, color, appear_t in tasks:
        if t < appear_t:
            continue
        age = t - appear_t
        fade = min(1.0, age / 0.5)

        # Status based on time progression
        if status == "active" and age > 10:
            status = "done"
            color = GREEN
        elif status == "pending" and age > 5:
            status = "active"
            color = CYAN

        c = tuple(int(v * fade) for v in color)
        d = tuple(int(v * fade) for v in DIM)

        # Status dot
        draw.ellipse([(DASH_MARGIN + 20, ty + 4), (DASH_MARGIN + 30, ty + 14)], fill=c)
        draw.text((DASH_MARGIN + 38, ty), title, fill=c, font=font(13))

        # Progress for active tasks
        if status == "active":
            prog = min(1.0, (age - 5) / 10) if age > 5 else min(0.5, age / 10)
            bar_x = DASH_MARGIN + 20
            bar_w = left_w - 50
            draw.rounded_rectangle([(bar_x, ty + 20), (bar_x + bar_w, ty + 26)],
                                   radius=3, fill=(25, 25, 40))
            filled = int(bar_w * prog)
            if filled > 0:
                draw.rounded_rectangle([(bar_x, ty + 20), (bar_x + filled, ty + 26)],
                                       radius=3, fill=c)

        ty += 55

    # === AGENT STATUS (center top) ===
    center_x = DASH_MARGIN + left_w + DASH_GAP
    center_w = W - center_x - DASH_MARGIN - 450 - DASH_GAP
    if center_w < 200:
        center_w = 500

    draw_rounded_rect(draw, (center_x, panel_y, center_x + center_w, panel_y + 200),
                      radius=10, fill=BG_CARD, outline=(35, 35, 55))
    draw.rectangle([(center_x + 1, panel_y + 1), (center_x + center_w - 1, panel_y + 4)],
                   fill=GREEN)
    draw.text((center_x + 15, panel_y + 12), "AGENT STATUS", fill=GREEN, font=font(14, bold=True))

    # Progress rings for current task phases
    if t >= 9.0:
        phases = [
            ("Orient", 0.0, CYAN),
            ("Investigate", 3.0, BLUE),
            ("Plan", 6.0, YELLOW),
            ("Execute", 9.0, GREEN),
            ("Verify", 12.0, MAGENTA),
        ]
        ring_y = panel_y + 120
        for i, (name, delay, color) in enumerate(phases):
            rx = center_x + 50 + i * (center_w - 80) // 5
            phase_t = max(0, t - 9.0 - delay)
            prog = min(1.0, phase_t / 5.0) if phase_t > 0 else 0
            draw_progress_ring(draw, rx, ring_y, 22, prog, color=color, width=4)
            f_sm = font(9)
            tw_sm = draw.textlength(name, font=f_sm)
            draw.text((rx - tw_sm / 2, ring_y + 28), name, fill=DIM, font=f_sm)

    # === RETRY LADDER (center bottom) ===
    retry_y = panel_y + 200 + DASH_GAP
    retry_h = panel_h - 200 - DASH_GAP

    draw_rounded_rect(draw, (center_x, retry_y, center_x + center_w, retry_y + retry_h),
                      radius=10, fill=BG_CARD, outline=(35, 35, 55))
    draw.rectangle([(center_x + 1, retry_y + 1), (center_x + center_w - 1, retry_y + 4)],
                   fill=YELLOW)
    draw.text((center_x + 15, retry_y + 12), "RETRY LADDER", fill=YELLOW, font=font(14, bold=True))

    if t >= 14.0:
        strategies = [
            ("Quick-Fix", 2, 14.0, RED),
            ("Refactor", 1, 18.0, RED),
            ("Alternative", 1, 22.0, GREEN),
            ("Escalate", 1, 26.0, DIM),
        ]
        sy = retry_y + 40
        for name, max_att, appear_t, result_c in strategies:
            if t < appear_t:
                break
            age = t - appear_t

            draw.text((center_x + 20, sy), name, fill=WHITE, font=font(13, bold=True))
            draw.text((center_x + 140, sy), f"({max_att} att)", fill=DIM, font=font(11))

            # Result
            if age > 3.0:
                if result_c == GREEN:
                    draw.text((center_x + center_w - 60, sy), "PASS", fill=GREEN, font=font(12, bold=True))
                elif result_c == RED:
                    draw.text((center_x + center_w - 60, sy), "FAIL", fill=RED, font=font(12, bold=True))
            elif age > 1.0:
                # Spinning dots
                dot_x = center_x + center_w - 50 + math.cos(t * 5) * 8
                dot_y = sy + 6 + math.sin(t * 5) * 4
                draw.ellipse([(dot_x - 3, dot_y - 3), (dot_x + 3, dot_y + 3)], fill=YELLOW)

            sy += 32

    # === RIGHT PANEL — LIVE LOG ===
    right_x = W - DASH_MARGIN - 450
    right_w = 450

    draw_rounded_rect(draw, (right_x, panel_y, right_x + right_w, panel_y + panel_h),
                      radius=10, fill=BG_CARD, outline=(35, 35, 55))
    draw.rectangle([(right_x + 1, panel_y + 1), (right_x + right_w - 1, panel_y + 4)],
                   fill=ORANGE)
    draw.text((right_x + 15, panel_y + 12), "LIVE LOG", fill=ORANGE, font=font(14, bold=True))

    log_entries = [
        (2.0, "00:02", "Board initialized", CYAN),
        (5.0, "00:05", "Task picked up: Review API", GREEN),
        (7.0, "00:07", "Agent starting Orient phase", BLUE),
        (9.0, "00:09", "Checkpoint saved: Orient", GREEN),
        (11.0, "00:11", "Investigating 5 source files", BLUE),
        (13.0, "00:13", "Checkpoint saved: Investigate", GREEN),
        (14.0, "00:14", "Build failed: CS0246", RED),
        (15.0, "00:15", "Retry: quick-fix attempt 1", YELLOW),
        (16.5, "00:16", "Retry: quick-fix attempt 2", YELLOW),
        (18.0, "00:18", "Retry: refactor attempt", BLUE),
        (20.0, "00:20", "Retry: alternative attempt", MAGENTA),
        (22.0, "00:22", "BUILD SUCCEEDED", GREEN),
        (23.0, "00:23", "Validating output...", CYAN),
        (24.0, "00:24", "Contract: code_change PASS", GREEN),
        (26.0, "00:26", "Checkpoint saved: Execute", GREEN),
        (28.0, "00:28", "Running verification tests", BLUE),
        (30.0, "00:30", "All tests passed", GREEN),
        (32.0, "00:32", "Task completed", GREEN),
        (34.0, "00:34", "Memory stored: outcome", CYAN),
        (36.0, "00:36", "Next task: Fix auth regression", YELLOW),
    ]

    ly = panel_y + 38
    max_lines = (panel_h - 50) // 20
    visible = [(lt, ts, msg, c) for lt, ts, msg, c in log_entries if t >= lt]
    visible = visible[-max_lines:]  # Show most recent

    for lt, ts, msg, color in visible:
        age = t - lt
        fade = min(1.0, age / 0.5)
        c = tuple(int(v * fade) for v in color)
        d = tuple(int(v * fade) for v in DIM)

        draw.text((right_x + 10, ly), ts, fill=d, font=font(11, mono=True))
        # Truncate long messages
        display_msg = msg[:35]
        draw.text((right_x + 60, ly), display_msg, fill=c, font=font(12, mono=True))
        ly += 20

    # === BOTTOM STATS BAR ===
    stats_y = panel_y + panel_h + DASH_GAP
    stats_h = H - stats_y - 100 - DASH_GAP

    if stats_h > 50:
        draw_rounded_rect(draw, (DASH_MARGIN, stats_y, W - DASH_MARGIN, stats_y + stats_h),
                          radius=10, fill=BG_CARD, outline=(35, 35, 55))

        # Counters
        counters_data = [
            (DASH_MARGIN + 120, "Tasks", int(min(5, t / 5)), CYAN),
            (DASH_MARGIN + 300, "Checkpoints", int(min(12, t / 3)), GREEN),
            (DASH_MARGIN + 500, "Retries", int(min(4, max(0, t - 14) / 3)), YELLOW),
            (DASH_MARGIN + 700, "Validations", int(min(8, max(0, t - 23) / 2)), MAGENTA),
            (DASH_MARGIN + 920, "Workers", int(min(5, max(0, t - 19) / 2)), BLUE),
        ]

        for cx, label, val, color in counters_data:
            f_big = font(28, bold=True)
            f_sm = font(11)
            val_str = str(val)
            tw = draw.textlength(val_str, font=f_big)
            draw.text((cx - tw / 2, stats_y + 10), val_str, fill=color, font=f_big)
            lw = draw.textlength(label, font=f_sm)
            draw.text((cx - lw / 2, stats_y + 44), label, fill=DIM, font=f_sm)

        # Mini activity graph
        if t > 5.0:
            graph_x = W - DASH_MARGIN - 380
            graph_w = 340
            graph_y = stats_y + 10
            graph_h = stats_h - 20

            # Generate fake activity data based on time
            data_points = 30
            data = []
            for i in range(data_points):
                pt = (t - 5.0) * i / data_points
                val = 0.3 + 0.3 * math.sin(pt * 0.5) + 0.2 * math.sin(pt * 1.3)
                # Spike during retry
                if 14.0 <= pt + 5.0 <= 22.0:
                    val += 0.3
                data.append(min(1.0, max(0.0, val)))

            draw_mini_graph(draw, graph_x, graph_y, graph_w, graph_h, data, CYAN)

    # Caption bar
    caption = get_caption(t)
    if caption:
        draw_caption(draw, caption)

    return img


def generate_thumbnail():
    img = render_frame_fn(0, 30.0)
    draw = ImageDraw.Draw(img)
    # Semi-transparent overlay for title
    draw.rectangle([(0, 0), (W, 120)], fill=(12, 12, 20))
    draw_big_text(draw, "The Complete Agent System", 20, color=WHITE, size=44)
    draw_subtitle(draw, "cadre-ai — 5 Integrated Systems", 75, color=CYAN, size=22)
    img.save(str(THUMBNAIL), quality=95)
    print(f"  Thumbnail: {THUMBNAIL}")


def main():
    print("=" * 50)
    print("Rendering Video 06: Full System Showcase")
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
