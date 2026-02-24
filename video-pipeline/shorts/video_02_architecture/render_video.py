#!/usr/bin/env python3
"""
Render Video 02: Architecture Overview — "5 Systems. Zero Dependencies."
Animated architecture diagram with nodes, connections, flowing data.
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

DURATION = 42.0
TOTAL_FRAMES = int(DURATION * FPS)

# ── NODE POSITIONS ────────────────────────────────
# Center hub + 5 surrounding systems
HUB = (W // 2, H // 2)
NODES = {
    "hub":        (W // 2, H // 2,       "CADRE\nAI",     WHITE),
    "board":      (W // 2 - 400, H // 2 - 200, "TASK\nBOARD",   CYAN),
    "retry":      (W // 2 + 400, H // 2 - 200, "ADAPTIVE\nRETRY", YELLOW),
    "checkpoint": (W // 2 - 400, H // 2 + 200, "CHECK-\nPOINT",  GREEN),
    "validator":  (W // 2 + 400, H // 2 + 200, "OUTPUT\nVALID.",  MAGENTA),
    "swarm":      (W // 2,       H // 2 - 350, "SWARM\nENGINE",  BLUE),
}

CONNECTIONS = [
    ("hub", "board"), ("hub", "retry"), ("hub", "checkpoint"),
    ("hub", "validator"), ("hub", "swarm"),
    ("board", "checkpoint"), ("retry", "validator"), ("swarm", "board"),
]

# ── CAPTIONS ──────────────────────────────────────
CAPTIONS = [
    (0.0,  5.0, "5 systems. Zero external dependencies."),
    (5.0,  5.0, "Task board — tracks everything across sessions."),
    (10.0, 5.0, "Adaptive retry — escalates when things fail."),
    (15.0, 5.0, "Checkpoints — save state, never lose progress."),
    (20.0, 5.0, "Output validation — contracts enforce quality."),
    (25.0, 5.0, "Swarm engine — parallel workers, one task."),
    (30.0, 6.0, "All integrated. All local. All open source."),
    (36.0, 6.0, "cadre-ai — github.com/WeberG619"),
]

# ── TIMELINE: which nodes are active when ─────────
NODE_APPEAR = {
    "hub": 0.5,
    "board": 5.0,
    "retry": 10.0,
    "checkpoint": 15.0,
    "validator": 20.0,
    "swarm": 25.0,
}

CONN_APPEAR = {
    ("hub", "board"): 6.0,
    ("hub", "retry"): 11.0,
    ("hub", "checkpoint"): 16.0,
    ("hub", "validator"): 21.0,
    ("hub", "swarm"): 26.0,
    ("board", "checkpoint"): 30.0,
    ("retry", "validator"): 31.0,
    ("swarm", "board"): 32.0,
}


def get_caption(t):
    for start, dur, text in CAPTIONS:
        if start <= t < start + dur:
            return text
    return None


def render_frame_fn(frame_idx, t):
    img = new_frame()
    draw = ImageDraw.Draw(img)
    draw_grid(draw, spacing=50)

    # Title (fades out after 4s)
    if t < 4.0:
        alpha = min(1.0, t / 0.5) * max(0.0, 1.0 - (t - 3.0))
        c = tuple(int(v * alpha) for v in WHITE)
        draw_big_text(draw, "5 Systems. Zero Dependencies.", 40, color=c, size=44)

    # Draw connections
    for (n1, n2), appear_t in CONN_APPEAR.items():
        if t < appear_t:
            continue
        x1, y1 = NODES[n1][0], NODES[n1][1]
        x2, y2 = NODES[n2][0], NODES[n2][1]
        age = t - appear_t
        # Fade in
        fade = min(1.0, age / 1.0)
        c = tuple(int(v * fade * 0.5) for v in DIM)
        anim = (t * 0.3) if age > 1.0 else None
        draw_connection(draw, x1, y1, x2, y2, color=c, width=2, animated_pos=anim)

    # Draw nodes
    for name, (cx, cy, label, color) in NODES.items():
        appear_t = NODE_APPEAR.get(name, 0)
        if t < appear_t:
            continue

        age = t - appear_t
        # Scale-in animation
        scale = ease_in_out(min(1.0, age / 0.8))
        r = int(50 * scale) if name == "hub" else int(42 * scale)

        # Glow when first appearing
        glow = age < 3.0
        # Active = highlighted state
        active = age < 2.0

        # Pulsing glow for hub
        if name == "hub" and t > 2.0:
            pulse = 0.5 + 0.5 * math.sin(t * 2)
            glow = pulse > 0.7

        draw_node(draw, cx, cy, radius=r, label=label.replace("\n", " "),
                  color=color, active=active, glow=glow)

    # Stats counters (appear at 30s)
    if t >= 30.0:
        fade = min(1.0, (t - 30.0) / 1.0)
        y_base = H - 180
        counters = [
            (W // 2 - 400, "5", "Systems"),
            (W // 2 - 200, "0", "Dependencies"),
            (W // 2,       "∞", "Sessions"),
            (W // 2 + 200, "10", "Max Workers"),
            (W // 2 + 400, "100%", "Local"),
        ]
        for cx, val, label in counters:
            c = tuple(int(v * fade) for v in CYAN)
            d = tuple(int(v * fade) for v in DIM)
            f_big = font(36, bold=True)
            tw = draw.textlength(val, font=f_big)
            draw.text((cx - tw / 2, y_base), val, fill=c, font=f_big)
            f_sm = font(14)
            lw = draw.textlength(label, font=f_sm)
            draw.text((cx - lw / 2, y_base + 42), label, fill=d, font=f_sm)

    # Caption bar
    caption = get_caption(t)
    if caption:
        draw_caption(draw, caption)

    return img


def generate_thumbnail():
    img = render_frame_fn(0, 33.0)
    draw = ImageDraw.Draw(img)
    # Overlay title
    draw_big_text(draw, "5 Systems. Zero Dependencies.", 30, color=CYAN, size=48)
    draw_subtitle(draw, "cadre-ai — AI Agent Architecture", 90, color=DIM, size=24)
    img.save(str(THUMBNAIL), quality=95)
    print(f"  Thumbnail: {THUMBNAIL}")


def main():
    print("=" * 50)
    print("Rendering Video 02: Architecture Overview")
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
