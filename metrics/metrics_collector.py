#!/usr/bin/env python3
"""
Agent System Metrics Collector
Weber Gouin / BIM Ops Studio

Queries all agent infrastructure databases and produces a text dashboard.
No external dependencies — stdlib only.
"""

import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ─── Paths ────────────────────────────────────────────────────────────────────

BASE = Path("/mnt/d/_CLAUDE-TOOLS")
BOARD_DB      = BASE / "task-board/board.db"
MEMORIES_DB   = BASE / "claude-memory-server/data/memories.db"
EVENTS_NDJSON = BASE / "system-bridge/events.ndjson"
AUDIT_NDJSON  = BASE / "system-bridge/audit.ndjson"
BRAIN_JSON    = BASE / "brain-state/brain.json"
LIVE_STATE    = BASE / "system-bridge/live_state.json"

NOW = datetime.now(timezone.utc)
NOW_NAIVE = datetime.utcnow()
CUTOFF_24H = NOW_NAIVE - timedelta(hours=24)
CUTOFF_7D  = NOW_NAIVE - timedelta(days=7)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _db_connect(path: Path) -> Optional[sqlite3.Connection]:
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _parse_ts(s: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime (naive UTC)."""
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None


def _bar(value: float, max_val: float, width: int = 20, fill: str = "█") -> str:
    """ASCII progress bar."""
    if max_val <= 0:
        return "─" * width
    filled = int(round(value / max_val * width))
    filled = max(0, min(width, filled))
    return fill * filled + "░" * (width - filled)


def _pct(num: int, den: int) -> float:
    return round(num / den * 100, 1) if den else 0.0


def _section(title: str) -> str:
    return f"\n{'═' * 60}\n  {title}\n{'═' * 60}"


# ─── Task Board ───────────────────────────────────────────────────────────────

def collect_tasks() -> dict:
    result = {
        "available": False,
        "total": 0,
        "by_status": {},
        "completion_rate_pct": 0.0,
        "completed_7d": 0,
        "avg_per_day_7d": 0.0,
        "high_priority_pending": 0,
        "retry_failures": 0,
        "recent_completions": [],
        "error_rate_pct": 0.0,
    }
    conn = _db_connect(BOARD_DB)
    if not conn:
        return result
    try:
        result["available"] = True
        c = conn.cursor()

        # Status counts
        c.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        by_status = {row[0]: row[1] for row in c.fetchall()}
        result["by_status"] = by_status
        total = sum(by_status.values())
        result["total"] = total

        completed = by_status.get("completed", 0)
        failed    = by_status.get("failed", 0) + by_status.get("error", 0)
        result["completion_rate_pct"] = _pct(completed, total)
        result["error_rate_pct"] = _pct(failed, total)

        # Completed in last 7 days
        c.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='completed' AND completed_at >= ?",
            (CUTOFF_7D.isoformat(),),
        )
        completed_7d = c.fetchone()[0]
        result["completed_7d"] = completed_7d
        result["avg_per_day_7d"] = round(completed_7d / 7, 1)

        # High priority pending (priority >= 7)
        c.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='pending' AND priority >= 7"
        )
        result["high_priority_pending"] = c.fetchone()[0]

        # Retry failures
        c.execute("SELECT COUNT(*) FROM retry_log WHERE success=0")
        result["retry_failures"] = c.fetchone()[0]

        # Recent completions (last 3)
        c.execute(
            "SELECT title, project, completed_at FROM tasks "
            "WHERE status='completed' ORDER BY completed_at DESC LIMIT 3"
        )
        result["recent_completions"] = [dict(r) for r in c.fetchall()]

    except Exception as e:
        result["error"] = str(e)
    finally:
        conn.close()

    return result


# ─── Memory / Corrections ─────────────────────────────────────────────────────

def collect_memories() -> dict:
    result = {
        "available": False,
        "total": 0,
        "by_type": {},
        "corrections_total": 0,
        "corrections_by_project": [],
        "recent_corrections": [],
        "top_importance": [],
        "high_importance_count": 0,
        "projects_tracked": 0,
        "goals_active": 0,
        "goals_total": 0,
        "corrections_7d": 0,
    }
    conn = _db_connect(MEMORIES_DB)
    if not conn:
        return result
    try:
        result["available"] = True
        c = conn.cursor()

        # Total and by type
        c.execute("SELECT COUNT(*) FROM memories")
        result["total"] = c.fetchone()[0]

        c.execute(
            "SELECT memory_type, COUNT(*) as n FROM memories "
            "GROUP BY memory_type ORDER BY n DESC"
        )
        result["by_type"] = {row[0]: row[1] for row in c.fetchall()}

        # Corrections
        c.execute("SELECT COUNT(*) FROM memories WHERE memory_type='correction'")
        result["corrections_total"] = c.fetchone()[0]

        c.execute(
            "SELECT project, COUNT(*) as n FROM memories "
            "WHERE memory_type='correction' "
            "GROUP BY project ORDER BY n DESC LIMIT 8"
        )
        result["corrections_by_project"] = [
            {"project": row[0] or "untagged", "count": row[1]}
            for row in c.fetchall()
        ]

        # Recent corrections (last 5)
        c.execute(
            "SELECT id, summary, project, importance, created_at FROM memories "
            "WHERE memory_type='correction' ORDER BY created_at DESC LIMIT 5"
        )
        result["recent_corrections"] = [
            {
                "id": row[0],
                "summary": (row[1] or "")[:80],
                "project": row[2] or "untagged",
                "importance": row[3],
                "created_at": row[4],
            }
            for row in c.fetchall()
        ]

        # Corrections in last 7 days
        c.execute(
            "SELECT COUNT(*) FROM memories "
            "WHERE memory_type='correction' AND created_at >= ?",
            (CUTOFF_7D.isoformat(),),
        )
        result["corrections_7d"] = c.fetchone()[0]

        # High importance (>= 9)
        c.execute("SELECT COUNT(*) FROM memories WHERE importance >= 9")
        result["high_importance_count"] = c.fetchone()[0]

        # Top importance memories (non-correction)
        c.execute(
            "SELECT summary, importance, memory_type, project FROM memories "
            "WHERE memory_type != 'correction' "
            "ORDER BY importance DESC, created_at DESC LIMIT 5"
        )
        result["top_importance"] = [
            {
                "summary": (row[0] or "")[:70],
                "importance": row[1],
                "type": row[2],
                "project": row[3] or "—",
            }
            for row in c.fetchall()
        ]

        # Projects tracked
        c.execute("SELECT COUNT(*) FROM projects")
        result["projects_tracked"] = c.fetchone()[0]

        # Goals
        c.execute("SELECT COUNT(*) FROM goals")
        result["goals_total"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM goals WHERE status NOT IN ('done','cancelled','completed')")
        result["goals_active"] = c.fetchone()[0]

    except Exception as e:
        result["error"] = str(e)
    finally:
        conn.close()

    return result


# ─── System Events ────────────────────────────────────────────────────────────

def collect_events() -> dict:
    result = {
        "available": False,
        "total_in_file": 0,
        "last_24h": 0,
        "by_type_24h": {},
        "most_common_type": "—",
        "audit_blocks_total": 0,
        "audit_blocks_7d": 0,
        "last_event_ts": None,
    }

    # events.ndjson (system events)
    if EVENTS_NDJSON.exists():
        try:
            result["available"] = True
            type_counter_24h: Counter = Counter()
            total = 0
            last_ts = None

            with EVENTS_NDJSON.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    total += 1
                    ev_type = ev.get("event_type") or ev.get("type", "unknown")
                    ts_str = ev.get("ts") or ev.get("timestamp")
                    ts = _parse_ts(ts_str)

                    if ts and (last_ts is None or ts > last_ts):
                        last_ts = ts

                    if ts and ts >= CUTOFF_24H:
                        type_counter_24h[ev_type] += 1

            result["total_in_file"] = total
            result["last_24h"] = sum(type_counter_24h.values())
            result["by_type_24h"] = dict(type_counter_24h.most_common(8))
            if type_counter_24h:
                result["most_common_type"] = type_counter_24h.most_common(1)[0][0]
            if last_ts:
                result["last_event_ts"] = last_ts.isoformat()

        except Exception as e:
            result["error"] = str(e)

    # audit.ndjson (seatbelt blocks)
    if AUDIT_NDJSON.exists():
        try:
            blocks_total = 0
            blocks_7d = 0
            with AUDIT_NDJSON.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("action") == "block":
                        blocks_total += 1
                        ts = _parse_ts(ev.get("timestamp"))
                        if ts and ts >= CUTOFF_7D:
                            blocks_7d += 1
            result["audit_blocks_total"] = blocks_total
            result["audit_blocks_7d"] = blocks_7d
        except Exception:
            pass

    return result


# ─── Brain State ──────────────────────────────────────────────────────────────

def collect_brain() -> dict:
    result = {
        "available": False,
        "last_updated": None,
        "last_session_date": None,
        "last_session_messages": 0,
        "active_projects": [],
        "pending_tasks": 0,
        "completed_tasks_in_brain": 0,
        "corrections_in_brain": 0,
    }
    if not BRAIN_JSON.exists():
        return result
    try:
        data = json.loads(BRAIN_JSON.read_text(encoding="utf-8"))
        result["available"] = True
        result["last_updated"] = data.get("last_updated")

        last_sess = data.get("last_session", {})
        result["last_session_date"] = last_sess.get("date")
        result["last_session_messages"] = last_sess.get("messages", 0)

        active = data.get("active_projects", [])
        result["active_projects"] = [p.get("name", "?") for p in active]

        pending = data.get("pending_tasks", [])
        result["pending_tasks"] = sum(
            1 for t in pending if t.get("status") not in ("completed", "done")
        )
        result["completed_tasks_in_brain"] = sum(
            1 for t in pending if t.get("status") in ("completed", "done")
        )
        result["corrections_in_brain"] = len(data.get("critical_corrections", []))

    except Exception as e:
        result["error"] = str(e)

    return result


# ─── Live State ───────────────────────────────────────────────────────────────

def collect_live_state() -> dict:
    result = {
        "available": False,
        "memory_pct": 0,
        "memory_used_gb": 0.0,
        "memory_total_gb": 0.0,
        "cpu_pct": 0,
        "monitor_count": 0,
        "app_count": 0,
        "daemon_updates": 0,
        "daemon_errors": 0,
        "daemon_restarts": 0,
        "daemon_started_at": None,
        "revit_connected": False,
        "bluebeam_running": False,
    }
    if not LIVE_STATE.exists():
        return result
    try:
        data = json.loads(LIVE_STATE.read_text(encoding="utf-8"))
        result["available"] = True

        sys = data.get("system", {})
        result["memory_pct"] = sys.get("memory_percent", 0)
        result["memory_used_gb"] = sys.get("memory_used_gb", 0.0)
        result["memory_total_gb"] = sys.get("memory_total_gb", 0.0)
        result["cpu_pct"] = sys.get("cpu_percent", 0)

        monitors = data.get("monitors", {})
        result["monitor_count"] = monitors.get("count", 0)
        result["app_count"] = len(data.get("applications", []))

        stats = data.get("daemon_stats", {})
        result["daemon_updates"] = stats.get("updates", 0)
        result["daemon_errors"] = stats.get("errors", 0)
        result["daemon_restarts"] = stats.get("restarts", 0)
        result["daemon_started_at"] = stats.get("started_at")

        revit = data.get("revit", {})
        result["revit_connected"] = revit.get("connected", False)
        result["bluebeam_running"] = data.get("bluebeam", {}).get("running", False)

    except Exception as e:
        result["error"] = str(e)

    return result


# ─── Health Score ─────────────────────────────────────────────────────────────

def compute_health_score(tasks: dict, memories: dict, events: dict, brain: dict, live: dict) -> tuple[int, list[str]]:
    """
    Heuristic health score 0-100. Returns (score, list_of_flags).
    Weights:
      - Task completion rate    (30 pts)
      - Low error rate          (20 pts)
      - Memory system healthy   (20 pts)
      - Daemon stability        (15 pts)
      - Correction rate stable  (15 pts)
    """
    score = 0
    flags = []

    # Task completion (30 pts) — scaled by completion rate
    if tasks["available"] and tasks["total"] > 0:
        comp_pct = tasks["completion_rate_pct"]
        task_score = int(comp_pct * 0.30)
        score += task_score
        if comp_pct < 50:
            flags.append(f"Low task completion rate ({comp_pct}%) — investigate blockers")
        if tasks["high_priority_pending"] >= 3:
            flags.append(f"{tasks['high_priority_pending']} high-priority tasks still pending")
    elif not tasks["available"]:
        score += 15  # neutral if no data
        flags.append("Task board DB unavailable")

    # Error rate (20 pts)
    if tasks["available"] and tasks["total"] > 0:
        err_pct = tasks["error_rate_pct"]
        if err_pct == 0:
            score += 20
        elif err_pct < 10:
            score += 15
        elif err_pct < 25:
            score += 8
            flags.append(f"Elevated task error rate ({err_pct}%)")
        else:
            flags.append(f"High task error rate ({err_pct}%) — review failed tasks")
    else:
        score += 10

    # Memory system (20 pts)
    if memories["available"]:
        score += 15
        if memories["total"] > 0:
            score += 5
        if memories["corrections_7d"] > 10:
            flags.append(
                f"{memories['corrections_7d']} corrections in last 7 days — prompts may need tuning"
            )
        if memories["total"] > 800:
            flags.append(
                f"Memory bank large ({memories['total']} entries) — consider pruning low-importance memories"
            )
    else:
        flags.append("Memories DB unavailable")

    # Daemon stability (15 pts)
    if live["available"]:
        restarts = live["daemon_restarts"]
        errors   = live["daemon_errors"]
        if restarts < 5 and errors < 5:
            score += 15
        elif restarts < 20 and errors < 20:
            score += 10
        elif restarts < 60:
            score += 5
            flags.append(f"Daemon has restarted {restarts}x — check watchdog logs")
        else:
            flags.append(f"Daemon instability: {restarts} restarts, {errors} errors")
    else:
        score += 7
        flags.append("Live state unavailable")

    # Correction rate (15 pts)
    if memories["available"]:
        c7d = memories["corrections_7d"]
        if c7d <= 3:
            score += 15
        elif c7d <= 7:
            score += 10
        elif c7d <= 15:
            score += 5
            flags.append(f"Correction rate trending up ({c7d}/week) — monitor agent behaviour")
        else:
            flags.append(f"High correction rate ({c7d}/week) — prompts need fixing")
    else:
        score += 7

    score = max(0, min(100, score))
    return score, flags


def health_label(score: int) -> str:
    if score >= 85:
        return "HEALTHY"
    elif score >= 65:
        return "GOOD"
    elif score >= 45:
        return "DEGRADED"
    else:
        return "CRITICAL"


# ─── Render Dashboard ─────────────────────────────────────────────────────────

def render(tasks: dict, memories: dict, events: dict, brain: dict, live: dict) -> str:
    lines = []
    ts_str = NOW.strftime("%Y-%m-%d %H:%M UTC")

    health_score, health_flags = compute_health_score(tasks, memories, events, brain, live)
    label = health_label(health_score)

    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║         CLAUDE AGENT SYSTEM — OBSERVABILITY DASHBOARD   ║")
    lines.append(f"║  {ts_str:<56}║")
    lines.append("╚══════════════════════════════════════════════════════════╝")

    # Health score banner
    bar = _bar(health_score, 100, width=30)
    lines.append(f"\n  HEALTH SCORE: {health_score}/100  [{label}]")
    lines.append(f"  [{bar}]")

    if health_flags:
        lines.append("\n  ANOMALIES DETECTED:")
        for flag in health_flags:
            lines.append(f"    ! {flag}")
    else:
        lines.append("\n  No anomalies detected.")

    # ── Task Board ──
    lines.append(_section("TASK BOARD"))
    if not tasks["available"]:
        lines.append("  [unavailable] board.db not found")
    else:
        lines.append(f"  Total tasks:       {tasks['total']}")
        lines.append(f"  Completion rate:   {tasks['completion_rate_pct']}%")
        lines.append(f"  Error rate:        {tasks['error_rate_pct']}%")
        lines.append(f"  High-pri pending:  {tasks['high_priority_pending']}")
        lines.append(f"  Completed (7d):    {tasks['completed_7d']}  ({tasks['avg_per_day_7d']}/day avg)")
        lines.append(f"  Retry failures:    {tasks['retry_failures']}")

        if tasks["by_status"]:
            lines.append("\n  Status breakdown:")
            for status, count in sorted(tasks["by_status"].items()):
                bar = _bar(count, tasks["total"], width=15)
                lines.append(f"    {status:<12} {count:>4}  [{bar}]")

        if tasks["recent_completions"]:
            lines.append("\n  Recent completions:")
            for t in tasks["recent_completions"]:
                lines.append(f"    - {t['title'][:50]}  [{t['project'] or '—'}]")

    # ── Memory System ──
    lines.append(_section("MEMORY SYSTEM"))
    if not memories["available"]:
        lines.append("  [unavailable] memories.db not found")
    else:
        lines.append(f"  Total memories:    {memories['total']}")
        lines.append(f"  High importance:   {memories['high_importance_count']}  (importance >= 9)")
        lines.append(f"  Corrections total: {memories['corrections_total']}")
        lines.append(f"  Corrections (7d):  {memories['corrections_7d']}")
        lines.append(f"  Projects tracked:  {memories['projects_tracked']}")
        lines.append(f"  Goals (active/total): {memories['goals_active']}/{memories['goals_total']}")

        if memories["by_type"]:
            lines.append("\n  Memory types:")
            total_mem = memories["total"] or 1
            for mtype, count in sorted(memories["by_type"].items(), key=lambda x: -x[1]):
                bar = _bar(count, total_mem, width=15)
                pct = _pct(count, total_mem)
                lines.append(f"    {mtype:<12} {count:>4}  [{bar}]  {pct}%")

        if memories["corrections_by_project"]:
            lines.append("\n  Corrections by project:")
            for entry in memories["corrections_by_project"][:6]:
                lines.append(f"    {entry['project']:<30} {entry['count']:>3}")

        if memories["recent_corrections"]:
            lines.append("\n  5 most recent corrections:")
            for corr in memories["recent_corrections"]:
                date = corr["created_at"][:10] if corr["created_at"] else "?"
                lines.append(
                    f"    [{date}] [{corr['project']}] "
                    f"(imp:{corr['importance']}) {corr['summary'][:60]}"
                )

        if memories["top_importance"]:
            lines.append("\n  Top importance memories (non-correction):")
            for m in memories["top_importance"]:
                lines.append(
                    f"    [{m['importance']:>2}] [{m['type']:<10}] {m['summary'][:55]}"
                    f"  ({m['project']})"
                )

    # ── System Events ──
    lines.append(_section("SYSTEM EVENTS  (events.ndjson)"))
    if not events["available"]:
        lines.append("  [unavailable] events.ndjson not found")
    else:
        lines.append(f"  Events in file:    {events['total_in_file']}")
        lines.append(f"  Events (last 24h): {events['last_24h']}")
        lines.append(f"  Most common type:  {events['most_common_type']}")
        if events["last_event_ts"]:
            lines.append(f"  Last event:        {events['last_event_ts']}")

        if events["by_type_24h"]:
            lines.append("\n  Event types (last 24h):")
            max_count = max(events["by_type_24h"].values()) or 1
            for etype, count in sorted(events["by_type_24h"].items(), key=lambda x: -x[1]):
                bar = _bar(count, max_count, width=15)
                lines.append(f"    {etype:<20} {count:>4}  [{bar}]")

        lines.append(f"\n  Seatbelt audit blocks:")
        lines.append(f"    All time:          {events['audit_blocks_total']}")
        lines.append(f"    Last 7 days:       {events['audit_blocks_7d']}")

    # ── Brain State ──
    lines.append(_section("BRAIN STATE"))
    if not brain["available"]:
        lines.append("  [unavailable] brain.json not found")
    else:
        lines.append(f"  Last updated:      {brain['last_updated'] or '?'}")
        lines.append(f"  Last session:      {brain['last_session_date'] or '?'}  ({brain['last_session_messages']} messages)")
        lines.append(f"  Active projects:   {', '.join(brain['active_projects']) or '—'}")
        lines.append(f"  Pending tasks:     {brain['pending_tasks']}")
        lines.append(f"  Completed tasks:   {brain['completed_tasks_in_brain']}")
        lines.append(f"  Corrections (hot): {brain['corrections_in_brain']}")

    # ── Live System ──
    lines.append(_section("LIVE SYSTEM  (live_state.json)"))
    if not live["available"]:
        lines.append("  [unavailable] live_state.json not found")
    else:
        mem_bar = _bar(live["memory_pct"], 100, width=20)
        cpu_bar = _bar(live["cpu_pct"], 100, width=20)
        lines.append(f"  Memory:  {live['memory_pct']:>3}%  [{mem_bar}]  "
                     f"{live['memory_used_gb']:.1f}/{live['memory_total_gb']:.0f} GB")
        lines.append(f"  CPU:     {live['cpu_pct']:>3}%  [{cpu_bar}]")
        lines.append(f"  Monitors: {live['monitor_count']}    Apps open: {live['app_count']}")
        lines.append(f"  Revit:    {'connected' if live['revit_connected'] else 'not connected'}")
        lines.append(f"  Bluebeam: {'running' if live['bluebeam_running'] else 'not running'}")
        lines.append(f"\n  Daemon stats:")
        lines.append(f"    Started:   {live['daemon_started_at'] or '?'}")
        lines.append(f"    Updates:   {live['daemon_updates']:,}")
        lines.append(f"    Errors:    {live['daemon_errors']}")
        lines.append(f"    Restarts:  {live['daemon_restarts']}")

    # ── Footer ──
    lines.append("\n" + "─" * 60)
    lines.append(f"  Score: {health_score}/100 [{label}]  |  Generated: {ts_str}")
    lines.append("─" * 60)

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    tasks    = collect_tasks()
    memories = collect_memories()
    events   = collect_events()
    brain    = collect_brain()
    live     = collect_live_state()

    print(render(tasks, memories, events, brain, live))


if __name__ == "__main__":
    main()
