#!/usr/bin/env python3
"""
Cross-Session Task Board — Single source of truth for all tasks.
SQLite-backed. Syncs from brain.json, task-orchestrator, autonomous-agent.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).parent / "board.db"

# Sources we can sync from
BRAIN_FILE = Path("/mnt/d/_CLAUDE-TOOLS/brain-state/brain.json")
TASK_ORCH_DIR = Path("/mnt/d/_CLAUDE-TOOLS/task-orchestrator/queues")
AUTO_AGENT_DB = Path("/mnt/d/_CLAUDE-TOOLS/autonomous-agent/queues/tasks.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','active','blocked','done','failed')),
    priority INTEGER DEFAULT 5 CHECK(priority BETWEEN 1 AND 10),
    project TEXT DEFAULT '',
    agent TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    blocked_by TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    checkpoint_data TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    result TEXT,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    parent_task_id TEXT,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    event TEXT NOT NULL,
    details TEXT DEFAULT '',
    timestamp TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    direction TEXT DEFAULT 'inbound',
    items_synced INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS retry_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    operation TEXT NOT NULL,
    strategy TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    success INTEGER DEFAULT 0,
    error TEXT,
    duration_seconds REAL,
    context TEXT DEFAULT '{}',
    timestamp TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    phase_number INTEGER DEFAULT 0,
    total_phases INTEGER DEFAULT 0,
    state TEXT DEFAULT '{}',
    completed_phases TEXT DEFAULT '[]',
    next_action TEXT DEFAULT '',
    context TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_task_history_task ON task_history(task_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_task ON checkpoints(task_id);
CREATE INDEX IF NOT EXISTS idx_retry_log_task ON retry_log(task_id);
"""


def _now() -> str:
    return datetime.now().isoformat()


def _gen_id() -> str:
    return uuid.uuid4().hex[:8]


class TaskBoard:
    """Unified task board backed by SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        conn = self._conn()
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()

    # ── CRUD ──────────────────────────────────────────

    def add(self, title: str, description: str = "", priority: int = 5,
            project: str = "", agent: str = "", source: str = "manual",
            tags: List[str] = None, parent_task_id: str = None,
            task_id: str = None) -> str:
        """Create a new task. Returns task ID."""
        tid = task_id or _gen_id()
        now = _now()
        conn = self._conn()
        conn.execute("""
            INSERT INTO tasks (id, title, description, priority, project, agent,
                               source, tags, created_at, updated_at, parent_task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tid, title, description, priority, project, agent, source,
              json.dumps(tags or []), now, now, parent_task_id))
        conn.execute("""
            INSERT INTO task_history (task_id, event, details, timestamp)
            VALUES (?, 'created', ?, ?)
        """, (tid, f"Priority {priority}, source: {source}", now))
        conn.commit()
        conn.close()
        return tid

    def get(self, task_id: str) -> Optional[Dict]:
        """Get a single task by ID."""
        conn = self._conn()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def update(self, task_id: str, **kwargs) -> bool:
        """Update task fields. Logs the change."""
        allowed = {'title', 'description', 'status', 'priority', 'project',
                   'agent', 'blocked_by', 'tags', 'checkpoint_data', 'result',
                   'error', 'retry_count', 'parent_task_id'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        # Cycle detection on blocked_by changes
        if 'blocked_by' in updates:
            new_blockers = updates['blocked_by']
            if isinstance(new_blockers, str):
                try:
                    new_blockers = json.loads(new_blockers)
                except (json.JSONDecodeError, TypeError):
                    new_blockers = []
            if new_blockers and self._would_create_cycle(task_id, new_blockers):
                return False  # Reject — would create circular dependency

        # JSON-encode list/dict fields
        for k in ('blocked_by', 'tags', 'checkpoint_data'):
            if k in updates and not isinstance(updates[k], str):
                updates[k] = json.dumps(updates[k])

        updates['updated_at'] = _now()

        # Track status transitions
        if 'status' in updates:
            # Block activation guard: prevent starting blocked tasks
            if updates['status'] == 'active':
                task = self.get(task_id)
                if task:
                    try:
                        blockers = json.loads(task.get('blocked_by', '[]'))
                    except (json.JSONDecodeError, TypeError):
                        blockers = []
                    if blockers:
                        conn = self._conn()
                        placeholders = ','.join('?' * len(blockers))
                        unresolved = conn.execute(f"""
                            SELECT COUNT(*) as cnt FROM tasks
                            WHERE id IN ({placeholders}) AND status != 'done'
                        """, blockers).fetchone()
                        conn.close()
                        if unresolved['cnt'] > 0:
                            updates['status'] = 'blocked'
                updates['started_at'] = _now()
            elif updates['status'] in ('done', 'failed'):
                updates['completed_at'] = _now()

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [task_id]

        conn = self._conn()
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        conn.execute("""
            INSERT INTO task_history (task_id, event, details, timestamp)
            VALUES (?, 'updated', ?, ?)
        """, (task_id, json.dumps({k: str(v)[:100] for k, v in kwargs.items()}), _now()))
        conn.commit()
        conn.close()
        return True

    def done(self, task_id: str, result: str = "") -> bool:
        """Mark task as done. Auto-promotes blocked tasks whose blockers are now resolved."""
        success = self.update(task_id, status="done", result=result)
        if success:
            self._auto_promote(task_id)
            self._notify_cognitive_core(task_id, result)
        return success

    def _notify_cognitive_core(self, task_id: str, result: str = ""):
        """Fire a task_completed event through the cognitive dispatcher."""
        try:
            import sys
            task = self.get(task_id)
            if not task:
                return

            sys.path.insert(0, str(Path("/mnt/d/_CLAUDE-TOOLS/cognitive-core")))
            from dispatcher import CognitiveDispatcher
            cd = CognitiveDispatcher()
            cd.dispatch({
                "type": "task_completed",
                "source": "task_board",
                "priority": "low",
                "data": {
                    "task_id": task_id,
                    "title": task.get("title", ""),
                    "project": task.get("project", ""),
                    "result": (result or "")[:200],
                },
            })
        except Exception:
            pass  # Never fail the board operation due to cognitive wiring

    def _auto_promote(self, completed_id: str):
        """After completing a task, promote blocked tasks whose blockers are all done."""
        conn = self._conn()
        blocked_tasks = conn.execute(
            "SELECT id, blocked_by FROM tasks WHERE status = 'blocked'"
        ).fetchall()
        conn.close()

        for row in blocked_tasks:
            task = dict(row)
            try:
                blockers = json.loads(task.get('blocked_by', '[]'))
            except (json.JSONDecodeError, TypeError):
                continue

            if completed_id not in blockers:
                continue

            # Check if ALL blockers are now done
            conn = self._conn()
            placeholders = ','.join('?' * len(blockers))
            unresolved = conn.execute(f"""
                SELECT COUNT(*) as cnt FROM tasks
                WHERE id IN ({placeholders}) AND status != 'done'
            """, blockers).fetchone()
            conn.close()

            if unresolved['cnt'] == 0:
                self.update(task['id'], status='pending')
                conn = self._conn()
                conn.execute("""
                    INSERT INTO task_history (task_id, event, details, timestamp)
                    VALUES (?, 'auto_promoted', ?, ?)
                """, (task['id'], f"All blockers resolved (last: {completed_id})", _now()))
                conn.commit()
                conn.close()

    def _would_create_cycle(self, task_id: str, new_blockers: list) -> bool:
        """DFS cycle detection. Returns True if adding new_blockers would create a cycle."""
        visited = set()

        def dfs(current_id: str) -> bool:
            if current_id == task_id:
                return True
            if current_id in visited:
                return False
            visited.add(current_id)

            task = self.get(current_id)
            if not task:
                return False

            try:
                blockers = json.loads(task.get('blocked_by', '[]'))
            except (json.JSONDecodeError, TypeError):
                return False

            for b in blockers:
                if dfs(b):
                    return True
            return False

        for blocker_id in new_blockers:
            visited.clear()
            if dfs(blocker_id):
                return True
        return False

    def fail(self, task_id: str, error: str = "") -> bool:
        """Mark task as failed."""
        return self.update(task_id, status="failed", error=error)

    def delete(self, task_id: str) -> bool:
        """Delete a task and its history."""
        conn = self._conn()
        conn.execute("DELETE FROM task_history WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM checkpoints WHERE task_id = ?", (task_id,))
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        conn.close()
        return deleted

    # ── QUERIES ───────────────────────────────────────

    def list_tasks(self, status: str = None, project: str = None,
                   limit: int = 50) -> List[Dict]:
        """List tasks with optional filters."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if project:
            query += " AND project = ?"
            params.append(project)
        query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
        params.append(limit)

        conn = self._conn()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def next_task(self) -> Optional[Dict]:
        """Get the highest-priority pending task that isn't blocked."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM tasks
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
        """).fetchall()
        conn.close()

        for row in rows:
            task = dict(row)
            blocked = json.loads(task.get('blocked_by', '[]'))
            if not blocked:
                return task
            # Check if all blockers are done
            conn = self._conn()
            placeholders = ','.join('?' * len(blocked))
            blockers = conn.execute(f"""
                SELECT id FROM tasks WHERE id IN ({placeholders}) AND status != 'done'
            """, blocked).fetchall()
            conn.close()
            if not blockers:
                return task
        return None

    def get_history(self, task_id: str) -> List[Dict]:
        """Get audit trail for a task."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM task_history WHERE task_id = ?
            ORDER BY timestamp DESC
        """, (task_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        """Get board statistics."""
        conn = self._conn()
        counts = dict(conn.execute(
            "SELECT status, COUNT(*) FROM tasks GROUP BY status"
        ).fetchall())
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        projects = [r[0] for r in conn.execute(
            "SELECT DISTINCT project FROM tasks WHERE project != ''"
        ).fetchall()]
        conn.close()
        return {
            "total": total,
            "pending": counts.get("pending", 0),
            "active": counts.get("active", 0),
            "blocked": counts.get("blocked", 0),
            "done": counts.get("done", 0),
            "failed": counts.get("failed", 0),
            "projects": projects,
        }

    # ── SYNC ──────────────────────────────────────────

    def sync_from_brain(self) -> int:
        """Pull tasks from brain.json pending_tasks if any."""
        if not BRAIN_FILE.exists():
            return 0
        try:
            brain = json.loads(BRAIN_FILE.read_text())
        except Exception:
            return 0

        count = 0
        for item in brain.get("pending_tasks", []):
            title = item if isinstance(item, str) else item.get("title", "")
            if not title:
                continue
            # Check for duplicates by title+source
            existing = self._find_by_title_source(title, "brain.json")
            if not existing:
                self.add(title=title, source="brain.json",
                         priority=item.get("priority", 5) if isinstance(item, dict) else 5,
                         project=item.get("project", "") if isinstance(item, dict) else "")
                count += 1

        self._log_sync("brain.json", count)
        return count

    def sync_from_auto_agent(self) -> int:
        """Pull tasks from autonomous-agent SQLite DB."""
        if not AUTO_AGENT_DB.exists():
            return 0
        try:
            conn = sqlite3.connect(str(AUTO_AGENT_DB))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, title, prompt, status, priority, created_at
                FROM tasks WHERE status IN ('pending', 'in_progress')
            """).fetchall()
            conn.close()
        except Exception:
            return 0

        count = 0
        for row in rows:
            r = dict(row)
            existing = self._find_by_title_source(r['title'], "autonomous-agent")
            if not existing:
                status_map = {'pending': 'pending', 'in_progress': 'active'}
                self.add(
                    title=r['title'],
                    description=r.get('prompt', ''),
                    source="autonomous-agent",
                    priority=r.get('priority', 5),
                    task_id=f"aa-{r['id']}",
                )
                if r['status'] == 'in_progress':
                    self.update(f"aa-{r['id']}", status='active')
                count += 1

        self._log_sync("autonomous-agent", count)
        return count

    def sync_from_task_orchestrator(self) -> int:
        """Pull tasks from task-orchestrator queue JSON files."""
        if not TASK_ORCH_DIR.exists():
            return 0
        count = 0
        for qfile in TASK_ORCH_DIR.glob("*.json"):
            try:
                data = json.loads(qfile.read_text())
                tasks = data if isinstance(data, list) else data.get("tasks", [])
                for item in tasks:
                    title = item.get("title", item.get("name", ""))
                    if not title:
                        continue
                    existing = self._find_by_title_source(title, "task-orchestrator")
                    if not existing:
                        self.add(
                            title=title,
                            description=item.get("description", ""),
                            source="task-orchestrator",
                            priority=item.get("priority", 5),
                            project=item.get("project", ""),
                        )
                        count += 1
            except Exception:
                continue

        self._log_sync("task-orchestrator", count)
        return count

    def sync_all(self) -> Dict[str, int]:
        """Sync from all known sources."""
        return {
            "brain.json": self.sync_from_brain(),
            "autonomous-agent": self.sync_from_auto_agent(),
            "task-orchestrator": self.sync_from_task_orchestrator(),
        }

    def _find_by_title_source(self, title: str, source: str) -> Optional[Dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM tasks WHERE title = ? AND source = ?", (title, source)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def _log_sync(self, source: str, count: int):
        conn = self._conn()
        conn.execute("""
            INSERT INTO sync_log (source, direction, items_synced, timestamp)
            VALUES (?, 'inbound', ?, ?)
        """, (source, count, _now()))
        conn.commit()
        conn.close()

    # ── DAG VIEW ──────────────────────────────────────

    def dag_view(self) -> str:
        """Generate ASCII dependency graph of tasks."""
        conn = self._conn()
        tasks = conn.execute(
            "SELECT id, title, status, blocked_by FROM tasks WHERE status != 'done'"
        ).fetchall()
        conn.close()

        if not tasks:
            return "No active tasks."

        lines = ["Task Dependency Graph:", ""]
        task_map = {}
        for row in tasks:
            t = dict(row)
            try:
                blockers = json.loads(t.get('blocked_by', '[]'))
            except (json.JSONDecodeError, TypeError):
                blockers = []
            task_map[t['id']] = {'title': t['title'], 'status': t['status'], 'blockers': blockers}

        # Find root tasks (no blockers)
        roots = [tid for tid, t in task_map.items() if not t['blockers']]
        other = [tid for tid, t in task_map.items() if t['blockers']]

        status_icons = {'pending': 'O', 'active': '>', 'blocked': 'X', 'failed': '!'}

        def render(tid, indent=0):
            t = task_map.get(tid)
            if not t:
                return
            icon = status_icons.get(t['status'], '?')
            prefix = "  " * indent + ("+-" if indent > 0 else "")
            lines.append(f"{prefix}[{icon}] {tid[:8]} {t['title'][:40]}")

            # Find tasks that this one blocks
            children = [oid for oid, ot in task_map.items()
                        if tid in ot['blockers']]
            for child in children:
                render(child, indent + 1)

        for root in roots:
            render(root)

        # Show orphan blocked tasks not reachable from roots
        rendered = set()
        for line in lines:
            for tid in task_map:
                if tid[:8] in line:
                    rendered.add(tid)
        for tid in other:
            if tid not in rendered:
                t = task_map[tid]
                icon = status_icons.get(t['status'], '?')
                blockers_str = ",".join(b[:8] for b in t['blockers'])
                lines.append(f"[{icon}] {tid[:8]} {t['title'][:40]}  (blocked by: {blockers_str})")

        return "\n".join(lines)

    # ── DASHBOARD ─────────────────────────────────────

    def dashboard(self) -> str:
        """Generate a text dashboard for session briefing."""
        s = self.stats()
        lines = []
        lines.append("## Task Board")
        lines.append(f"**{s['pending']} pending** | {s['active']} active | "
                     f"{s['blocked']} blocked | {s['done']} done | {s['failed']} failed")

        # Next task
        nxt = self.next_task()
        if nxt:
            lines.append(f"\n**Next up:** [{nxt['id']}] {nxt['title']} (P{nxt['priority']})")

        # Active tasks
        active = self.list_tasks(status="active")
        if active:
            lines.append("\n**Active:**")
            for t in active[:5]:
                lines.append(f"  - [{t['id']}] {t['title']}")

        # Blocked tasks
        blocked = self.list_tasks(status="blocked")
        if blocked:
            lines.append(f"\n**Blocked:** {len(blocked)} task(s)")

        # By project
        if s['projects']:
            lines.append(f"\n**Projects:** {', '.join(s['projects'])}")

        return "\n".join(lines)


if __name__ == "__main__":
    board = TaskBoard()
    print(board.dashboard())
