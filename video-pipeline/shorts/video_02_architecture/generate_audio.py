#!/usr/bin/env python3
"""Generate voiceover for Video 02: Architecture Overview."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from gfx_engine import generate_audio
from pathlib import Path

SEGMENTS = [
    ("01_hook", "Five systems. Zero external dependencies. All running on one machine."),
    ("02_board", "The task board tracks every operation across sessions."),
    ("03_retry", "Adaptive retry escalates strategies when something fails."),
    ("04_checkpoint", "Checkpoints save agent state so nothing is ever lost."),
    ("05_validator", "Output contracts validate every result before delivery."),
    ("06_swarm", "The swarm engine fans out parallel workers for big tasks."),
    ("07_cta", "All open source. cadre AI. Link in bio."),
]

if __name__ == "__main__":
    out = Path(__file__).parent / "audio"
    generate_audio(SEGMENTS, out)
    print("Done!")
