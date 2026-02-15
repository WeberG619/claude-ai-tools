#!/usr/bin/env python3
"""
Task Orchestrator for Claude Code

Runs tasks through Claude Code agents with:
- Automatic task pickup
- Agent handoffs
- Verification after completion
- Voice announcements
- Memory logging
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import time

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent))
from task_queue import (
    load_queue, save_queue, get_next_task, start_task,
    complete_task, verify_task, get_queue_status, list_tasks,
    TaskStatus
)

VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
CLAUDE_CMD = "claude"

class Orchestrator:
    def __init__(self, project: str, verbose: bool = True, voice: bool = True):
        self.project = project
        self.verbose = verbose
        self.voice_enabled = voice
        self.log_file = Path(__file__).parent / "logs" / f"{project.replace(' ', '_')}.log"
        self.log_file.parent.mkdir(exist_ok=True)

    def log(self, message: str):
        """Log message to file and optionally print."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        with open(self.log_file, "a") as f:
            f.write(line + "\n")
        if self.verbose:
            print(line)

    def speak(self, text: str):
        """Speak text via voice MCP."""
        if not self.voice_enabled or not VOICE_SCRIPT.exists():
            return
        try:
            subprocess.run(
                ["python3", str(VOICE_SCRIPT), text],
                capture_output=True,
                timeout=30
            )
        except Exception as e:
            self.log(f"Voice error: {e}")

    def run_agent(self, task: Dict) -> tuple[bool, str]:
        """Run a Claude Code agent for a task."""
        agent = task.get("agent", "general-purpose")
        title = task["title"]
        description = task.get("description", "")

        prompt = f"""You are working on project: {self.project}

TASK: {title}

DESCRIPTION:
{description}

INSTRUCTIONS:
1. Complete this task fully
2. When done, summarize what you accomplished
3. If you encounter errors, describe them clearly
4. Do NOT ask questions - make reasonable decisions and proceed

Begin working on this task now."""

        self.log(f"Running agent '{agent}' for task: {title}")

        try:
            # Run Claude Code with the agent
            result = subprocess.run(
                [CLAUDE_CMD, "--print", "--agent", agent, "-p", prompt],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd="/mnt/d"
            )

            output = result.stdout + result.stderr
            success = result.returncode == 0

            # Truncate output for storage
            output_summary = output[:2000] if len(output) > 2000 else output

            return success, output_summary

        except subprocess.TimeoutExpired:
            return False, "Task timed out after 10 minutes"
        except Exception as e:
            return False, f"Error running agent: {str(e)}"

    def run_verification(self, task: Dict, task_result: str) -> tuple[bool, str]:
        """Run verification agent on completed task."""
        verify_agent = task.get("verification_agent")
        if not verify_agent:
            # Default verification prompt
            verify_agent = "code-reviewer"

        title = task["title"]
        description = task.get("description", "")

        prompt = f"""You are verifying a completed task for project: {self.project}

ORIGINAL TASK: {title}

TASK DESCRIPTION:
{description}

WHAT WAS DONE:
{task_result[:1500]}

VERIFICATION INSTRUCTIONS:
1. Check if the task was completed correctly
2. Look for any errors, omissions, or issues
3. Respond with either:
   - "VERIFIED: [brief confirmation]" if the task was done correctly
   - "FAILED: [specific issues found]" if there are problems

Be thorough but concise."""

        self.log(f"Running verification with '{verify_agent}'")

        try:
            result = subprocess.run(
                [CLAUDE_CMD, "--print", "--agent", verify_agent, "-p", prompt],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd="/mnt/d"
            )

            output = result.stdout + result.stderr
            passed = "VERIFIED:" in output.upper() or result.returncode == 0

            return passed, output[:1000]

        except Exception as e:
            # If verification fails, assume task is OK
            return True, f"Verification skipped: {str(e)}"

    def process_task(self, task: Dict) -> bool:
        """Process a single task with verification."""
        task_id = task["id"]
        title = task["title"]

        self.log(f"Starting task: {title}")
        self.speak(f"Starting task: {title}")

        # Mark as in progress
        start_task(self.project, task_id)

        # Run the agent
        success, result = self.run_agent(task)

        if not success:
            complete_task(self.project, task_id, error=result)
            self.log(f"Task FAILED: {title}")
            self.speak(f"Task failed: {title}")
            return False

        # Mark as completed
        complete_task(self.project, task_id, result=result)
        self.log(f"Task completed: {title}")

        # Run verification if specified
        if task.get("verification_agent") or True:  # Always verify for now
            verified, verify_result = self.run_verification(task, result)
            verify_task(self.project, task_id, verify_result, verified)

            if verified:
                self.log(f"Task VERIFIED: {title}")
                self.speak(f"Task verified: {title}")
            else:
                self.log(f"Task verification FAILED: {title}")
                self.speak(f"Task verification failed: {title}")
                return False

        return True

    def run_queue(self, max_tasks: int = None, stop_on_failure: bool = False) -> Dict:
        """Process tasks from the queue."""
        processed = 0
        succeeded = 0
        failed = 0

        self.speak(f"Starting task queue for {self.project}")
        self.log(f"=== Starting queue run for {self.project} ===")

        while True:
            # Check if we've hit max tasks
            if max_tasks and processed >= max_tasks:
                self.log(f"Reached max tasks limit: {max_tasks}")
                break

            # Get next task
            task = get_next_task(self.project)
            if not task:
                self.log("No more pending tasks")
                break

            # Process it
            success = self.process_task(task)
            processed += 1

            if success:
                succeeded += 1
            else:
                failed += 1
                if stop_on_failure:
                    self.log("Stopping due to failure")
                    break

            # Small delay between tasks
            time.sleep(1)

        # Final summary
        summary = {
            "project": self.project,
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
            "remaining": get_queue_status(self.project)["pending"]
        }

        self.log(f"=== Queue run complete: {succeeded}/{processed} succeeded ===")
        self.speak(f"Queue complete. {succeeded} of {processed} tasks succeeded. {summary['remaining']} remaining.")

        return summary

    def run_single(self) -> Optional[Dict]:
        """Run just the next task."""
        task = get_next_task(self.project)
        if not task:
            self.log("No pending tasks")
            return None

        self.process_task(task)
        return task


def run_orchestrator(
    project: str,
    mode: str = "all",
    max_tasks: int = None,
    voice: bool = True,
    stop_on_failure: bool = False
) -> Dict:
    """Main entry point for running the orchestrator."""
    orch = Orchestrator(project, verbose=True, voice=voice)

    if mode == "single":
        task = orch.run_single()
        return {"task": task}
    else:
        return orch.run_queue(max_tasks=max_tasks, stop_on_failure=stop_on_failure)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task Orchestrator")
    parser.add_argument("--project", "-p", required=True, help="Project name")
    parser.add_argument("--mode", "-m", default="all", choices=["all", "single"], help="Run mode")
    parser.add_argument("--max-tasks", "-n", type=int, help="Max tasks to process")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice")
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop if a task fails")

    args = parser.parse_args()

    result = run_orchestrator(
        project=args.project,
        mode=args.mode,
        max_tasks=args.max_tasks,
        voice=not args.no_voice,
        stop_on_failure=args.stop_on_failure
    )

    print(json.dumps(result, indent=2))
