#!/usr/bin/env python3
"""
Session API Handler - Listens for session commands and spawns agent teams.
=========================================================================
Bridges the dashboard UI controls to the autonomous agent system.
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict

import aiohttp
from aiohttp import web

# Server endpoint for session state
SERVER_URL = "http://127.0.0.1:8890"  # Use IPv4 explicitly
STATUS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/agent_status.json")

# Current session process
current_process: Optional[subprocess.Popen] = None
session_paused = False


class SessionRunner:
    """Manages agent team sessions based on dashboard commands."""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.paused = False
        self.task = None
        self.mode = None
        self.ws = None
        self.execution_enabled = False
        self.workspace = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/projects")

    async def connect_websocket(self):
        """Connect to server WebSocket for commands."""
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(f"{SERVER_URL}/ws") as ws:
                        self.ws = ws
                        print("✓ Connected to server WebSocket")

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                await self.handle_message(data)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                print(f"WebSocket error: {ws.exception()}")
                                break

            except Exception as e:
                print(f"Connection error: {e}")
                await asyncio.sleep(2)  # Retry

    async def handle_message(self, msg: Dict):
        """Handle incoming WebSocket messages."""
        msg_type = msg.get("type")

        if msg_type == "session_state":
            state = msg.get("data", {})
            await self.handle_session_state(state)

        elif msg_type == "execution_mode":
            data = msg.get("data", {})
            self.execution_enabled = data.get("enabled", False)
            if "workspace" in data:
                self.workspace = Path(data.get("workspace"))
            print(f"Execution mode: {'ENABLED' if self.execution_enabled else 'DISABLED'}")

    async def handle_session_state(self, state: Dict):
        """Handle session state changes from server."""
        # Update execution settings if provided
        if "execution_enabled" in state:
            self.execution_enabled = state.get("execution_enabled", False)
        if "workspace" in state:
            self.workspace = Path(state.get("workspace", self.workspace))

        if state.get("active") and not self.process:
            # Start new session
            self.task = state.get("task")
            self.mode = state.get("mode", "work")
            self.start_agent_team()

        elif not state.get("active") and self.process:
            # Stop session
            self.stop_agent_team()

        elif state.get("paused") != self.paused:
            # Pause/resume
            self.paused = state.get("paused", False)
            self.handle_pause()

    def start_agent_team(self):
        """Start the agent team process."""
        if self.process:
            print("Session already running")
            return

        exec_status = "ENABLED" if self.execution_enabled else "DISABLED"
        print(f"\n{'='*60}")
        print(f"  Starting Agent Team Session")
        print(f"  Task: {self.task}")
        print(f"  Mode: {self.mode}")
        print(f"  Execution: {exec_status}")
        print(f"  Workspace: {self.workspace}")
        print(f"{'='*60}\n")

        # Determine which script to run based on mode
        agent_dir = Path(__file__).parent

        if self.mode == "parallel":
            # Run parallel build demo
            script = agent_dir / "parallel_demo.py"
            if not script.exists():
                # Create a simple parallel demo script
                self.create_parallel_demo(script)
        else:
            # Use run_team.py if it exists, otherwise autonomous_agents.py
            script = agent_dir / "run_team.py"
            if not script.exists():
                script = agent_dir / "autonomous_agents.py"

        # Build command with execution mode
        cmd = [
            sys.executable,
            str(script),
            "--mode", self.mode,
            "--task", self.task,
            "--workspace", str(self.workspace),
        ]

        # Add execution flag
        if self.execution_enabled:
            cmd.append("--execute")
        else:
            cmd.append("--simulate")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(agent_dir)
            )

            # Start output monitor thread
            threading.Thread(
                target=self.monitor_output,
                daemon=True
            ).start()

            print(f"✓ Agent team started (PID: {self.process.pid})")

        except Exception as e:
            print(f"Failed to start agent team: {e}")
            self.process = None

    def stop_agent_team(self):
        """Stop the agent team process."""
        if not self.process:
            return

        print("\n⏹ Stopping agent team...")

        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        except Exception as e:
            print(f"Error stopping process: {e}")

        self.process = None
        self.task = None
        self.mode = None
        print("✓ Agent team stopped")

    def handle_pause(self):
        """Handle pause/resume."""
        if self.paused:
            print("\n⏸ Session paused")
            # Could send SIGSTOP on Unix, but we'll use a simpler approach
            # Just update status file to indicate paused
            self.update_status({"paused": True})
        else:
            print("\n▶ Session resumed")
            self.update_status({"paused": False})

    def update_status(self, update: Dict):
        """Update the status file with additional info."""
        try:
            status = {}
            if STATUS_FILE.exists():
                with open(STATUS_FILE) as f:
                    status = json.load(f)

            status.update(update)
            status["timestamp"] = time.time()

            with open(STATUS_FILE, "w") as f:
                json.dump(status, f)
        except Exception as e:
            print(f"Status update error: {e}")

    def monitor_output(self):
        """Monitor agent team process output."""
        if not self.process:
            return

        try:
            for line in self.process.stdout:
                print(line.rstrip())
        except Exception as e:
            print(f"Output monitor error: {e}")

        # Process ended
        if self.process:
            self.process.wait()
            print(f"\nAgent team process ended (code: {self.process.returncode})")
            self.process = None

    def create_parallel_demo(self, script_path: Path):
        """Create a parallel build demo script."""
        script_content = '''#!/usr/bin/env python3
"""Parallel Build Demo - Run multiple builders simultaneously."""

import sys
from autonomous_agents import AutonomousTeam

def main():
    if len(sys.argv) < 3:
        print("Usage: parallel_demo.py parallel <task>")
        return

    task = sys.argv[2]

    team = AutonomousTeam()

    # Split task into builder-specific parts
    tasks = {
        "builder": f"Backend implementation for: {task}",
        "builder-frontend": f"Frontend UI for: {task}",
        "builder-infra": f"Deployment setup for: {task}"
    }

    # Run parallel build
    results = team.parallel_build(tasks)

    # Have narrator summarize
    summary_context = f"Summarize the parallel build results for: {task}"
    team.narrator.respond(summary_context, team.team_history)

if __name__ == "__main__":
    main()
'''
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        print(f"Created parallel demo script: {script_path}")


async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  Session API Handler")
    print("  Listening for dashboard commands...")
    print("=" * 60 + "\n")

    runner = SessionRunner()
    await runner.connect_websocket()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession handler stopped.")
