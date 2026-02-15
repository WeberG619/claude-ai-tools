#!/usr/bin/env python3
"""
Live Meeting Protocol - All Agents Speak Out Loud

This protocol has every agent speak their turn audibly.
More immersive but slower - like sitting in on a real meeting.

Best for:
- When you want to hear the full debate
- Demonstrations and showcases
- When audio feedback helps you think
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_prompts import get_prompt

VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
REGISTRY_FILE = Path(__file__).parent.parent / "voice_registry.json"


class LiveMeetingProtocol:
    """
    Full voice meeting - every agent speaks.

    Flow:
    1. Each agent speaks their turn out loud
    2. Brief pause between speakers (like real conversation)
    3. Visual + audio feedback throughout
    4. Narrator summarizes at end
    """

    def __init__(self, max_turns: int = 8, pause_between: float = 0.5):
        self.max_turns = max_turns
        self.pause_between = pause_between  # Seconds between speakers
        self.history: List[Dict] = []
        self.artifacts: List[str] = []
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        with open(REGISTRY_FILE) as f:
            return json.load(f)

    def _get_voice(self, agent: str) -> str:
        """Get the voice for an agent."""
        return self.registry["agents"].get(agent, {}).get("voice", "andrew")

    def _speak(self, text: str, voice: str):
        """Speak text using TTS with mic lock (waits until done)."""
        try:
            result = subprocess.run(
                ["python3", str(VOICE_SCRIPT), text, voice],  # voice is positional
                check=True,
                capture_output=True,
                timeout=90  # Longer timeout for live mode
            )
            return True
        except Exception as e:
            print(f"[Voice Error] {e}")
            return False

    def _announce_speaker(self, agent: str):
        """Visual indicator of who's speaking."""
        role = self.registry["agents"].get(agent, {}).get("role", agent.title())
        voice = self._get_voice(agent)

        print(f"\n{'─'*50}")
        print(f"🎤 {role.upper()} ({voice})")
        print(f"{'─'*50}")

    def _simulate_agent_response(self, agent: str, task: str) -> str:
        """Placeholder for agent response - real version calls Claude."""
        responses = {
            "planner": f"Alright team, I'm Andrew your Planner. The task is: {task[:40]}. Breaking into three phases. Research, implementation, validation. Guy, start investigating.",
            "researcher": "This is Guy, your Researcher. Found the relevant modules. Existing patterns we can follow. Christopher, implement using these conventions.",
            "builder": "Christopher here, the Builder. Implemented the core functionality with proper error handling. Eric, please validate.",
            "critic": "Eric speaking, the Critic. Reviewing now. Implementation is solid. Error handling looks good. Approved. Task complete.",
            "narrator": "This is Jenny with your summary. The team completed your request. Andrew planned it, Guy researched, Christopher built it, and Eric approved. All done."
        }
        return responses.get(agent, "Standing by.")

    def run_meeting(self, task: str, tool_executor=None) -> Dict:
        """
        Run the full live meeting with voice.

        Args:
            task: The task description
            tool_executor: Optional callable for tool execution

        Returns:
            Meeting results
        """
        print("\n" + "="*60)
        print("🎙️  LIVE CODING WAR-ROOM MEETING")
        print("="*60)
        print(f"Task: {task}")
        print("="*60 + "\n")

        # Opening announcement
        self._speak("Coding war room meeting starting now. Let's get to work.", "jenny")
        time.sleep(self.pause_between)

        turn_order = ["planner", "researcher", "builder", "critic"]
        turn_idx = 0

        for i in range(self.max_turns):
            agent = turn_order[turn_idx % len(turn_order)]
            voice = self._get_voice(agent)

            # Announce speaker
            self._announce_speaker(agent)

            # Get response (placeholder)
            response = self._simulate_agent_response(agent, task)

            # Speak the response
            print(f"  \"{response}\"")
            self._speak(response, voice)

            # Record turn
            self.history.append({
                "turn": i + 1,
                "speaker": agent,
                "content": response,
                "voice": voice,
                "timestamp": datetime.now().isoformat()
            })

            # Check for completion
            if "task complete" in response.lower() or "approved" in response.lower():
                print("\n✅ Meeting concluded - consensus reached!")
                break

            # Pause between speakers
            time.sleep(self.pause_between)
            turn_idx += 1

        # Closing summary from narrator
        self._announce_speaker("narrator")
        summary = self._simulate_agent_response("narrator", task)
        print(f"  \"{summary}\"")
        self._speak(summary, self._get_voice("narrator"))

        self.history.append({
            "turn": len(self.history) + 1,
            "speaker": "narrator",
            "content": summary,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "history": self.history,
            "artifacts": self.artifacts,
            "status": "complete",
            "turns": len(self.history),
            "mode": "live"
        }

    def run(self, task: str, tool_executor=None) -> Dict:
        """Main entry point for the protocol."""
        return self.run_meeting(task, tool_executor)


def main():
    """Test the live meeting protocol."""
    import argparse

    parser = argparse.ArgumentParser(description="Live Meeting Protocol Test")
    parser.add_argument("task", nargs="?", default="Create a simple API endpoint",
                        help="Task for the team")

    args = parser.parse_args()

    protocol = LiveMeetingProtocol()
    result = protocol.run(args.task)

    print("\n" + "="*60)
    print("LIVE MEETING COMPLETE")
    print(f"Total turns: {result['turns']}")
    print("="*60)


if __name__ == "__main__":
    main()
