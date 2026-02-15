#!/usr/bin/env python3
"""
Test all agent voices to hear the distinct personalities.
"""

import json
import subprocess
import time
from pathlib import Path

VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
REGISTRY = Path(__file__).parent / "voice_registry.json"

# Sample lines for each agent personality (short for quick testing)
AGENT_LINES = {
    "planner": "I'm Andrew, the Planner. Let me break this task down into steps.",
    "researcher": "I'm Guy, the Researcher. I found the relevant files we need.",
    "builder": "I'm Christopher, the Builder. Implementation is ready.",
    "critic": "I'm Eric, the Critic. The code looks solid, approved.",
    "narrator": "I'm Jenny, the Narrator. The team completed your request successfully."
}

def test_voices():
    with open(REGISTRY) as f:
        registry = json.load(f)

    print("\n" + "="*60)
    print("AGENT VOICE TEST - Hearing all team members")
    print("="*60 + "\n")

    for agent_id, config in registry["agents"].items():
        voice = config["voice"]
        role = config["role"]
        line = AGENT_LINES.get(agent_id, f"Hello, I am the {role}.")

        print(f"[{role.upper()}] Voice: {voice}")
        print(f"  Speaking: \"{line[:50]}...\"")

        try:
            subprocess.run(
                ["python3", str(VOICE_SCRIPT), line, voice],  # voice is positional, not --voice
                check=True,
                capture_output=True,
                timeout=30
            )
            print("  ✓ Complete\n")
        except Exception as e:
            print(f"  ✗ Error: {e}\n")

        time.sleep(0.5)  # Brief pause between agents

    print("="*60)
    print("Voice test complete!")
    print("="*60)

if __name__ == "__main__":
    test_voices()
