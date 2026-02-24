#!/usr/bin/env python3
"""Generate voiceover for Video 05: Output Validation."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from gfx_engine import generate_audio
from pathlib import Path

SEGMENTS = [
    ("01_hook", "My AI doesn't just generate output. It proves it's correct."),
    ("02_problem", "Most AI agents ship broken results. No checks. No contracts."),
    ("03_contracts", "Every output has a contract. JSON schema. Text assertions."),
    ("04_validate", "Missing a required field? Fails. Contains a TODO? Fails."),
    ("05_retry", "Failed validation triggers automatic retry. Up to two attempts."),
    ("06_result", "Every result that reaches you has been validated."),
    ("07_cta", "Output contracts for AI. Open source. cadre AI."),
]

if __name__ == "__main__":
    out = Path(__file__).parent / "audio"
    generate_audio(SEGMENTS, out)
    print("Done!")
