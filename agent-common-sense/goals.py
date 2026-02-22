"""
Goal Engine v1.0
=================
Hierarchical goal tracking with dependencies, progress rollup,
and brain.json integration for the Autonomy Engine.

Goals persist in memories.db across sessions. They can be organized
in parent-child hierarchies with dependency tracking between them.
Progress rolls up automatically from children to parents.

Usage:
    from goals import GoalEngine, Goal

    engine = GoalEngine()

    # Create a goal hierarchy
    parent = engine.create_goal("Ship Autonomy Engine", priority="high")
    child1 = engine.create_goal("Build GoalEngine", parent_goal_id=parent)
    child2 = engine.create_goal("Build Planner", parent_goal_id=parent)

    # Add dependencies
    engine.add_dependency(child2, child1)  # planner depends on goals

    # Track progress
    engine.update_progress(child1, 100)
    engine.complete_goal(child1)
    engine.rollup_progress(parent)  # auto-calculates from children

    # Query
    actionable = engine.get_actionable()  # active, no blockers, leaf goals
    tree = engine.get_tree(parent)        # full hierarchy

CLI:
    python goals.py list [--project X] [--status active]
    python goals.py create "Title" [--parent ID] [--priority high]
    python goals.py update ID --status active --progress 50
    python goals.py complete ID
    python goals.py tree [ID]
    python goals.py actionable
"""

import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ─── DATA CLASSES ──────────────────────────────────────────────

@dataclass
class Goal:
    """A tracked goal with hierarchy and dependency support."""
    id: int = 0
    title: str = ""
    description: str = ""
    parent_goal_id: Optional[int] = None
    project: str = ""
    status: str = "draft"  # draft|active|blocked|completed|abandoned
    priority: str = "medium"  # critical|high|medium|low
    progress_pct: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    deadline: Optional[str] = None
    tags: str = "[]"
    domain: str = "general"
    source: str = "manual"
    notes: str = ""
    # Populated by queries, not stored directly
    children: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def priority_rank(self) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(self.priority, 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "parent_goal_id": self.parent_goal_id,
            "project": self.project,
            "status": self.status,
            "priority": self.priority,
            "progress_pct": self.progress_pct,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deadline": self.deadline,
            "tags": self.tags,
            "domain": self.domain,
            "source": self.source,
            "notes": self.notes,
        }


@dataclass
class GoalEvent:
    """Audit trail entry for goal changes."""
    id: int = 0
    goal_id: int = 0
    event_type: str = ""  # created|status_change|progress_update|note|linked_task|completed_task|replan
    old_value: str = ""
    new_value: str = ""
    details: str = ""
    timestamp: str = ""


# ─── GOAL ENGINE ───────────────────────────────────────────────

class GoalEngine:
    """
    Hierarchical goal tracking with dependencies, progress rollup,
    and brain.json sync.
    """

    VALID_STATUSES = {"draft", "active", "blocked", "completed", "abandoned"}
    VALID_PRIORITIES = {"critical", "high", "medium", "low"}
    VALID_DEP_TYPES = {"blocks", "soft", "informs"}

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._find_db()
        if self.db_path:
            self._ensure_schema()

    def _find_db(self) -> Optional[str]:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self):
        """Create goal tables if they don't exist."""
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                parent_goal_id INTEGER,
                project TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                priority TEXT DEFAULT 'medium',
                progress_pct REAL DEFAULT 0.0,
                created_at TEXT,
                updated_at TEXT,
                deadline TEXT,
                tags TEXT DEFAULT '[]',
                domain TEXT DEFAULT 'general',
                source TEXT DEFAULT 'manual',
                notes TEXT DEFAULT '',
                FOREIGN KEY (parent_goal_id) REFERENCES goals(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS goal_dependencies (
                goal_id INTEGER NOT NULL,
                depends_on_goal_id INTEGER NOT NULL,
                dependency_type TEXT DEFAULT 'blocks',
                created_at TEXT,
                PRIMARY KEY (goal_id, depends_on_goal_id),
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
                FOREIGN KEY (depends_on_goal_id) REFERENCES goals(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS goal_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                old_value TEXT DEFAULT '',
                new_value TEXT DEFAULT '',
                details TEXT DEFAULT '',
                timestamp TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        conn.close()

    # ─── CRUD ──────────────────────────────────────────────────

    def create_goal(self, title: str, description: str = "",
                    parent_goal_id: Optional[int] = None,
                    project: str = "", status: str = "draft",
                    priority: str = "medium", deadline: Optional[str] = None,
                    tags: Optional[list] = None, domain: str = "general",
                    source: str = "manual", notes: str = "") -> int:
        """Create a new goal. Returns the goal ID."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        if priority not in self.VALID_PRIORITIES:
            raise ValueError(f"Invalid priority: {priority}")

        # Verify parent exists if specified
        if parent_goal_id is not None:
            parent = self.get_goal(parent_goal_id)
            if not parent:
                raise ValueError(f"Parent goal {parent_goal_id} not found")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        cursor = conn.execute("""
            INSERT INTO goals (title, description, parent_goal_id, project,
                             status, priority, progress_pct, created_at, updated_at,
                             deadline, tags, domain, source, notes)
            VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, parent_goal_id, project,
              status, priority, now, now, deadline,
              json.dumps(tags or []), domain, source, notes))
        goal_id = cursor.lastrowid
        conn.commit()

        # Audit
        self._record_event(conn, goal_id, "created", "", title,
                          f"priority={priority}, status={status}")
        conn.commit()
        conn.close()
        return goal_id

    def get_goal(self, goal_id: int) -> Optional[Goal]:
        """Get a goal by ID."""
        conn = self._conn()
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_goal(row)

    def update_goal(self, goal_id: int, **kwargs) -> bool:
        """Update goal fields. Supported: title, description, status, priority,
        progress_pct, deadline, tags, domain, notes, parent_goal_id."""
        goal = self.get_goal(goal_id)
        if not goal:
            return False

        allowed = {"title", "description", "status", "priority", "progress_pct",
                   "deadline", "tags", "domain", "notes", "parent_goal_id", "project"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "status" in updates and updates["status"] not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {updates['status']}")
        if "priority" in updates and updates["priority"] not in self.VALID_PRIORITIES:
            raise ValueError(f"Invalid priority: {updates['priority']}")

        # Cycle detection for parent moves
        if "parent_goal_id" in updates and updates["parent_goal_id"] is not None:
            if self._would_create_cycle(goal_id, updates["parent_goal_id"]):
                raise ValueError("Cannot set parent: would create cycle")

        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])

        updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self._conn()

        # Record events for status/progress changes
        if "status" in updates and updates["status"] != goal.status:
            self._record_event(conn, goal_id, "status_change",
                             goal.status, updates["status"])
        if "progress_pct" in updates and updates["progress_pct"] != goal.progress_pct:
            self._record_event(conn, goal_id, "progress_update",
                             str(goal.progress_pct), str(updates["progress_pct"]))

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [goal_id]
        conn.execute(f"UPDATE goals SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True

    def delete_goal(self, goal_id: int, cascade: bool = False) -> bool:
        """Delete a goal. If cascade, also deletes children."""
        goal = self.get_goal(goal_id)
        if not goal:
            return False

        conn = self._conn()
        if cascade:
            children = self._get_all_descendant_ids(conn, goal_id)
            if children:
                placeholders = ",".join("?" * len(children))
                conn.execute(f"DELETE FROM goals WHERE id IN ({placeholders})", children)

        conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        conn.commit()
        conn.close()
        return True

    # ─── HIERARCHY ─────────────────────────────────────────────

    def get_children(self, goal_id: int) -> list[Goal]:
        """Get direct children of a goal."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM goals WHERE parent_goal_id = ? ORDER BY priority, created_at",
            (goal_id,)
        ).fetchall()
        conn.close()
        return [self._row_to_goal(r) for r in rows]

    def get_tree(self, goal_id: Optional[int] = None) -> list[Goal]:
        """Get a full goal tree. If goal_id is None, returns all root goals with trees."""
        if goal_id is None:
            roots = self.get_roots()
            for root in roots:
                self._populate_children(root)
            return roots
        else:
            goal = self.get_goal(goal_id)
            if goal:
                self._populate_children(goal)
                return [goal]
            return []

    def get_roots(self) -> list[Goal]:
        """Get all root goals (no parent)."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM goals WHERE parent_goal_id IS NULL ORDER BY priority, created_at"
        ).fetchall()
        conn.close()
        return [self._row_to_goal(r) for r in rows]

    def move_goal(self, goal_id: int, new_parent_id: Optional[int]) -> bool:
        """Move a goal to a new parent. None for root. Checks for cycles."""
        if new_parent_id is not None:
            if self._would_create_cycle(goal_id, new_parent_id):
                raise ValueError("Cannot move: would create cycle")
            if not self.get_goal(new_parent_id):
                raise ValueError(f"Parent goal {new_parent_id} not found")

        return self.update_goal(goal_id, parent_goal_id=new_parent_id)

    def _would_create_cycle(self, goal_id: int, proposed_parent_id: int) -> bool:
        """Check if setting proposed_parent_id as parent of goal_id would create a cycle."""
        if goal_id == proposed_parent_id:
            return True

        # Walk up from proposed_parent to see if we reach goal_id
        conn = self._conn()
        visited = set()
        current = proposed_parent_id
        while current is not None:
            if current == goal_id:
                conn.close()
                return True
            if current in visited:
                conn.close()
                return True  # Already a cycle in the data
            visited.add(current)
            row = conn.execute(
                "SELECT parent_goal_id FROM goals WHERE id = ?", (current,)
            ).fetchone()
            current = row["parent_goal_id"] if row else None

        conn.close()
        return False

    def _populate_children(self, goal: Goal):
        """Recursively populate children for a goal."""
        goal.children = self.get_children(goal.id)
        for child in goal.children:
            self._populate_children(child)

    def _get_all_descendant_ids(self, conn: sqlite3.Connection, goal_id: int) -> list[int]:
        """Get all descendant IDs recursively."""
        ids = []
        rows = conn.execute(
            "SELECT id FROM goals WHERE parent_goal_id = ?", (goal_id,)
        ).fetchall()
        for row in rows:
            ids.append(row["id"])
            ids.extend(self._get_all_descendant_ids(conn, row["id"]))
        return ids

    # ─── DEPENDENCIES ──────────────────────────────────────────

    def add_dependency(self, goal_id: int, depends_on_id: int,
                       dependency_type: str = "blocks") -> bool:
        """Add a dependency: goal_id depends on depends_on_id."""
        if dependency_type not in self.VALID_DEP_TYPES:
            raise ValueError(f"Invalid dependency type: {dependency_type}")
        if goal_id == depends_on_id:
            raise ValueError("A goal cannot depend on itself")

        # Check for circular dependency
        if self._would_create_dep_cycle(goal_id, depends_on_id):
            raise ValueError("Would create circular dependency")

        conn = self._conn()
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT OR IGNORE INTO goal_dependencies
                (goal_id, depends_on_goal_id, dependency_type, created_at)
                VALUES (?, ?, ?, ?)
            """, (goal_id, depends_on_id, dependency_type, now))
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False

    def remove_dependency(self, goal_id: int, depends_on_id: int) -> bool:
        """Remove a dependency."""
        conn = self._conn()
        conn.execute("""
            DELETE FROM goal_dependencies
            WHERE goal_id = ? AND depends_on_goal_id = ?
        """, (goal_id, depends_on_id))
        changed = conn.total_changes
        conn.commit()
        conn.close()
        return changed > 0

    def is_ready(self, goal_id: int) -> bool:
        """Check if a goal has all blocking dependencies completed."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT g.status FROM goal_dependencies d
            JOIN goals g ON g.id = d.depends_on_goal_id
            WHERE d.goal_id = ? AND d.dependency_type = 'blocks'
        """, (goal_id,)).fetchall()
        conn.close()
        return all(row["status"] == "completed" for row in rows)

    def get_blocked_by(self, goal_id: int) -> list[Goal]:
        """Get goals that are blocking this goal."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT g.* FROM goal_dependencies d
            JOIN goals g ON g.id = d.depends_on_goal_id
            WHERE d.goal_id = ? AND d.dependency_type = 'blocks'
            AND g.status != 'completed'
        """, (goal_id,)).fetchall()
        conn.close()
        return [self._row_to_goal(r) for r in rows]

    def get_dependents(self, goal_id: int) -> list[Goal]:
        """Get goals that depend on this goal."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT g.* FROM goal_dependencies d
            JOIN goals g ON g.id = d.goal_id
            WHERE d.depends_on_goal_id = ?
        """, (goal_id,)).fetchall()
        conn.close()
        return [self._row_to_goal(r) for r in rows]

    def _would_create_dep_cycle(self, goal_id: int, depends_on_id: int) -> bool:
        """Check if adding this dependency would create a cycle."""
        # Walk the dependency graph from depends_on_id to see if we reach goal_id
        conn = self._conn()
        visited = set()
        stack = [depends_on_id]
        while stack:
            current = stack.pop()
            if current == goal_id:
                conn.close()
                return True
            if current in visited:
                continue
            visited.add(current)
            rows = conn.execute("""
                SELECT depends_on_goal_id FROM goal_dependencies
                WHERE goal_id = ?
            """, (current,)).fetchall()
            for row in rows:
                stack.append(row["depends_on_goal_id"])
        conn.close()
        return False

    # ─── PROGRESS ──────────────────────────────────────────────

    def update_progress(self, goal_id: int, progress_pct: float) -> bool:
        """Update progress for a goal (0-100)."""
        progress_pct = max(0.0, min(100.0, progress_pct))
        return self.update_goal(goal_id, progress_pct=progress_pct)

    def rollup_progress(self, goal_id: int) -> float:
        """Calculate progress from children using weighted average.
        Weight is based on priority (critical=4, high=3, medium=2, low=1).
        Returns the computed progress percentage.
        """
        children = self.get_children(goal_id)
        if not children:
            goal = self.get_goal(goal_id)
            return goal.progress_pct if goal else 0.0

        # First rollup each child recursively
        for child in children:
            grandchildren = self.get_children(child.id)
            if grandchildren:
                self.rollup_progress(child.id)

        # Reload children after recursive rollups
        children = self.get_children(goal_id)

        weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        total_weight = sum(weights.get(c.priority, 2) for c in children)
        if total_weight == 0:
            return 0.0

        weighted_progress = sum(
            c.progress_pct * weights.get(c.priority, 2)
            for c in children
        )
        progress = weighted_progress / total_weight

        self.update_goal(goal_id, progress_pct=round(progress, 1))
        return round(progress, 1)

    def complete_goal(self, goal_id: int) -> bool:
        """Mark a goal as completed with 100% progress."""
        result = self.update_goal(goal_id, status="completed", progress_pct=100.0)
        if result:
            # Auto-rollup parent
            goal = self.get_goal(goal_id)
            if goal and goal.parent_goal_id:
                self.rollup_progress(goal.parent_goal_id)
        return result

    # ─── QUERIES ───────────────────────────────────────────────

    def list_goals(self, project: Optional[str] = None,
                   status: Optional[str] = None,
                   priority: Optional[str] = None,
                   domain: Optional[str] = None) -> list[Goal]:
        """List goals with optional filters."""
        conn = self._conn()
        sql = "SELECT * FROM goals WHERE 1=1"
        params = []

        if project:
            sql += " AND project = ?"
            params.append(project)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if priority:
            sql += " AND priority = ?"
            params.append(priority)
        if domain:
            sql += " AND domain = ?"
            params.append(domain)

        sql += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, created_at"

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [self._row_to_goal(r) for r in rows]

    def search_goals(self, query: str) -> list[Goal]:
        """Search goals by title, description, or notes."""
        conn = self._conn()
        like = f"%{query}%"
        rows = conn.execute("""
            SELECT * FROM goals
            WHERE title LIKE ? OR description LIKE ? OR notes LIKE ?
            ORDER BY priority, created_at
        """, (like, like, like)).fetchall()
        conn.close()
        return [self._row_to_goal(r) for r in rows]

    def get_actionable(self) -> list[Goal]:
        """Get goals that are active, have no blocking dependencies,
        and are leaf goals (no children). These are the ones to work on NOW."""
        conn = self._conn()
        # Active goals with no children
        rows = conn.execute("""
            SELECT g.* FROM goals g
            WHERE g.status = 'active'
            AND g.id NOT IN (SELECT DISTINCT parent_goal_id FROM goals WHERE parent_goal_id IS NOT NULL)
            ORDER BY CASE g.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END,
                     g.created_at
        """).fetchall()
        conn.close()

        goals = [self._row_to_goal(r) for r in rows]
        # Filter out those blocked by uncompleted dependencies
        return [g for g in goals if self.is_ready(g.id)]

    def get_stale(self, days: int = 14) -> list[Goal]:
        """Get active goals with no updates in the given number of days."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM goals
            WHERE status = 'active' AND updated_at < ?
            ORDER BY updated_at ASC
        """, (cutoff,)).fetchall()
        conn.close()
        return [self._row_to_goal(r) for r in rows]

    # ─── INTEGRATION ───────────────────────────────────────────

    def link_task_to_goal(self, goal_id: int, task_description: str) -> bool:
        """Record that a task was linked to this goal."""
        conn = self._conn()
        self._record_event(conn, goal_id, "linked_task", "", task_description)
        conn.commit()
        conn.close()
        return True

    def on_task_completed(self, goal_id: int, task_description: str,
                          progress_increment: float = 0) -> bool:
        """Record a task completion and optionally increment progress."""
        goal = self.get_goal(goal_id)
        if not goal:
            return False

        conn = self._conn()
        self._record_event(conn, goal_id, "completed_task", "", task_description)
        conn.commit()
        conn.close()

        if progress_increment > 0:
            new_progress = min(100.0, goal.progress_pct + progress_increment)
            self.update_progress(goal_id, new_progress)

        return True

    def sync_to_brain(self, brain_path: Optional[str] = None) -> bool:
        """Sync active goals to brain.json for session persistence."""
        if brain_path is None:
            brain_path = str(Path("/mnt/d/_CLAUDE-TOOLS/brain.json"))

        brain_file = Path(brain_path)
        if brain_file.exists():
            try:
                brain = json.loads(brain_file.read_text())
            except (json.JSONDecodeError, OSError):
                brain = {}
        else:
            brain = {}

        # Build goal summaries
        active_goals = self.list_goals(status="active")
        completed_recent = self._get_recently_completed(days=7)

        brain["goals"] = {
            "active": [
                {
                    "id": g.id,
                    "title": g.title,
                    "priority": g.priority,
                    "progress": g.progress_pct,
                    "project": g.project,
                    "domain": g.domain,
                }
                for g in active_goals
            ],
            "recently_completed": [
                {
                    "id": g.id,
                    "title": g.title,
                    "completed_at": g.updated_at,
                }
                for g in completed_recent
            ],
            "summary": f"{len(active_goals)} active, {len(completed_recent)} completed this week",
            "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        try:
            brain_file.write_text(json.dumps(brain, indent=2))
            return True
        except OSError:
            return False

    def to_memory_summary(self) -> str:
        """Generate a summary suitable for memory storage."""
        active = self.list_goals(status="active")
        if not active:
            return "No active goals."

        lines = [f"Active goals ({len(active)}):"]
        for g in active[:10]:
            lines.append(f"- [{g.priority.upper()}] {g.title} ({g.progress_pct:.0f}%)")
        return "\n".join(lines)

    def get_events(self, goal_id: int, limit: int = 20) -> list[GoalEvent]:
        """Get audit trail for a goal."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM goal_events
            WHERE goal_id = ? ORDER BY timestamp DESC LIMIT ?
        """, (goal_id, limit)).fetchall()
        conn.close()
        return [
            GoalEvent(
                id=r["id"], goal_id=r["goal_id"],
                event_type=r["event_type"],
                old_value=r["old_value"], new_value=r["new_value"],
                details=r["details"], timestamp=r["timestamp"]
            )
            for r in rows
        ]

    # ─── INTERNALS ─────────────────────────────────────────────

    def _row_to_goal(self, row: sqlite3.Row) -> Goal:
        return Goal(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            parent_goal_id=row["parent_goal_id"],
            project=row["project"] or "",
            status=row["status"] or "draft",
            priority=row["priority"] or "medium",
            progress_pct=row["progress_pct"] or 0.0,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            deadline=row["deadline"],
            tags=row["tags"] or "[]",
            domain=row["domain"] or "general",
            source=row["source"] or "manual",
            notes=row["notes"] or "",
        )

    def _record_event(self, conn: sqlite3.Connection, goal_id: int,
                      event_type: str, old_value: str = "",
                      new_value: str = "", details: str = ""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO goal_events (goal_id, event_type, old_value, new_value, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (goal_id, event_type, old_value, new_value, details, now))

    def _get_recently_completed(self, days: int = 7) -> list[Goal]:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM goals
            WHERE status = 'completed' AND updated_at >= ?
            ORDER BY updated_at DESC
        """, (cutoff,)).fetchall()
        conn.close()
        return [self._row_to_goal(r) for r in rows]

    # ─── DISPLAY ───────────────────────────────────────────────

    def format_tree(self, goals: list[Goal], indent: int = 0) -> str:
        """Format a goal tree for display."""
        lines = []
        for g in goals:
            prefix = "  " * indent
            status_icon = {
                "draft": "[ ]", "active": "[>]", "blocked": "[!]",
                "completed": "[x]", "abandoned": "[-]"
            }.get(g.status, "[ ]")
            prio = {"critical": "!!!", "high": "!!", "medium": "!", "low": "~"}.get(g.priority, "!")
            lines.append(f"{prefix}{status_icon} {prio} #{g.id} {g.title} ({g.progress_pct:.0f}%)")
            if g.children:
                lines.append(self.format_tree(g.children, indent + 1))
        return "\n".join(lines)


# ─── CLI ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Goal Engine v1.0")
    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list", help="List goals")
    p_list.add_argument("--project", default=None)
    p_list.add_argument("--status", default=None)
    p_list.add_argument("--priority", default=None)
    p_list.add_argument("--domain", default=None)
    p_list.add_argument("--db", default=None)

    # create
    p_create = sub.add_parser("create", help="Create a goal")
    p_create.add_argument("title")
    p_create.add_argument("--description", default="")
    p_create.add_argument("--parent", type=int, default=None)
    p_create.add_argument("--project", default="")
    p_create.add_argument("--priority", default="medium")
    p_create.add_argument("--status", default="draft")
    p_create.add_argument("--domain", default="general")
    p_create.add_argument("--deadline", default=None)
    p_create.add_argument("--db", default=None)

    # update
    p_update = sub.add_parser("update", help="Update a goal")
    p_update.add_argument("id", type=int)
    p_update.add_argument("--title", default=None)
    p_update.add_argument("--status", default=None)
    p_update.add_argument("--priority", default=None)
    p_update.add_argument("--progress", type=float, default=None)
    p_update.add_argument("--notes", default=None)
    p_update.add_argument("--db", default=None)

    # complete
    p_complete = sub.add_parser("complete", help="Complete a goal")
    p_complete.add_argument("id", type=int)
    p_complete.add_argument("--db", default=None)

    # tree
    p_tree = sub.add_parser("tree", help="Show goal tree")
    p_tree.add_argument("id", type=int, nargs="?", default=None)
    p_tree.add_argument("--db", default=None)

    # actionable
    p_act = sub.add_parser("actionable", help="Show actionable goals")
    p_act.add_argument("--db", default=None)

    # events
    p_events = sub.add_parser("events", help="Show goal events")
    p_events.add_argument("id", type=int)
    p_events.add_argument("--limit", type=int, default=20)
    p_events.add_argument("--db", default=None)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    db = getattr(args, "db", None)
    engine = GoalEngine(db_path=db)

    if args.command == "list":
        goals = engine.list_goals(project=args.project, status=args.status,
                                  priority=args.priority, domain=args.domain)
        if not goals:
            print("No goals found.")
            return
        print(f"Goals ({len(goals)}):\n")
        for g in goals:
            status_icon = {"draft": "[ ]", "active": "[>]", "blocked": "[!]",
                           "completed": "[x]", "abandoned": "[-]"}.get(g.status, "[ ]")
            print(f"  {status_icon} #{g.id} [{g.priority}] {g.title} ({g.progress_pct:.0f}%)")
            if g.description:
                print(f"       {g.description[:60]}")

    elif args.command == "create":
        goal_id = engine.create_goal(
            title=args.title, description=args.description,
            parent_goal_id=args.parent, project=args.project,
            priority=args.priority, status=args.status,
            domain=args.domain, deadline=args.deadline,
        )
        print(f"Created goal #{goal_id}: {args.title}")

    elif args.command == "update":
        updates = {}
        if args.title: updates["title"] = args.title
        if args.status: updates["status"] = args.status
        if args.priority: updates["priority"] = args.priority
        if args.progress is not None: updates["progress_pct"] = args.progress
        if args.notes: updates["notes"] = args.notes

        if engine.update_goal(args.id, **updates):
            print(f"Updated goal #{args.id}")
        else:
            print(f"Goal #{args.id} not found")

    elif args.command == "complete":
        if engine.complete_goal(args.id):
            print(f"Completed goal #{args.id}")
        else:
            print(f"Goal #{args.id} not found")

    elif args.command == "tree":
        trees = engine.get_tree(args.id)
        if trees:
            print(engine.format_tree(trees))
        else:
            print("No goals found.")

    elif args.command == "actionable":
        goals = engine.get_actionable()
        if not goals:
            print("No actionable goals. Create some or unblock existing ones.")
            return
        print(f"Actionable goals ({len(goals)}):\n")
        for g in goals:
            prio = {"critical": "!!!", "high": "!!", "medium": "!", "low": "~"}.get(g.priority, "!")
            print(f"  {prio} #{g.id} {g.title} ({g.progress_pct:.0f}%)")

    elif args.command == "events":
        events = engine.get_events(args.id, limit=args.limit)
        if not events:
            print(f"No events for goal #{args.id}")
            return
        print(f"Events for goal #{args.id}:\n")
        for e in events:
            print(f"  [{e.timestamp}] {e.event_type}: {e.old_value} -> {e.new_value}")
            if e.details:
                print(f"    {e.details}")


if __name__ == "__main__":
    main()
