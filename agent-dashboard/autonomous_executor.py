#!/usr/bin/env python3
"""
Autonomous Agent Executor
=========================
The BRAIN that makes agents actually DO work.

This connects:
- Triggers (events that wake agents up)
- Agent definitions (what they know how to do)
- Claude API (the intelligence)
- MCP servers (the hands that do real work)

Author: Weber Gouin
"""

import asyncio
import json
import os
import sys
import subprocess
import sqlite3
import hashlib
import anthropic
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
import logging
import re

# ============================================
# CONFIGURATION
# ============================================

CONFIG = {
    # Paths
    "agents_dir": Path("/home/weber/.claude/agents"),
    "live_state_file": Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json"),
    "task_db": Path("/mnt/d/_CLAUDE-TOOLS/autonomous-agent/queues/tasks.db"),
    "memory_db": Path("/mnt/d/_CLAUDE-TOOLS/claude-memory/memories.db"),
    "log_file": Path("/mnt/d/_CLAUDE-TOOLS/agent-dashboard/executor.log"),

    # Timing
    "poll_interval": 30,  # Check for work every 30 seconds
    "max_concurrent_agents": 3,  # Don't overload the system

    # Claude API
    "model": "claude-sonnet-4-20250514",  # Fast and capable
    "max_tokens": 4096,
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("executor")

# ============================================
# TRIGGER DEFINITIONS
# ============================================

@dataclass
class Trigger:
    """A condition that wakes up agents."""
    name: str
    description: str
    check_fn: str  # Name of function to check if triggered
    agents: List[str]  # Agents to wake up
    cooldown_minutes: int = 15  # Don't re-trigger too often
    last_triggered: Optional[datetime] = None
    enabled: bool = True

# Pre-defined autonomous triggers
AUTONOMOUS_TRIGGERS = [
    Trigger(
        name="revit_project_opened",
        description="When a Revit project is opened, check model quality",
        check_fn="check_revit_opened",
        agents=["bim-validator", "qc-agent"],
        cooldown_minutes=30
    ),
    Trigger(
        name="new_sheet_created",
        description="When new sheets are detected, validate layout",
        check_fn="check_new_sheets",
        agents=["sheet-layout", "cd-reviewer"],
        cooldown_minutes=15
    ),
    Trigger(
        name="morning_briefing",
        description="Every morning, prepare project status",
        check_fn="check_morning_time",
        agents=["orchestrator", "schedule-builder"],
        cooldown_minutes=720  # Once per 12 hours
    ),
    Trigger(
        name="idle_detection",
        description="When system is idle, run background tasks",
        check_fn="check_system_idle",
        agents=["learning-agent"],
        cooldown_minutes=60
    ),
    Trigger(
        name="pending_tasks",
        description="When tasks are in queue, assign to agents",
        check_fn="check_pending_tasks",
        agents=["orchestrator"],
        cooldown_minutes=1
    ),
]

# ============================================
# TRIGGER CHECK FUNCTIONS
# ============================================

class TriggerChecker:
    """Checks if triggers should fire."""

    def __init__(self):
        self.last_revit_project = None
        self.last_sheet_count = 0
        self.state_cache = {}

    def get_live_state(self) -> dict:
        """Load current system state."""
        try:
            if CONFIG["live_state_file"].exists():
                return json.loads(CONFIG["live_state_file"].read_text())
        except:
            pass
        return {}

    def check_revit_opened(self) -> Optional[dict]:
        """Check if Revit project changed."""
        state = self.get_live_state()
        apps = state.get("applications", [])

        for app in apps:
            if app.get("ProcessName") == "Revit":
                title = app.get("MainWindowTitle", "")
                # Extract project name
                match = re.search(r'\[(.+?) -', title)
                if match:
                    project = match.group(1)
                    if project != self.last_revit_project:
                        self.last_revit_project = project
                        return {
                            "project": project,
                            "title": title,
                            "context": f"Revit project '{project}' was just opened"
                        }
        return None

    def check_new_sheets(self) -> Optional[dict]:
        """Check for new sheets (would need Revit MCP)."""
        # This would query Revit via MCP - placeholder
        return None

    def check_morning_time(self) -> Optional[dict]:
        """Check if it's morning briefing time."""
        now = datetime.now()
        if 7 <= now.hour < 8:
            return {
                "time": now.strftime("%H:%M"),
                "context": "Morning briefing time - prepare daily status"
            }
        return None

    def check_system_idle(self) -> Optional[dict]:
        """Check if system is idle (low CPU, no active work)."""
        state = self.get_live_state()
        cpu = state.get("system", {}).get("cpu_percent", 100)

        if cpu < 20:
            return {
                "cpu_percent": cpu,
                "context": "System is idle - good time for background tasks"
            }
        return None

    def check_pending_tasks(self) -> Optional[dict]:
        """Check if there are pending tasks in queue."""
        try:
            conn = sqlite3.connect(str(CONFIG["task_db"]))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            count = cur.fetchone()[0]
            conn.close()

            if count > 0:
                return {
                    "pending_count": count,
                    "context": f"{count} tasks waiting in queue"
                }
        except:
            pass
        return None

# ============================================
# AGENT EXECUTOR
# ============================================

class AgentExecutor:
    """Executes agent definitions using Claude API."""

    def __init__(self):
        self.client = None
        self.agent_definitions: Dict[str, str] = {}
        self._load_agents()
        self._init_client()

    def _init_client(self):
        """Initialize Claude API client."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info("Claude API client initialized")
        else:
            logger.warning("No ANTHROPIC_API_KEY found - will use CLI fallback")

    def _load_agents(self):
        """Load all agent definitions."""
        if not CONFIG["agents_dir"].exists():
            return

        for file in CONFIG["agents_dir"].glob("*.md"):
            name = file.stem
            content = file.read_text()
            self.agent_definitions[name] = content

        logger.info(f"Loaded {len(self.agent_definitions)} agent definitions")

    def get_agent_prompt(self, agent_name: str) -> Optional[str]:
        """Get the system prompt for an agent."""
        return self.agent_definitions.get(agent_name)

    async def execute_agent(self, agent_name: str, task: str, context: dict = None) -> dict:
        """Execute an agent with a task."""

        agent_prompt = self.get_agent_prompt(agent_name)
        if not agent_prompt:
            return {"error": f"Agent '{agent_name}' not found"}

        # Build the full prompt
        system_prompt = f"""You are the {agent_name} agent.

{agent_prompt}

Current context:
{json.dumps(context or {}, indent=2)}

Execute the following task and report your findings/actions."""

        user_message = task

        logger.info(f"Executing agent '{agent_name}' for task: {task[:50]}...")

        # Try Claude API first
        if self.client:
            try:
                response = self.client.messages.create(
                    model=CONFIG["model"],
                    max_tokens=CONFIG["max_tokens"],
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                )

                result = response.content[0].text
                logger.info(f"Agent '{agent_name}' completed successfully")

                return {
                    "agent": agent_name,
                    "task": task,
                    "result": result,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"API error for agent '{agent_name}': {e}")
                return {"error": str(e), "agent": agent_name}

        # Fallback to CLI
        else:
            return await self._execute_via_cli(agent_name, system_prompt, user_message)

    async def _execute_via_cli(self, agent_name: str, system: str, message: str) -> dict:
        """Execute via claude CLI as fallback."""
        try:
            # Use claude CLI in print mode
            result = subprocess.run(
                ["claude", "-p", message],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "CLAUDE_SYSTEM_PROMPT": system}
            )

            if result.returncode == 0:
                return {
                    "agent": agent_name,
                    "result": result.stdout,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"error": result.stderr, "agent": agent_name}

        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out", "agent": agent_name}
        except Exception as e:
            return {"error": str(e), "agent": agent_name}

# ============================================
# AUTONOMOUS ORCHESTRATOR
# ============================================

class AutonomousOrchestrator:
    """The main brain that coordinates everything."""

    def __init__(self):
        self.trigger_checker = TriggerChecker()
        self.executor = AgentExecutor()
        self.triggers = {t.name: t for t in AUTONOMOUS_TRIGGERS}
        self.running = False
        self.active_agents: Dict[str, asyncio.Task] = {}

        # Status tracking for dashboard
        self.status = {
            "running": False,
            "last_check": None,
            "triggers_fired": [],
            "agents_active": [],
            "tasks_completed": 0
        }

    def check_trigger(self, trigger: Trigger) -> Optional[dict]:
        """Check if a trigger should fire."""
        if not trigger.enabled:
            return None

        # Check cooldown
        if trigger.last_triggered:
            elapsed = datetime.now() - trigger.last_triggered
            if elapsed < timedelta(minutes=trigger.cooldown_minutes):
                return None

        # Run the check function
        check_fn = getattr(self.trigger_checker, trigger.check_fn, None)
        if check_fn:
            return check_fn()

        return None

    async def process_trigger(self, trigger: Trigger, context: dict):
        """Process a fired trigger by activating agents."""
        logger.info(f"🔔 Trigger fired: {trigger.name}")
        trigger.last_triggered = datetime.now()

        self.status["triggers_fired"].append({
            "trigger": trigger.name,
            "time": datetime.now().isoformat(),
            "context": context
        })

        # Wake up the assigned agents
        for agent_name in trigger.agents:
            if agent_name not in self.active_agents:
                task = asyncio.create_task(
                    self.run_agent(agent_name, trigger.description, context)
                )
                self.active_agents[agent_name] = task

    async def run_agent(self, agent_name: str, task: str, context: dict):
        """Run an agent and handle the result."""
        self.status["agents_active"].append(agent_name)

        try:
            result = await self.executor.execute_agent(agent_name, task, context)

            # Log the result
            logger.info(f"Agent '{agent_name}' result: {result.get('status', 'unknown')}")

            # Store in task database
            self._store_result(agent_name, task, result)

            self.status["tasks_completed"] += 1

        except Exception as e:
            logger.error(f"Agent '{agent_name}' failed: {e}")

        finally:
            self.status["agents_active"].remove(agent_name)
            if agent_name in self.active_agents:
                del self.active_agents[agent_name]

    def _store_result(self, agent_name: str, task: str, result: dict):
        """Store execution result in database."""
        try:
            conn = sqlite3.connect(str(CONFIG["task_db"]))
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO tasks (title, description, priority, status, created_at, completed_at, result)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"[{agent_name}] {task[:100]}",
                json.dumps(result),
                5,
                result.get("status", "completed"),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                result.get("result", "")[:1000]
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to store result: {e}")

    async def check_manual_tasks(self):
        """Check for manually queued tasks."""
        try:
            conn = sqlite3.connect(str(CONFIG["task_db"]))
            cur = conn.cursor()

            cur.execute("""
                SELECT id, title, description FROM tasks
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 5
            """)

            tasks = cur.fetchall()

            for task_id, title, description in tasks:
                # Mark as in progress
                cur.execute(
                    "UPDATE tasks SET status = 'running', started_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), task_id)
                )
                conn.commit()

                # Determine which agent should handle it
                agent_name = self._route_task(title, description)

                # Execute
                context = {"task_id": task_id, "source": "manual_queue"}
                asyncio.create_task(
                    self.run_agent(agent_name, title, context)
                )

            conn.close()

        except Exception as e:
            logger.error(f"Error checking manual tasks: {e}")

    def _route_task(self, title: str, description: str) -> str:
        """Determine which agent should handle a task."""
        text = f"{title} {description}".lower()

        # Simple keyword routing
        if any(k in text for k in ["revit", "model", "bim", "element"]):
            return "revit-builder"
        elif any(k in text for k in ["sheet", "layout", "viewport"]):
            return "sheet-layout"
        elif any(k in text for k in ["quality", "qc", "check", "review"]):
            return "qc-agent"
        elif any(k in text for k in ["schedule", "report"]):
            return "schedule-builder"
        elif any(k in text for k in ["annotate", "dimension", "tag"]):
            return "annotation-agent"
        else:
            return "orchestrator"  # Default to orchestrator

    async def run_loop(self):
        """Main autonomous loop."""
        self.running = True
        self.status["running"] = True
        logger.info("🚀 Autonomous Orchestrator starting...")

        while self.running:
            try:
                self.status["last_check"] = datetime.now().isoformat()

                # Check all triggers
                for trigger in self.triggers.values():
                    # Don't exceed max concurrent agents
                    if len(self.active_agents) >= CONFIG["max_concurrent_agents"]:
                        break

                    context = self.check_trigger(trigger)
                    if context:
                        await self.process_trigger(trigger, context)

                # Also check manual task queue
                await self.check_manual_tasks()

                # Wait before next check
                await asyncio.sleep(CONFIG["poll_interval"])

            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(5)

        logger.info("Autonomous Orchestrator stopped")

    def stop(self):
        """Stop the orchestrator."""
        self.running = False
        self.status["running"] = False

# ============================================
# MAIN
# ============================================

orchestrator = AutonomousOrchestrator()

async def main():
    """Main entry point."""
    print("=" * 60)
    print("🤖 AUTONOMOUS AGENT EXECUTOR")
    print("=" * 60)
    print(f"📊 Loaded {len(orchestrator.executor.agent_definitions)} agents")
    print(f"🔔 {len(orchestrator.triggers)} triggers configured")
    print(f"⏱️  Checking every {CONFIG['poll_interval']} seconds")
    print("=" * 60)

    # Check for API key
    if not orchestrator.executor.client:
        print("\n⚠️  No ANTHROPIC_API_KEY found!")
        print("   Set it with: export ANTHROPIC_API_KEY=your-key")
        print("   Or add to ~/.bashrc")
        print("\n   Without API key, agents cannot execute autonomously.")
        return

    await orchestrator.run_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        orchestrator.stop()
