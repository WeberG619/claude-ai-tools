#!/usr/bin/env python3
"""
Claude CLI Agent Executor
=========================
Runs agents through Claude Code CLI - uses your Max subscription.
No API key needed - same Claude you're already using.

Author: Weber Gouin
"""

import asyncio
import json
import os
import sys
import subprocess
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import re
import threading
import queue

# ============================================
# CONFIGURATION
# ============================================

CONFIG = {
    "agents_dir": Path("/home/weber/.claude/agents"),
    "live_state_file": Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json"),
    "task_db": Path("/mnt/d/_CLAUDE-TOOLS/autonomous-agent/queues/tasks.db"),
    "status_file": Path("/mnt/d/_CLAUDE-TOOLS/agent-dashboard/executor_status.json"),
    "log_file": Path("/mnt/d/_CLAUDE-TOOLS/agent-dashboard/executor.log"),

    "poll_interval": 30,
    "max_concurrent": 2,  # Don't overload - Claude CLI is heavy
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cli_executor")

# ============================================
# STATUS BROADCASTER
# ============================================

class StatusBroadcaster:
    """Broadcasts agent status to the dashboard."""

    def __init__(self):
        self.status = {
            "running": False,
            "last_update": None,
            "active_agents": {},
            "completed_tasks": [],
            "pending_triggers": []
        }

    def update(self):
        """Write status to file for dashboard to read."""
        self.status["last_update"] = datetime.now().isoformat()
        CONFIG["status_file"].write_text(json.dumps(self.status, indent=2))

    def agent_started(self, agent_name: str, task: str):
        self.status["active_agents"][agent_name] = {
            "task": task,
            "started": datetime.now().isoformat(),
            "status": "working"
        }
        self.update()

    def agent_progress(self, agent_name: str, progress: str):
        if agent_name in self.status["active_agents"]:
            self.status["active_agents"][agent_name]["progress"] = progress
            self.update()

    def agent_completed(self, agent_name: str, result: str):
        if agent_name in self.status["active_agents"]:
            completed = self.status["active_agents"].pop(agent_name)
            completed["completed"] = datetime.now().isoformat()
            completed["result"] = result[:500]
            self.status["completed_tasks"].insert(0, completed)
            # Keep only last 20
            self.status["completed_tasks"] = self.status["completed_tasks"][:20]
            self.update()

    def trigger_fired(self, trigger_name: str, context: dict):
        self.status["pending_triggers"].append({
            "trigger": trigger_name,
            "time": datetime.now().isoformat(),
            "context": context
        })
        self.update()

# ============================================
# CLAUDE CLI EXECUTOR
# ============================================

class ClaudeCliExecutor:
    """Executes agents via Claude Code CLI."""

    def __init__(self, broadcaster: StatusBroadcaster):
        self.broadcaster = broadcaster
        self.agent_prompts: Dict[str, str] = {}
        self._load_agents()

    def _load_agents(self):
        """Load agent definition files."""
        if not CONFIG["agents_dir"].exists():
            return

        for file in CONFIG["agents_dir"].glob("*.md"):
            name = file.stem
            self.agent_prompts[name] = file.read_text()

        logger.info(f"Loaded {len(self.agent_prompts)} agent definitions")

    def execute_sync(self, agent_name: str, task: str, context: dict = None) -> str:
        """
        Execute an agent using Claude CLI.

        Uses `claude -p` (print mode) for non-interactive execution.
        """
        agent_prompt = self.agent_prompts.get(agent_name, "")

        # Build the full prompt
        full_prompt = f"""You are acting as the '{agent_name}' agent.

## Agent Definition:
{agent_prompt[:2000]}

## Current Context:
{json.dumps(context or {}, indent=2)}

## Task:
{task}

Execute this task. Be concise and actionable. Report what you did or found."""

        self.broadcaster.agent_started(agent_name, task)
        logger.info(f"🤖 Starting agent '{agent_name}': {task[:50]}...")

        try:
            # Use claude CLI in print mode
            result = subprocess.run(
                ["claude", "-p", full_prompt],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd="/mnt/d"  # Working directory
            )

            output = result.stdout if result.returncode == 0 else result.stderr
            self.broadcaster.agent_completed(agent_name, output)
            logger.info(f"✅ Agent '{agent_name}' completed")
            return output

        except subprocess.TimeoutExpired:
            error = "Agent timed out after 5 minutes"
            self.broadcaster.agent_completed(agent_name, error)
            logger.error(f"⏰ Agent '{agent_name}' timed out")
            return error

        except FileNotFoundError:
            error = "Claude CLI not found. Make sure 'claude' is in PATH."
            self.broadcaster.agent_completed(agent_name, error)
            logger.error(error)
            return error

        except Exception as e:
            error = f"Error: {str(e)}"
            self.broadcaster.agent_completed(agent_name, error)
            logger.error(f"❌ Agent '{agent_name}' error: {e}")
            return error

    async def execute_async(self, agent_name: str, task: str, context: dict = None) -> str:
        """Async wrapper for CLI execution."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.execute_sync,
            agent_name, task, context
        )

# ============================================
# TRIGGER SYSTEM
# ============================================

class TriggerSystem:
    """Watches for conditions that should wake up agents."""

    def __init__(self):
        self.last_state_hash = None
        self.last_revit_project = None
        self.morning_briefing_done = False
        self.cooldowns: Dict[str, datetime] = {}

    def get_live_state(self) -> dict:
        try:
            return json.loads(CONFIG["live_state_file"].read_text())
        except:
            return {}

    def check_cooldown(self, trigger_name: str, minutes: int) -> bool:
        """Check if trigger is on cooldown."""
        if trigger_name in self.cooldowns:
            elapsed = datetime.now() - self.cooldowns[trigger_name]
            if elapsed < timedelta(minutes=minutes):
                return True  # Still on cooldown
        return False

    def set_cooldown(self, trigger_name: str):
        """Set cooldown for a trigger."""
        self.cooldowns[trigger_name] = datetime.now()

    def check_all_triggers(self) -> List[dict]:
        """Check all triggers and return list of fired ones."""
        fired = []
        state = self.get_live_state()

        # 1. Revit project changed
        if not self.check_cooldown("revit_project", 30):
            apps = state.get("applications", [])
            for app in apps:
                if app.get("ProcessName") == "Revit":
                    title = app.get("MainWindowTitle", "")
                    match = re.search(r'\[(.+?) -', title)
                    if match:
                        project = match.group(1)
                        if project != self.last_revit_project:
                            self.last_revit_project = project
                            self.set_cooldown("revit_project")
                            fired.append({
                                "trigger": "revit_project_changed",
                                "agents": ["bim-validator"],
                                "task": f"Quick health check on project: {project}",
                                "context": {"project": project}
                            })

        # 2. Morning briefing (7-8 AM)
        now = datetime.now()
        if 7 <= now.hour < 8 and not self.morning_briefing_done:
            if not self.check_cooldown("morning", 720):
                self.morning_briefing_done = True
                self.set_cooldown("morning")
                fired.append({
                    "trigger": "morning_briefing",
                    "agents": ["orchestrator"],
                    "task": "Prepare morning status briefing",
                    "context": {"time": now.strftime("%H:%M")}
                })
        elif now.hour >= 8:
            self.morning_briefing_done = False  # Reset for tomorrow

        # 3. Pending tasks in queue
        if not self.check_cooldown("pending_tasks", 2):
            try:
                conn = sqlite3.connect(str(CONFIG["task_db"]))
                cur = conn.cursor()
                cur.execute("SELECT id, title, description FROM tasks WHERE status = 'pending' LIMIT 1")
                task = cur.fetchone()
                conn.close()

                if task:
                    self.set_cooldown("pending_tasks")
                    fired.append({
                        "trigger": "pending_task",
                        "agents": ["orchestrator"],
                        "task": task[1],  # title
                        "context": {"task_id": task[0], "description": task[2]}
                    })
            except:
                pass

        return fired

# ============================================
# MAIN ORCHESTRATOR
# ============================================

class Orchestrator:
    """Coordinates triggers, agents, and execution."""

    def __init__(self):
        self.broadcaster = StatusBroadcaster()
        self.executor = ClaudeCliExecutor(self.broadcaster)
        self.triggers = TriggerSystem()
        self.running = False
        self.task_queue = asyncio.Queue()
        self.active_count = 0

    async def worker(self, worker_id: int):
        """Worker that processes tasks from the queue."""
        while self.running:
            try:
                # Get task with timeout
                try:
                    task_info = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    continue

                agent_name = task_info["agent"]
                task = task_info["task"]
                context = task_info.get("context", {})

                self.active_count += 1
                try:
                    result = await self.executor.execute_async(agent_name, task, context)
                    self._store_result(agent_name, task, result)
                finally:
                    self.active_count -= 1
                    self.task_queue.task_done()

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

    def _store_result(self, agent_name: str, task: str, result: str):
        """Store result in database."""
        try:
            conn = sqlite3.connect(str(CONFIG["task_db"]))
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO tasks (title, description, priority, status, created_at, completed_at, result)
                VALUES (?, ?, ?, 'completed', ?, ?, ?)
            """, (
                f"[AUTO] [{agent_name}] {task[:80]}",
                f"Autonomous execution by {agent_name}",
                5,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                result[:2000]
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to store result: {e}")

    async def trigger_loop(self):
        """Loop that checks triggers and queues work."""
        while self.running:
            try:
                # Check all triggers
                fired = self.triggers.check_all_triggers()

                for trigger_info in fired:
                    self.broadcaster.trigger_fired(
                        trigger_info["trigger"],
                        trigger_info.get("context", {})
                    )

                    # Queue work for each agent
                    for agent in trigger_info["agents"]:
                        if self.task_queue.qsize() < 10:  # Don't queue too much
                            await self.task_queue.put({
                                "agent": agent,
                                "task": trigger_info["task"],
                                "context": trigger_info.get("context", {})
                            })

                await asyncio.sleep(CONFIG["poll_interval"])

            except Exception as e:
                logger.error(f"Trigger loop error: {e}")
                await asyncio.sleep(5)

    async def run(self):
        """Run the orchestrator."""
        self.running = True
        self.broadcaster.status["running"] = True
        self.broadcaster.update()

        logger.info("🚀 Autonomous Orchestrator starting...")

        # Start workers
        workers = [
            asyncio.create_task(self.worker(i))
            for i in range(CONFIG["max_concurrent"])
        ]

        # Start trigger loop
        trigger_task = asyncio.create_task(self.trigger_loop())

        try:
            # Run until stopped
            await asyncio.gather(trigger_task, *workers)
        except asyncio.CancelledError:
            pass

        self.running = False
        self.broadcaster.status["running"] = False
        self.broadcaster.update()

    def stop(self):
        self.running = False

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("🤖 CLAUDE CLI AUTONOMOUS EXECUTOR")
    print("=" * 60)
    print("Uses your Claude Max subscription - no API key needed")
    print(f"Loaded agents: {len(list(CONFIG['agents_dir'].glob('*.md')))}")
    print(f"Checking every {CONFIG['poll_interval']} seconds")
    print("=" * 60)
    print("\nTriggers enabled:")
    print("  • Revit project changed → BIM validator")
    print("  • Morning (7-8 AM) → Status briefing")
    print("  • Pending tasks → Route to appropriate agent")
    print("=" * 60)

    orchestrator = Orchestrator()

    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        orchestrator.stop()

if __name__ == "__main__":
    main()
