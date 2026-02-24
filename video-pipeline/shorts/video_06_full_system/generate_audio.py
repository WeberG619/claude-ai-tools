#!/usr/bin/env python3
"""Generate voiceover for Video 06: Full System Showcase."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from gfx_engine import generate_audio
from pathlib import Path

SEGMENTS = [
    ("01_hook", "This is what happens when you give an AI agent a real engineering system."),
    ("02_flow", "A task comes in. The board picks it up."),
    ("03_execute", "The agent starts working. Checkpoint after every phase."),
    ("04_fail", "Something fails? The retry ladder kicks in."),
    ("05_swarm", "Too big for one agent? The swarm fans out."),
    ("06_validate", "Every output validated. Every result quality-checked."),
    ("07_memory", "It remembers everything. Gets smarter with every run."),
    ("08_cta", "This is cadre AI. All open source. Link in bio."),
]

if __name__ == "__main__":
    out = Path(__file__).parent / "audio"
    generate_audio(SEGMENTS, out)
    print("Done!")
