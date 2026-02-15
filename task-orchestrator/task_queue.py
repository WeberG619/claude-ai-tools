#!/usr/bin/env python3
"""
Persistent Task Queue for Claude Code Projects

Tasks persist across sessions. Each project has its own queue.
Agents work through tasks with automatic handoffs and verification.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

QUEUE_DIR = Path(__file__).parent / "queues"
QUEUE_DIR.mkdir(exist_ok=True)

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    VERIFIED = "verified"
    FAILED = "failed"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

def get_queue_path(project: str) -> Path:
    """Get path to project's task queue file."""
    safe_name = project.replace(" ", "_").replace("/", "_")
    return QUEUE_DIR / f"{safe_name}.json"

def load_queue(project: str) -> Dict[str, Any]:
    """Load project's task queue."""
    path = get_queue_path(project)
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        "project": project,
        "created_at": datetime.now().isoformat(),
        "tasks": [],
        "completed_tasks": [],
        "metadata": {}
    }

def save_queue(project: str, queue: Dict[str, Any]):
    """Save project's task queue."""
    path = get_queue_path(project)
    queue["updated_at"] = datetime.now().isoformat()
    with open(path, 'w') as f:
        json.dump(queue, f, indent=2)

def add_task(
    project: str,
    title: str,
    description: str,
    agent: str = "general-purpose",
    priority: str = "normal",
    depends_on: List[str] = None,
    verification_agent: str = None,
    metadata: Dict = None
) -> Dict:
    """Add a task to the project queue."""
    queue = load_queue(project)

    task = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "description": description,
        "agent": agent,
        "priority": priority,
        "status": TaskStatus.PENDING.value,
        "depends_on": depends_on or [],
        "verification_agent": verification_agent,
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "verified_at": None,
        "result": None,
        "verification_result": None,
        "error": None
    }

    queue["tasks"].append(task)
    save_queue(project, queue)
    return task

def add_task_batch(project: str, tasks: List[Dict]) -> List[Dict]:
    """Add multiple tasks at once."""
    created = []
    for t in tasks:
        task = add_task(
            project=project,
            title=t.get("title"),
            description=t.get("description", ""),
            agent=t.get("agent", "general-purpose"),
            priority=t.get("priority", "normal"),
            depends_on=t.get("depends_on"),
            verification_agent=t.get("verification_agent"),
            metadata=t.get("metadata")
        )
        created.append(task)
    return created

def get_next_task(project: str) -> Optional[Dict]:
    """Get next available task (pending, no blockers)."""
    queue = load_queue(project)

    completed_ids = {t["id"] for t in queue["tasks"] if t["status"] in ["completed", "verified"]}
    completed_ids.update({t["id"] for t in queue.get("completed_tasks", [])})

    # Priority order
    priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

    pending = [
        t for t in queue["tasks"]
        if t["status"] == TaskStatus.PENDING.value
        and all(dep in completed_ids for dep in t.get("depends_on", []))
    ]

    if not pending:
        return None

    # Sort by priority, then creation time
    pending.sort(key=lambda t: (priority_order.get(t["priority"], 2), t["created_at"]))
    return pending[0]

def start_task(project: str, task_id: str) -> Dict:
    """Mark task as in progress."""
    queue = load_queue(project)

    for task in queue["tasks"]:
        if task["id"] == task_id:
            task["status"] = TaskStatus.IN_PROGRESS.value
            task["started_at"] = datetime.now().isoformat()
            save_queue(project, queue)
            return task

    raise ValueError(f"Task {task_id} not found")

def complete_task(project: str, task_id: str, result: str = None, error: str = None) -> Dict:
    """Mark task as completed (or failed)."""
    queue = load_queue(project)

    for task in queue["tasks"]:
        if task["id"] == task_id:
            if error:
                task["status"] = TaskStatus.FAILED.value
                task["error"] = error
            else:
                task["status"] = TaskStatus.COMPLETED.value
                task["result"] = result
            task["completed_at"] = datetime.now().isoformat()
            save_queue(project, queue)
            return task

    raise ValueError(f"Task {task_id} not found")

def verify_task(project: str, task_id: str, verification_result: str, passed: bool) -> Dict:
    """Mark task as verified."""
    queue = load_queue(project)

    for task in queue["tasks"]:
        if task["id"] == task_id:
            task["verification_result"] = verification_result
            if passed:
                task["status"] = TaskStatus.VERIFIED.value
                task["verified_at"] = datetime.now().isoformat()
            else:
                task["status"] = TaskStatus.FAILED.value
                task["error"] = f"Verification failed: {verification_result}"
            save_queue(project, queue)
            return task

    raise ValueError(f"Task {task_id} not found")

def get_queue_status(project: str) -> Dict:
    """Get summary of queue status."""
    queue = load_queue(project)

    status_counts = {}
    for task in queue["tasks"]:
        status = task["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "project": project,
        "total_tasks": len(queue["tasks"]),
        "by_status": status_counts,
        "pending": status_counts.get("pending", 0),
        "in_progress": status_counts.get("in_progress", 0),
        "completed": status_counts.get("completed", 0) + status_counts.get("verified", 0),
        "failed": status_counts.get("failed", 0),
        "next_task": get_next_task(project)
    }

def list_tasks(project: str, status: str = None) -> List[Dict]:
    """List all tasks, optionally filtered by status."""
    queue = load_queue(project)
    tasks = queue["tasks"]

    if status:
        tasks = [t for t in tasks if t["status"] == status]

    return tasks

def clear_completed(project: str) -> int:
    """Move completed/verified tasks to archive."""
    queue = load_queue(project)

    completed = [t for t in queue["tasks"] if t["status"] in ["completed", "verified"]]
    queue["completed_tasks"].extend(completed)
    queue["tasks"] = [t for t in queue["tasks"] if t["status"] not in ["completed", "verified"]]

    save_queue(project, queue)
    return len(completed)

def list_projects() -> List[str]:
    """List all projects with task queues."""
    return [f.stem for f in QUEUE_DIR.glob("*.json")]


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task Queue Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add task
    add_parser = subparsers.add_parser("add", help="Add a task")
    add_parser.add_argument("--project", "-p", required=True, help="Project name")
    add_parser.add_argument("--title", "-t", required=True, help="Task title")
    add_parser.add_argument("--description", "-d", default="", help="Task description")
    add_parser.add_argument("--agent", "-a", default="general-purpose", help="Agent to use")
    add_parser.add_argument("--priority", default="normal", choices=["low", "normal", "high", "urgent"])
    add_parser.add_argument("--verify-with", help="Verification agent")

    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--project", "-p", required=True, help="Project name")
    list_parser.add_argument("--status", "-s", help="Filter by status")

    # Get status
    status_parser = subparsers.add_parser("status", help="Queue status")
    status_parser.add_argument("--project", "-p", required=True, help="Project name")

    # Next task
    next_parser = subparsers.add_parser("next", help="Get next task")
    next_parser.add_argument("--project", "-p", required=True, help="Project name")

    # Start task
    start_parser = subparsers.add_parser("start", help="Start a task")
    start_parser.add_argument("--project", "-p", required=True, help="Project name")
    start_parser.add_argument("--task-id", "-i", required=True, help="Task ID")

    # Complete task
    complete_parser = subparsers.add_parser("complete", help="Complete a task")
    complete_parser.add_argument("--project", "-p", required=True, help="Project name")
    complete_parser.add_argument("--task-id", "-i", required=True, help="Task ID")
    complete_parser.add_argument("--result", "-r", help="Result message")
    complete_parser.add_argument("--error", "-e", help="Error message (marks as failed)")

    # List projects
    projects_parser = subparsers.add_parser("projects", help="List all projects")

    args = parser.parse_args()

    if args.command == "add":
        task = add_task(
            project=args.project,
            title=args.title,
            description=args.description,
            agent=args.agent,
            priority=args.priority,
            verification_agent=args.verify_with
        )
        print(json.dumps(task, indent=2))

    elif args.command == "list":
        tasks = list_tasks(args.project, args.status)
        for t in tasks:
            status_icon = {"pending": "○", "in_progress": "◐", "completed": "●", "verified": "✓", "failed": "✗"}.get(t["status"], "?")
            print(f"{status_icon} [{t['id']}] {t['title']} ({t['agent']}) - {t['status']}")

    elif args.command == "status":
        status = get_queue_status(args.project)
        print(json.dumps(status, indent=2))

    elif args.command == "next":
        task = get_next_task(args.project)
        if task:
            print(json.dumps(task, indent=2))
        else:
            print("No pending tasks")

    elif args.command == "start":
        task = start_task(args.project, args.task_id)
        print(f"Started: {task['title']}")

    elif args.command == "complete":
        task = complete_task(args.project, args.task_id, args.result, args.error)
        print(f"{'Failed' if args.error else 'Completed'}: {task['title']}")

    elif args.command == "projects":
        projects = list_projects()
        for p in projects:
            status = get_queue_status(p)
            print(f"• {p}: {status['pending']} pending, {status['completed']} done")

    else:
        parser.print_help()
