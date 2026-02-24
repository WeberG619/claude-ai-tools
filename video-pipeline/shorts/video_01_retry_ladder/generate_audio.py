#!/usr/bin/env python3
"""Generate voiceover for Video 01: Retry Ladder."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from gfx_engine import generate_audio
from pathlib import Path

SEGMENTS = [
    ("01_hook", "When my AI agent fails, it doesn't just try the same thing twice."),
    ("02_intro", "It runs a strategy ladder."),
    ("03_quickfix", "First. Quick fix. Minimal change. Two shots at it."),
    ("04_refactor", "If that fails, it reads more context, and refactors the approach."),
    ("05_alternative", "Still failing? Completely different strategy. Alternative solution."),
    ("06_escalate", "And if nothing works, it writes me a detailed failure report, so I'm not starting from zero."),
    ("07_result", "Four strategies. Five max attempts. Fifteen minute hard timeout."),
    ("08_memory", "It logs every attempt, so next time, it skips straight to what worked."),
    ("09_cta", "This is cadre AI. Link in bio."),
]

if __name__ == "__main__":
    out = Path(__file__).parent / "audio"
    generate_audio(SEGMENTS, out)
    print("Done!")
