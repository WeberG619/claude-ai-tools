"""
Agent Coordinator v1.0
=======================
Cross-agent coordination: session tracking, resource locking,
shared state, handoff validation, and conflict detection.

Tracks which agents are active within a workflow, prevents resource
conflicts, enables state sharing between agents, and ensures clean
handoffs between sequential agents.

Usage:
    from coordinator import AgentCoordinator

    coord = AgentCoordinator()

    # Start a workflow
    wf_id = coord.start_workflow("pdf-to-revit", project="Avon Park")

    # Register agents
    coord.register_agent(wf_id, "floor-plan-processor", agent_type="explorer")
    coord.agent_started(wf_id, "floor-plan-processor")

    # Resource locking
    coord.acquire_lock("file", "/path/to/plan.pdf", wf_id, "floor-plan-processor")

    # Share state between agents
    coord.set_state(wf_id, "extracted_walls", json.dumps(walls), "floor-plan-processor")
    walls_json = coord.get_state(wf_id, "extracted_walls")

    # Agent completion
    coord.agent_completed(wf_id, "floor-plan-processor", result_summary="Extracted 24 walls")

    # Cleanup
    coord.release_all_locks(wf_id, "floor-plan-processor")

CLI:
    python coordinator.py status
    python coordinator.py workflows
    python coordinator.py locks
    python coordinator.py cleanup
"""

import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ─── DATA CLASSES ──────────────────────────────────────────────

@dataclass
class AgentSession:
    """Tracks an agent within a workflow."""
    id: int = 0
    session_id: str = ""
    agent_name: str = ""
    agent_type: str = ""
    status: str = "registered"  # registered|running|completed|failed
    parent_session_id: str = ""
    parent_agent: str = ""
    started_at: str = ""
    completed_at: str = ""
    prompt_hash: str = ""
    result_summary: str = ""
    artifacts: str = "[]"
    resources_locked: str = "[]"
    error: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_summary": self.result_summary,
            "error": self.error,
        }


@dataclass
class ResourceLock:
    """A lock on a shared resource."""
    id: int = 0
    resource_type: str = ""  # file|revit_model|excel_workbook|database|api
    resource_id: str = ""
    locked_by_session: str = ""
    locked_by_agent: str = ""
    lock_type: str = "exclusive"  # exclusive|shared
    acquired_at: str = ""
    expires_at: str = ""
    released_at: str = ""

    @property
    def is_active(self) -> bool:
        if self.released_at:
            return False
        if self.expires_at:
            try:
                exp = datetime.strptime(self.expires_at, "%Y-%m-%d %H:%M:%S")
                return datetime.now() < exp
            except ValueError:
                return True
        return True


@dataclass
class WorkflowState:
    """Summary of a workflow's current state."""
    session_id: str = ""
    project: str = ""
    status: str = "active"
    agents: list[AgentSession] = field(default_factory=list)
    shared_state_keys: list[str] = field(default_factory=list)
    active_locks: list[ResourceLock] = field(default_factory=list)
    started_at: str = ""


# ─── AGENT COORDINATOR ────────────────────────────────────────

class AgentCoordinator:
    """
    Coordinates agents within workflows: session tracking, resource locking,
    shared state, handoff validation, and conflict detection.
    """

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
        return conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                agent_type TEXT DEFAULT '',
                status TEXT DEFAULT 'registered',
                parent_session_id TEXT DEFAULT '',
                parent_agent TEXT DEFAULT '',
                started_at TEXT,
                completed_at TEXT,
                prompt_hash TEXT DEFAULT '',
                result_summary TEXT DEFAULT '',
                artifacts TEXT DEFAULT '[]',
                resources_locked TEXT DEFAULT '[]',
                error TEXT DEFAULT '',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS resource_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                locked_by_session TEXT NOT NULL,
                locked_by_agent TEXT DEFAULT '',
                lock_type TEXT DEFAULT 'exclusive',
                acquired_at TEXT,
                expires_at TEXT,
                released_at TEXT
            );

            CREATE TABLE IF NOT EXISTS shared_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT DEFAULT '',
                set_by_agent TEXT DEFAULT '',
                set_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_agent_sessions_session
                ON agent_sessions(session_id);
            CREATE INDEX IF NOT EXISTS idx_resource_locks_resource
                ON resource_locks(resource_type, resource_id);
            CREATE INDEX IF NOT EXISTS idx_shared_state_session
                ON shared_state(session_id, key);
        """)
        conn.commit()
        conn.close()

    # ─── SESSIONS ──────────────────────────────────────────────

    def start_workflow(self, name: str = "", project: str = "",
                       parent_session_id: str = "") -> str:
        """Start a new workflow session. Returns the session ID."""
        session_id = f"wf-{uuid.uuid4().hex[:12]}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self._conn()
        conn.execute("""
            INSERT INTO agent_sessions
            (session_id, agent_name, agent_type, status,
             parent_session_id, started_at, created_at)
            VALUES (?, ?, 'workflow', 'running', ?, ?, ?)
        """, (session_id, name or "workflow", parent_session_id, now, now))
        conn.commit()
        conn.close()
        return session_id

    def register_agent(self, session_id: str, agent_name: str,
                       agent_type: str = "", parent_agent: str = "") -> bool:
        """Register an agent within a workflow session."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute("""
            INSERT INTO agent_sessions
            (session_id, agent_name, agent_type, status,
             parent_agent, created_at)
            VALUES (?, ?, ?, 'registered', ?, ?)
        """, (session_id, agent_name, agent_type, parent_agent, now))
        conn.commit()
        conn.close()
        return True

    def agent_started(self, session_id: str, agent_name: str) -> bool:
        """Mark an agent as running."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute("""
            UPDATE agent_sessions SET status = 'running', started_at = ?
            WHERE session_id = ? AND agent_name = ? AND status = 'registered'
        """, (now, session_id, agent_name))
        conn.commit()
        conn.close()
        return True

    def agent_completed(self, session_id: str, agent_name: str,
                        result_summary: str = "", artifacts: Optional[list] = None) -> bool:
        """Mark an agent as completed."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute("""
            UPDATE agent_sessions SET status = 'completed', completed_at = ?,
                   result_summary = ?, artifacts = ?
            WHERE session_id = ? AND agent_name = ? AND status = 'running'
        """, (now, result_summary, json.dumps(artifacts or []),
              session_id, agent_name))
        conn.commit()
        conn.close()

        # Auto-release locks
        self.release_all_locks(session_id, agent_name)
        return True

    def agent_failed(self, session_id: str, agent_name: str,
                     error: str = "") -> bool:
        """Mark an agent as failed."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute("""
            UPDATE agent_sessions SET status = 'failed', completed_at = ?, error = ?
            WHERE session_id = ? AND agent_name = ? AND status = 'running'
        """, (now, error, session_id, agent_name))
        conn.commit()
        conn.close()

        # Auto-release locks
        self.release_all_locks(session_id, agent_name)
        return True

    def get_workflow_status(self, session_id: str) -> Optional[WorkflowState]:
        """Get the current status of a workflow."""
        conn = self._conn()

        agents = conn.execute("""
            SELECT * FROM agent_sessions WHERE session_id = ?
            ORDER BY created_at
        """, (session_id,)).fetchall()

        if not agents:
            conn.close()
            return None

        locks = conn.execute("""
            SELECT * FROM resource_locks
            WHERE locked_by_session = ? AND released_at IS NULL
        """, (session_id,)).fetchall()

        state_keys = conn.execute("""
            SELECT DISTINCT key FROM shared_state WHERE session_id = ?
        """, (session_id,)).fetchall()

        conn.close()

        wf = WorkflowState(
            session_id=session_id,
            agents=[self._row_to_session(a) for a in agents],
            active_locks=[self._row_to_lock(l) for l in locks],
            shared_state_keys=[r["key"] for r in state_keys],
            started_at=agents[0]["started_at"] or agents[0]["created_at"],
        )

        # Determine overall status (exclude workflow root from calculation)
        real_agents = [a for a in agents if a["agent_type"] != "workflow"]
        if not real_agents:
            wf.status = "pending"
        else:
            statuses = {a["status"] for a in real_agents}
            if "running" in statuses:
                wf.status = "active"
            elif "failed" in statuses:
                wf.status = "failed"
            elif all(s == "completed" for s in statuses):
                wf.status = "completed"
            else:
                wf.status = "pending"

        return wf

    # ─── RESOURCE LOCKING ─────────────────────────────────────

    def acquire_lock(self, resource_type: str, resource_id: str,
                     session_id: str, agent_name: str,
                     lock_type: str = "exclusive",
                     timeout_minutes: int = 30) -> bool:
        """Acquire a lock on a resource. Returns False if already locked."""
        # Check for existing active locks
        conflict = self.check_conflict(resource_type, resource_id,
                                        lock_type, session_id)
        if conflict:
            return False

        now = datetime.now()
        expires = now + timedelta(minutes=timeout_minutes)

        conn = self._conn()
        conn.execute("""
            INSERT INTO resource_locks
            (resource_type, resource_id, locked_by_session, locked_by_agent,
             lock_type, acquired_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (resource_type, resource_id, session_id, agent_name,
              lock_type,
              now.strftime("%Y-%m-%d %H:%M:%S"),
              expires.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True

    def release_lock(self, resource_type: str, resource_id: str,
                     session_id: str) -> bool:
        """Release a specific lock."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute("""
            UPDATE resource_locks SET released_at = ?
            WHERE resource_type = ? AND resource_id = ?
            AND locked_by_session = ? AND released_at IS NULL
        """, (now, resource_type, resource_id, session_id))
        conn.commit()
        conn.close()
        return True

    def release_all_locks(self, session_id: str, agent_name: str = "") -> int:
        """Release all locks held by a session (or specific agent in session)."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()

        if agent_name:
            conn.execute("""
                UPDATE resource_locks SET released_at = ?
                WHERE locked_by_session = ? AND locked_by_agent = ?
                AND released_at IS NULL
            """, (now, session_id, agent_name))
        else:
            conn.execute("""
                UPDATE resource_locks SET released_at = ?
                WHERE locked_by_session = ? AND released_at IS NULL
            """, (now, session_id))

        count = conn.total_changes
        conn.commit()
        conn.close()
        return count

    def check_conflict(self, resource_type: str, resource_id: str,
                       requested_type: str = "exclusive",
                       requesting_session: str = "") -> Optional[ResourceLock]:
        """Check if a resource lock would conflict. Returns the conflicting lock or None."""
        conn = self._conn()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rows = conn.execute("""
            SELECT * FROM resource_locks
            WHERE resource_type = ? AND resource_id = ?
            AND released_at IS NULL
            AND (expires_at IS NULL OR expires_at > ?)
        """, (resource_type, resource_id, now)).fetchall()
        conn.close()

        for row in rows:
            lock = self._row_to_lock(row)
            # Same session can re-acquire
            if lock.locked_by_session == requesting_session:
                continue
            # Exclusive lock blocks everything
            if lock.lock_type == "exclusive":
                return lock
            # Shared lock blocks exclusive requests
            if requested_type == "exclusive" and lock.lock_type == "shared":
                return lock

        return None

    def detect_conflicts(self, session_id: str) -> list[dict]:
        """Detect all resource conflicts for a workflow."""
        conn = self._conn()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Find all active locks for this session
        our_locks = conn.execute("""
            SELECT * FROM resource_locks
            WHERE locked_by_session = ? AND released_at IS NULL
            AND (expires_at IS NULL OR expires_at > ?)
        """, (session_id, now)).fetchall()

        conflicts = []
        for lock in our_locks:
            # Check if any other session holds a conflicting lock
            others = conn.execute("""
                SELECT * FROM resource_locks
                WHERE resource_type = ? AND resource_id = ?
                AND locked_by_session != ?
                AND released_at IS NULL
                AND (expires_at IS NULL OR expires_at > ?)
            """, (lock["resource_type"], lock["resource_id"],
                  session_id, now)).fetchall()

            for other in others:
                conflicts.append({
                    "resource_type": lock["resource_type"],
                    "resource_id": lock["resource_id"],
                    "our_agent": lock["locked_by_agent"],
                    "their_session": other["locked_by_session"],
                    "their_agent": other["locked_by_agent"],
                    "our_lock_type": lock["lock_type"],
                    "their_lock_type": other["lock_type"],
                })

        conn.close()
        return conflicts

    # ─── SHARED STATE ──────────────────────────────────────────

    def set_state(self, session_id: str, key: str, value: str,
                  agent_name: str = "") -> bool:
        """Set a shared state value within a workflow."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()

        # Upsert
        existing = conn.execute("""
            SELECT id FROM shared_state
            WHERE session_id = ? AND key = ?
        """, (session_id, key)).fetchone()

        if existing:
            conn.execute("""
                UPDATE shared_state SET value = ?, set_by_agent = ?, set_at = ?
                WHERE session_id = ? AND key = ?
            """, (value, agent_name, now, session_id, key))
        else:
            conn.execute("""
                INSERT INTO shared_state (session_id, key, value, set_by_agent, set_at)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, key, value, agent_name, now))

        conn.commit()
        conn.close()
        return True

    def get_state(self, session_id: str, key: str) -> Optional[str]:
        """Get a shared state value."""
        conn = self._conn()
        row = conn.execute("""
            SELECT value FROM shared_state
            WHERE session_id = ? AND key = ?
        """, (session_id, key)).fetchone()
        conn.close()
        return row["value"] if row else None

    def get_accumulated_context(self, session_id: str) -> dict:
        """Get all shared state for a workflow as a dict."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT key, value, set_by_agent FROM shared_state
            WHERE session_id = ?
        """, (session_id,)).fetchall()
        conn.close()
        return {r["key"]: {"value": r["value"], "set_by": r["set_by_agent"]} for r in rows}

    # ─── HANDOFF ───────────────────────────────────────────────

    def validate_handoff(self, session_id: str, from_agent: str,
                         to_agent: str) -> dict:
        """Validate that a handoff between agents is clean."""
        issues = []

        conn = self._conn()

        # Check from_agent is completed
        from_row = conn.execute("""
            SELECT status FROM agent_sessions
            WHERE session_id = ? AND agent_name = ?
            ORDER BY created_at DESC LIMIT 1
        """, (session_id, from_agent)).fetchone()

        if not from_row:
            issues.append(f"Agent '{from_agent}' not found in session")
        elif from_row["status"] != "completed":
            issues.append(f"Agent '{from_agent}' status is '{from_row['status']}', expected 'completed'")

        # Check for unreleased locks from from_agent
        locks = conn.execute("""
            SELECT * FROM resource_locks
            WHERE locked_by_session = ? AND locked_by_agent = ?
            AND released_at IS NULL
        """, (session_id, from_agent)).fetchall()

        if locks:
            resources = [f"{l['resource_type']}:{l['resource_id']}" for l in locks]
            issues.append(f"Unreleased locks from '{from_agent}': {resources}")

        # Check to_agent is registered
        to_row = conn.execute("""
            SELECT status FROM agent_sessions
            WHERE session_id = ? AND agent_name = ?
            ORDER BY created_at DESC LIMIT 1
        """, (session_id, to_agent)).fetchone()

        if not to_row:
            issues.append(f"Agent '{to_agent}' not registered in session")

        conn.close()

        return {
            "valid": len(issues) == 0,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "issues": issues,
        }

    def record_handoff(self, session_id: str, from_agent: str,
                       to_agent: str, context: str = "") -> bool:
        """Record a handoff event."""
        if context:
            self.set_state(session_id, f"handoff_{from_agent}_to_{to_agent}",
                          context, from_agent)
        return True

    # ─── MONITORING ────────────────────────────────────────────

    def aggregate_results(self, session_id: str) -> dict:
        """Aggregate results from all agents in a workflow."""
        conn = self._conn()
        agents = conn.execute("""
            SELECT * FROM agent_sessions
            WHERE session_id = ? AND agent_type != 'workflow'
            ORDER BY created_at
        """, (session_id,)).fetchall()
        conn.close()

        if not agents:
            return {"session_id": session_id, "agents": 0}

        total = len(agents)
        completed = sum(1 for a in agents if a["status"] == "completed")
        failed = sum(1 for a in agents if a["status"] == "failed")
        running = sum(1 for a in agents if a["status"] == "running")

        summaries = []
        for a in agents:
            if a["result_summary"]:
                summaries.append(f"[{a['agent_name']}] {a['result_summary']}")

        return {
            "session_id": session_id,
            "agents": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": completed / total if total > 0 else 0,
            "summaries": summaries,
        }

    def get_active_agents(self, session_id: Optional[str] = None) -> list[AgentSession]:
        """Get currently running agents (excludes workflow root sessions)."""
        conn = self._conn()
        if session_id:
            rows = conn.execute("""
                SELECT * FROM agent_sessions
                WHERE session_id = ? AND status = 'running'
                AND agent_type != 'workflow'
            """, (session_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM agent_sessions WHERE status = 'running'
                AND agent_type != 'workflow'
            """).fetchall()
        conn.close()
        return [self._row_to_session(r) for r in rows]

    def get_idle_agents(self, session_id: str) -> list[AgentSession]:
        """Get registered but not-yet-started agents."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM agent_sessions
            WHERE session_id = ? AND status = 'registered'
        """, (session_id,)).fetchall()
        conn.close()
        return [self._row_to_session(r) for r in rows]

    def cleanup_stale(self, timeout_minutes: int = 60) -> dict:
        """Cleanup stale sessions and expired locks."""
        now = datetime.now()
        cutoff = (now - timedelta(minutes=timeout_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        conn = self._conn()

        # Release expired locks
        expired_locks = conn.execute("""
            UPDATE resource_locks SET released_at = ?
            WHERE released_at IS NULL AND expires_at < ?
        """, (now_str, now_str))
        expired_count = conn.total_changes

        # Mark stale running agents as failed
        stale_agents = conn.execute("""
            UPDATE agent_sessions SET status = 'failed',
                   error = 'Timed out (stale cleanup)',
                   completed_at = ?
            WHERE status = 'running' AND started_at < ?
        """, (now_str, cutoff))
        stale_count = conn.total_changes

        conn.commit()
        conn.close()

        return {
            "expired_locks_released": expired_count,
            "stale_agents_failed": stale_count,
        }

    # ─── DISPATCH INTEGRATION ─────────────────────────────────

    def enhance_dispatch_prompt(self, session_id: str, agent_name: str,
                                 base_prompt: str) -> str:
        """Add workflow context to an agent's prompt."""
        parts = [base_prompt]

        # Add accumulated context (with compression for large values)
        context = self.get_accumulated_context(session_id)
        if context:
            try:
                from aggregator import Aggregator
                agg = Aggregator(strategy="heuristic")
                parts.append("\n## Workflow Context (compressed)")
                for key, info in context.items():
                    value = info["value"]
                    if len(value) > 500:
                        compressed = agg._extract_key_lines(value)
                        value_preview = "\n".join(compressed[:5])
                    else:
                        value_preview = value
                    parts.append(f"- **{key}** (from {info['set_by']}): {value_preview}")
            except ImportError:
                parts.append("\n## Workflow Context (from prior agents)")
                for key, info in context.items():
                    value_preview = info["value"][:500] if len(info["value"]) > 500 else info["value"]
                    parts.append(f"- **{key}** (set by {info['set_by']}): {value_preview}")

        # Add active agent info
        active = self.get_active_agents(session_id)
        other_active = [a for a in active if a.agent_name != agent_name]
        if other_active:
            parts.append(f"\n## Active Agents ({len(other_active)} running)")
            for a in other_active:
                parts.append(f"- {a.agent_name} ({a.agent_type})")

        return "\n".join(parts)

    # ─── INTERNALS ─────────────────────────────────────────────

    def _row_to_session(self, row: sqlite3.Row) -> AgentSession:
        return AgentSession(
            id=row["id"],
            session_id=row["session_id"],
            agent_name=row["agent_name"],
            agent_type=row["agent_type"] or "",
            status=row["status"] or "registered",
            parent_session_id=row["parent_session_id"] or "",
            parent_agent=row["parent_agent"] or "",
            started_at=row["started_at"] or "",
            completed_at=row["completed_at"] or "",
            prompt_hash=row["prompt_hash"] or "",
            result_summary=row["result_summary"] or "",
            artifacts=row["artifacts"] or "[]",
            resources_locked=row["resources_locked"] or "[]",
            error=row["error"] or "",
            created_at=row["created_at"] or "",
        )

    def _row_to_lock(self, row: sqlite3.Row) -> ResourceLock:
        return ResourceLock(
            id=row["id"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            locked_by_session=row["locked_by_session"],
            locked_by_agent=row["locked_by_agent"] or "",
            lock_type=row["lock_type"] or "exclusive",
            acquired_at=row["acquired_at"] or "",
            expires_at=row["expires_at"] or "",
            released_at=row["released_at"] or "",
        )


# ─── CLI ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Coordinator v1.0")
    sub = parser.add_subparsers(dest="command")

    # status
    p_status = sub.add_parser("status", help="Show coordinator status")
    p_status.add_argument("--session", default=None)
    p_status.add_argument("--db", default=None)

    # workflows
    p_wf = sub.add_parser("workflows", help="List active workflows")
    p_wf.add_argument("--db", default=None)

    # locks
    p_locks = sub.add_parser("locks", help="Show active locks")
    p_locks.add_argument("--db", default=None)

    # cleanup
    p_clean = sub.add_parser("cleanup", help="Cleanup stale data")
    p_clean.add_argument("--timeout", type=int, default=60)
    p_clean.add_argument("--db", default=None)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    db = getattr(args, "db", None)
    coord = AgentCoordinator(db_path=db)

    if args.command == "status":
        if args.session:
            wf = coord.get_workflow_status(args.session)
            if not wf:
                print(f"Workflow {args.session} not found")
                return
            print(f"Workflow: {wf.session_id}")
            print(f"Status: {wf.status}")
            print(f"Agents: {len(wf.agents)}")
            print(f"Locks: {len(wf.active_locks)}")
            print(f"State keys: {wf.shared_state_keys}")
            for a in wf.agents:
                icon = {"running": "[>]", "completed": "[x]", "failed": "[!]",
                        "registered": "[ ]"}.get(a.status, "[ ]")
                print(f"  {icon} {a.agent_name} ({a.agent_type})")
        else:
            active = coord.get_active_agents()
            print(f"Active agents: {len(active)}")
            for a in active:
                print(f"  [>] {a.agent_name} in {a.session_id}")

    elif args.command == "workflows":
        conn = coord._conn()
        rows = conn.execute("""
            SELECT DISTINCT session_id FROM agent_sessions
            WHERE agent_type = 'workflow'
            ORDER BY created_at DESC LIMIT 20
        """).fetchall()
        conn.close()

        for r in rows:
            wf = coord.get_workflow_status(r["session_id"])
            if wf:
                print(f"  [{wf.status:10s}] {wf.session_id} ({len(wf.agents)} agents)")

    elif args.command == "locks":
        conn = coord._conn()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute("""
            SELECT * FROM resource_locks
            WHERE released_at IS NULL
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY acquired_at DESC
        """, (now,)).fetchall()
        conn.close()

        if not rows:
            print("No active locks.")
            return
        print(f"Active locks ({len(rows)}):")
        for r in rows:
            print(f"  [{r['lock_type']:9s}] {r['resource_type']}:{r['resource_id']}")
            print(f"  {'':12s} by {r['locked_by_agent']} in {r['locked_by_session']}")

    elif args.command == "cleanup":
        result = coord.cleanup_stale(timeout_minutes=args.timeout)
        print(f"Cleanup results:")
        for k, v in result.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
