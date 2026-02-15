#!/usr/bin/env python3
"""
Backstage Protocol - Fast Internal Debate + Voice Summary

This protocol runs the team conversation in text-only mode (fast),
then has the Narrator speak the final summary out loud.

Best for:
- Speed-critical tasks
- Not annoying the user with constant audio
- Complex multi-turn debates that need to happen quickly
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_prompts import get_prompt

VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
REGISTRY_FILE = Path(__file__).parent.parent / "voice_registry.json"


class BackstageProtocol:
    """
    Fast text-only debate, voice summary only.

    Flow:
    1. Planner analyzes and creates plan
    2. Researcher gathers context (can use tools)
    3. Builder implements (can use tools)
    4. Critic validates
    5. Loop until consensus or max turns
    6. Narrator speaks summary to user
    """

    def __init__(self, max_internal_turns: int = 6):
        self.max_internal_turns = max_internal_turns
        self.history: List[Dict] = []
        self.artifacts: List[str] = []
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        with open(REGISTRY_FILE) as f:
            return json.load(f)

    def _speak(self, text: str, voice: str = "jenny"):
        """Speak text using TTS."""
        try:
            subprocess.run(
                ["python3", str(VOICE_SCRIPT), text, voice],  # voice is positional
                check=True,
                capture_output=True,
                timeout=60
            )
        except Exception as e:
            print(f"[Voice Error] {e}")

    def _simulate_agent_response(self, agent: str, task: str, context: str = "") -> str:
        """
        Simulate an agent response.
        In production, this calls Claude with the agent's prompt.
        """
        # This is a placeholder - the real director.py handles Claude calls
        responses = {
            "planner": f"Task received: {task[:50]}... Breaking into steps. Researcher, investigate the codebase.",
            "researcher": "Found relevant code. Key files identified. Builder, implement the solution.",
            "builder": "Implementation complete. Created the necessary changes. Critic, validate.",
            "critic": "Changes look good. No issues found. Approved. Task complete.",
            "narrator": f"The team completed the task: {task[:30]}... All agents reached consensus."
        }
        return responses.get(agent, "No response.")

    def format_history(self) -> str:
        """Format history for context."""
        if not self.history:
            return "No conversation yet."

        lines = []
        for turn in self.history[-6:]:
            speaker = turn["speaker"].upper()
            content = turn["content"]
            lines.append(f"[{speaker}]: {content}")

        return "\n".join(lines)

    def run_internal_debate(self, task: str, tool_executor=None) -> Dict:
        """
        Run the fast internal debate (text-only).

        Args:
            task: The task description
            tool_executor: Optional callable for tool execution (Builder uses this)

        Returns:
            Dict with history, artifacts, and final status
        """
        print("\n[BACKSTAGE] Starting internal debate...")
        print(f"[BACKSTAGE] Task: {task}\n")

        turn_order = ["planner", "researcher", "builder", "critic"]
        turn_idx = 0

        for i in range(self.max_internal_turns):
            agent = turn_order[turn_idx % len(turn_order)]

            # Get agent response (placeholder - real implementation uses Claude)
            response = self._simulate_agent_response(agent, task, self.format_history())

            # Record turn
            turn = {
                "turn": i + 1,
                "speaker": agent,
                "content": response,
                "timestamp": datetime.now().isoformat()
            }
            self.history.append(turn)

            print(f"  [{agent.upper()}]: {response[:80]}...")

            # Check for completion
            if "task complete" in response.lower() or "approved" in response.lower():
                print("\n[BACKSTAGE] Consensus reached!")
                break

            turn_idx += 1

        return {
            "history": self.history,
            "artifacts": self.artifacts,
            "status": "complete",
            "turns": len(self.history)
        }

    def deliver_summary(self, task: str) -> str:
        """
        Have the Narrator speak the summary to the user.
        This is the only spoken output in backstage mode.
        """
        narrator_config = self.registry["agents"]["narrator"]
        voice = narrator_config["voice"]

        # Generate summary
        summary_prompt = get_prompt(
            "narrator",
            full_history=self.format_history(),
            artifacts="\n".join(self.artifacts) if self.artifacts else "None",
            status="complete"
        )

        # Placeholder summary - real implementation calls Claude
        summary = f"The team completed your request. We analyzed the task, researched the codebase, implemented a solution, and validated the results. The implementation is ready for your review."

        print(f"\n[NARRATOR] Speaking summary...")
        self._speak(summary, voice)

        return summary

    def run(self, task: str, tool_executor=None) -> Dict:
        """
        Full backstage protocol execution.

        1. Run internal debate (fast, text-only)
        2. Deliver spoken summary

        Returns:
            Complete session results
        """
        # Phase 1: Internal debate
        debate_result = self.run_internal_debate(task, tool_executor)

        # Phase 2: Spoken summary
        summary = self.deliver_summary(task)

        return {
            **debate_result,
            "summary": summary,
            "mode": "backstage"
        }


def main():
    """Test the backstage protocol."""
    import argparse

    parser = argparse.ArgumentParser(description="Backstage Protocol Test")
    parser.add_argument("task", nargs="?", default="Create a hello world function",
                        help="Task for the team")

    args = parser.parse_args()

    protocol = BackstageProtocol()
    result = protocol.run(args.task)

    print("\n" + "="*60)
    print("BACKSTAGE PROTOCOL COMPLETE")
    print(f"Turns: {result['turns']}")
    print(f"Status: {result['status']}")
    print("="*60)


if __name__ == "__main__":
    main()
