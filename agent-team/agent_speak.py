#!/usr/bin/env python3
"""
Agent Speech Helper - Properly coordinates agent status with voice output.
Updates the monitor status file and plays audio with correct agent highlighting.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

STATUS_FILE = Path("/tmp/agent_speech_status.json")
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")

# Agent voice mappings
AGENT_VOICES = {
    "planner": "andrew",
    "researcher": "guy",
    "builder": "christopher",
    "critic": "eric",
    "narrator": "jenny"
}

def set_status(agent: str, text: str, speaking: bool = True):
    """Update the agent status file for the monitor."""
    status = {
        "status": "speaking" if speaking else "idle",
        "agent": agent if speaking else None,
        "role": agent.upper() if speaking else None,
        "text": text if speaking else ""
    }
    STATUS_FILE.write_text(json.dumps(status))

def speak(agent: str, text: str) -> bool:
    """Have an agent speak with proper status updates."""
    voice = AGENT_VOICES.get(agent, "andrew")

    # Set status to speaking
    set_status(agent, text, speaking=True)

    try:
        # Generate audio using edge TTS
        result = subprocess.run(
            ["python3", str(VOICE_SCRIPT), text, voice],
            capture_output=True,
            text=True,
            timeout=120
        )
        success = result.returncode == 0
    except Exception as e:
        print(f"Speech error: {e}")
        success = False

    # Small delay to let audio finish
    time.sleep(0.5)

    # Reset status to idle
    set_status(agent, "", speaking=False)

    return success

def main():
    if len(sys.argv) < 3:
        print("Usage: python agent_speak.py <agent> <text>")
        print(f"Agents: {', '.join(AGENT_VOICES.keys())}")
        sys.exit(1)

    agent = sys.argv[1].lower()
    text = sys.argv[2]

    if agent not in AGENT_VOICES:
        print(f"Unknown agent: {agent}")
        print(f"Available: {', '.join(AGENT_VOICES.keys())}")
        sys.exit(1)

    success = speak(agent, text)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
