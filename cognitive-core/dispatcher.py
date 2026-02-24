#!/usr/bin/env python3
"""
Cognitive Dispatcher — The bridge between events and intelligent action.

Before this existed, events fired actions directly:
  File changed → run validation
  Email arrived → notify user
  Revit opened → load context

Now events go through the cognitive core first:
  Event → Assess → Think → Decide → Route → Queue → Execute → Evaluate

This is what makes the system "think before acting."

Key features:
1. Event intake from any source (triggers, watchers, manual, scheduled)
2. Goal-aware filtering (should we even act on this?)
3. Cognitive routing (which framework, which model)
4. Task queuing into the autonomous-agent executor
5. Outcome evaluation after tasks complete
6. Pattern learning from event→outcome pairs

Usage:
    from dispatcher import CognitiveDispatcher
    cd = CognitiveDispatcher()

    # Process an event
    result = cd.dispatch({
        "type": "file_changed",
        "source": "watcher",
        "data": {"path": "/mnt/d/model.rvt", "change": "modified"},
        "priority": "medium"
    })

    # Process with goal awareness
    result = cd.dispatch(event, goal_context="Complete CD set for ResidentialA")

    # Record outcome after task completes
    cd.record_outcome(dispatch_id, success=True, result="Validation passed")
"""

import json
import sqlite3
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

# Cognitive core imports
try:
    from .core import CognitiveCore
    from .evaluator import Evaluator
    from .meta_router import MetaRouter, RoutingDecision
except ImportError:
    from core import CognitiveCore
    from evaluator import Evaluator
    from meta_router import MetaRouter, RoutingDecision

logger = logging.getLogger("cognitive-core.dispatcher")

DB_PATH = Path(__file__).parent / "cognitive.db"
AUTO_AGENT_DB = Path("/mnt/d/_CLAUDE-TOOLS/autonomous-agent/queues/tasks.db")
BOARD_DB = Path("/mnt/d/_CLAUDE-TOOLS/task-board/board.db")


@dataclass
class Event:
    """An event that may trigger cognitive action."""
    type: str = ""                      # file_changed, email_arrived, revit_opened, etc.
    source: str = ""                    # watcher, trigger_engine, autonomous_triggers, manual
    data: dict = field(default_factory=dict)
    priority: str = "medium"            # low, medium, high, critical
    timestamp: str = ""
    goal_context: str = ""              # Optional goal this relates to

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "source": self.source,
            "data": self.data,
            "priority": self.priority,
            "timestamp": self.timestamp or datetime.now().isoformat(),
            "goal_context": self.goal_context,
        }


@dataclass
class DispatchResult:
    """Result of cognitive dispatch."""
    dispatch_id: str = ""
    action_taken: str = ""              # queued, suppressed, deferred, escalated
    reasoning: str = ""
    task_id: str = ""                   # ID in the agent queue (if queued)
    routing: RoutingDecision = None
    goal_relevance: float = 0.0         # 0-1, how relevant to active goals

    def to_dict(self) -> dict:
        return {
            "dispatch_id": self.dispatch_id,
            "action_taken": self.action_taken,
            "reasoning": self.reasoning,
            "task_id": self.task_id,
            "goal_relevance": self.goal_relevance,
        }


# Event type → action mapping
# Defines what kind of cognitive processing each event type gets
EVENT_ACTIONS = {
    # File events
    "file_changed": {"action": "assess_and_maybe_act", "default_priority": "medium"},
    "file_created": {"action": "assess_and_maybe_act", "default_priority": "medium"},
    "model_saved": {"action": "queue_validation", "default_priority": "high"},
    "build_failed": {"action": "queue_investigation", "default_priority": "high"},
    "build_succeeded": {"action": "log_and_learn", "default_priority": "low"},
    "test_failed": {"action": "queue_investigation", "default_priority": "high"},

    # App events
    "revit_opened": {"action": "load_context", "default_priority": "low"},
    "revit_project_changed": {"action": "load_context_and_preflight", "default_priority": "medium"},
    "bluebeam_document": {"action": "offer_markup_extraction", "default_priority": "low"},

    # Email events
    "priority_email": {"action": "assess_and_queue", "default_priority": "high"},
    "invoice_email": {"action": "queue_specific", "default_priority": "medium"},
    "rfp_email": {"action": "queue_specific", "default_priority": "high"},

    # System events
    "memory_high": {"action": "notify_only", "default_priority": "medium"},
    "session_start": {"action": "morning_think", "default_priority": "low"},
    "session_end": {"action": "reflect", "default_priority": "low"},

    # Scheduled events
    "daily_review": {"action": "compile_and_reflect", "default_priority": "low"},
    "weekly_synthesis": {"action": "deep_reflect", "default_priority": "low"},

    # Goal events
    "goal_stalled": {"action": "investigate_blocker", "default_priority": "medium"},
    "goal_deadline": {"action": "escalate_goal", "default_priority": "high"},

    # Task events
    "task_completed": {"action": "update_goals_from_task", "default_priority": "low"},
}

# Suppression rules: events to ignore under certain conditions
SUPPRESSION_RULES = [
    {"event_type": "file_changed", "condition": "cooldown", "cooldown_seconds": 30},
    {"event_type": "revit_opened", "condition": "cooldown", "cooldown_seconds": 300},
    {"event_type": "memory_high", "condition": "cooldown", "cooldown_seconds": 600},
    {"event_type": "bluebeam_document", "condition": "cooldown", "cooldown_seconds": 600},
]


class CognitiveDispatcher:
    """
    The bridge between events and intelligent action.

    Flow: Event → Filter → Assess → Think → Route → Queue → Track
    """

    def __init__(self, project: str = "general", db_path: Path = DB_PATH):
        self.project = project
        self.db_path = db_path
        self.brain = CognitiveCore(project=project, db_path=db_path)
        self.cooldowns: Dict[str, datetime] = {}
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS dispatch_log (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                event_source TEXT,
                event_data TEXT DEFAULT '{}',
                priority TEXT DEFAULT 'medium',
                action_taken TEXT NOT NULL,
                reasoning TEXT,
                task_id TEXT,
                goal_relevance REAL DEFAULT 0.0,
                routing_framework TEXT,
                routing_model TEXT,
                outcome_success INTEGER,
                outcome_notes TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS event_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                outcome_success INTEGER,
                count INTEGER DEFAULT 1,
                last_seen TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_dispatch_type ON dispatch_log(event_type);
            CREATE INDEX IF NOT EXISTS idx_dispatch_action ON dispatch_log(action_taken);
            CREATE INDEX IF NOT EXISTS idx_dispatch_created ON dispatch_log(created_at);
        """)
        conn.commit()
        conn.close()

    def dispatch(self, event_dict: dict, goal_context: str = "") -> DispatchResult:
        """
        Main dispatch method. Takes an event, thinks, acts.

        Steps:
        1. Parse and validate event
        2. Check suppression rules (cooldowns, duplicates)
        3. Assess goal relevance
        4. Determine action type
        5. Route through cognitive core if needed
        6. Queue task or take immediate action
        7. Log and track
        """
        import uuid

        # Parse event
        event = Event(
            type=event_dict.get("type", "unknown"),
            source=event_dict.get("source", "unknown"),
            data=event_dict.get("data", {}),
            priority=event_dict.get("priority", "medium"),
            timestamp=event_dict.get("timestamp", datetime.now().isoformat()),
            goal_context=goal_context,
        )

        dispatch_id = uuid.uuid4().hex[:10]

        # Step 1: Check suppression
        suppressed, suppress_reason = self._check_suppression(event)
        if suppressed:
            result = DispatchResult(
                dispatch_id=dispatch_id,
                action_taken="suppressed",
                reasoning=suppress_reason,
            )
            self._log_dispatch(dispatch_id, event, result)
            return result

        # Step 2: Assess goal relevance
        goal_relevance = self._assess_goal_relevance(event)

        # Step 3: Determine action
        event_config = EVENT_ACTIONS.get(event.type, {
            "action": "assess_and_maybe_act",
            "default_priority": "medium"
        })
        action_type = event_config["action"]

        # Step 4: Execute action based on type
        if action_type == "assess_and_maybe_act":
            result = self._assess_and_act(dispatch_id, event, goal_relevance)
        elif action_type == "queue_validation":
            result = self._queue_task(dispatch_id, event, "validate", goal_relevance)
        elif action_type == "queue_investigation":
            result = self._queue_task(dispatch_id, event, "investigate", goal_relevance)
        elif action_type == "queue_specific":
            result = self._queue_task(dispatch_id, event, "specific", goal_relevance)
        elif action_type == "assess_and_queue":
            result = self._assess_and_queue(dispatch_id, event, goal_relevance)
        elif action_type == "load_context":
            result = self._context_only(dispatch_id, event, goal_relevance)
        elif action_type == "load_context_and_preflight":
            result = self._context_with_preflight(dispatch_id, event, goal_relevance)
        elif action_type == "reflect":
            result = self._trigger_reflection(dispatch_id, event)
        elif action_type == "compile_and_reflect":
            result = self._compile_and_reflect(dispatch_id, event)
        elif action_type == "deep_reflect":
            result = self._deep_reflect(dispatch_id, event)
        elif action_type == "investigate_blocker":
            result = self._queue_task(dispatch_id, event, "investigate", goal_relevance)
        elif action_type == "escalate_goal":
            result = self._escalate(dispatch_id, event, goal_relevance)
        elif action_type == "update_goals_from_task":
            result = self._update_goals_from_task(dispatch_id, event)
        elif action_type in ("notify_only", "log_and_learn", "offer_markup_extraction",
                              "morning_think"):
            result = DispatchResult(
                dispatch_id=dispatch_id,
                action_taken="noted",
                reasoning=f"Event {event.type} logged. Action: {action_type}.",
                goal_relevance=goal_relevance,
            )
        else:
            result = self._assess_and_act(dispatch_id, event, goal_relevance)

        # Step 5: Log
        self._log_dispatch(dispatch_id, event, result)

        return result

    def _check_suppression(self, event: Event) -> tuple:
        """Check if event should be suppressed."""
        for rule in SUPPRESSION_RULES:
            if rule["event_type"] == event.type and rule["condition"] == "cooldown":
                cooldown_key = f"{event.type}:{event.data.get('path', event.data.get('project', ''))}"
                if cooldown_key in self.cooldowns:
                    elapsed = (datetime.now() - self.cooldowns[cooldown_key]).total_seconds()
                    if elapsed < rule["cooldown_seconds"]:
                        return True, f"On cooldown ({elapsed:.0f}s < {rule['cooldown_seconds']}s)"

                # Set cooldown
                self.cooldowns[cooldown_key] = datetime.now()

        return False, ""

    def _assess_goal_relevance(self, event: Event) -> float:
        """Score how relevant this event is to active goals."""
        goals = self.brain.get_goals()
        if not goals:
            return 0.5  # No goals = neutral relevance

        event_text = f"{event.type} {json.dumps(event.data)} {event.goal_context}".lower()
        max_relevance = 0.0

        for goal in goals:
            goal_words = set(goal["title"].lower().split()) - {"the", "a", "to", "for"}
            event_words = set(event_text.split())
            overlap = len(goal_words & event_words)
            if goal_words:
                relevance = overlap / len(goal_words)
                max_relevance = max(max_relevance, relevance)

        return min(1.0, max_relevance)

    def _assess_and_act(self, dispatch_id: str, event: Event,
                         goal_relevance: float) -> DispatchResult:
        """Assess event and decide whether to act."""
        # Low priority + low goal relevance = suppress
        if event.priority == "low" and goal_relevance < 0.2:
            return DispatchResult(
                dispatch_id=dispatch_id,
                action_taken="suppressed",
                reasoning="Low priority and low goal relevance — not worth acting on.",
                goal_relevance=goal_relevance,
            )

        # Route through cognitive core
        task_desc = self._event_to_task_description(event)
        routing = self.brain.route(task_desc)

        # If router says "direct" and it's low priority, just log
        if routing.framework == "direct" and event.priority in ("low", "medium"):
            return DispatchResult(
                dispatch_id=dispatch_id,
                action_taken="noted",
                reasoning=f"Routed as direct/{routing.model_tier}. Priority {event.priority}. Logged.",
                routing=routing,
                goal_relevance=goal_relevance,
            )

        # Otherwise, queue it
        return self._queue_task(dispatch_id, event, "general", goal_relevance, routing)

    def _assess_and_queue(self, dispatch_id: str, event: Event,
                           goal_relevance: float) -> DispatchResult:
        """Assess and always queue (for high-priority events like emails)."""
        task_desc = self._event_to_task_description(event)
        routing = self.brain.route(task_desc)
        return self._queue_task(dispatch_id, event, "priority", goal_relevance, routing)

    def _queue_task(self, dispatch_id: str, event: Event, task_type: str,
                     goal_relevance: float,
                     routing: RoutingDecision = None) -> DispatchResult:
        """Queue a task in the autonomous-agent executor."""
        task_desc = self._event_to_task_description(event)

        if not routing:
            routing = self.brain.route(task_desc)

        # Build the prompt for the claude -p executor
        prompt = self._build_task_prompt(event, task_type, routing)

        # Queue in autonomous-agent DB
        task_id = self._queue_in_agent_db(
            title=f"[Cognitive] {event.type}: {self._event_summary(event)}",
            prompt=prompt,
            priority=self._priority_to_int(event.priority),
        )

        if task_id:
            return DispatchResult(
                dispatch_id=dispatch_id,
                action_taken="queued",
                reasoning=f"Queued as {routing.framework}/{routing.model_tier}. "
                          f"Goal relevance: {goal_relevance:.0%}. Task #{task_id}.",
                task_id=str(task_id),
                routing=routing,
                goal_relevance=goal_relevance,
            )
        else:
            return DispatchResult(
                dispatch_id=dispatch_id,
                action_taken="failed",
                reasoning="Failed to queue task in agent DB.",
                goal_relevance=goal_relevance,
            )

    def _context_only(self, dispatch_id: str, event: Event,
                       goal_relevance: float) -> DispatchResult:
        """Load context without queuing a task."""
        return DispatchResult(
            dispatch_id=dispatch_id,
            action_taken="context_loaded",
            reasoning=f"Context loaded for {event.type}. No task queued.",
            goal_relevance=goal_relevance,
        )

    def _context_with_preflight(self, dispatch_id: str, event: Event,
                                  goal_relevance: float) -> DispatchResult:
        """Load context and run preflight checks."""
        domain = event.data.get("domain", "revit")
        preflight = self.brain.compiler.preflight(domain)

        reasoning = f"Context loaded. {len(preflight)} preflight rules for {domain}."
        if preflight:
            blocking = [r for r in preflight if r.get("level") == "blocking"]
            if blocking:
                reasoning += f" {len(blocking)} BLOCKING rules active."

        return DispatchResult(
            dispatch_id=dispatch_id,
            action_taken="context_loaded",
            reasoning=reasoning,
            goal_relevance=goal_relevance,
        )

    def _trigger_reflection(self, dispatch_id: str, event: Event) -> DispatchResult:
        """Trigger end-of-session reflection."""
        session_data = event.data.get("session_data", {})
        if session_data:
            reflection = self.brain.reflect(session_data)
            return DispatchResult(
                dispatch_id=dispatch_id,
                action_taken="reflected",
                reasoning=f"Session reflection: {reflection.quality_score}/10. "
                          f"Momentum: {reflection.momentum}.",
            )
        return DispatchResult(
            dispatch_id=dispatch_id,
            action_taken="noted",
            reasoning="Reflection requested but no session data provided.",
        )

    def _compile_and_reflect(self, dispatch_id: str, event: Event) -> DispatchResult:
        """Daily: compile learnings and reflect."""
        rules = self.brain.compile()
        weekly = self.brain.reflector.weekly_synthesis()

        return DispatchResult(
            dispatch_id=dispatch_id,
            action_taken="compiled",
            reasoning=f"Compiled {rules.total_rules_generated} rules from "
                      f"{rules.total_corrections_analyzed} corrections. "
                      f"Weekly: {weekly.get('sessions', 0)} sessions, "
                      f"trend: {weekly.get('trend', 'N/A')}.",
        )

    def _deep_reflect(self, dispatch_id: str, event: Event) -> DispatchResult:
        """Weekly: deep synthesis of patterns."""
        rules = self.brain.compile()
        weekly = self.brain.reflector.weekly_synthesis()

        return DispatchResult(
            dispatch_id=dispatch_id,
            action_taken="deep_reflected",
            reasoning=f"Weekly synthesis complete. {rules.total_rules_generated} rules, "
                      f"{weekly.get('sessions', 0)} sessions, "
                      f"avg quality {weekly.get('avg_quality', 'N/A')}, "
                      f"trend: {weekly.get('trend', 'N/A')}.",
        )

    def _update_goals_from_task(self, dispatch_id: str,
                                 event: Event) -> DispatchResult:
        """Update goal progress when a board task completes."""
        task_title = event.data.get("title", "")
        task_project = event.data.get("project", "")
        task_result = event.data.get("result", "")

        # Find matching goals and update progress
        goals = self.brain.get_goals()
        updated = []
        for goal in goals:
            goal_words = set(goal["title"].lower().split()) - {"the", "a", "to", "for", "and"}
            task_words = set(task_title.lower().split()) - {"the", "a", "to", "for", "and"}
            overlap = len(goal_words & task_words)
            if overlap >= 2 or (task_project and task_project == goal.get("project")):
                # Increment progress by a small amount
                current = goal.get("progress", 0.0)
                new_progress = min(1.0, current + 0.1)
                self.brain.reflector.update_goal_progress(
                    goal["id"], new_progress,
                    notes=f"Board task completed: {task_title[:80]}"
                )
                updated.append(goal["title"])

        if updated:
            reasoning = f"Updated {len(updated)} goal(s): {', '.join(updated[:3])}"
        else:
            reasoning = f"Task completed: {task_title[:60]}. No matching goals."

        return DispatchResult(
            dispatch_id=dispatch_id,
            action_taken="goal_updated" if updated else "noted",
            reasoning=reasoning,
        )

    def _escalate(self, dispatch_id: str, event: Event,
                    goal_relevance: float) -> DispatchResult:
        """Escalate to human attention."""
        return DispatchResult(
            dispatch_id=dispatch_id,
            action_taken="escalated",
            reasoning=f"ESCALATED: {event.type}. Goal relevance: {goal_relevance:.0%}. "
                      f"Needs human attention.",
            goal_relevance=goal_relevance,
        )

    # ── Task Building ────────────────────────────────

    def _event_to_task_description(self, event: Event) -> str:
        """Convert event to a task description for routing."""
        parts = [event.type.replace("_", " ")]
        data = event.data
        if "path" in data:
            parts.append(f"file: {data['path']}")
        if "subject" in data:
            parts.append(f"subject: {data['subject']}")
        if "error" in data:
            parts.append(f"error: {data['error']}")
        if event.goal_context:
            parts.append(f"goal: {event.goal_context}")
        return ". ".join(parts)

    def _event_summary(self, event: Event) -> str:
        """Short summary of event for task titles."""
        data = event.data
        if "path" in data:
            return Path(data["path"]).name
        if "subject" in data:
            return data["subject"][:50]
        if "filename" in data:
            return data["filename"]
        return event.type[:50]

    def _build_task_prompt(self, event: Event, task_type: str,
                            routing: RoutingDecision) -> str:
        """Build a prompt for the autonomous executor."""
        parts = [
            f"# Cognitive Dispatch: {event.type}",
            f"Priority: {event.priority}",
            f"Source: {event.source}",
            f"Framework: {routing.framework} / Model: {routing.model_tier}",
            "",
            "## Event Data",
            json.dumps(event.data, indent=2),
            "",
        ]

        if event.goal_context:
            parts.extend([
                "## Goal Context",
                event.goal_context,
                "",
            ])

        # Task-type specific instructions
        if task_type == "validate":
            parts.extend([
                "## Task",
                "Validate the changed resource. Check for issues, run applicable checks.",
                "Report findings. If issues found, create a fix task.",
            ])
        elif task_type == "investigate":
            parts.extend([
                "## Task",
                "Investigate the failure/issue. Find root cause.",
                "Propose a fix. If confident, apply it.",
            ])
        elif task_type == "priority":
            parts.extend([
                "## Task",
                "Handle this priority event. Assess urgency.",
                "Take appropriate action or prepare a response.",
            ])
        else:
            parts.extend([
                "## Task",
                f"Handle this {event.type} event appropriately.",
                "Use the cognitive core's routing recommendation.",
            ])

        parts.extend([
            "",
            "## Instructions",
            "- Follow the strong agent framework (5 phases)",
            "- Self-evaluate before reporting (Phase 4.5)",
            "- Store learnings in memory",
        ])

        return "\n".join(parts)

    def _queue_in_agent_db(self, title: str, prompt: str,
                            priority: int = 5) -> Optional[int]:
        """Queue a task in the autonomous-agent task DB."""
        if not AUTO_AGENT_DB.exists():
            AUTO_AGENT_DB.parent.mkdir(parents=True, exist_ok=True)

        try:
            conn = sqlite3.connect(str(AUTO_AGENT_DB))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    error TEXT,
                    execution_time_seconds REAL
                )
            """)
            conn.execute("""
                INSERT INTO tasks (title, prompt, priority, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
            """, (title, prompt, priority, datetime.now().isoformat()))
            task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            conn.close()
            logger.info(f"Queued task #{task_id}: {title[:60]}")
            return task_id
        except Exception as e:
            logger.error(f"Failed to queue task: {e}")
            return None

    @staticmethod
    def _priority_to_int(priority: str) -> int:
        return {"critical": 10, "high": 8, "medium": 5, "low": 3}.get(priority, 5)

    # ── Outcome Tracking ─────────────────────────────

    def record_outcome(self, dispatch_id: str, success: bool,
                        notes: str = ""):
        """Record the outcome of a dispatched task."""
        conn = self._conn()
        conn.execute("""
            UPDATE dispatch_log
            SET outcome_success = ?, outcome_notes = ?, completed_at = ?
            WHERE id = ?
        """, (1 if success else 0, notes, datetime.now().isoformat(), dispatch_id))

        # Get event type for pattern tracking
        row = conn.execute(
            "SELECT event_type, action_taken FROM dispatch_log WHERE id = ?",
            (dispatch_id,)
        ).fetchone()

        if row:
            # Update or insert event pattern
            existing = conn.execute("""
                SELECT id, count FROM event_patterns
                WHERE event_type = ? AND action_taken = ? AND outcome_success = ?
            """, (row["event_type"], row["action_taken"], 1 if success else 0)).fetchone()

            if existing:
                conn.execute("""
                    UPDATE event_patterns SET count = count + 1, last_seen = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), existing["id"]))
            else:
                conn.execute("""
                    INSERT INTO event_patterns
                    (event_type, action_taken, outcome_success, count, last_seen)
                    VALUES (?, ?, ?, 1, ?)
                """, (row["event_type"], row["action_taken"],
                      1 if success else 0, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    # ── Logging ──────────────────────────────────────

    def _log_dispatch(self, dispatch_id: str, event: Event,
                       result: DispatchResult):
        """Log dispatch decision."""
        conn = self._conn()
        conn.execute("""
            INSERT INTO dispatch_log
            (id, event_type, event_source, event_data, priority,
             action_taken, reasoning, task_id, goal_relevance,
             routing_framework, routing_model, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dispatch_id, event.type, event.source,
            json.dumps(event.data), event.priority,
            result.action_taken, result.reasoning, result.task_id,
            result.goal_relevance,
            result.routing.framework if result.routing else None,
            result.routing.model_tier if result.routing else None,
            datetime.now().isoformat(),
        ))
        conn.commit()
        conn.close()

    # ── Stats ────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get dispatch statistics."""
        conn = self._conn()

        total = conn.execute("SELECT COUNT(*) FROM dispatch_log").fetchone()[0]
        by_action = dict(conn.execute("""
            SELECT action_taken, COUNT(*) FROM dispatch_log GROUP BY action_taken
        """).fetchall())
        by_type = dict(conn.execute("""
            SELECT event_type, COUNT(*) FROM dispatch_log GROUP BY event_type
            ORDER BY COUNT(*) DESC LIMIT 10
        """).fetchall())

        # Success rate of queued tasks
        queued = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN outcome_success = 1 THEN 1 ELSE 0 END) as successes
            FROM dispatch_log
            WHERE action_taken = 'queued' AND outcome_success IS NOT NULL
        """).fetchone()

        conn.close()

        return {
            "total_dispatches": total,
            "by_action": by_action,
            "top_event_types": by_type,
            "queued_success_rate": round(
                queued["successes"] / queued["total"], 2
            ) if queued and queued["total"] else "N/A",
        }

    def get_recent(self, limit: int = 20) -> list:
        """Get recent dispatch log."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM dispatch_log ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cognitive Dispatcher")
    sub = parser.add_subparsers(dest="command")

    d = sub.add_parser("dispatch", help="Dispatch an event")
    d.add_argument("--type", required=True)
    d.add_argument("--source", default="manual")
    d.add_argument("--priority", default="medium")
    d.add_argument("--data", default="{}")

    sub.add_parser("stats", help="Dispatch statistics")
    sub.add_parser("recent", help="Recent dispatches")

    args = parser.parse_args()
    cd = CognitiveDispatcher()

    if args.command == "dispatch":
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            data = {"raw": args.data}

        result = cd.dispatch({
            "type": args.type,
            "source": args.source,
            "priority": args.priority,
            "data": data,
        })
        print(f"Action: {result.action_taken}")
        print(f"Reasoning: {result.reasoning}")
        if result.task_id:
            print(f"Task ID: {result.task_id}")

    elif args.command == "stats":
        stats = cd.get_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")

    elif args.command == "recent":
        recent = cd.get_recent(10)
        for r in recent:
            print(f"  [{r['action_taken']:12s}] {r['event_type']:20s} {r['reasoning'][:60]}")


if __name__ == "__main__":
    main()
