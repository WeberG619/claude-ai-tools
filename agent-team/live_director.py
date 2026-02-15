#!/usr/bin/env python3
"""
Live Director - Real Claude-powered agent orchestration with recording.

This director makes actual Claude API calls and coordinates real work
between agents. Each agent has access to tools and can produce artifacts.

Usage:
    python live_director.py "Build an Agent Command Center dashboard"
"""

import json
import subprocess
import sys
import os
import time
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import re

sys.path.insert(0, str(Path(__file__).parent))

from agent_prompts import get_prompt
from recording.record_session import SessionRecorder

# Paths
SCRIPT_DIR = Path(__file__).parent
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
VOICE_REGISTRY = SCRIPT_DIR / "voice_registry.json"
PROJECT_DIR = SCRIPT_DIR / "projects"


@dataclass
class AgentConfig:
    name: str
    voice: str
    role: str
    style: str
    can_write_code: bool = False
    can_run_commands: bool = False


class LiveDirector:
    """
    Production director that coordinates real Claude-powered agents.
    """

    AGENTS = {
        "planner": AgentConfig(
            name="planner",
            voice="andrew",
            role="Planner",
            style="methodical and strategic",
            can_write_code=False,
            can_run_commands=False
        ),
        "researcher": AgentConfig(
            name="researcher",
            voice="guy",
            role="Researcher",
            style="thorough and informative",
            can_write_code=False,
            can_run_commands=True  # Can explore files
        ),
        "builder": AgentConfig(
            name="builder",
            voice="christopher",
            role="Builder",
            style="direct and action-oriented",
            can_write_code=True,
            can_run_commands=True
        ),
        "critic": AgentConfig(
            name="critic",
            voice="eric",
            role="Critic",
            style="analytical and precise",
            can_write_code=False,
            can_run_commands=True  # Can run tests
        ),
        "narrator": AgentConfig(
            name="narrator",
            voice="jenny",
            role="Narrator",
            style="warm and professional",
            can_write_code=False,
            can_run_commands=False
        )
    }

    def __init__(self, project_name: str, project_dir: Optional[Path] = None):
        self.project_name = project_name
        self.project_dir = project_dir or PROJECT_DIR / self._sanitize_name(project_name)
        self.project_dir.mkdir(parents=True, exist_ok=True)

        self.recorder = SessionRecorder(project_name)
        self.history: List[Dict] = []
        self.artifacts: List[str] = []
        self.shared_context: Dict = {
            "project_name": project_name,
            "project_dir": str(self.project_dir),
            "files_created": [],
            "current_phase": "planning",
            "issues": [],
            "decisions": []
        }

        self.turn_count = 0
        self.max_turns = 50  # Allow longer sessions

        # Load voice registry
        with open(VOICE_REGISTRY) as f:
            self.voice_registry = json.load(f)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for directory."""
        return re.sub(r'[^\w\-]', '_', name.lower())[:50]

    def _speak(self, text: str, voice: str) -> bool:
        """Speak text and return success status."""
        try:
            # Also save audio for recording
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            audio_file = self.recorder.session_dir / f"audio_{timestamp}.mp3"

            result = subprocess.run(
                ["python3", str(VOICE_SCRIPT), text, voice],
                capture_output=True,
                timeout=120
            )

            return result.returncode == 0
        except Exception as e:
            print(f"[Voice Error] {e}")
            return False

    def _call_claude(self, prompt: str, agent_name: str) -> str:
        """
        Call Claude CLI to get agent response.
        Uses --print flag for non-interactive mode.
        """
        try:
            # Create temp file with prompt
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name

            # Call Claude CLI
            result = subprocess.run(
                ["claude", "--print", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(self.project_dir)
            )

            response = result.stdout.strip()

            # Clean up
            os.unlink(prompt_file)

            if not response:
                return f"[{agent_name}] I need more context to proceed."

            return response

        except subprocess.TimeoutExpired:
            return f"[{agent_name}] Response timed out. Let me try a simpler approach."
        except Exception as e:
            return f"[{agent_name}] Encountered an issue: {str(e)[:100]}"

    def _build_agent_prompt(self, agent: AgentConfig, task_context: str) -> str:
        """Build the full prompt for an agent."""
        history_text = self._format_history()

        base_prompt = f"""You are {agent.role} in a coding team working on: {self.project_name}

YOUR VOICE/STYLE: {agent.style}
YOUR CAPABILITIES:
- Can write code: {agent.can_write_code}
- Can run commands: {agent.can_run_commands}

PROJECT DIRECTORY: {self.project_dir}

TEAM MEMBERS:
- Planner (Andrew): Breaks down tasks, defines strategy
- Researcher (Guy): Gathers info, explores codebase
- Builder (Christopher): Writes code, creates files
- Critic (Eric): Reviews, finds bugs, validates

CONVERSATION SO FAR:
{history_text}

SHARED CONTEXT:
{json.dumps(self.shared_context, indent=2)}

CURRENT TASK/CONTEXT:
{task_context}

RULES:
1. Keep response to 3-4 sentences MAX (this will be spoken aloud)
2. End with a clear handoff: "[AgentName], [action]" (e.g., "Builder, implement the header component")
3. If you find an issue, say "Issue found: [description]. [Agent], please address this."
4. If blocked, say "Blocked: [reason]. Need [what you need]."
5. When your part is done, say "My part complete. [NextAgent], continue."
6. If all done, say "Task complete. Narrator, summarize."

Your response ({agent.role}, speaking as {agent.voice}):"""

        return base_prompt

    def _format_history(self, last_n: int = 10) -> str:
        """Format conversation history."""
        if not self.history:
            return "No conversation yet."

        recent = self.history[-last_n:]
        lines = []
        for turn in recent:
            agent = turn["agent"].upper()
            content = turn["content"][:200]  # Truncate for context
            lines.append(f"[{agent}]: {content}")

        return "\n".join(lines)

    def _parse_handoff(self, response: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse who to hand off to and what action.
        Returns (next_agent, action) or (None, None) if complete.
        """
        response_lower = response.lower()

        # Check for completion
        if "task complete" in response_lower or "all done" in response_lower:
            return ("narrator", "summarize")

        # Check for specific handoffs
        handoff_patterns = [
            (r"planner[,.]?\s+(\w+)", "planner"),
            (r"researcher[,.]?\s+(\w+)", "researcher"),
            (r"builder[,.]?\s+(\w+)", "builder"),
            (r"critic[,.]?\s+(\w+)", "critic"),
            (r"narrator[,.]?\s+(\w+)", "narrator"),
            (r"guy[,.]?\s+(\w+)", "researcher"),
            (r"christopher[,.]?\s+(\w+)", "builder"),
            (r"eric[,.]?\s+(\w+)", "critic"),
            (r"andrew[,.]?\s+(\w+)", "planner"),
            (r"jenny[,.]?\s+(\w+)", "narrator"),
        ]

        for pattern, agent in handoff_patterns:
            match = re.search(pattern, response_lower)
            if match:
                action = match.group(1) if match.groups() else "continue"
                return (agent, action)

        # Default flow if no explicit handoff
        return (None, None)

    def _detect_issue(self, response: str) -> Optional[str]:
        """Detect if an issue was reported."""
        patterns = [
            r"issue found:?\s*(.+?)(?:\.|$)",
            r"problem:?\s*(.+?)(?:\.|$)",
            r"bug:?\s*(.+?)(?:\.|$)",
            r"error:?\s*(.+?)(?:\.|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, response.lower())
            if match:
                return match.group(1).strip()

        return None

    def run_turn(self, agent_name: str, context: str = "") -> Dict:
        """Execute a single agent turn."""
        agent = self.AGENTS[agent_name]
        self.turn_count += 1

        print(f"\n{'─'*50}")
        print(f"🎤 Turn {self.turn_count}: {agent.role.upper()} ({agent.voice})")
        print(f"{'─'*50}")

        # Build prompt
        prompt = self._build_agent_prompt(agent, context)

        # Get Claude response
        print(f"[{agent.role}] thinking...")
        response = self._call_claude(prompt, agent_name)

        # Truncate for speaking (max ~30 seconds of speech)
        spoken_response = response[:500] if len(response) > 500 else response

        print(f"\n{spoken_response}\n")

        # Speak the response
        self._speak(spoken_response, agent.voice)

        # Log to recorder
        self.recorder.log_turn(agent_name, response, agent.voice)

        # Check for issues
        issue = self._detect_issue(response)
        if issue:
            self.shared_context["issues"].append({
                "found_by": agent_name,
                "description": issue,
                "turn": self.turn_count
            })
            self.recorder.log_issue(issue, "pending")

        # Parse handoff
        next_agent, action = self._parse_handoff(response)

        # Record turn
        turn = {
            "turn": self.turn_count,
            "agent": agent_name,
            "content": response,
            "voice": agent.voice,
            "timestamp": datetime.now().isoformat(),
            "handoff_to": next_agent,
            "action": action,
            "issue": issue
        }
        self.history.append(turn)

        return turn

    def run_session(self, initial_task: str) -> Dict:
        """Run a full agent session."""
        self.recorder.start()

        # Opening announcement
        opening = f"Starting coding session for: {self.project_name}. The team is ready."
        print(f"\n🎬 {opening}")
        self._speak(opening, "jenny")

        # Start with planner
        current_agent = "planner"
        current_context = initial_task

        while self.turn_count < self.max_turns:
            turn = self.run_turn(current_agent, current_context)

            # Check if done
            if turn["handoff_to"] == "narrator" and current_agent == "narrator":
                break

            # Get next agent
            if turn["handoff_to"]:
                current_agent = turn["handoff_to"]
                current_context = turn.get("action", "continue")
            else:
                # Default progression
                flow = ["planner", "researcher", "builder", "critic"]
                if current_agent in flow:
                    idx = flow.index(current_agent)
                    current_agent = flow[(idx + 1) % len(flow)]
                else:
                    current_agent = "planner"
                current_context = "continue from previous"

            # If we've been going a while, check with narrator
            if self.turn_count > 0 and self.turn_count % 8 == 0:
                # Periodic summary
                self.run_turn("narrator", "Provide a brief progress update")

        # Final narration
        if current_agent != "narrator":
            self.run_turn("narrator", "Summarize the complete session and outcomes")

        # Finish recording
        session_dir = self.recorder.finish("complete")

        return {
            "session_id": self.recorder.session_id,
            "project_name": self.project_name,
            "project_dir": str(self.project_dir),
            "turns": self.turn_count,
            "artifacts": self.artifacts,
            "recording_dir": str(session_dir),
            "history": self.history
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Live Director - Real Agent Sessions")
    parser.add_argument("project", help="Project description")
    parser.add_argument("--max-turns", type=int, default=30,
                        help="Maximum turns (default: 30)")

    args = parser.parse_args()

    director = LiveDirector(args.project)
    director.max_turns = args.max_turns

    result = director.run_session(args.project)

    print(f"\n✅ Session complete!")
    print(f"📁 Recording: {result['recording_dir']}")
    print(f"💬 Total turns: {result['turns']}")


if __name__ == "__main__":
    main()
