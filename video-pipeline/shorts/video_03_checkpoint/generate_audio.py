#!/usr/bin/env python3
"""Generate voiceover for Video 03: Checkpointing."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from gfx_engine import generate_audio
from pathlib import Path

SEGMENTS = [
    ("01_hook", "My AI agent saves its own brain. Here's how."),
    ("02_problem", "Long tasks crash. Sessions timeout. Context fills up."),
    ("03_solution", "After every phase, the agent checkpoints its state."),
    ("04_what", "Files modified. Decisions made. What comes next."),
    ("05_resume", "New session? Resume from the last checkpoint. Full context restored."),
    ("06_never", "Nothing is ever lost. Not a single decision."),
    ("07_cta", "Open source. cadre AI. Link in bio."),
]

if __name__ == "__main__":
    out = Path(__file__).parent / "audio"
    generate_audio(SEGMENTS, out)
    print("Done!")
