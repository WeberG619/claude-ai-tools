#!/usr/bin/env python3
"""
Swarm Engine — Decompose, dispatch, collect, merge parallel agent work.

Dispatches subtasks to the autonomous-agent daemon (which runs `claude -p` subprocesses).
The daemon handles actual parallelism, not the session.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from decomposition_prompts import decompose_items, build_worker_prompt, list_strategies
from merge_strategies import get_merge_strategy, list_merge_strategies

# Board DB for task tracking
BOARD_DB = Path("/mnt/d/_CLAUDE-TOOLS/task-board/board.db")
# Autonomous agent DB for dispatching
AUTO_AGENT_DB = Path("/mnt/d/_CLAUDE-TOOLS/autonomous-agent/queues/tasks.db")


def _now() -> str:
    return datetime.now().isoformat()


def _gen_id() -> str:
    return uuid.uuid4().hex[:8]


class SwarmEngine:
    """Orchestrates parallel agent swarms."""

    def __init__(self):
        self.swarm_id = _gen_id()

    def plan(self, task_description: str, items: List[str],
             num_workers: int = 5, strategy: str = "by_chunk",
             merge: str = "deduplicate") -> Dict:
        """
        Create a decomposition plan (doesn't execute yet).
        Returns the plan for approval.
        """
        chunks = decompose_items(items, num_workers)
        actual_workers = len(chunks)

        subtasks = []
        for i, chunk in enumerate(chunks):
            prompt = build_worker_prompt(
                strategy_name=strategy,
                worker_id=i + 1,
                total_workers=actual_workers,
                assigned_items=", ".join(str(item) for item in chunk),
                task_description=task_description,
            )
            subtasks.append({
                "worker_id": i + 1,
                "items": chunk,
                "prompt": prompt,
            })

        plan = {
            "swarm_id": self.swarm_id,
            "task": task_description,
            "strategy": strategy,
            "merge_strategy": merge,
            "num_workers": actual_workers,
            "subtasks": subtasks,
            "status": "planned",
            "created_at": _now(),
        }
        return plan

    def dispatch(self, plan: Dict, project: str = "",
                 priority: int = 5) -> Dict:
        """
        Dispatch all subtasks to the autonomous-agent queue.
        Creates a parent task on the board and child tasks in the agent queue.
        """
        # Create parent task on board
        parent_id = None
        try:
            import sys
            sys.path.insert(0, str(BOARD_DB.parent))
            from board import TaskBoard
            board = TaskBoard()
            parent_id = board.add(
                title=f"Swarm: {plan['task'][:80]}",
                description=f"Swarm {plan['swarm_id']} — {plan['num_workers']} workers, "
                           f"strategy: {plan['strategy']}, merge: {plan['merge_strategy']}",
                priority=priority,
                project=project,
                source="swarm",
                tags=["swarm", plan['swarm_id']],
            )
            board.update(parent_id, status="active")
        except Exception:
            parent_id = plan['swarm_id']

        # Dispatch subtasks to autonomous-agent queue
        dispatched = []
        if AUTO_AGENT_DB.exists():
            try:
                conn = sqlite3.connect(str(AUTO_AGENT_DB))
                for subtask in plan['subtasks']:
                    title = f"[Swarm {plan['swarm_id']}] Worker {subtask['worker_id']}/{plan['num_workers']}"
                    conn.execute("""
                        INSERT INTO tasks (title, prompt, priority, status, created_at)
                        VALUES (?, ?, ?, 'pending', ?)
                    """, (title, subtask['prompt'], priority, _now()))
                    task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    dispatched.append({
                        "worker_id": subtask['worker_id'],
                        "agent_task_id": task_id,
                        "status": "queued",
                    })
                conn.commit()
                conn.close()
            except Exception as e:
                # Fallback: save to board as child tasks
                try:
                    for subtask in plan['subtasks']:
                        child_id = board.add(
                            title=f"Swarm W{subtask['worker_id']}: {plan['task'][:60]}",
                            description=subtask['prompt'],
                            priority=priority,
                            project=project,
                            source="swarm",
                            parent_task_id=parent_id,
                        )
                        dispatched.append({
                            "worker_id": subtask['worker_id'],
                            "board_task_id": child_id,
                            "status": "queued",
                        })
                except Exception:
                    pass
        else:
            # No autonomous agent — create board tasks as fallback
            try:
                for subtask in plan['subtasks']:
                    child_id = board.add(
                        title=f"Swarm W{subtask['worker_id']}: {plan['task'][:60]}",
                        description=subtask['prompt'],
                        priority=priority,
                        project=project,
                        source="swarm",
                        parent_task_id=parent_id,
                    )
                    dispatched.append({
                        "worker_id": subtask['worker_id'],
                        "board_task_id": child_id,
                        "status": "queued",
                    })
            except Exception:
                pass

        result = {
            "swarm_id": plan['swarm_id'],
            "parent_task_id": parent_id,
            "dispatched": dispatched,
            "total_workers": plan['num_workers'],
            "status": "dispatched",
        }
        return result

    def status(self, swarm_id: str) -> Dict:
        """Check status of a swarm's subtasks."""
        # Check autonomous-agent DB
        completed = 0
        failed = 0
        in_progress = 0
        pending = 0
        results = []

        if AUTO_AGENT_DB.exists():
            try:
                conn = sqlite3.connect(str(AUTO_AGENT_DB))
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT * FROM tasks WHERE title LIKE ?
                    ORDER BY id
                """, (f"%Swarm {swarm_id}%",)).fetchall()
                conn.close()

                for row in rows:
                    r = dict(row)
                    if r['status'] == 'completed':
                        completed += 1
                        results.append(r.get('result', ''))
                    elif r['status'] == 'failed':
                        failed += 1
                    elif r['status'] == 'in_progress':
                        in_progress += 1
                    else:
                        pending += 1
            except Exception:
                pass

        total = completed + failed + in_progress + pending
        return {
            "swarm_id": swarm_id,
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "all_done": total > 0 and (completed + failed) == total,
            "results": results,
        }

    def collect(self, swarm_id: str, merge_strategy: str = "deduplicate") -> Optional[str]:
        """Collect and merge results from completed swarm workers."""
        s = self.status(swarm_id)
        if not s['all_done']:
            return None

        merge_fn = get_merge_strategy(merge_strategy)
        if s['results']:
            return merge_fn(s['results'])
        return "No results collected."

    def format_plan(self, plan: Dict) -> str:
        """Format a plan for display/approval."""
        lines = [f"## Swarm Plan: {plan['swarm_id']}"]
        lines.append(f"**Task:** {plan['task']}")
        lines.append(f"**Strategy:** {plan['strategy']}")
        lines.append(f"**Workers:** {plan['num_workers']}")
        lines.append(f"**Merge:** {plan['merge_strategy']}")
        lines.append("")
        lines.append("### Subtasks")
        for st in plan['subtasks']:
            items_preview = ", ".join(str(i) for i in st['items'][:3])
            if len(st['items']) > 3:
                items_preview += f" (+{len(st['items'])-3} more)"
            lines.append(f"  Worker {st['worker_id']}: {items_preview}")
        return "\n".join(lines)

    def format_status(self, swarm_id: str) -> str:
        """Format swarm status for display."""
        s = self.status(swarm_id)
        total = s['total']
        if total == 0:
            return f"Swarm {swarm_id}: No tasks found."

        bar_len = 20
        done = s['completed'] + s['failed']
        progress = int((done / total) * bar_len) if total else 0
        bar = "=" * progress + "-" * (bar_len - progress)

        lines = [f"## Swarm {swarm_id} [{bar}] {done}/{total}"]
        lines.append(f"  Completed: {s['completed']} | Failed: {s['failed']} | "
                     f"In Progress: {s['in_progress']} | Pending: {s['pending']}")
        if s['all_done']:
            lines.append("  STATUS: ALL DONE — ready to collect")
        return "\n".join(lines)
