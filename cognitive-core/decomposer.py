#!/usr/bin/env python3
"""
Goal Decomposition Engine — Breaks high-level goals into executable task trees.

Given a vague goal like "Set up CD sheets for residential project", the decomposer:
1. Classifies the domain and complexity
2. Checks for similar past decompositions
3. Generates a dependency-ordered task tree
4. Creates entries in the task board
5. Estimates which agent/framework handles each subtask

Usage:
    from decomposer import GoalDecomposer
    gd = GoalDecomposer()

    tree = gd.decompose(
        "Extract floor plan from PDF and create walls in Revit",
        context={"project": "ResidentialA", "revit_version": "2026"}
    )

    # Auto-create tasks on the board
    task_ids = gd.create_board_tasks(tree, project="ResidentialA")
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "cognitive.db"
BOARD_DB = Path("/mnt/d/_CLAUDE-TOOLS/task-board/board.db")


@dataclass
class TaskNode:
    """A single node in a task tree."""
    id: str = ""
    title: str = ""
    description: str = ""
    depends_on: list = field(default_factory=list)  # IDs of prerequisite tasks
    agent_type: str = "general"         # Which agent handles this
    framework: str = "strong_agent"     # strong_agent | pipeline | swarm | direct
    model_tier: str = "sonnet"          # haiku | sonnet | opus
    estimated_effort: str = "medium"    # trivial | small | medium | large | huge
    domain: str = "general"
    priority: int = 5
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "depends_on": self.depends_on,
            "agent_type": self.agent_type,
            "framework": self.framework,
            "model_tier": self.model_tier,
            "estimated_effort": self.estimated_effort,
            "domain": self.domain,
            "priority": self.priority,
            "tags": self.tags,
        }


@dataclass
class TaskTree:
    """A decomposed goal as a dependency tree of tasks."""
    goal: str = ""
    domain: str = "general"
    complexity: str = "medium"
    tasks: list = field(default_factory=list)  # List of TaskNode
    total_estimated_effort: str = "medium"
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "domain": self.domain,
            "complexity": self.complexity,
            "tasks": [t.to_dict() for t in self.tasks],
            "total_estimated_effort": self.total_estimated_effort,
            "reasoning": self.reasoning,
        }

    def dag_view(self) -> str:
        """ASCII dependency graph."""
        lines = [f"Goal: {self.goal}", f"Complexity: {self.complexity}", ""]
        task_map = {t.id: t for t in self.tasks}
        roots = [t for t in self.tasks if not t.depends_on]

        def render(node, indent=0):
            prefix = "  " * indent + ("+-" if indent > 0 else "")
            lines.append(f"{prefix}[{node.id}] {node.title} ({node.model_tier}/{node.framework})")
            children = [t for t in self.tasks if node.id in t.depends_on]
            for child in children:
                render(child, indent + 1)

        for root in roots:
            render(root)

        return "\n".join(lines)


# Domain classification patterns
DOMAIN_PATTERNS = {
    "revit": ["revit", "wall", "floor", "door", "window", "sheet", "view",
              "family", "parameter", "level", "grid", "bim", "model",
              "element", "room", "annotation", "schedule"],
    "code": ["code", "function", "class", "refactor", "bug", "test",
             "implement", "api", "endpoint", "build", "compile", "debug",
             "commit", "branch", "merge", "deploy"],
    "desktop": ["excel", "bluebeam", "browser", "chrome", "window",
                "screenshot", "click", "type", "navigate", "open", "close"],
    "pipeline": ["pipeline", "workflow", "extract", "process", "transform",
                 "stage", "phase", "cd set", "construction document",
                 "floor plan", "markup"],
    "document": ["pdf", "document", "report", "email", "draft", "write",
                 "template", "letter", "proposal"],
}

# Complexity classification thresholds
COMPLEXITY_SIGNALS = {
    "trivial": {"max_words": 8, "signals": ["fix typo", "rename", "change", "update one"]},
    "small": {"max_words": 15, "signals": ["add a", "create one", "modify", "update"]},
    "medium": {"max_words": 30, "signals": ["implement", "build", "set up", "configure"]},
    "large": {"max_words": 50, "signals": ["redesign", "migrate", "overhaul", "integrate"]},
    "huge": {"max_words": 999, "signals": ["rebuild from scratch", "full system", "complete"]},
}

# Template decompositions for known goal patterns
TEMPLATES = {
    "cd_set": {
        "patterns": ["cd set", "construction document", "sheet set"],
        "tasks": [
            {"title": "Analyze model for views needed", "framework": "strong_agent",
             "model": "haiku", "effort": "small"},
            {"title": "Create sheet layout plan", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium", "depends": [0]},
            {"title": "Create sheets from template", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium", "depends": [1]},
            {"title": "Place views on sheets", "framework": "strong_agent",
             "model": "sonnet", "effort": "large", "depends": [2]},
            {"title": "Add annotations and dimensions", "framework": "strong_agent",
             "model": "sonnet", "effort": "large", "depends": [3]},
            {"title": "Verify output and fix issues", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium", "depends": [4]},
        ],
    },
    "floor_plan_extraction": {
        "patterns": ["floor plan", "pdf to revit", "extract walls", "trace perimeter"],
        "tasks": [
            {"title": "Extract floor plan geometry from source", "framework": "pipeline",
             "model": "sonnet", "effort": "medium"},
            {"title": "Classify wall types and dimensions", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium", "depends": [0]},
            {"title": "Create walls in Revit model", "framework": "strong_agent",
             "model": "sonnet", "effort": "large", "depends": [1]},
            {"title": "Verify wall placement and joins", "framework": "strong_agent",
             "model": "haiku", "effort": "small", "depends": [2]},
        ],
    },
    "revit_project_setup": {
        "patterns": ["project setup", "new project", "initialize project", "set up project"],
        "tasks": [
            {"title": "Create project from template", "framework": "strong_agent",
             "model": "sonnet", "effort": "small"},
            {"title": "Set project information parameters", "framework": "direct",
             "model": "haiku", "effort": "trivial", "depends": [0]},
            {"title": "Configure levels", "framework": "strong_agent",
             "model": "sonnet", "effort": "small", "depends": [0]},
            {"title": "Create grid system", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium", "depends": [2]},
            {"title": "Set up standard views", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium", "depends": [2, 3]},
            {"title": "Verify model setup", "framework": "strong_agent",
             "model": "haiku", "effort": "small", "depends": [4]},
        ],
    },
    "code_feature": {
        "patterns": ["add feature", "implement", "new endpoint", "new functionality"],
        "tasks": [
            {"title": "Research existing patterns and conventions", "framework": "strong_agent",
             "model": "haiku", "effort": "small"},
            {"title": "Design approach and interfaces", "framework": "pipeline",
             "model": "sonnet", "effort": "medium", "depends": [0]},
            {"title": "Implement core logic", "framework": "strong_agent",
             "model": "sonnet", "effort": "large", "depends": [1]},
            {"title": "Write tests", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium", "depends": [2]},
            {"title": "Verify build and all tests pass", "framework": "direct",
             "model": "haiku", "effort": "small", "depends": [3]},
        ],
    },
    "bug_fix": {
        "patterns": ["fix bug", "debug", "fix issue", "fix error", "broken"],
        "tasks": [
            {"title": "Reproduce and investigate root cause", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium"},
            {"title": "Implement fix", "framework": "strong_agent",
             "model": "sonnet", "effort": "medium", "depends": [0]},
            {"title": "Test fix and check for regressions", "framework": "strong_agent",
             "model": "sonnet", "effort": "small", "depends": [1]},
        ],
    },
}


class GoalDecomposer:
    """Breaks high-level goals into executable task trees."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS decompositions (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                domain TEXT,
                complexity TEXT,
                task_tree TEXT,
                template_used TEXT,
                success INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_decomp_domain ON decompositions(domain);
        """)
        conn.commit()
        conn.close()

    def decompose(self, goal: str, context: dict = None) -> TaskTree:
        """
        Decompose a high-level goal into an executable task tree.

        Steps:
        1. Classify domain
        2. Assess complexity
        3. Check for matching template
        4. Check for similar past decompositions
        5. Generate task tree
        6. Store for learning
        """
        context = context or {}
        domain = self._classify_domain(goal)
        complexity = self._assess_complexity(goal)

        # Try template match first
        template = self._match_template(goal)
        if template:
            tree = self._apply_template(goal, template, domain, complexity, context)
        else:
            # Generate from scratch using heuristic decomposition
            tree = self._heuristic_decompose(goal, domain, complexity, context)

        # Store for future reference
        self._store_decomposition(tree, template_name=template[0] if template else None)

        return tree

    def _classify_domain(self, goal: str) -> str:
        """Classify goal into a domain based on keyword matching."""
        goal_lower = goal.lower()
        scores = {}
        for domain, keywords in DOMAIN_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"

    def _assess_complexity(self, goal: str) -> str:
        """Assess goal complexity from text analysis."""
        goal_lower = goal.lower()
        word_count = len(goal.split())

        # Check for explicit complexity signals
        for level in ["huge", "large", "medium", "small", "trivial"]:
            signals = COMPLEXITY_SIGNALS[level]["signals"]
            if any(s in goal_lower for s in signals):
                return level

        # Fall back to word count heuristic
        for level in ["trivial", "small", "medium", "large", "huge"]:
            if word_count <= COMPLEXITY_SIGNALS[level]["max_words"]:
                return level

        return "large"

    def _match_template(self, goal: str) -> Optional[tuple]:
        """Check if goal matches a known template."""
        goal_lower = goal.lower()
        for name, template in TEMPLATES.items():
            for pattern in template["patterns"]:
                if pattern in goal_lower:
                    return (name, template)
        return None

    def _apply_template(self, goal: str, template: tuple, domain: str,
                        complexity: str, context: dict) -> TaskTree:
        """Apply a template to generate a task tree."""
        name, tmpl = template
        tasks = []

        for i, task_def in enumerate(tmpl["tasks"]):
            node = TaskNode(
                id=f"t{i+1}",
                title=task_def["title"],
                description=f"Part of: {goal}",
                depends_on=[f"t{d+1}" for d in task_def.get("depends", [])],
                framework=task_def.get("framework", "strong_agent"),
                model_tier=task_def.get("model", "sonnet"),
                estimated_effort=task_def.get("effort", "medium"),
                domain=domain,
                priority=8 - i,  # Earlier tasks get higher priority
                tags=[name, domain],
            )
            tasks.append(node)

        effort_map = {"trivial": 1, "small": 2, "medium": 4, "large": 8, "huge": 16}
        total = sum(effort_map.get(t.estimated_effort, 4) for t in tasks)
        if total <= 4:
            total_effort = "small"
        elif total <= 12:
            total_effort = "medium"
        elif total <= 24:
            total_effort = "large"
        else:
            total_effort = "huge"

        return TaskTree(
            goal=goal,
            domain=domain,
            complexity=complexity,
            tasks=tasks,
            total_estimated_effort=total_effort,
            reasoning=f"Applied template '{name}' ({len(tasks)} tasks). Domain: {domain}.",
        )

    def _heuristic_decompose(self, goal: str, domain: str,
                             complexity: str, context: dict) -> TaskTree:
        """
        Generate a task tree from heuristics when no template matches.

        Uses a generic pattern:
        1. Research/investigate
        2. Plan approach
        3. Execute
        4. Verify

        Adjusts granularity based on complexity.
        """
        tasks = []

        if complexity in ("trivial", "small"):
            # Simple tasks: just execute and verify
            tasks.append(TaskNode(
                id="t1", title=f"Execute: {goal}",
                description=goal,
                framework="direct", model_tier="sonnet",
                estimated_effort=complexity, domain=domain, priority=8,
            ))
            tasks.append(TaskNode(
                id="t2", title="Verify result",
                description=f"Confirm that '{goal}' was completed correctly",
                depends_on=["t1"],
                framework="direct", model_tier="haiku",
                estimated_effort="trivial", domain=domain, priority=7,
            ))

        elif complexity == "medium":
            # Medium: investigate, execute, verify
            tasks.append(TaskNode(
                id="t1", title=f"Investigate requirements for: {goal[:60]}",
                description=f"Research what's needed to accomplish: {goal}",
                framework="strong_agent", model_tier="haiku",
                estimated_effort="small", domain=domain, priority=8,
            ))
            tasks.append(TaskNode(
                id="t2", title=f"Execute: {goal[:60]}",
                description=goal,
                depends_on=["t1"],
                framework="strong_agent", model_tier="sonnet",
                estimated_effort="medium", domain=domain, priority=7,
            ))
            tasks.append(TaskNode(
                id="t3", title="Verify and clean up",
                description=f"Verify '{goal}' completed correctly, fix any issues",
                depends_on=["t2"],
                framework="strong_agent", model_tier="haiku",
                estimated_effort="small", domain=domain, priority=6,
            ))

        else:
            # Large/huge: full lifecycle
            tasks.append(TaskNode(
                id="t1", title=f"Research and scope: {goal[:50]}",
                description=f"Investigate requirements, dependencies, and risks for: {goal}",
                framework="strong_agent", model_tier="haiku",
                estimated_effort="medium", domain=domain, priority=9,
            ))
            tasks.append(TaskNode(
                id="t2", title="Design approach",
                description=f"Plan the approach for: {goal}. Identify subtasks and dependencies.",
                depends_on=["t1"],
                framework="strong_agent", model_tier="sonnet",
                estimated_effort="medium", domain=domain, priority=8,
            ))
            tasks.append(TaskNode(
                id="t3", title="Implement core",
                description=f"Execute the main work for: {goal}",
                depends_on=["t2"],
                framework="pipeline" if domain in ("code", "pipeline") else "strong_agent",
                model_tier="opus" if complexity == "huge" else "sonnet",
                estimated_effort="large", domain=domain, priority=7,
            ))
            tasks.append(TaskNode(
                id="t4", title="Test and validate",
                description=f"Verify all deliverables for: {goal}",
                depends_on=["t3"],
                framework="strong_agent", model_tier="sonnet",
                estimated_effort="medium", domain=domain, priority=6,
            ))
            if complexity == "huge":
                tasks.append(TaskNode(
                    id="t5", title="Review and iterate",
                    description="Final review, address feedback, polish",
                    depends_on=["t4"],
                    framework="strong_agent", model_tier="sonnet",
                    estimated_effort="medium", domain=domain, priority=5,
                ))

        return TaskTree(
            goal=goal,
            domain=domain,
            complexity=complexity,
            tasks=tasks,
            total_estimated_effort=complexity,
            reasoning=f"Heuristic decomposition for {complexity} {domain} task ({len(tasks)} steps).",
        )

    def create_board_tasks(self, tree: TaskTree, project: str = "") -> list:
        """
        Create tasks on the cross-session task board from a task tree.

        Returns list of created task IDs (board IDs, not tree IDs).
        """
        if not BOARD_DB.exists():
            return []

        import sys
        sys.path.insert(0, str(BOARD_DB.parent))
        from board import TaskBoard
        board = TaskBoard()

        # Map tree IDs to board IDs
        id_map = {}
        created_ids = []

        for node in tree.tasks:
            # Map dependencies
            blocked_by = [id_map[dep] for dep in node.depends_on if dep in id_map]

            board_id = board.add(
                title=node.title,
                description=node.description,
                priority=node.priority,
                project=project,
                source="cognitive-decomposer",
                tags=node.tags + [tree.domain, f"framework:{node.framework}",
                                  f"model:{node.model_tier}"],
            )

            if blocked_by:
                board.update(board_id, blocked_by=blocked_by)
                board.update(board_id, status="blocked")

            id_map[node.id] = board_id
            created_ids.append(board_id)

        return created_ids

    def _store_decomposition(self, tree: TaskTree, template_name: str = None):
        """Store decomposition for learning."""
        import uuid
        conn = self._conn()
        conn.execute("""
            INSERT INTO decompositions (id, goal, domain, complexity, task_tree,
                                        template_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            uuid.uuid4().hex[:10], tree.goal, tree.domain, tree.complexity,
            json.dumps(tree.to_dict()), template_name,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def record_success(self, decomposition_id: str, success: bool):
        """Record whether a decomposition led to successful execution."""
        conn = self._conn()
        conn.execute(
            "UPDATE decompositions SET success = ? WHERE id = ?",
            (1 if success else 0, decomposition_id)
        )
        conn.commit()
        conn.close()


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Goal Decomposition Engine")
    sub = parser.add_subparsers(dest="command")

    dec = sub.add_parser("decompose", help="Decompose a goal")
    dec.add_argument("goal", help="The goal to decompose")
    dec.add_argument("--create-tasks", action="store_true",
                     help="Create tasks on the board")
    dec.add_argument("--project", default="")

    sub.add_parser("templates", help="List available templates")

    args = parser.parse_args()
    gd = GoalDecomposer()

    if args.command == "decompose":
        tree = gd.decompose(args.goal)
        print(tree.dag_view())
        print(f"\nReasoning: {tree.reasoning}")
        print(f"Total effort: {tree.total_estimated_effort}")

        if args.create_tasks:
            ids = gd.create_board_tasks(tree, project=args.project)
            print(f"\nCreated {len(ids)} board tasks: {ids}")

    elif args.command == "templates":
        for name, tmpl in TEMPLATES.items():
            patterns = ", ".join(tmpl["patterns"])
            print(f"  {name}: {patterns} ({len(tmpl['tasks'])} tasks)")


if __name__ == "__main__":
    main()
