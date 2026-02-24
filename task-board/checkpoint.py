#!/usr/bin/env python3
"""
Checkpoint Manager — Save/load/resume state for long-running tasks.
Persists to board.db checkpoints table so state survives session death.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).parent / "board.db"


def _now() -> str:
    return datetime.now().isoformat()


def _gen_id() -> str:
    return uuid.uuid4().hex[:8]


class CheckpointManager:
    """Save and restore task checkpoints across sessions."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, task_id: str, phase: str, phase_number: int = 0,
             total_phases: int = 0, state: Dict = None,
             completed_phases: List[str] = None, next_action: str = "",
             context: Dict = None) -> str:
        """Save a checkpoint. Returns checkpoint ID."""
        cp_id = _gen_id()
        conn = self._conn()
        conn.execute("""
            INSERT INTO checkpoints (id, task_id, phase, phase_number, total_phases,
                                     state, completed_phases, next_action, context, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cp_id, task_id, phase, phase_number, total_phases,
            json.dumps(state or {}),
            json.dumps(completed_phases or []),
            next_action,
            json.dumps(context or {}),
            _now(),
        ))
        # Also log to task_history
        conn.execute("""
            INSERT INTO task_history (task_id, event, details, timestamp)
            VALUES (?, 'checkpoint', ?, ?)
        """, (task_id, f"Phase: {phase} ({phase_number}/{total_phases})", _now()))
        # Update task checkpoint_data
        conn.execute("""
            UPDATE tasks SET checkpoint_data = ?, updated_at = ? WHERE id = ?
        """, (json.dumps({"checkpoint_id": cp_id, "phase": phase}), _now(), task_id))
        conn.commit()
        conn.close()
        return cp_id

    def load(self, checkpoint_id: str) -> Optional[Dict]:
        """Load a specific checkpoint."""
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM checkpoints WHERE id = ?", (checkpoint_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        cp = dict(row)
        cp['state'] = json.loads(cp.get('state', '{}'))
        cp['completed_phases'] = json.loads(cp.get('completed_phases', '[]'))
        cp['context'] = json.loads(cp.get('context', '{}'))
        return cp

    def latest_for_task(self, task_id: str) -> Optional[Dict]:
        """Get the most recent checkpoint for a task."""
        conn = self._conn()
        row = conn.execute("""
            SELECT * FROM checkpoints WHERE task_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (task_id,)).fetchone()
        conn.close()
        if not row:
            return None
        cp = dict(row)
        cp['state'] = json.loads(cp.get('state', '{}'))
        cp['completed_phases'] = json.loads(cp.get('completed_phases', '[]'))
        cp['context'] = json.loads(cp.get('context', '{}'))
        return cp

    def list_checkpoints(self, task_id: str = None, limit: int = 20) -> List[Dict]:
        """List checkpoints, optionally filtered by task."""
        conn = self._conn()
        if task_id:
            rows = conn.execute("""
                SELECT c.*, t.title as task_title FROM checkpoints c
                LEFT JOIN tasks t ON c.task_id = t.id
                WHERE c.task_id = ? ORDER BY c.created_at DESC LIMIT ?
            """, (task_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT c.*, t.title as task_title FROM checkpoints c
                LEFT JOIN tasks t ON c.task_id = t.id
                ORDER BY c.created_at DESC LIMIT ?
            """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def list_resumable(self) -> List[Dict]:
        """List tasks that have checkpoints and aren't done."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT c.*, t.title as task_title, t.status as task_status
            FROM checkpoints c
            JOIN tasks t ON c.task_id = t.id
            WHERE t.status IN ('pending', 'active', 'blocked')
            AND c.id IN (
                SELECT id FROM checkpoints c2
                WHERE c2.task_id = c.task_id
                ORDER BY c2.created_at DESC LIMIT 1
            )
            ORDER BY c.created_at DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def generate_resume_prompt(self, checkpoint_id: str) -> Optional[str]:
        """Generate a full resume prompt from a checkpoint."""
        cp = self.load(checkpoint_id)
        if not cp:
            return None

        # Get task info
        conn = self._conn()
        task_row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (cp['task_id'],)
        ).fetchone()
        conn.close()
        task = dict(task_row) if task_row else {}

        parts = []
        parts.append("# RESUMING FROM CHECKPOINT")
        parts.append("")
        parts.append(f"**Task:** {task.get('title', 'Unknown')}")
        parts.append(f"**Task ID:** {cp['task_id']}")
        parts.append(f"**Phase:** {cp['phase']} ({cp['phase_number']}/{cp['total_phases']})")
        parts.append(f"**Checkpoint saved:** {cp['created_at']}")
        parts.append("")

        # Completed phases
        completed = cp.get('completed_phases', [])
        if completed:
            parts.append("## Completed Phases")
            for p in completed:
                parts.append(f"  - {p}")
            parts.append("")

        # State
        state = cp.get('state', {})
        if state:
            parts.append("## Saved State")
            if state.get('files_modified'):
                parts.append(f"**Files modified:** {', '.join(state['files_modified'])}")
            if state.get('decisions'):
                parts.append("**Decisions made:**")
                for d in state['decisions']:
                    parts.append(f"  - {d}")
            if state.get('variables'):
                parts.append("**Variables:**")
                for k, v in state['variables'].items():
                    parts.append(f"  - {k}: {v}")
            # Any other state keys
            for k, v in state.items():
                if k not in ('files_modified', 'decisions', 'variables'):
                    parts.append(f"**{k}:** {v}")
            parts.append("")

        # Context
        ctx = cp.get('context', {})
        if ctx:
            parts.append("## Context")
            for k, v in ctx.items():
                parts.append(f"**{k}:** {v}")
            parts.append("")

        # Next action
        if cp.get('next_action'):
            parts.append(f"## NEXT ACTION")
            parts.append(cp['next_action'])
            parts.append("")

        parts.append("---")
        parts.append("Continue from the next action above. All previous phases are complete.")

        return "\n".join(parts)

    def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        conn = self._conn()
        cur = conn.execute("DELETE FROM checkpoints WHERE id = ?", (checkpoint_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        conn.close()
        return deleted

    def dashboard(self) -> str:
        """Show checkpoint dashboard."""
        resumable = self.list_resumable()
        if not resumable:
            return "No resumable checkpoints."

        lines = ["## Resumable Checkpoints"]
        for cp in resumable:
            title = cp.get('task_title', 'Unknown')
            phase = cp.get('phase', '?')
            progress = f"{cp.get('phase_number', '?')}/{cp.get('total_phases', '?')}"
            lines.append(f"  [{cp['id']}] {title} — {phase} ({progress})")
            if cp.get('next_action'):
                lines.append(f"         Next: {cp['next_action'][:80]}")
        return "\n".join(lines)
