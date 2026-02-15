#!/usr/bin/env python3
"""
Agent Team Director - The Silent Orchestrator

This is the conductor that manages turn-taking, enforces rules,
and coordinates the coding war-room team.

Usage:
    python director.py "Your task description here"
    python director.py --mode live "Task description"  # Agents speak out loud
    python director.py --mode backstage "Task description"  # Fast + summary only
"""

import json
import subprocess
import sys
import os
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent_prompts import get_prompt

# Paths
SCRIPT_DIR = Path(__file__).parent
VOICE_REGISTRY = SCRIPT_DIR / "voice_registry.json"
STATE_FILE = SCRIPT_DIR / "turn_state.json"
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
LOGS_DIR = SCRIPT_DIR / "logs"


class AgentRole(Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    BUILDER = "builder"
    CRITIC = "critic"
    NARRATOR = "narrator"


class SessionStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Turn:
    """A single turn in the conversation."""
    turn_number: int
    speaker: str
    content: str
    timestamp: str
    handoff_to: Optional[str] = None
    artifacts: List[str] = None
    tool_calls: List[Dict] = None

    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []
        if self.tool_calls is None:
            self.tool_calls = []


@dataclass
class Session:
    """A team collaboration session."""
    session_id: str
    task: str
    mode: str  # "backstage" or "live"
    status: str
    current_speaker: Optional[str]
    turn_number: int
    max_turns: int
    history: List[Dict]
    shared_context: Dict
    artifacts: List[str]
    consensus: Optional[str]
    pending_actions: List[Dict]
    user_approval_queue: List[Dict]
    started_at: str
    completed_at: Optional[str] = None

    @classmethod
    def new(cls, task: str, mode: str = "backstage", max_turns: int = 8):
        return cls(
            session_id=str(uuid.uuid4())[:8],
            task=task,
            mode=mode,
            status=SessionStatus.RUNNING.value,
            current_speaker=AgentRole.PLANNER.value,
            turn_number=0,
            max_turns=max_turns,
            history=[],
            shared_context={},
            artifacts=[],
            consensus=None,
            pending_actions=[],
            user_approval_queue=[],
            started_at=datetime.now().isoformat()
        )

    def to_dict(self):
        return asdict(self)

    def save(self):
        with open(STATE_FILE, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls):
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                data = json.load(f)
                return cls(**data)
        return None


class Director:
    """The silent orchestrator that runs the show."""

    def __init__(self, mode: str = "backstage"):
        self.mode = mode
        self.registry = self._load_registry()
        self.session: Optional[Session] = None

    def _load_registry(self) -> Dict:
        with open(VOICE_REGISTRY) as f:
            return json.load(f)

    def _speak(self, text: str, voice: str = "andrew"):
        """Play TTS audio."""
        try:
            subprocess.run(
                ["python3", str(VOICE_SCRIPT), text, voice],  # voice is positional
                check=True,
                capture_output=True,
                timeout=60
            )
        except Exception as e:
            print(f"[Voice Error] {e}")

    def _call_claude(self, prompt: str, agent_role: str) -> str:
        """
        Call Claude to get agent response.
        In production, this would use the Claude API or subprocess to claude CLI.
        For now, we'll use a simple subprocess call.
        """
        # Create a temp file with the prompt
        prompt_file = SCRIPT_DIR / f"temp_prompt_{agent_role}.txt"
        prompt_file.write_text(prompt)

        try:
            # Use claude CLI in non-interactive mode
            result = subprocess.run(
                ["claude", "--print", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(SCRIPT_DIR)
            )
            response = result.stdout.strip()
            if not response:
                response = f"[{agent_role}] No response generated."
            return response
        except subprocess.TimeoutExpired:
            return f"[{agent_role}] Response timeout."
        except Exception as e:
            return f"[{agent_role}] Error: {e}"
        finally:
            if prompt_file.exists():
                prompt_file.unlink()

    def _parse_handoff(self, response: str) -> Optional[str]:
        """Extract who the agent is handing off to."""
        response_lower = response.lower()

        handoff_map = {
            "planner": ["planner,", "planner.", "planner:"],
            "researcher": ["researcher,", "researcher.", "researcher:", "investigate"],
            "builder": ["builder,", "builder.", "builder:", "implement"],
            "critic": ["critic,", "critic.", "critic:", "validate", "review"],
        }

        for agent, triggers in handoff_map.items():
            for trigger in triggers:
                if trigger in response_lower:
                    return agent

        # Check for completion signals
        completion_signals = ["task complete", "approved", "consensus reached", "done"]
        for signal in completion_signals:
            if signal in response_lower:
                return "complete"

        return None

    def _format_history(self) -> str:
        """Format conversation history for prompts."""
        if not self.session or not self.session.history:
            return "No conversation yet."

        lines = []
        for turn in self.session.history[-6:]:  # Last 6 turns for context
            speaker = turn.get("speaker", "unknown").upper()
            content = turn.get("content", "")
            lines.append(f"[{speaker}]: {content}")

        return "\n".join(lines)

    def _decide_next_speaker(self, handoff: Optional[str]) -> str:
        """Decide who speaks next based on handoff and current state."""
        if handoff == "complete":
            return "narrator"  # Summarize and finish

        if handoff and handoff in [r.value for r in AgentRole]:
            return handoff

        # Default flow: planner -> researcher -> builder -> critic -> planner
        flow = ["planner", "researcher", "builder", "critic"]
        current = self.session.current_speaker

        if current in flow:
            idx = flow.index(current)
            return flow[(idx + 1) % len(flow)]

        return "planner"

    def _check_stop_conditions(self) -> tuple[bool, str]:
        """Check if we should stop the session."""
        if self.session.turn_number >= self.session.max_turns:
            return True, "max_turns_exceeded"

        if self.session.consensus:
            return True, "consensus_reached"

        # Check last response for completion
        if self.session.history:
            last = self.session.history[-1].get("content", "").lower()
            if "task complete" in last or "approved" in last:
                return True, "task_complete"

        return False, ""

    def run_turn(self) -> Dict:
        """Execute a single turn of the conversation."""
        agent = self.session.current_speaker
        agent_config = self.registry["agents"].get(agent, {})

        # Build the prompt
        prompt = get_prompt(
            agent,
            task=self.session.task,
            history=self._format_history(),
            context=json.dumps(self.session.shared_context, indent=2),
            plan=self.session.shared_context.get("plan", "No plan yet"),
            artifacts="\n".join(self.session.artifacts) if self.session.artifacts else "None yet"
        )

        # Get response from Claude
        print(f"\n[{agent.upper()}] thinking...")
        response = self._call_claude(prompt, agent)

        # In live mode, speak the response
        if self.mode == "live":
            voice = agent_config.get("voice", "andrew")
            self._speak(response, voice)

        # Parse handoff
        handoff = self._parse_handoff(response)

        # Record turn
        turn = {
            "turn_number": self.session.turn_number,
            "speaker": agent,
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "handoff_to": handoff
        }
        self.session.history.append(turn)
        self.session.turn_number += 1

        # Update speaker
        self.session.current_speaker = self._decide_next_speaker(handoff)

        # Save state
        self.session.save()

        return turn

    def run_session(self, task: str) -> Dict:
        """Run a complete team session."""
        self.session = Session.new(task, self.mode)
        self.session.save()

        print(f"\n{'='*60}")
        print(f"CODING WAR-ROOM SESSION: {self.session.session_id}")
        print(f"Mode: {self.mode}")
        print(f"Task: {task}")
        print(f"{'='*60}\n")

        # Main loop
        while True:
            turn = self.run_turn()
            print(f"[{turn['speaker'].upper()}]: {turn['content']}\n")

            # Check stop conditions
            should_stop, reason = self._check_stop_conditions()
            if should_stop:
                print(f"\n[DIRECTOR] Stopping: {reason}")
                break

            # If narrator just spoke, we're done
            if turn["speaker"] == "narrator":
                break

        # Final summary via narrator (in backstage mode)
        if self.mode == "backstage" and self.session.current_speaker != "narrator":
            self._run_narrator()

        self.session.status = SessionStatus.COMPLETE.value
        self.session.completed_at = datetime.now().isoformat()
        self.session.save()

        # Log the session
        self._save_log()

        return self.session.to_dict()

    def _run_narrator(self):
        """Have the narrator summarize for the user (always spoken)."""
        prompt = get_prompt(
            "narrator",
            full_history=self._format_history(),
            artifacts="\n".join(self.session.artifacts) if self.session.artifacts else "None",
            status=self.session.status
        )

        print("\n[NARRATOR] Preparing summary...")
        summary = self._call_claude(prompt, "narrator")

        print(f"\n[NARRATOR]: {summary}\n")

        # Always speak the narrator summary
        voice = self.registry["agents"]["narrator"]["voice"]
        self._speak(summary, voice)

        # Add to history
        self.session.history.append({
            "turn_number": self.session.turn_number,
            "speaker": "narrator",
            "content": summary,
            "timestamp": datetime.now().isoformat()
        })

    def _save_log(self):
        """Save session log to file."""
        LOGS_DIR.mkdir(exist_ok=True)
        log_file = LOGS_DIR / f"session_{self.session.session_id}.json"
        with open(log_file, 'w') as f:
            json.dump(self.session.to_dict(), f, indent=2)
        print(f"[DIRECTOR] Session logged to: {log_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Agent Team Director")
    parser.add_argument("task", nargs="?", help="The task for the team")
    parser.add_argument("--mode", choices=["backstage", "live"], default="backstage",
                        help="backstage=fast+summary, live=all agents speak")
    parser.add_argument("--max-turns", type=int, default=8,
                        help="Maximum turns before stopping")

    args = parser.parse_args()

    if not args.task:
        print("Usage: python director.py 'Your task here'")
        print("       python director.py --mode live 'Your task here'")
        sys.exit(1)

    director = Director(mode=args.mode)
    result = director.run_session(args.task)

    print(f"\n{'='*60}")
    print("SESSION COMPLETE")
    print(f"Turns: {result['turn_number']}")
    print(f"Status: {result['status']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
