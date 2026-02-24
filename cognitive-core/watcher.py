#!/usr/bin/env python3
"""
Cognitive Watcher — File and system event monitor that feeds the dispatcher.

Watches for:
1. File changes in watched directories (Revit models, code repos, project folders)
2. System state changes (from live_state.json)
3. Scheduled cognitive events (daily compile, weekly synthesis)
4. Goal deadline proximity

Events are fed through the Cognitive Dispatcher, which thinks before acting.

Usage:
    # As a daemon
    python watcher.py --daemon

    # One-shot check
    python watcher.py --check

    # Add a watch path
    python watcher.py --watch /mnt/d/RevitMCPBridge2026 --patterns "*.cs" --label "RevitBridge code"
"""

import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

try:
    from .dispatcher import CognitiveDispatcher
except ImportError:
    from dispatcher import CognitiveDispatcher

logger = logging.getLogger("cognitive-core.watcher")

SYSTEM_STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
WATCHER_STATE_FILE = Path(__file__).parent / "watcher_state.json"
WATCHER_CONFIG_FILE = Path(__file__).parent / "watcher_config.json"


@dataclass
class WatchTarget:
    """A directory or file being watched."""
    path: str
    patterns: List[str] = field(default_factory=lambda: ["*"])
    label: str = ""
    event_type: str = "file_changed"
    priority: str = "medium"
    known_state: Dict[str, float] = field(default_factory=dict)  # path -> mtime


# Default watch targets
DEFAULT_WATCHES = [
    {
        "path": "/mnt/d/RevitMCPBridge2026",
        "patterns": ["*.cs", "*.csproj"],
        "label": "RevitMCPBridge2026 code",
        "event_type": "file_changed",
        "priority": "medium",
    },
    {
        "path": "/mnt/d/_CLAUDE-TOOLS",
        "patterns": ["*.py"],
        "label": "Claude Tools code",
        "event_type": "file_changed",
        "priority": "low",
    },
]


class CognitiveWatcher:
    """
    Watches files and system state, feeds events to the cognitive dispatcher.

    Unlike raw file watchers, this one:
    - Batches rapid changes (debounce)
    - Classifies change significance
    - Feeds through cognitive core for goal-aware decisions
    - Tracks patterns over time
    """

    def __init__(self, project: str = "general"):
        self.project = project
        self.dispatcher = CognitiveDispatcher(project=project)
        self.watches: List[WatchTarget] = []
        self.last_system_state: Dict = {}
        self.last_system_hash: str = ""
        self.last_daily_compile: Optional[datetime] = None
        self.last_weekly_synthesis: Optional[datetime] = None
        self.change_buffer: Dict[str, List[dict]] = {}  # Debounce buffer
        self.buffer_flush_interval = 10  # seconds

        # Load config
        self._load_config()
        self._load_state()

    def _load_config(self):
        """Load watch configuration."""
        if WATCHER_CONFIG_FILE.exists():
            try:
                config = json.loads(WATCHER_CONFIG_FILE.read_text())
                for wc in config.get("watches", []):
                    self.watches.append(WatchTarget(**wc))
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        # Add defaults if no config
        if not self.watches:
            for w in DEFAULT_WATCHES:
                self.watches.append(WatchTarget(**w))

    def _load_state(self):
        """Load watcher state (known file states)."""
        if WATCHER_STATE_FILE.exists():
            try:
                state = json.loads(WATCHER_STATE_FILE.read_text())
                for watch in self.watches:
                    watch.known_state = state.get(watch.path, {})
                self.last_daily_compile = (
                    datetime.fromisoformat(state["last_daily_compile"])
                    if state.get("last_daily_compile") else None
                )
                self.last_weekly_synthesis = (
                    datetime.fromisoformat(state["last_weekly_synthesis"])
                    if state.get("last_weekly_synthesis") else None
                )
            except Exception as e:
                logger.error(f"Error loading state: {e}")

    def _save_state(self):
        """Save watcher state."""
        state = {
            watch.path: watch.known_state for watch in self.watches
        }
        if self.last_daily_compile:
            state["last_daily_compile"] = self.last_daily_compile.isoformat()
        if self.last_weekly_synthesis:
            state["last_weekly_synthesis"] = self.last_weekly_synthesis.isoformat()

        WATCHER_STATE_FILE.write_text(json.dumps(state, indent=2))

    def add_watch(self, path: str, patterns: List[str] = None,
                  label: str = "", event_type: str = "file_changed",
                  priority: str = "medium"):
        """Add a new watch target."""
        watch = WatchTarget(
            path=path,
            patterns=patterns or ["*"],
            label=label or Path(path).name,
            event_type=event_type,
            priority=priority,
        )
        # Initial scan
        watch.known_state = self._scan_directory(path, patterns or ["*"])
        self.watches.append(watch)
        self._save_config()
        logger.info(f"Added watch: {label or path} ({len(watch.known_state)} files)")

    def _save_config(self):
        """Save watch configuration."""
        config = {
            "watches": [
                {
                    "path": w.path,
                    "patterns": w.patterns,
                    "label": w.label,
                    "event_type": w.event_type,
                    "priority": w.priority,
                }
                for w in self.watches
            ]
        }
        WATCHER_CONFIG_FILE.write_text(json.dumps(config, indent=2))

    def _scan_directory(self, path: str, patterns: List[str]) -> Dict[str, float]:
        """Scan directory and return file -> mtime map."""
        files = {}
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return files

            for pattern in patterns:
                for f in dir_path.rglob(pattern):
                    if f.is_file() and not any(
                        skip in str(f) for skip in [
                            "__pycache__", ".git", "node_modules",
                            "bin/Debug", "bin/Release", "obj/",
                        ]
                    ):
                        try:
                            files[str(f)] = f.stat().st_mtime
                        except OSError:
                            pass
        except Exception as e:
            logger.error(f"Error scanning {path}: {e}")
        return files

    # ── File Change Detection ────────────────────────

    def check_files(self) -> List[dict]:
        """Check all watched directories for changes."""
        all_events = []

        for watch in self.watches:
            current_state = self._scan_directory(watch.path, watch.patterns)

            # Find changes
            modified = []
            created = []
            deleted = []

            for filepath, mtime in current_state.items():
                if filepath not in watch.known_state:
                    created.append(filepath)
                elif mtime != watch.known_state[filepath]:
                    modified.append(filepath)

            for filepath in watch.known_state:
                if filepath not in current_state:
                    deleted.append(filepath)

            # Generate events
            for fp in modified:
                all_events.append({
                    "type": watch.event_type,
                    "source": "cognitive_watcher",
                    "priority": watch.priority,
                    "data": {
                        "path": fp,
                        "change": "modified",
                        "watch_label": watch.label,
                    }
                })

            for fp in created:
                all_events.append({
                    "type": "file_created",
                    "source": "cognitive_watcher",
                    "priority": watch.priority,
                    "data": {
                        "path": fp,
                        "change": "created",
                        "watch_label": watch.label,
                    }
                })

            # Update known state
            watch.known_state = current_state

        return all_events

    # ── System State Detection ───────────────────────

    def check_system_state(self) -> List[dict]:
        """Check system state for significant changes."""
        events = []

        try:
            if not SYSTEM_STATE_FILE.exists():
                return events

            state = json.loads(SYSTEM_STATE_FILE.read_text())
            state_hash = hashlib.md5(
                json.dumps(state.get("active_window", "")).encode()
            ).hexdigest()

            if state_hash == self.last_system_hash:
                return events

            self.last_system_hash = state_hash

            # Detect Revit events
            active_window = state.get("active_window", "")
            prev_window = self.last_system_state.get("active_window", "")

            if "Revit" in active_window and "Revit" not in prev_window:
                events.append({
                    "type": "revit_opened",
                    "source": "cognitive_watcher",
                    "priority": "medium",
                    "data": {"window_title": active_window},
                })
            elif "Revit" in active_window and "Revit" in prev_window:
                # Check for project change
                if active_window != prev_window:
                    events.append({
                        "type": "revit_project_changed",
                        "source": "cognitive_watcher",
                        "priority": "medium",
                        "data": {
                            "window_title": active_window,
                            "domain": "revit",
                        },
                    })

            # Detect Bluebeam events
            bb = state.get("bluebeam", {})
            prev_bb = self.last_system_state.get("bluebeam", {})
            if bb.get("running") and bb.get("document") != prev_bb.get("document"):
                events.append({
                    "type": "bluebeam_document",
                    "source": "cognitive_watcher",
                    "priority": "low",
                    "data": {"document": bb.get("document", "")},
                })

            # Memory warning
            system = state.get("system", {})
            memory_pct = system.get("memory_percent", 0)
            if memory_pct > 85:
                events.append({
                    "type": "memory_high",
                    "source": "cognitive_watcher",
                    "priority": "medium",
                    "data": {"memory_percent": memory_pct},
                })

            self.last_system_state = state

        except Exception as e:
            logger.error(f"Error checking system state: {e}")

        return events

    # ── Scheduled Events ─────────────────────────────

    def check_scheduled(self) -> List[dict]:
        """Check for scheduled cognitive events."""
        events = []
        now = datetime.now()

        # Daily compile: once per day at 11 PM
        if now.hour == 23 and now.minute < 5:
            if not self.last_daily_compile or \
               (now - self.last_daily_compile).days >= 1:
                events.append({
                    "type": "daily_review",
                    "source": "cognitive_watcher",
                    "priority": "low",
                    "data": {"date": now.strftime("%Y-%m-%d")},
                })
                self.last_daily_compile = now

        # Weekly synthesis: Sunday at 10 PM
        if now.weekday() == 6 and now.hour == 22 and now.minute < 5:
            if not self.last_weekly_synthesis or \
               (now - self.last_weekly_synthesis).days >= 6:
                events.append({
                    "type": "weekly_synthesis",
                    "source": "cognitive_watcher",
                    "priority": "low",
                    "data": {"week": now.strftime("%Y-W%W")},
                })
                self.last_weekly_synthesis = now

        # Goal deadline check: every 6 hours
        goals = self.dispatcher.brain.get_goals()
        for goal in goals:
            if goal.get("target_date"):
                try:
                    target = datetime.fromisoformat(goal["target_date"])
                    days_left = (target - now).days
                    if days_left <= 2 and days_left >= 0:
                        events.append({
                            "type": "goal_deadline",
                            "source": "cognitive_watcher",
                            "priority": "high",
                            "data": {
                                "goal_id": goal["id"],
                                "goal_title": goal["title"],
                                "days_left": days_left,
                                "progress": goal["progress"],
                            },
                        })
                except (ValueError, TypeError):
                    pass

        return events

    # ── Main Loop ────────────────────────────────────

    def check_all(self) -> List[dict]:
        """Run all checks and dispatch events."""
        all_events = []

        # File changes
        file_events = self.check_files()
        all_events.extend(file_events)

        # System state
        system_events = self.check_system_state()
        all_events.extend(system_events)

        # Scheduled
        scheduled_events = self.check_scheduled()
        all_events.extend(scheduled_events)

        # Dispatch all events through the cognitive core
        results = []
        for event in all_events:
            try:
                result = self.dispatcher.dispatch(event)
                results.append(result)
                if result.action_taken not in ("suppressed", "noted"):
                    logger.info(f"Dispatched: {event['type']} -> {result.action_taken} "
                               f"({result.reasoning[:80]})")
            except Exception as e:
                logger.error(f"Dispatch error for {event['type']}: {e}")

        # Save state
        if all_events:
            self._save_state()

        return results

    def run_daemon(self, interval: int = 30):
        """Run as a background daemon."""
        logger.info(f"Cognitive Watcher daemon starting (interval: {interval}s)")
        logger.info(f"Watching {len(self.watches)} directories")

        while True:
            try:
                results = self.check_all()
                active = [r for r in results if r.action_taken not in ("suppressed", "noted")]
                if active:
                    logger.info(f"Cycle: {len(results)} events, {len(active)} actions taken")
            except Exception as e:
                logger.error(f"Watcher cycle error: {e}")

            time.sleep(interval)


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    parser = argparse.ArgumentParser(description="Cognitive Watcher")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--check", action="store_true", help="Run one check cycle")
    parser.add_argument("--interval", type=int, default=30, help="Daemon interval (seconds)")
    parser.add_argument("--watch", help="Add a watch path")
    parser.add_argument("--patterns", help="File patterns (comma-separated)")
    parser.add_argument("--label", help="Watch label")
    parser.add_argument("--stats", action="store_true", help="Show dispatch stats")

    args = parser.parse_args()
    watcher = CognitiveWatcher()

    if args.watch:
        patterns = args.patterns.split(",") if args.patterns else ["*"]
        watcher.add_watch(args.watch, patterns, args.label or "")
        print(f"Added watch: {args.watch}")

    elif args.daemon:
        watcher.run_daemon(args.interval)

    elif args.check:
        results = watcher.check_all()
        print(f"Check complete: {len(results)} events processed")
        for r in results:
            if r.action_taken != "suppressed":
                print(f"  [{r.action_taken}] {r.reasoning[:80]}")

    elif args.stats:
        stats = watcher.dispatcher.get_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
