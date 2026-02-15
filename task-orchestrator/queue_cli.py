#!/usr/bin/env python3
"""
Quick CLI for Task Queue - designed for Claude Code integration.

Usage from Claude Code:
    python3 /mnt/d/_CLAUDE-TOOLS/task-orchestrator/queue_cli.py add "Project" "Task title" "Description"
    python3 /mnt/d/_CLAUDE-TOOLS/task-orchestrator/queue_cli.py status "Project"
    python3 /mnt/d/_CLAUDE-TOOLS/task-orchestrator/queue_cli.py run "Project"
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from task_queue import (
    add_task, add_task_batch, get_queue_status, list_tasks,
    get_next_task, start_task, complete_task, verify_task,
    list_projects, clear_completed
)
from orchestrator import run_orchestrator

def print_status(project: str):
    """Print formatted queue status."""
    status = get_queue_status(project)
    print(f"\n{'='*50}")
    print(f"PROJECT: {project}")
    print(f"{'='*50}")
    print(f"Total Tasks: {status['total_tasks']}")
    print(f"  Pending:     {status['pending']}")
    print(f"  In Progress: {status['in_progress']}")
    print(f"  Completed:   {status['completed']}")
    print(f"  Failed:      {status['failed']}")

    if status['next_task']:
        print(f"\nNext Task: [{status['next_task']['id']}] {status['next_task']['title']}")

    print()
    tasks = list_tasks(project)
    if tasks:
        print("TASK LIST:")
        for t in tasks:
            icon = {
                "pending": "○",
                "in_progress": "◐",
                "completed": "●",
                "verified": "✓",
                "failed": "✗"
            }.get(t["status"], "?")
            priority = {"urgent": "!!!", "high": "!!", "normal": "", "low": "~"}.get(t["priority"], "")
            print(f"  {icon} [{t['id']}] {priority}{t['title']} ({t['agent']})")
    print()

def add_tasks_interactive(project: str, tasks_json: str):
    """Add multiple tasks from JSON."""
    tasks = json.loads(tasks_json)
    created = add_task_batch(project, tasks)
    print(f"Added {len(created)} tasks to {project}")
    for t in created:
        print(f"  + [{t['id']}] {t['title']}")

def main():
    if len(sys.argv) < 2:
        print("""
Task Queue CLI

Commands:
  add <project> <title> [description] [--agent NAME] [--priority LEVEL]
  batch <project> '<json array of tasks>'
  status <project>
  list <project> [--status STATUS]
  next <project>
  start <project> --task-id <ID>
  complete <project> --task-id <ID> [--result "msg"] [--error "msg"]
  exec <project>    (generate execution instructions for current session)
  run <project> [--single] [--max N]  (subprocess mode - slower)
  projects
  clear <project>  (archive completed tasks)

Examples:
  queue_cli.py add "6365 W Sample" "Create floor plan views" "Set up L1, L2 views" --agent revit-builder
  queue_cli.py status "6365 W Sample"
  queue_cli.py exec "6365 W Sample"   # For current session execution
  queue_cli.py run "6365 W Sample"    # For background execution
        """)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "add":
        if len(sys.argv) < 4:
            print("Usage: add <project> <title> [description] [--agent NAME] [--priority LEVEL]")
            sys.exit(1)

        project = sys.argv[2]
        title = sys.argv[3]
        description = sys.argv[4] if len(sys.argv) > 4 and not sys.argv[4].startswith("--") else ""

        # Parse optional args
        agent = "general-purpose"
        priority = "normal"
        verify_agent = None

        args = sys.argv[4:]
        for i, arg in enumerate(args):
            if arg == "--agent" and i + 1 < len(args):
                agent = args[i + 1]
            elif arg == "--priority" and i + 1 < len(args):
                priority = args[i + 1]
            elif arg == "--verify" and i + 1 < len(args):
                verify_agent = args[i + 1]

        task = add_task(
            project=project,
            title=title,
            description=description,
            agent=agent,
            priority=priority,
            verification_agent=verify_agent
        )
        print(f"Added task [{task['id']}]: {title}")

    elif cmd == "batch":
        if len(sys.argv) < 4:
            print("Usage: batch <project> '<json array>'")
            sys.exit(1)
        project = sys.argv[2]
        tasks_json = sys.argv[3]
        add_tasks_interactive(project, tasks_json)

    elif cmd == "status":
        if len(sys.argv) < 3:
            print("Usage: status <project>")
            sys.exit(1)
        print_status(sys.argv[2])

    elif cmd == "list":
        if len(sys.argv) < 3:
            print("Usage: list <project> [--status STATUS]")
            sys.exit(1)
        project = sys.argv[2]
        status = None
        if "--status" in sys.argv:
            idx = sys.argv.index("--status")
            if idx + 1 < len(sys.argv):
                status = sys.argv[idx + 1]
        tasks = list_tasks(project, status)
        print(json.dumps(tasks, indent=2))

    elif cmd == "next":
        if len(sys.argv) < 3:
            print("Usage: next <project>")
            sys.exit(1)
        task = get_next_task(sys.argv[2])
        if task:
            print(json.dumps(task, indent=2))
        else:
            print("No pending tasks")

    elif cmd == "start":
        if len(sys.argv) < 3:
            print("Usage: start <project> --task-id <ID>")
            sys.exit(1)
        project = sys.argv[2]
        task_id = None
        if "--task-id" in sys.argv:
            idx = sys.argv.index("--task-id")
            if idx + 1 < len(sys.argv):
                task_id = sys.argv[idx + 1]
        if not task_id:
            print("Error: --task-id required")
            sys.exit(1)
        from session_executor import mark_started
        result = mark_started(project, task_id)
        print(f"Started: {result['task']['title']}")

    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Usage: complete <project> --task-id <ID> [--result msg] [--error msg]")
            sys.exit(1)
        project = sys.argv[2]
        task_id = None
        result_msg = None
        error_msg = None
        args_list = sys.argv[3:]
        for i, arg in enumerate(args_list):
            if arg == "--task-id" and i + 1 < len(args_list):
                task_id = args_list[i + 1]
            elif arg == "--result" and i + 1 < len(args_list):
                result_msg = args_list[i + 1]
            elif arg == "--error" and i + 1 < len(args_list):
                error_msg = args_list[i + 1]
        if not task_id:
            print("Error: --task-id required")
            sys.exit(1)
        from session_executor import mark_completed
        result = mark_completed(project, task_id, result_msg, error_msg)
        print(f"{'Completed' if not error_msg else 'Failed'}: {result['task']['title']}")

    elif cmd == "exec":
        if len(sys.argv) < 3:
            print("Usage: exec <project>")
            sys.exit(1)
        from session_executor import generate_execution_instructions
        print(generate_execution_instructions(sys.argv[2]))

    elif cmd == "run":
        if len(sys.argv) < 3:
            print("Usage: run <project> [--single] [--max N] [--no-voice]")
            sys.exit(1)

        project = sys.argv[2]
        mode = "single" if "--single" in sys.argv else "all"
        voice = "--no-voice" not in sys.argv

        max_tasks = None
        if "--max" in sys.argv:
            idx = sys.argv.index("--max")
            if idx + 1 < len(sys.argv):
                max_tasks = int(sys.argv[idx + 1])

        result = run_orchestrator(
            project=project,
            mode=mode,
            max_tasks=max_tasks,
            voice=voice
        )
        print(json.dumps(result, indent=2))

    elif cmd == "projects":
        projects = list_projects()
        if projects:
            print("Projects with task queues:")
            for p in projects:
                status = get_queue_status(p)
                print(f"  • {p}: {status['pending']} pending, {status['completed']} done")
        else:
            print("No projects with task queues yet")

    elif cmd == "clear":
        if len(sys.argv) < 3:
            print("Usage: clear <project>")
            sys.exit(1)
        count = clear_completed(sys.argv[2])
        print(f"Archived {count} completed tasks")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
