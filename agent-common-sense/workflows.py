"""
Workflow recording and replay for the Common Sense Engine.

Records multi-step sequences of tool calls as named workflows,
stores them in the database, and retrieves similar workflows
for new tasks.

This enables pattern learning: "Last time you did X, you used
these steps in this order. Consider following the same pattern."

Usage:
    from workflows import WorkflowRecorder

    recorder = WorkflowRecorder(db_path)

    # Start recording
    recorder.start("deploy-revit-addin")

    # Record steps as they happen
    recorder.add_step("Bash", {"command": "dotnet build"}, "Build succeeded")
    recorder.add_step("Bash", {"command": "cp ..."}, "Copied DLL")
    recorder.add_step("mcp__revit__restart", {}, "Revit restarted")

    # Save the workflow
    recorder.save(tags=["revit", "deployment"])

    # Later: find similar workflows
    matches = recorder.find_similar("deploy revit plugin")

CLI:
    python workflows.py list                      # List all workflows
    python workflows.py show <name>               # Show workflow details
    python workflows.py find "deploy revit"        # Find similar workflows
    python workflows.py delete <name>              # Delete a workflow
"""

import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    tool_name: str
    tool_input: dict
    result_summary: str = ""
    timestamp: str = ""
    order: int = 0

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "result_summary": self.result_summary,
            "timestamp": self.timestamp,
            "order": self.order,
        }


@dataclass
class Workflow:
    """A recorded multi-step workflow."""
    name: str
    steps: list[WorkflowStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    description: str = ""
    created_at: str = ""
    success: bool = True
    domain: str = "general"
    times_used: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "tags": self.tags,
            "description": self.description,
            "created_at": self.created_at,
            "success": self.success,
            "domain": self.domain,
            "times_used": self.times_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        steps = [
            WorkflowStep(
                tool_name=s.get("tool_name", ""),
                tool_input=s.get("tool_input", {}),
                result_summary=s.get("result_summary", ""),
                timestamp=s.get("timestamp", ""),
                order=s.get("order", i),
            )
            for i, s in enumerate(data.get("steps", []))
        ]
        return cls(
            name=data.get("name", ""),
            steps=steps,
            tags=data.get("tags", []),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            success=data.get("success", True),
            domain=data.get("domain", "general"),
            times_used=data.get("times_used", 0),
        )


# ─── WORKFLOW RECORDER ──────────────────────────────────────────

class WorkflowRecorder:
    """Records, stores, and retrieves multi-step workflows."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._find_db()
        self._current: Optional[Workflow] = None
        self._step_counter = 0
        if self.db_path:
            self._ensure_table()

    def _find_db(self) -> str:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return ""

    def _ensure_table(self):
        """Create workflows table if it doesn't exist."""
        if not self.db_path:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    steps TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    description TEXT DEFAULT '',
                    domain TEXT DEFAULT 'general',
                    success INTEGER DEFAULT 1,
                    times_used INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Workflow table creation failed: {e}", file=sys.stderr)

    # ─── RECORDING ───────────────────────────────────────────

    def start(self, name: str, description: str = "",
              domain: str = "general"):
        """Start recording a new workflow."""
        self._current = Workflow(
            name=name,
            description=description,
            domain=domain,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._step_counter = 0

    def add_step(self, tool_name: str, tool_input: dict,
                 result_summary: str = ""):
        """Add a step to the current recording."""
        if self._current is None:
            return

        self._step_counter += 1
        step = WorkflowStep(
            tool_name=tool_name,
            tool_input=tool_input,
            result_summary=result_summary,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            order=self._step_counter,
        )
        self._current.steps.append(step)

    def save(self, tags: list[str] = None, success: bool = True) -> bool:
        """Save the current recording to the database."""
        if self._current is None:
            return False

        self._current.tags = tags or []
        self._current.success = success

        result = self._store_workflow(self._current)
        self._current = None
        self._step_counter = 0
        return result

    def cancel(self):
        """Cancel the current recording."""
        self._current = None
        self._step_counter = 0

    @property
    def recording(self) -> bool:
        """Whether a recording is in progress."""
        return self._current is not None

    @property
    def current_steps(self) -> int:
        """Number of steps in the current recording."""
        return len(self._current.steps) if self._current else 0

    # ─── STORAGE ─────────────────────────────────────────────

    def _store_workflow(self, workflow: Workflow) -> bool:
        """Store a workflow in the database."""
        if not self.db_path:
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Check if workflow with this name already exists
            existing = conn.execute(
                "SELECT id FROM workflows WHERE name = ?",
                (workflow.name,)
            ).fetchone()

            if existing:
                # Update existing
                conn.execute("""
                    UPDATE workflows
                    SET steps = ?, tags = ?, description = ?,
                        domain = ?, success = ?, updated_at = ?
                    WHERE name = ?
                """, (
                    json.dumps([s.to_dict() for s in workflow.steps]),
                    json.dumps(workflow.tags),
                    workflow.description,
                    workflow.domain,
                    1 if workflow.success else 0,
                    now,
                    workflow.name,
                ))
            else:
                # Insert new
                conn.execute("""
                    INSERT INTO workflows
                    (name, steps, tags, description, domain, success,
                     times_used, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """, (
                    workflow.name,
                    json.dumps([s.to_dict() for s in workflow.steps]),
                    json.dumps(workflow.tags),
                    workflow.description,
                    workflow.domain,
                    1 if workflow.success else 0,
                    workflow.created_at or now,
                    now,
                ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Workflow store failed: {e}", file=sys.stderr)
            return False

    def _load_workflow(self, name: str) -> Optional[Workflow]:
        """Load a workflow by name."""
        if not self.db_path:
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM workflows WHERE name = ?", (name,)
            ).fetchone()
            conn.close()

            if not row:
                return None

            row = dict(row)
            data = {
                "name": row["name"],
                "steps": json.loads(row.get("steps", "[]")),
                "tags": json.loads(row.get("tags", "[]")),
                "description": row.get("description", ""),
                "created_at": row.get("created_at", ""),
                "success": bool(row.get("success", 1)),
                "domain": row.get("domain", "general"),
                "times_used": row.get("times_used", 0),
            }
            return Workflow.from_dict(data)

        except Exception as e:
            print(f"Workflow load failed: {e}", file=sys.stderr)
            return None

    # ─── RETRIEVAL ───────────────────────────────────────────

    def list_workflows(self, domain: str = None) -> list[dict]:
        """List all stored workflows."""
        if not self.db_path:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            sql = "SELECT name, description, domain, success, times_used, created_at FROM workflows"
            params = []

            if domain:
                sql += " WHERE domain = ?"
                params.append(domain)

            sql += " ORDER BY times_used DESC, created_at DESC"

            rows = conn.execute(sql, params).fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception:
            return []

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name and increment its usage counter."""
        workflow = self._load_workflow(name)

        if workflow and self.db_path:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    "UPDATE workflows SET times_used = times_used + 1 WHERE name = ?",
                    (name,)
                )
                conn.commit()
                conn.close()
            except Exception:
                pass

        return workflow

    def find_similar(self, query: str, limit: int = 5) -> list[dict]:
        """Find workflows similar to a query description.

        Uses keyword matching against workflow names, descriptions,
        tags, and tool names.
        """
        if not self.db_path:
            return []

        query_words = set(re.findall(r'[a-z]{3,}', query.lower()))
        if not query_words:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                "SELECT * FROM workflows ORDER BY times_used DESC"
            ).fetchall()
            conn.close()

            scored = []
            for row in rows:
                row = dict(row)

                # Build searchable text
                searchable = " ".join([
                    row.get("name", ""),
                    row.get("description", ""),
                    " ".join(json.loads(row.get("tags", "[]"))),
                    row.get("domain", ""),
                ])

                # Also search tool names in steps
                try:
                    steps = json.loads(row.get("steps", "[]"))
                    for step in steps:
                        searchable += " " + step.get("tool_name", "")
                except (json.JSONDecodeError, TypeError):
                    pass

                searchable_words = set(re.findall(r'[a-z]{3,}', searchable.lower()))
                overlap = query_words & searchable_words

                if overlap:
                    score = len(overlap) / len(query_words)

                    # Bonus for successful workflows
                    if row.get("success", 1):
                        score *= 1.2

                    # Bonus for frequently used
                    times_used = row.get("times_used", 0)
                    if times_used > 0:
                        score *= (1 + min(times_used, 10) * 0.05)

                    scored.append({
                        "name": row["name"],
                        "description": row.get("description", ""),
                        "domain": row.get("domain", "general"),
                        "step_count": len(json.loads(row.get("steps", "[]"))),
                        "times_used": times_used,
                        "success": bool(row.get("success", 1)),
                        "score": round(score, 3),
                    })

            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:limit]

        except Exception as e:
            print(f"Workflow search failed: {e}", file=sys.stderr)
            return []

    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow by name."""
        if not self.db_path:
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM workflows WHERE name = ?", (name,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def format_workflow(self, workflow: Workflow) -> str:
        """Format a workflow as human-readable text."""
        lines = [
            f"Workflow: {workflow.name}",
            f"Domain: {workflow.domain}",
            f"Steps: {len(workflow.steps)}",
            f"Status: {'success' if workflow.success else 'failed'}",
            f"Used: {workflow.times_used} times",
        ]

        if workflow.description:
            lines.append(f"Description: {workflow.description}")

        if workflow.tags:
            lines.append(f"Tags: {', '.join(workflow.tags)}")

        lines.append(f"\nSteps:")
        for i, step in enumerate(workflow.steps, 1):
            tool = step.tool_name
            # Summarize input (first key-value or first 100 chars)
            input_summary = ""
            if step.tool_input:
                first_key = next(iter(step.tool_input), "")
                first_val = step.tool_input.get(first_key, "")
                if isinstance(first_val, str):
                    input_summary = f"{first_key}={first_val[:80]}"
                else:
                    input_summary = f"{first_key}={json.dumps(first_val)[:80]}"

            result = step.result_summary[:80] if step.result_summary else ""
            lines.append(f"  {i}. {tool}({input_summary})")
            if result:
                lines.append(f"     → {result}")

        return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Workflow recorder")
    parser.add_argument("command",
                        choices=["list", "show", "find", "delete", "stats"],
                        help="Command to run")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("--db", help="Path to memory database")
    parser.add_argument("--domain", help="Filter by domain")
    args = parser.parse_args()

    recorder = WorkflowRecorder(db_path=args.db)

    if args.command == "list":
        workflows = recorder.list_workflows(domain=args.domain)
        if not workflows:
            print("No workflows recorded.")
            return

        print(f"Recorded workflows ({len(workflows)}):\n")
        for wf in workflows:
            success = "ok" if wf.get("success", 1) else "FAILED"
            print(f"  [{success}] {wf['name']:30s} "
                  f"({wf.get('domain', '?')}, "
                  f"used {wf.get('times_used', 0)}x)")
            if wf.get("description"):
                print(f"           {wf['description'][:60]}")

    elif args.command == "show":
        if not args.args:
            print("Usage: python workflows.py show <name>")
            return
        name = " ".join(args.args)
        workflow = recorder._load_workflow(name)
        if workflow:
            print(recorder.format_workflow(workflow))
        else:
            print(f"Workflow '{name}' not found.")

    elif args.command == "find":
        if not args.args:
            print("Usage: python workflows.py find <query>")
            return
        query = " ".join(args.args)
        matches = recorder.find_similar(query)
        if matches:
            print(f"Similar workflows for '{query}':\n")
            for m in matches:
                print(f"  [{m['score']:.0%}] {m['name']} "
                      f"({m['step_count']} steps, domain: {m['domain']})")
        else:
            print("No similar workflows found.")

    elif args.command == "delete":
        if not args.args:
            print("Usage: python workflows.py delete <name>")
            return
        name = " ".join(args.args)
        if recorder.delete_workflow(name):
            print(f"Deleted workflow '{name}'.")
        else:
            print(f"Failed to delete workflow '{name}'.")

    elif args.command == "stats":
        workflows = recorder.list_workflows()
        if not workflows:
            print("No workflows recorded.")
            return

        print(f"Workflow stats:")
        print(f"  Total: {len(workflows)}")
        print(f"  Successful: {sum(1 for w in workflows if w.get('success', 1))}")
        print(f"  Failed: {sum(1 for w in workflows if not w.get('success', 1))}")
        print(f"  Total uses: {sum(w.get('times_used', 0) for w in workflows)}")

        # Domain breakdown
        domains = {}
        for w in workflows:
            d = w.get("domain", "general")
            domains[d] = domains.get(d, 0) + 1
        print(f"\n  By domain:")
        for d, count in sorted(domains.items(), key=lambda kv: kv[1], reverse=True):
            print(f"    {d:20s} {count}")


if __name__ == "__main__":
    main()
