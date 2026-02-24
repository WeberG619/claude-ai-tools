#!/usr/bin/env python3
"""Generate voiceover for Video 04: Swarm Engine."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from gfx_engine import generate_audio
from pathlib import Path

SEGMENTS = [
    ("01_hook", "One task. Five AI agents. All working at the same time."),
    ("02_problem", "Big tasks are slow when one agent does everything."),
    ("03_decompose", "The swarm engine decomposes the task into independent pieces."),
    ("04_dispatch", "Each piece goes to a parallel worker. Five agents, five threads."),
    ("05_validate", "Every result is validated against an output contract."),
    ("06_merge", "Results merge back. Deduplicated. Quality-checked."),
    ("07_cta", "Parallel AI agents. Open source. cadre AI."),
]

if __name__ == "__main__":
    out = Path(__file__).parent / "audio"
    generate_audio(SEGMENTS, out)
    print("Done!")
