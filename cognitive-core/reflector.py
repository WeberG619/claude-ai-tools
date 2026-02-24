#!/usr/bin/env python3
"""
Session Reflector — Cross-session quality assessment and goal tracking.

At the end of each session, the reflector:
1. Assesses what was accomplished
2. Scores session quality
3. Tracks progress toward persistent goals
4. Identifies patterns across sessions
5. Stores learnings for future sessions

This closes the loop: without reflection, each session is independent.
With reflection, the system maintains continuity of purpose.

Usage:
    from reflector import SessionReflector
    ref = SessionReflector()

    # End-of-session reflection
    reflection = ref.reflect({
        "session_id": "abc123",
        "goals_stated": ["Fix wall joins", "Set up CD sheets"],
        "actions_taken": ["Read model", "Fixed 3 wall joins", "Created 5 sheets"],
        "corrections_applied": 4,
        "errors_encountered": ["Sheet placement failed once"],
        "duration_minutes": 45,
    })

    # Track a persistent goal
    ref.set_goal("Complete CD set for ResidentialA", project="ResidentialA")

    # Update goal progress
    ref.update_goal_progress(goal_id, progress=0.6, notes="5/8 sheets done")

    # Weekly synthesis
    summary = ref.weekly_synthesis()
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "cognitive.db"
BRAIN_FILE = Path("/mnt/d/_CLAUDE-TOOLS/brain-state/brain.json")


@dataclass
class Reflection:
    """Result of session reflection."""
    session_id: str = ""
    quality_score: int = 5              # 1-10
    goals_pursued: list = field(default_factory=list)
    goals_achieved: list = field(default_factory=list)
    goals_partially_done: list = field(default_factory=list)
    corrections_applied: int = 0
    errors_encountered: list = field(default_factory=list)
    learnings: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    momentum: str = "steady"            # accelerating | steady | stalling | blocked
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "quality_score": self.quality_score,
            "goals_pursued": self.goals_pursued,
            "goals_achieved": self.goals_achieved,
            "goals_partially_done": self.goals_partially_done,
            "corrections_applied": self.corrections_applied,
            "errors_encountered": self.errors_encountered,
            "learnings": self.learnings,
            "recommendations": self.recommendations,
            "momentum": self.momentum,
            "summary": self.summary,
        }


@dataclass
class Goal:
    """A persistent goal tracked across sessions."""
    id: str = ""
    title: str = ""
    description: str = ""
    project: str = ""
    progress: float = 0.0              # 0.0 to 1.0
    status: str = "active"              # active | paused | completed | abandoned
    milestones: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    target_date: str = ""


class SessionReflector:
    """Cross-session reflection and goal tracking."""

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
            CREATE TABLE IF NOT EXISTS session_reflections (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                quality_score INTEGER,
                goals_pursued TEXT DEFAULT '[]',
                goals_achieved TEXT DEFAULT '[]',
                goals_partially_done TEXT DEFAULT '[]',
                corrections_applied INTEGER DEFAULT 0,
                errors TEXT DEFAULT '[]',
                learnings TEXT DEFAULT '[]',
                recommendations TEXT DEFAULT '[]',
                momentum TEXT DEFAULT 'steady',
                summary TEXT DEFAULT '',
                duration_minutes INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS persistent_goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                project TEXT DEFAULT '',
                progress REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                milestones TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                target_date TEXT,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS goal_progress_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                session_id TEXT,
                progress_delta REAL,
                new_progress REAL,
                notes TEXT DEFAULT '',
                timestamp TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES persistent_goals(id)
            );

            CREATE INDEX IF NOT EXISTS idx_reflections_date ON session_reflections(created_at);
            CREATE INDEX IF NOT EXISTS idx_goals_status ON persistent_goals(status);
            CREATE INDEX IF NOT EXISTS idx_goals_project ON persistent_goals(project);
            CREATE INDEX IF NOT EXISTS idx_progress_goal ON goal_progress_log(goal_id);
        """)
        conn.commit()
        conn.close()

    # ── SESSION REFLECTION ───────────────────────────────

    def reflect(self, session_data: dict) -> Reflection:
        """
        Perform end-of-session reflection.

        Analyzes what happened, scores quality, identifies learnings.
        """
        import uuid

        session_id = session_data.get("session_id", uuid.uuid4().hex[:8])
        goals_stated = session_data.get("goals_stated", [])
        actions_taken = session_data.get("actions_taken", [])
        corrections = session_data.get("corrections_applied", 0)
        errors = session_data.get("errors_encountered", [])
        duration = session_data.get("duration_minutes", 0)

        # Classify goal completion
        achieved = []
        partial = []
        not_started = []

        for goal in goals_stated:
            goal_lower = goal.lower()
            # Check if any action matches this goal
            action_text = " ".join(a.lower() for a in actions_taken)
            completion_signals = ["completed", "done", "finished", "created",
                                "fixed", "built", "set up", "configured"]
            partial_signals = ["started", "partially", "began", "in progress"]

            if any(s in action_text for s in completion_signals) and \
               any(w in action_text for w in goal_lower.split()[:3]):
                achieved.append(goal)
            elif any(s in action_text for s in partial_signals):
                partial.append(goal)
            elif actions_taken:
                # If actions were taken, assume at least partial progress
                partial.append(goal)
            else:
                not_started.append(goal)

        # Quality scoring
        quality_score = self._score_session(
            goals_stated, achieved, partial, errors, corrections, actions_taken, duration
        )

        # Momentum assessment
        momentum = self._assess_momentum(quality_score)

        # Generate learnings
        learnings = self._extract_learnings(
            actions_taken, errors, corrections, achieved
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            quality_score, errors, partial, not_started, momentum
        )

        # Summary
        summary = self._build_summary(
            quality_score, achieved, partial, errors, momentum, duration
        )

        reflection = Reflection(
            session_id=session_id,
            quality_score=quality_score,
            goals_pursued=goals_stated,
            goals_achieved=achieved,
            goals_partially_done=partial,
            corrections_applied=corrections,
            errors_encountered=errors,
            learnings=learnings,
            recommendations=recommendations,
            momentum=momentum,
            summary=summary,
        )

        # Store reflection
        self._store_reflection(reflection, duration)

        # Update persistent goals if any match
        self._update_matching_goals(achieved, partial, session_id)

        return reflection

    def _score_session(self, goals: list, achieved: list, partial: list,
                       errors: list, corrections: int, actions: list,
                       duration: int) -> int:
        """Score session quality 1-10."""
        if not goals and not actions:
            return 3  # Empty session

        score = 5  # Base

        # Goal completion
        if goals:
            completion_rate = (len(achieved) + 0.5 * len(partial)) / len(goals)
            score += round(completion_rate * 3)  # Up to +3

        # Error rate
        if actions:
            error_rate = len(errors) / len(actions)
            if error_rate > 0.5:
                score -= 2
            elif error_rate > 0.2:
                score -= 1

        # Corrections applied (learning happened)
        if corrections > 0:
            score += 1

        # Productivity (actions per minute, if duration known)
        if duration > 0 and actions:
            actions_per_min = len(actions) / duration
            if actions_per_min > 0.5:
                score += 1  # Productive session

        return max(1, min(10, score))

    def _assess_momentum(self, current_score: int) -> str:
        """Assess momentum by comparing to recent sessions."""
        conn = self._conn()
        recent = conn.execute("""
            SELECT quality_score FROM session_reflections
            ORDER BY created_at DESC LIMIT 5
        """).fetchall()
        conn.close()

        if not recent or len(recent) < 2:
            return "steady"

        recent_scores = [r["quality_score"] for r in recent]
        avg_recent = sum(recent_scores) / len(recent_scores)

        if current_score >= avg_recent + 1.5:
            return "accelerating"
        elif current_score <= avg_recent - 1.5:
            return "stalling"
        elif current_score <= 3:
            return "blocked"
        return "steady"

    def _extract_learnings(self, actions: list, errors: list,
                           corrections: int, achieved: list) -> list:
        """Extract learnings from session data."""
        learnings = []

        if errors:
            learnings.append(f"Encountered {len(errors)} error(s) — review for prevention patterns")

        if corrections > 3:
            learnings.append(f"Applied {corrections} corrections — system knowledge is growing")

        if achieved:
            learnings.append(f"Successfully completed {len(achieved)} goal(s)")

        if not errors and achieved:
            learnings.append("Clean execution — this workflow pattern is working well")

        return learnings

    def _generate_recommendations(self, score: int, errors: list,
                                   partial: list, not_started: list,
                                   momentum: str) -> list:
        """Generate actionable recommendations for next session."""
        recs = []

        if partial:
            recs.append(f"Continue work on: {', '.join(partial[:3])}")

        if not_started:
            recs.append(f"Start: {', '.join(not_started[:3])}")

        if errors:
            recs.append("Review errors from this session before proceeding")

        if momentum == "stalling":
            recs.append("Momentum is declining — consider breaking tasks into smaller pieces")
        elif momentum == "blocked":
            recs.append("Session appears blocked — identify and resolve the blocker first")
        elif momentum == "accelerating":
            recs.append("Strong momentum — keep this pace, avoid scope creep")

        if score < 5:
            recs.append("Low session quality — consider simplifying goals for next session")

        return recs

    def _build_summary(self, score: int, achieved: list, partial: list,
                       errors: list, momentum: str, duration: int) -> str:
        """Build a concise session summary."""
        parts = [f"Session quality: {score}/10."]

        if achieved:
            parts.append(f"Completed: {len(achieved)} goal(s).")
        if partial:
            parts.append(f"In progress: {len(partial)}.")
        if errors:
            parts.append(f"Errors: {len(errors)}.")
        if duration:
            parts.append(f"Duration: {duration}min.")

        parts.append(f"Momentum: {momentum}.")
        return " ".join(parts)

    def _store_reflection(self, ref: Reflection, duration: int = None):
        """Store session reflection."""
        import uuid
        conn = self._conn()
        conn.execute("""
            INSERT INTO session_reflections
            (id, session_id, quality_score, goals_pursued, goals_achieved,
             goals_partially_done, corrections_applied, errors, learnings,
             recommendations, momentum, summary, duration_minutes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uuid.uuid4().hex[:10], ref.session_id, ref.quality_score,
            json.dumps(ref.goals_pursued), json.dumps(ref.goals_achieved),
            json.dumps(ref.goals_partially_done), ref.corrections_applied,
            json.dumps(ref.errors_encountered), json.dumps(ref.learnings),
            json.dumps(ref.recommendations), ref.momentum, ref.summary,
            duration, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    # ── PERSISTENT GOALS ─────────────────────────────────

    def set_goal(self, title: str, description: str = "",
                 project: str = "", target_date: str = None) -> str:
        """Create a persistent goal tracked across sessions."""
        import uuid
        goal_id = uuid.uuid4().hex[:10]
        now = datetime.now().isoformat()

        conn = self._conn()
        conn.execute("""
            INSERT INTO persistent_goals
            (id, title, description, project, progress, status,
             created_at, updated_at, target_date)
            VALUES (?, ?, ?, ?, 0.0, 'active', ?, ?, ?)
        """, (goal_id, title, description, project, now, now, target_date))
        conn.commit()
        conn.close()
        return goal_id

    def update_goal_progress(self, goal_id: str, progress: float,
                              notes: str = "", session_id: str = ""):
        """Update progress on a persistent goal."""
        conn = self._conn()
        old = conn.execute(
            "SELECT progress FROM persistent_goals WHERE id = ?", (goal_id,)
        ).fetchone()

        if not old:
            conn.close()
            return

        delta = progress - old["progress"]
        now = datetime.now().isoformat()

        conn.execute("""
            UPDATE persistent_goals
            SET progress = ?, updated_at = ?,
                status = CASE WHEN ? >= 1.0 THEN 'completed' ELSE status END,
                completed_at = CASE WHEN ? >= 1.0 THEN ? ELSE completed_at END
            WHERE id = ?
        """, (progress, now, progress, progress, now, goal_id))

        conn.execute("""
            INSERT INTO goal_progress_log
            (goal_id, session_id, progress_delta, new_progress, notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (goal_id, session_id, delta, progress, notes, now))

        conn.commit()
        conn.close()

    def get_active_goals(self, project: str = None) -> list:
        """Get all active goals."""
        conn = self._conn()
        sql = "SELECT * FROM persistent_goals WHERE status = 'active'"
        params = []
        if project:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY updated_at DESC"

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_goal_timeline(self, goal_id: str) -> list:
        """Get progress history for a goal."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM goal_progress_log
            WHERE goal_id = ? ORDER BY timestamp ASC
        """, (goal_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _update_matching_goals(self, achieved: list, partial: list,
                                session_id: str):
        """Auto-update persistent goals that match session achievements."""
        goals = self.get_active_goals()
        for goal in goals:
            title_lower = goal["title"].lower()
            # Check if any achieved/partial goal matches
            for achieved_goal in achieved:
                if self._goals_overlap(title_lower, achieved_goal.lower()):
                    new_progress = min(1.0, goal["progress"] + 0.3)
                    self.update_goal_progress(
                        goal["id"], new_progress,
                        notes=f"Matched: {achieved_goal}", session_id=session_id
                    )
            for partial_goal in partial:
                if self._goals_overlap(title_lower, partial_goal.lower()):
                    new_progress = min(0.95, goal["progress"] + 0.1)
                    self.update_goal_progress(
                        goal["id"], new_progress,
                        notes=f"Partial: {partial_goal}", session_id=session_id
                    )

    @staticmethod
    def _goals_overlap(goal_a: str, goal_b: str) -> bool:
        """Check if two goal descriptions refer to the same thing."""
        words_a = set(goal_a.split()) - {"the", "a", "an", "to", "in", "for", "on"}
        words_b = set(goal_b.split()) - {"the", "a", "an", "to", "in", "for", "on"}
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
        return overlap > 0.4

    # ── WEEKLY SYNTHESIS ─────────────────────────────────

    def weekly_synthesis(self) -> dict:
        """Generate a weekly summary across all sessions."""
        conn = self._conn()

        # Get reflections from last 7 days
        reflections = conn.execute("""
            SELECT * FROM session_reflections
            WHERE created_at > datetime('now', '-7 days')
            ORDER BY created_at DESC
        """).fetchall()

        # Get goal progress from last 7 days
        goal_progress = conn.execute("""
            SELECT g.title, g.progress, g.status,
                   SUM(p.progress_delta) as week_delta
            FROM persistent_goals g
            LEFT JOIN goal_progress_log p ON g.id = p.goal_id
                AND p.timestamp > datetime('now', '-7 days')
            WHERE g.status = 'active'
            GROUP BY g.id
        """).fetchall()

        conn.close()

        if not reflections:
            return {
                "sessions": 0,
                "message": "No sessions this week.",
            }

        ref_data = [dict(r) for r in reflections]
        scores = [r["quality_score"] for r in ref_data]
        avg_score = round(sum(scores) / len(scores), 1)

        # Count total goals achieved
        total_achieved = 0
        total_errors = 0
        for r in ref_data:
            try:
                total_achieved += len(json.loads(r.get("goals_achieved", "[]")))
                total_errors += len(json.loads(r.get("errors", "[]")))
            except (json.JSONDecodeError, TypeError):
                pass

        # Momentum trend
        if len(scores) >= 3:
            first_half = scores[len(scores)//2:]
            second_half = scores[:len(scores)//2]
            if sum(second_half)/len(second_half) > sum(first_half)/len(first_half) + 0.5:
                trend = "improving"
            elif sum(second_half)/len(second_half) < sum(first_half)/len(first_half) - 0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient data"

        return {
            "sessions": len(ref_data),
            "avg_quality": avg_score,
            "total_goals_achieved": total_achieved,
            "total_errors": total_errors,
            "trend": trend,
            "goal_progress": [dict(g) for g in goal_progress] if goal_progress else [],
            "top_learnings": self._aggregate_learnings(ref_data),
        }

    def _aggregate_learnings(self, reflections: list) -> list:
        """Aggregate learnings across sessions."""
        all_learnings = []
        for r in reflections:
            try:
                learnings = json.loads(r.get("learnings", "[]"))
                all_learnings.extend(learnings)
            except (json.JSONDecodeError, TypeError):
                pass
        # Deduplicate
        seen = set()
        unique = []
        for l in all_learnings:
            if l not in seen:
                seen.add(l)
                unique.append(l)
        return unique[:10]

    def get_reflection_history(self, limit: int = 20) -> list:
        """Get recent session reflections."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT * FROM session_reflections
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Session Reflector")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("weekly", help="Weekly synthesis")
    sub.add_parser("goals", help="Show active goals")
    sub.add_parser("history", help="Recent reflections")

    goal_cmd = sub.add_parser("goal", help="Create a persistent goal")
    goal_cmd.add_argument("title", help="Goal title")
    goal_cmd.add_argument("--project", default="")

    args = parser.parse_args()
    ref = SessionReflector()

    if args.command == "weekly":
        summary = ref.weekly_synthesis()
        print("Weekly Summary:")
        for k, v in summary.items():
            print(f"  {k}: {v}")

    elif args.command == "goals":
        goals = ref.get_active_goals()
        if goals:
            for g in goals:
                bar_len = 20
                filled = int(g["progress"] * bar_len)
                bar = "=" * filled + "-" * (bar_len - filled)
                print(f"  [{bar}] {g['progress']:.0%} {g['title']}")
        else:
            print("  No active goals.")

    elif args.command == "goal":
        gid = ref.set_goal(args.title, project=args.project)
        print(f"Goal created: {gid}")

    elif args.command == "history":
        history = ref.get_reflection_history(10)
        for r in history:
            print(f"  [{r['quality_score']}/10] {r['momentum']:12s} {r['summary'][:60]}")


if __name__ == "__main__":
    main()
