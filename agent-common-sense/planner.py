"""
Autonomous Planner v1.0
========================
Decomposes goals into executable multi-step plans with agent assignments,
template matching, adaptive replanning, and dispatch integration.

Plans serve goals. Each plan is a sequence of steps that can be assigned
to agents, tracked, and replanned if steps fail.

Usage:
    from planner import Planner, Plan, PlanStep

    planner = Planner()

    # Create a plan from a goal
    plan_id = planner.create_plan(
        goal_id=1,
        title="Build RevitMCP Bridge",
        steps=[
            PlanStep(0, "Research existing code", agent="tech-scout"),
            PlanStep(1, "Implement bridge", agent="python-engineer"),
            PlanStep(2, "Write tests", agent="python-engineer"),
            PlanStep(3, "Validate in Revit", agent="bim-validator"),
        ]
    )

    # Or use a template
    plan_id = planner.create_from_template("build-feature", goal_id=1,
                                            context={"feature": "wall creation"})

    # Execute
    planner.start_plan(plan_id)
    steps = planner.get_next_steps(plan_id)
    planner.record_step_result(plan_id, 0, success=True, summary="Research done")

    # Adaptive replanning
    planner.replan(plan_id, from_step=2)

CLI:
    python planner.py create "Title" --goal-id 1
    python planner.py start PLAN_ID
    python planner.py status PLAN_ID
    python planner.py replan PLAN_ID --from-step 2
    python planner.py templates
"""

import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─── DATA CLASSES ──────────────────────────────────────────────

@dataclass
class PlanStep:
    """A single step in an execution plan."""
    index: int = 0
    title: str = ""
    description: str = ""
    agent: str = ""
    inputs: dict = field(default_factory=dict)
    expected_outputs: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)  # indices of prior steps
    estimated_minutes: int = 5
    can_parallel: bool = False
    fallback_agent: str = ""
    checkpoint: bool = False  # if True, pause for review after this step

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "description": self.description,
            "agent": self.agent,
            "inputs": self.inputs,
            "expected_outputs": self.expected_outputs,
            "dependencies": self.dependencies,
            "estimated_minutes": self.estimated_minutes,
            "can_parallel": self.can_parallel,
            "fallback_agent": self.fallback_agent,
            "checkpoint": self.checkpoint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlanStep":
        return cls(
            index=data.get("index", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            agent=data.get("agent", ""),
            inputs=data.get("inputs", {}),
            expected_outputs=data.get("expected_outputs", []),
            dependencies=data.get("dependencies", []),
            estimated_minutes=data.get("estimated_minutes", 5),
            can_parallel=data.get("can_parallel", False),
            fallback_agent=data.get("fallback_agent", ""),
            checkpoint=data.get("checkpoint", False),
        )


@dataclass
class Plan:
    """An execution plan linked to a goal."""
    id: int = 0
    goal_id: Optional[int] = None
    title: str = ""
    description: str = ""
    steps: list[PlanStep] = field(default_factory=list)
    status: str = "draft"  # draft|ready|executing|completed|failed|abandoned
    template_name: str = ""
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    current_step_index: int = 0
    total_steps: int = 0
    execution_context: dict = field(default_factory=dict)
    error_log: list = field(default_factory=list)
    tags: str = "[]"
    domain: str = "general"
    parent_plan_id: Optional[int] = None  # For recursive decomposition

    @property
    def progress_pct(self) -> float:
        if self.total_steps == 0:
            return 0.0
        completed = sum(1 for s in self._step_results if s.get("status") == "completed")
        return round(completed / self.total_steps * 100, 1)

    def __post_init__(self):
        self._step_results = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "template_name": self.template_name,
            "total_steps": self.total_steps,
            "current_step_index": self.current_step_index,
        }


@dataclass
class PlanTemplate:
    """A reusable plan pattern."""
    id: int = 0
    name: str = ""
    description: str = ""
    steps_template: list[dict] = field(default_factory=list)
    domain: str = "general"
    tags: str = "[]"
    times_used: int = 0
    avg_success_rate: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps_template": self.steps_template,
            "domain": self.domain,
            "times_used": self.times_used,
            "avg_success_rate": self.avg_success_rate,
        }


# ─── BUILT-IN TEMPLATES ───────────────────────────────────────

BUILTIN_TEMPLATES = {
    "build-feature": {
        "description": "Research, plan, implement, test, commit",
        "domain": "development",
        "steps": [
            {"title": "Research existing code", "agent": "tech-scout",
             "description": "Understand current codebase and patterns",
             "estimated_minutes": 10},
            {"title": "Design implementation plan", "agent": "code-architect",
             "description": "Create detailed implementation approach",
             "estimated_minutes": 10, "checkpoint": True},
            {"title": "Implement feature", "agent": "python-engineer",
             "description": "Write the code according to plan",
             "estimated_minutes": 30},
            {"title": "Write tests", "agent": "python-engineer",
             "description": "Write comprehensive test coverage",
             "estimated_minutes": 15, "dependencies": [2]},
            {"title": "Review and commit", "agent": "python-engineer",
             "description": "Final review, fix issues, commit",
             "estimated_minutes": 10, "dependencies": [3], "checkpoint": True},
        ],
    },
    "pdf-to-revit-model": {
        "description": "Extract geometry from PDF, create Revit elements, validate",
        "domain": "bim",
        "steps": [
            {"title": "Extract geometry from PDF", "agent": "floor-plan-processor",
             "description": "Extract walls, rooms, doors, windows from floor plan",
             "estimated_minutes": 15},
            {"title": "Create walls in Revit", "agent": "revit-builder",
             "description": "Build wall elements from extracted geometry",
             "estimated_minutes": 20, "dependencies": [0]},
            {"title": "Place openings", "agent": "revit-builder",
             "description": "Add doors and windows to walls",
             "estimated_minutes": 15, "dependencies": [1]},
            {"title": "Validate model", "agent": "bim-validator",
             "description": "Check model quality and dimensions",
             "estimated_minutes": 10, "dependencies": [2], "checkpoint": True},
            {"title": "Generate schedules", "agent": "revit-builder",
             "description": "Create door, window, and room schedules",
             "estimated_minutes": 10, "dependencies": [3]},
        ],
    },
    "client-deliverable": {
        "description": "Gather data, generate reports, review, export",
        "domain": "business",
        "steps": [
            {"title": "Gather project data", "agent": "tech-scout",
             "description": "Collect all relevant project information",
             "estimated_minutes": 15},
            {"title": "Generate reports", "agent": "excel-reporter",
             "description": "Create formatted reports and summaries",
             "estimated_minutes": 20, "dependencies": [0]},
            {"title": "Create documents", "agent": "client-liaison",
             "description": "Draft client-facing documents",
             "estimated_minutes": 15, "dependencies": [1]},
            {"title": "Review deliverables", "agent": "client-liaison",
             "description": "Quality check all outputs",
             "estimated_minutes": 10, "dependencies": [2], "checkpoint": True},
            {"title": "Export and package", "agent": "client-liaison",
             "description": "Package all deliverables for client",
             "estimated_minutes": 10, "dependencies": [3]},
        ],
    },
    "research-topic": {
        "description": "Initial research, deep analysis, synthesize findings",
        "domain": "research",
        "steps": [
            {"title": "Initial research", "agent": "tech-scout",
             "description": "Broad search and surface-level understanding",
             "estimated_minutes": 15},
            {"title": "Deep analysis", "agent": "tech-scout",
             "description": "Detailed investigation of key findings",
             "estimated_minutes": 20, "dependencies": [0]},
            {"title": "Synthesize findings", "agent": "tech-scout",
             "description": "Compile and structure all findings",
             "estimated_minutes": 10, "dependencies": [1], "checkpoint": True},
        ],
    },
}


# ─── PLANNER ───────────────────────────────────────────────────

class Planner:
    """Autonomous plan creation, execution tracking, and adaptive replanning."""

    VALID_STATUSES = {"draft", "ready", "executing", "completed", "failed", "abandoned"}

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._find_db()
        if self.db_path:
            self._ensure_schema()
            self._ensure_builtin_templates()

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
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                steps TEXT DEFAULT '[]',
                status TEXT DEFAULT 'draft',
                template_name TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                current_step_index INTEGER DEFAULT 0,
                total_steps INTEGER DEFAULT 0,
                execution_context TEXT DEFAULT '{}',
                error_log TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                domain TEXT DEFAULT 'general'
            );

            CREATE TABLE IF NOT EXISTS plan_step_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                step_index INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                agent_name TEXT DEFAULT '',
                started_at TEXT,
                completed_at TEXT,
                result_summary TEXT DEFAULT '',
                error TEXT DEFAULT '',
                output_artifacts TEXT DEFAULT '[]',
                duration_seconds REAL DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
            );

            -- parent_plan_id for recursive decomposition
            -- (added via ALTER if table already exists)
        """)

        # Add parent_plan_id column if not present (safe for existing DBs)
        try:
            conn.execute("ALTER TABLE plans ADD COLUMN parent_plan_id INTEGER DEFAULT NULL")
        except Exception:
            pass  # Column already exists

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS plan_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                steps_template TEXT DEFAULT '[]',
                domain TEXT DEFAULT 'general',
                tags TEXT DEFAULT '[]',
                times_used INTEGER DEFAULT 0,
                avg_success_rate REAL DEFAULT 0.0,
                created_at TEXT,
                updated_at TEXT
            );
        """)
        conn.commit()
        conn.close()

    def _ensure_builtin_templates(self):
        """Register built-in templates if not present."""
        conn = self._conn()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, tmpl in BUILTIN_TEMPLATES.items():
            existing = conn.execute(
                "SELECT id FROM plan_templates WHERE name = ?", (name,)
            ).fetchone()
            if not existing:
                conn.execute("""
                    INSERT INTO plan_templates (name, description, steps_template,
                                               domain, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, '[]', ?, ?)
                """, (name, tmpl["description"], json.dumps(tmpl["steps"]),
                      tmpl["domain"], now, now))
        conn.commit()
        conn.close()

    # ─── CREATION ──────────────────────────────────────────────

    def create_plan(self, title: str, goal_id: Optional[int] = None,
                    description: str = "", steps: Optional[list[PlanStep]] = None,
                    domain: str = "general", tags: Optional[list] = None) -> int:
        """Create a new plan. Returns the plan ID."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        step_list = steps or []
        # Auto-assign indices if not set
        for i, s in enumerate(step_list):
            if s.index == 0 and i > 0:
                s.index = i

        conn = self._conn()
        cursor = conn.execute("""
            INSERT INTO plans (goal_id, title, description, steps, status,
                             created_at, updated_at, total_steps, tags, domain)
            VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?)
        """, (goal_id, title, description,
              json.dumps([s.to_dict() for s in step_list]),
              now, now, len(step_list),
              json.dumps(tags or []), domain))
        plan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return plan_id

    def create_from_template(self, template_name: str,
                              goal_id: Optional[int] = None,
                              title: Optional[str] = None,
                              context: Optional[dict] = None) -> Optional[int]:
        """Create a plan from a template. Returns plan ID or None."""
        template = self.get_template(template_name)
        if not template:
            return None

        steps = []
        for i, step_data in enumerate(template.steps_template):
            step = PlanStep.from_dict({**step_data, "index": i})
            # Substitute context variables in descriptions
            if context:
                for key, value in context.items():
                    step.title = step.title.replace(f"{{{key}}}", str(value))
                    step.description = step.description.replace(f"{{{key}}}", str(value))
            steps.append(step)

        plan_title = title or f"{template.description} (from {template_name})"
        plan_id = self.create_plan(
            title=plan_title,
            goal_id=goal_id,
            description=template.description,
            steps=steps,
            domain=template.domain,
        )

        # Update template usage count
        conn = self._conn()
        conn.execute("""
            UPDATE plan_templates SET times_used = times_used + 1,
                   updated_at = ? WHERE name = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), template_name))
        # Record the template name in the plan
        conn.execute(
            "UPDATE plans SET template_name = ? WHERE id = ?",
            (template_name, plan_id)
        )
        conn.commit()
        conn.close()
        return plan_id

    def decompose_goal(self, goal_id: int, goal_title: str,
                       goal_description: str = "") -> int:
        """Auto-decompose a goal into a plan based on keywords and templates."""
        # Try to match a template
        template_name = self.match_template(goal_title + " " + goal_description)
        if template_name:
            plan_id = self.create_from_template(
                template_name, goal_id=goal_id,
                title=f"Plan for: {goal_title}",
                context={"feature": goal_title, "topic": goal_title}
            )
            if plan_id:
                return plan_id

        # Fallback: create a generic 3-step plan
        steps = [
            PlanStep(0, "Research and understand requirements", agent="tech-scout",
                     description=f"Research: {goal_description or goal_title}",
                     estimated_minutes=15),
            PlanStep(1, "Implement solution", agent="python-engineer",
                     description=f"Build: {goal_title}",
                     estimated_minutes=30, dependencies=[0]),
            PlanStep(2, "Verify and complete", agent="python-engineer",
                     description="Test, review, and finalize",
                     estimated_minutes=15, dependencies=[1], checkpoint=True),
        ]
        return self.create_plan(
            title=f"Plan for: {goal_title}",
            goal_id=goal_id,
            description=goal_description,
            steps=steps,
        )

    # ─── TEMPLATES ─────────────────────────────────────────────

    def register_template(self, name: str, description: str,
                          steps: list[dict], domain: str = "general",
                          tags: Optional[list] = None) -> int:
        """Register a new plan template. Returns template ID."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        cursor = conn.execute("""
            INSERT OR REPLACE INTO plan_templates
            (name, description, steps_template, domain, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, description, json.dumps(steps), domain,
              json.dumps(tags or []), now, now))
        tid = cursor.lastrowid
        conn.commit()
        conn.close()
        return tid

    def get_template(self, name: str) -> Optional[PlanTemplate]:
        """Get a template by name."""
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM plan_templates WHERE name = ?", (name,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_template(row)

    def list_templates(self) -> list[PlanTemplate]:
        """List all available templates."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM plan_templates ORDER BY times_used DESC"
        ).fetchall()
        conn.close()
        return [self._row_to_template(r) for r in rows]

    def match_template(self, description: str) -> Optional[str]:
        """Find the best matching template for a description."""
        desc_lower = description.lower()
        keywords = {
            "build-feature": ["build", "implement", "create", "add", "feature", "develop"],
            "pdf-to-revit-model": ["pdf", "revit", "floor plan", "model", "bim", "walls"],
            "client-deliverable": ["client", "deliverable", "report", "proposal", "document"],
            "research-topic": ["research", "analyze", "investigate", "study", "explore"],
        }

        best_match = None
        best_score = 0
        for template_name, kws in keywords.items():
            score = sum(1 for kw in kws if kw in desc_lower)
            if score > best_score:
                best_score = score
                best_match = template_name

        return best_match if best_score >= 2 else None

    def promote_plan_to_template(self, plan_id: int, template_name: str) -> Optional[int]:
        """Save a successful plan as a reusable template."""
        plan = self.get_plan(plan_id)
        if not plan:
            return None

        steps = [s.to_dict() for s in plan.steps]
        # Strip runtime data from steps
        for s in steps:
            s.pop("inputs", None)

        return self.register_template(
            name=template_name,
            description=plan.description or plan.title,
            steps=steps,
            domain=plan.domain,
        )

    # ─── PLAN RETRIEVAL ────────────────────────────────────────

    def get_plan(self, plan_id: int) -> Optional[Plan]:
        """Get a plan by ID with step results loaded."""
        conn = self._conn()
        row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            conn.close()
            return None

        plan = self._row_to_plan(row)

        # Load step results
        results = conn.execute("""
            SELECT * FROM plan_step_results
            WHERE plan_id = ? ORDER BY step_index
        """, (plan_id,)).fetchall()
        plan._step_results = [dict(r) for r in results]
        conn.close()
        return plan

    def list_plans(self, goal_id: Optional[int] = None,
                   status: Optional[str] = None) -> list[Plan]:
        """List plans with optional filters."""
        conn = self._conn()
        sql = "SELECT * FROM plans WHERE 1=1"
        params = []
        if goal_id is not None:
            sql += " AND goal_id = ?"
            params.append(goal_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY created_at DESC"

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [self._row_to_plan(r) for r in rows]

    # ─── EXECUTION ─────────────────────────────────────────────

    def start_plan(self, plan_id: int) -> bool:
        """Start executing a plan."""
        plan = self.get_plan(plan_id)
        if not plan or plan.status not in ("draft", "ready"):
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute("""
            UPDATE plans SET status = 'executing', started_at = ?,
                   updated_at = ?, current_step_index = 0
            WHERE id = ?
        """, (now, now, plan_id))

        # Initialize step results for all steps
        for step in plan.steps:
            conn.execute("""
                INSERT OR IGNORE INTO plan_step_results
                (plan_id, step_index, status, agent_name)
                VALUES (?, ?, 'pending', ?)
            """, (plan_id, step.index, step.agent))

        conn.commit()
        conn.close()
        return True

    def get_next_steps(self, plan_id: int) -> list[PlanStep]:
        """Get the next steps to execute. Returns steps whose dependencies
        are all completed. May return multiple steps if they can run in parallel."""
        plan = self.get_plan(plan_id)
        if not plan or plan.status != "executing":
            return []

        # Get completed step indices
        conn = self._conn()
        completed_rows = conn.execute("""
            SELECT step_index FROM plan_step_results
            WHERE plan_id = ? AND status = 'completed'
        """, (plan_id,)).fetchall()
        completed_indices = {r["step_index"] for r in completed_rows}

        # Get pending/failed step indices
        active_rows = conn.execute("""
            SELECT step_index FROM plan_step_results
            WHERE plan_id = ? AND status = 'in_progress'
        """, (plan_id,)).fetchall()
        active_indices = {r["step_index"] for r in active_rows}
        conn.close()

        ready = []
        for step in plan.steps:
            if step.index in completed_indices or step.index in active_indices:
                continue
            # Check if all dependencies are completed
            deps_met = all(d in completed_indices for d in step.dependencies)
            if deps_met:
                ready.append(step)

        return ready

    def record_step_result(self, plan_id: int, step_index: int,
                           success: bool, summary: str = "",
                           error: str = "", artifacts: Optional[list] = None,
                           duration_seconds: float = 0,
                           coherence_score: Optional[float] = None) -> bool:
        """Record the result of executing a plan step.

        Args:
            coherence_score: Optional coherence score from CoherenceMonitor.
                             Stored in plan execution_context for trend tracking.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "completed" if success else "failed"

        conn = self._conn()

        # Check if result row exists
        existing = conn.execute("""
            SELECT id, retry_count FROM plan_step_results
            WHERE plan_id = ? AND step_index = ?
        """, (plan_id, step_index)).fetchone()

        if existing:
            retry = existing["retry_count"] + (0 if success else 1)
            conn.execute("""
                UPDATE plan_step_results
                SET status = ?, completed_at = ?, result_summary = ?,
                    error = ?, output_artifacts = ?, duration_seconds = ?,
                    retry_count = ?
                WHERE plan_id = ? AND step_index = ?
            """, (status, now, summary, error,
                  json.dumps(artifacts or []), duration_seconds, retry,
                  plan_id, step_index))
        else:
            plan = self.get_plan(plan_id)
            agent = ""
            if plan:
                matching = [s for s in plan.steps if s.index == step_index]
                agent = matching[0].agent if matching else ""
            conn.execute("""
                INSERT INTO plan_step_results
                (plan_id, step_index, status, agent_name, completed_at,
                 result_summary, error, output_artifacts, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (plan_id, step_index, status, agent, now,
                  summary, error, json.dumps(artifacts or []), duration_seconds))

        # Store coherence score in plan execution context
        if coherence_score is not None:
            plan = self.get_plan(plan_id)
            if plan:
                ctx = plan.execution_context or {}
                coherence_history = ctx.get("coherence_scores", [])
                coherence_history.append({
                    "step_index": step_index,
                    "score": coherence_score,
                    "timestamp": now,
                })
                ctx["coherence_scores"] = coherence_history
                conn.execute(
                    "UPDATE plans SET execution_context = ? WHERE id = ?",
                    (json.dumps(ctx), plan_id)
                )

        # Update plan progress
        total = conn.execute(
            "SELECT total_steps FROM plans WHERE id = ?", (plan_id,)
        ).fetchone()
        completed_count = conn.execute("""
            SELECT COUNT(*) as c FROM plan_step_results
            WHERE plan_id = ? AND status = 'completed'
        """, (plan_id,)).fetchone()["c"]

        conn.execute("""
            UPDATE plans SET current_step_index = ?, updated_at = ?
            WHERE id = ?
        """, (step_index + 1, now, plan_id))

        # If step failed, log the error
        if not success:
            plan = self.get_plan(plan_id)
            if plan:
                errors = plan.error_log or []
                errors.append({
                    "step_index": step_index,
                    "error": error,
                    "timestamp": now,
                })
                conn.execute(
                    "UPDATE plans SET error_log = ? WHERE id = ?",
                    (json.dumps(errors), plan_id)
                )

        conn.commit()
        conn.close()
        return True

    def complete_plan(self, plan_id: int) -> bool:
        """Mark a plan as completed."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute("""
            UPDATE plans SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE id = ?
        """, (now, now, plan_id))
        conn.commit()
        conn.close()

        # Update goal progress if linked
        plan = self.get_plan(plan_id)
        if plan and plan.goal_id:
            try:
                from goals import GoalEngine
                ge = GoalEngine(db_path=self.db_path)
                ge.on_task_completed(plan.goal_id, f"Plan completed: {plan.title}")
            except ImportError:
                pass
        return True

    def fail_plan(self, plan_id: int, reason: str = "") -> bool:
        """Mark a plan as failed."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        conn.execute("""
            UPDATE plans SET status = 'failed', updated_at = ?
            WHERE id = ?
        """, (now, plan_id))
        if reason:
            plan = self.get_plan(plan_id)
            if plan:
                errors = plan.error_log or []
                errors.append({"reason": reason, "timestamp": now})
                conn.execute(
                    "UPDATE plans SET error_log = ? WHERE id = ?",
                    (json.dumps(errors), plan_id)
                )
        conn.commit()
        conn.close()
        return True

    def is_plan_complete(self, plan_id: int) -> bool:
        """Check if all steps in a plan are completed."""
        conn = self._conn()
        total = conn.execute(
            "SELECT total_steps FROM plans WHERE id = ?", (plan_id,)
        ).fetchone()
        if not total:
            conn.close()
            return False
        completed = conn.execute("""
            SELECT COUNT(*) as c FROM plan_step_results
            WHERE plan_id = ? AND status = 'completed'
        """, (plan_id,)).fetchone()["c"]
        conn.close()
        return completed >= total["total_steps"] and total["total_steps"] > 0

    # ─── ADAPTIVE REPLANNING ──────────────────────────────────

    def replan(self, plan_id: int, from_step: int,
               new_steps: Optional[list[PlanStep]] = None) -> bool:
        """Replace steps from from_step onward with new steps.
        If no new_steps provided, keeps existing steps but resets their results."""
        plan = self.get_plan(plan_id)
        if not plan:
            return False

        conn = self._conn()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Clear results for steps >= from_step
        conn.execute("""
            DELETE FROM plan_step_results
            WHERE plan_id = ? AND step_index >= ?
        """, (plan_id, from_step))

        if new_steps:
            # Replace steps from from_step onward
            kept = [s for s in plan.steps if s.index < from_step]
            for i, s in enumerate(new_steps):
                s.index = from_step + i
            all_steps = kept + new_steps

            conn.execute("""
                UPDATE plans SET steps = ?, total_steps = ?,
                       current_step_index = ?, updated_at = ?
                WHERE id = ?
            """, (json.dumps([s.to_dict() for s in all_steps]),
                  len(all_steps), from_step, now, plan_id))
        else:
            # Just reset results (retry)
            conn.execute("""
                UPDATE plans SET current_step_index = ?, updated_at = ?
                WHERE id = ?
            """, (from_step, now, plan_id))

        # Ensure plan is in executing state
        conn.execute("""
            UPDATE plans SET status = 'executing' WHERE id = ? AND status = 'failed'
        """, (plan_id,))

        conn.commit()
        conn.close()
        return True

    def suggest_alternative(self, plan_id: int, failed_step_index: int) -> Optional[PlanStep]:
        """Suggest an alternative for a failed step (try fallback agent)."""
        plan = self.get_plan(plan_id)
        if not plan:
            return None

        matching = [s for s in plan.steps if s.index == failed_step_index]
        if not matching:
            return None

        step = matching[0]
        if step.fallback_agent:
            return PlanStep(
                index=step.index,
                title=f"{step.title} (fallback)",
                description=step.description,
                agent=step.fallback_agent,
                inputs=step.inputs,
                expected_outputs=step.expected_outputs,
                dependencies=step.dependencies,
                estimated_minutes=step.estimated_minutes,
            )
        return None

    # ─── TASK DECOMPOSITION ─────────────────────────────────

    # Complexity signals: conjunctions, multi-domain keywords, high-effort phrases
    _CONJUNCTION_PATTERNS = [
        re.compile(r"\b(?:and then|followed by|after that|next|finally)\b", re.IGNORECASE),
        re.compile(r"\b(?:also|additionally|furthermore|plus)\b", re.IGNORECASE),
    ]
    _MULTI_DOMAIN_KEYWORDS = {
        "bim": {"revit", "wall", "floor", "model", "element", "family", "schedule"},
        "code": {"implement", "code", "function", "class", "module", "test", "script"},
        "research": {"research", "analyze", "investigate", "compare", "survey", "study"},
        "business": {"client", "proposal", "report", "invoice", "deliverable", "email"},
        "data": {"excel", "csv", "database", "query", "data", "extract", "parse"},
    }
    _COMPLEXITY_PHRASES = [
        re.compile(r"\b(?:research and implement|analyze and build|design and create)\b", re.IGNORECASE),
        re.compile(r"\b(?:full pipeline|end.to.end|complete workflow)\b", re.IGNORECASE),
        re.compile(r"\b(?:multiple|several|all|every|each)\b", re.IGNORECASE),
    ]

    def is_atomic(self, step: PlanStep) -> bool:
        """Determine if a step is atomic (executable in a single agent call).

        Non-atomic signals:
        - Description contains conjunctions ("and then", "followed by")
        - Description spans multiple domains (e.g., BIM + code)
        - Estimated time > 30 minutes
        - Description has 3+ action verbs
        """
        text = f"{step.title} {step.description}".lower()
        score = self.estimate_complexity(text)

        # Simple threshold: complexity <= 4 is atomic
        return score <= 4

    def estimate_complexity(self, description: str) -> int:
        """Estimate task complexity on a 1-10 scale.

        Factors:
        - Conjunction count (each adds +1)
        - Domain count (each beyond 1 adds +1)
        - Complexity phrases (+1 each)
        - Word count proxy (+1 per 30 words beyond 20)
        - Action verb count (+1 per verb beyond 2)
        """
        text = description.lower()
        score = 1  # Base complexity

        # Conjunctions
        for pattern in self._CONJUNCTION_PATTERNS:
            score += len(pattern.findall(text))

        # Multi-domain check
        domains_found = set()
        for domain, keywords in self._MULTI_DOMAIN_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                domains_found.add(domain)
        if len(domains_found) > 1:
            score += len(domains_found) - 1

        # Complexity phrases
        for pattern in self._COMPLEXITY_PHRASES:
            if pattern.search(text):
                score += 1

        # Word count
        words = text.split()
        if len(words) > 20:
            score += (len(words) - 20) // 30

        # Action verbs
        action_verbs = {"create", "build", "implement", "analyze", "research",
                        "extract", "generate", "validate", "configure", "deploy",
                        "test", "review", "update", "refactor", "design", "write",
                        "process", "parse", "transform", "migrate"}
        verb_count = sum(1 for w in words if w in action_verbs)
        if verb_count > 2:
            score += verb_count - 2

        return min(10, max(1, score))

    def validate_mece(self, plan_id: int) -> dict:
        """Validate that plan steps are MECE relative to the plan goal.

        MECE = Mutually Exclusive, Collectively Exhaustive.
        Returns coverage score, overlap score, and specific issues.
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return {"valid": False, "error": "Plan not found"}

        goal_text = f"{plan.title} {plan.description}".lower()
        goal_words = set(re.findall(r'[a-z]{3,}', goal_text))
        # Remove stop words
        stop = {"the", "and", "for", "with", "this", "that", "from", "have",
                "are", "was", "will", "not", "but", "its", "they", "into",
                "also", "than", "then", "each", "only", "just", "more", "plan"}
        goal_words -= stop

        if not goal_words:
            return {"valid": True, "coverage": 1.0, "overlap": 0.0, "issues": []}

        # Check coverage: do steps collectively cover all goal keywords?
        step_words_combined = set()
        step_word_sets = []
        for s in plan.steps:
            text = f"{s.title} {s.description}".lower()
            words = set(re.findall(r'[a-z]{3,}', text)) - stop
            step_word_sets.append(words)
            step_words_combined |= words

        covered = goal_words & step_words_combined
        coverage = len(covered) / len(goal_words) if goal_words else 1.0

        # Check overlap: do steps share too many keywords?
        total_overlap = 0
        overlap_pairs = []
        for i in range(len(step_word_sets)):
            for j in range(i + 1, len(step_word_sets)):
                shared = step_word_sets[i] & step_word_sets[j]
                if len(shared) >= 3:
                    total_overlap += len(shared)
                    overlap_pairs.append((i, j, shared))

        all_step_words = sum(len(s) for s in step_word_sets)
        overlap_ratio = total_overlap / max(all_step_words, 1)

        issues = []
        uncovered = goal_words - step_words_combined
        if uncovered and coverage < 0.8:
            issues.append(f"Uncovered goal keywords: {', '.join(list(uncovered)[:5])}")
        for i, j, shared in overlap_pairs:
            issues.append(
                f"Steps {i} and {j} overlap on: {', '.join(list(shared)[:3])}"
            )

        return {
            "valid": coverage >= 0.6 and overlap_ratio < 0.4,
            "coverage": round(coverage, 3),
            "overlap": round(overlap_ratio, 3),
            "issues": issues,
            "uncovered_keywords": list(uncovered)[:10],
        }

    def auto_decompose_step(self, plan_id: int, step_index: int) -> Optional[int]:
        """Recursively decompose a complex step into a sub-plan.

        If the step is non-atomic (complexity > 4), create a child plan
        that breaks it into smaller steps. Links via parent_plan_id.

        Returns the sub-plan ID, or None if step is already atomic.
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return None

        matching = [s for s in plan.steps if s.index == step_index]
        if not matching:
            return None

        step = matching[0]
        if self.is_atomic(step):
            return None

        # Decompose: try template matching first
        text = f"{step.title} {step.description}"
        template_name = self.match_template(text)

        if template_name:
            sub_plan_id = self.create_from_template(
                template_name, goal_id=plan.goal_id,
                title=f"Sub-plan for: {step.title}",
                context={"feature": step.title}
            )
        else:
            # Generate sub-steps heuristically based on complexity signals
            sub_steps = self._heuristic_decompose(step)
            sub_plan_id = self.create_plan(
                title=f"Sub-plan for: {step.title}",
                goal_id=plan.goal_id,
                description=step.description,
                steps=sub_steps,
                domain=plan.domain,
            )

        if sub_plan_id:
            # Link sub-plan to parent
            conn = self._conn()
            conn.execute(
                "UPDATE plans SET parent_plan_id = ? WHERE id = ?",
                (plan_id, sub_plan_id)
            )
            # Store sub-plan reference in parent's execution context
            ctx = plan.execution_context or {}
            sub_plans = ctx.get("sub_plans", {})
            sub_plans[str(step_index)] = sub_plan_id
            ctx["sub_plans"] = sub_plans
            conn.execute(
                "UPDATE plans SET execution_context = ? WHERE id = ?",
                (json.dumps(ctx), plan_id)
            )
            conn.commit()
            conn.close()

        return sub_plan_id

    def _heuristic_decompose(self, step: PlanStep) -> list[PlanStep]:
        """Break a complex step into smaller sub-steps using heuristics."""
        text = f"{step.title} {step.description}"

        # Try splitting on conjunctions
        parts = re.split(
            r'\b(?:and then|followed by|after that|then|,\s*then)\b',
            text, flags=re.IGNORECASE
        )
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 10]

        if len(parts) >= 2:
            # Conjunction-based split worked
            sub_steps = []
            for i, part in enumerate(parts):
                sub_steps.append(PlanStep(
                    index=i,
                    title=part[:80],
                    description=part,
                    agent=step.agent,
                    estimated_minutes=max(5, step.estimated_minutes // len(parts)),
                    dependencies=[i - 1] if i > 0 else [],
                ))
            return sub_steps

        # Fallback: research → implement → verify pattern
        return [
            PlanStep(0, f"Analyze: {step.title}", agent=step.agent or "tech-scout",
                     description=f"Understand requirements for: {step.description}",
                     estimated_minutes=max(5, step.estimated_minutes // 3)),
            PlanStep(1, f"Execute: {step.title}", agent=step.agent or "python-engineer",
                     description=f"Implement: {step.description}",
                     estimated_minutes=max(5, step.estimated_minutes // 2),
                     dependencies=[0]),
            PlanStep(2, f"Verify: {step.title}", agent=step.agent or "python-engineer",
                     description=f"Validate results of: {step.description}",
                     estimated_minutes=max(5, step.estimated_minutes // 4),
                     dependencies=[1]),
        ]

    def get_sub_plans(self, plan_id: int) -> list[Plan]:
        """Get all sub-plans for a given parent plan."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM plans WHERE parent_plan_id = ? ORDER BY id",
                (plan_id,)
            ).fetchall()
        except Exception:
            rows = []
        conn.close()
        return [self._row_to_plan(r) for r in rows]

    def decompose_all_complex_steps(self, plan_id: int) -> dict:
        """Auto-decompose all non-atomic steps in a plan.
        Returns dict of {step_index: sub_plan_id} for steps that were decomposed."""
        plan = self.get_plan(plan_id)
        if not plan:
            return {}

        decomposed = {}
        for step in plan.steps:
            if not self.is_atomic(step):
                sub_plan_id = self.auto_decompose_step(plan_id, step.index)
                if sub_plan_id:
                    decomposed[step.index] = sub_plan_id
        return decomposed

    # ─── DISPATCH INTEGRATION ─────────────────────────────────

    def to_dispatch_event(self, plan_id: int, step_index: int) -> Optional[dict]:
        """Convert a plan step into a dispatch event for agent_dispatcher."""
        plan = self.get_plan(plan_id)
        if not plan:
            return None

        matching = [s for s in plan.steps if s.index == step_index]
        if not matching:
            return None

        step = matching[0]
        return {
            "trigger_type": "plan_step",
            "data": {
                "plan_id": plan_id,
                "plan_title": plan.title,
                "step_index": step.index,
                "step_title": step.title,
                "step_description": step.description,
                "agent": step.agent,
                "inputs": step.inputs,
                "goal_id": plan.goal_id,
            },
            "priority": "medium",
            "source": f"planner:plan_{plan_id}:step_{step_index}",
        }

    def to_task_queue_entries(self, plan_id: int) -> list[dict]:
        """Convert plan steps into task queue entries for autonomous agent."""
        plan = self.get_plan(plan_id)
        if not plan:
            return []

        entries = []
        for step in plan.steps:
            entries.append({
                "title": f"[Plan #{plan_id}] {step.title}",
                "description": step.description,
                "agent": step.agent,
                "priority": "medium",
                "source": f"plan:{plan_id}",
                "metadata": {
                    "plan_id": plan_id,
                    "step_index": step.index,
                    "goal_id": plan.goal_id,
                    "dependencies": step.dependencies,
                },
            })
        return entries

    # ─── WORKFLOW INTEGRATION ─────────────────────────────────

    def plan_from_workflow(self, workflow_name: str,
                            goal_id: Optional[int] = None) -> Optional[int]:
        """Create a plan from a recorded workflow."""
        try:
            from workflows import WorkflowRecorder
            recorder = WorkflowRecorder(db_path=self.db_path)
            workflow = recorder.get_workflow(workflow_name)
            if not workflow:
                return None

            steps = []
            for i, wf_step in enumerate(workflow.steps):
                steps.append(PlanStep(
                    index=i,
                    title=wf_step.tool_name,
                    description=wf_step.result_summary or f"Execute {wf_step.tool_name}",
                    agent="",  # will be assigned based on tool
                    inputs=wf_step.tool_input,
                ))

            return self.create_plan(
                title=f"From workflow: {workflow_name}",
                goal_id=goal_id,
                description=workflow.description,
                steps=steps,
                domain=workflow.domain,
            )
        except ImportError:
            return None

    def save_as_workflow(self, plan_id: int, workflow_name: str) -> bool:
        """Save a completed plan as a reusable workflow."""
        plan = self.get_plan(plan_id)
        if not plan:
            return False

        try:
            from workflows import WorkflowRecorder, Workflow, WorkflowStep
            recorder = WorkflowRecorder(db_path=self.db_path)

            wf_steps = [
                WorkflowStep(
                    tool_name=s.agent or s.title,
                    tool_input=s.inputs,
                    result_summary=s.description,
                    order=s.index,
                )
                for s in plan.steps
            ]

            workflow = Workflow(
                name=workflow_name,
                steps=wf_steps,
                description=plan.description or plan.title,
                domain=plan.domain,
                success=plan.status == "completed",
            )
            return recorder._store_workflow(workflow)
        except ImportError:
            return False

    # ─── INTERNALS ─────────────────────────────────────────────

    def _row_to_plan(self, row: sqlite3.Row) -> Plan:
        steps_data = json.loads(row["steps"] or "[]")
        # parent_plan_id may not exist in older DBs
        try:
            parent_plan_id = row["parent_plan_id"]
        except (IndexError, KeyError):
            parent_plan_id = None
        plan = Plan(
            id=row["id"],
            goal_id=row["goal_id"],
            title=row["title"],
            description=row["description"] or "",
            steps=[PlanStep.from_dict({**s, "index": i}) for i, s in enumerate(steps_data)],
            status=row["status"] or "draft",
            template_name=row["template_name"] or "",
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            started_at=row["started_at"] or "",
            completed_at=row["completed_at"] or "",
            current_step_index=row["current_step_index"] or 0,
            total_steps=row["total_steps"] or 0,
            execution_context=json.loads(row["execution_context"] or "{}"),
            error_log=json.loads(row["error_log"] or "[]"),
            tags=row["tags"] or "[]",
            domain=row["domain"] or "general",
            parent_plan_id=parent_plan_id,
        )
        return plan

    def _row_to_template(self, row: sqlite3.Row) -> PlanTemplate:
        return PlanTemplate(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            steps_template=json.loads(row["steps_template"] or "[]"),
            domain=row["domain"] or "general",
            tags=row["tags"] or "[]",
            times_used=row["times_used"] or 0,
            avg_success_rate=row["avg_success_rate"] or 0.0,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )


# ─── CLI ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Autonomous Planner v1.0")
    sub = parser.add_subparsers(dest="command")

    # create
    p_create = sub.add_parser("create", help="Create a plan")
    p_create.add_argument("title")
    p_create.add_argument("--goal-id", type=int, default=None)
    p_create.add_argument("--template", default=None)
    p_create.add_argument("--db", default=None)

    # start
    p_start = sub.add_parser("start", help="Start a plan")
    p_start.add_argument("id", type=int)
    p_start.add_argument("--db", default=None)

    # status
    p_status = sub.add_parser("status", help="Show plan status")
    p_status.add_argument("id", type=int)
    p_status.add_argument("--db", default=None)

    # replan
    p_replan = sub.add_parser("replan", help="Replan from a step")
    p_replan.add_argument("id", type=int)
    p_replan.add_argument("--from-step", type=int, required=True)
    p_replan.add_argument("--db", default=None)

    # templates
    p_templates = sub.add_parser("templates", help="List templates")
    p_templates.add_argument("--db", default=None)

    # list
    p_list = sub.add_parser("list", help="List plans")
    p_list.add_argument("--status", default=None)
    p_list.add_argument("--goal-id", type=int, default=None)
    p_list.add_argument("--db", default=None)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    db = getattr(args, "db", None)
    planner = Planner(db_path=db)

    if args.command == "create":
        if args.template:
            plan_id = planner.create_from_template(
                args.template, goal_id=args.goal_id, title=args.title
            )
            if plan_id:
                print(f"Created plan #{plan_id} from template '{args.template}'")
            else:
                print(f"Template '{args.template}' not found")
        else:
            plan_id = planner.create_plan(title=args.title, goal_id=args.goal_id)
            print(f"Created plan #{plan_id}: {args.title}")

    elif args.command == "start":
        if planner.start_plan(args.id):
            print(f"Started plan #{args.id}")
        else:
            print(f"Cannot start plan #{args.id}")

    elif args.command == "status":
        plan = planner.get_plan(args.id)
        if not plan:
            print(f"Plan #{args.id} not found")
            return
        print(f"Plan #{plan.id}: {plan.title}")
        print(f"Status: {plan.status}")
        print(f"Progress: {plan.progress_pct:.0f}% ({plan.current_step_index}/{plan.total_steps})")
        if plan.goal_id:
            print(f"Goal: #{plan.goal_id}")
        print(f"\nSteps:")
        for s in plan.steps:
            result = next((r for r in plan._step_results if r["step_index"] == s.index), None)
            status = result["status"] if result else "pending"
            icon = {"completed": "[x]", "failed": "[!]", "in_progress": "[>]"}.get(status, "[ ]")
            print(f"  {icon} {s.index}. {s.title} ({s.agent})")

    elif args.command == "replan":
        if planner.replan(args.id, args.from_step):
            print(f"Replanned #{args.id} from step {args.from_step}")
        else:
            print(f"Cannot replan #{args.id}")

    elif args.command == "templates":
        templates = planner.list_templates()
        if not templates:
            print("No templates available.")
            return
        print(f"Plan templates ({len(templates)}):\n")
        for t in templates:
            print(f"  {t.name:25s} ({t.domain}) — {t.description}")
            print(f"  {'':25s} {len(t.steps_template)} steps, used {t.times_used}x")

    elif args.command == "list":
        plans = planner.list_plans(goal_id=args.goal_id, status=args.status)
        if not plans:
            print("No plans found.")
            return
        for p in plans:
            icon = {"completed": "[x]", "failed": "[!]", "executing": "[>]",
                    "draft": "[ ]", "ready": "[=]"}.get(p.status, "[ ]")
            print(f"  {icon} #{p.id} {p.title} ({p.status}, {p.total_steps} steps)")


if __name__ == "__main__":
    main()
