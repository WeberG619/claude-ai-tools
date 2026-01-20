#!/usr/bin/env python3
"""
BridgeAI Scheduler
==================
Runs automated tasks on schedules - the AI that works while you sleep.
"""

import os
import json
import time
import threading
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Callable, Any
import subprocess

class Task:
    """A scheduled task"""
    def __init__(self, name: str, action: Callable, schedule_type: str,
                 schedule_value: Any, enabled: bool = True):
        self.name = name
        self.action = action
        self.schedule_type = schedule_type  # 'interval', 'daily', 'weekly', 'cron'
        self.schedule_value = schedule_value
        self.enabled = enabled
        self.last_run = None
        self.run_count = 0
        self.errors = []

    def run(self):
        """Execute the task"""
        if not self.enabled:
            return

        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Running: {self.name}")
            self.action()
            self.last_run = datetime.now()
            self.run_count += 1
        except Exception as e:
            self.errors.append({
                'time': datetime.now().isoformat(),
                'error': str(e)
            })
            print(f"  Error: {e}")

class Scheduler:
    """
    Task scheduler that runs jobs automatically.
    """

    def __init__(self, config_path: Path = None):
        self.tasks: Dict[str, Task] = {}
        self.running = False
        self.config_path = config_path or Path('C:/BridgeAI/data/schedules.json')
        self._thread = None

        # Built-in tasks
        self._register_builtin_tasks()

    def _register_builtin_tasks(self):
        """Register default system tasks"""

        # Health check every 5 minutes
        self.add_task(
            name="system_health_check",
            action=self._health_check,
            schedule_type="interval",
            schedule_value=5  # minutes
        )

        # Cleanup old files daily at 3am
        self.add_task(
            name="daily_cleanup",
            action=self._daily_cleanup,
            schedule_type="daily",
            schedule_value="03:00"
        )

        # Memory optimization every hour
        self.add_task(
            name="memory_optimize",
            action=self._optimize_memory,
            schedule_type="interval",
            schedule_value=60  # minutes
        )

        # Backup important data daily
        self.add_task(
            name="daily_backup",
            action=self._daily_backup,
            schedule_type="daily",
            schedule_value="02:00"
        )

    def _health_check(self):
        """Check system health"""
        import socket

        checks = {
            'hub_5000': ('localhost', 5000),
            'brain_5001': ('localhost', 5001),
            'ollama_11434': ('localhost', 11434),
        }

        results = {}
        for name, (host, port) in checks.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                results[name] = result == 0
            except:
                results[name] = False

        # Log results
        log_path = Path('C:/BridgeAI/logs/health.log')
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {json.dumps(results)}\n")

        # Alert if something is down
        down = [k for k, v in results.items() if not v]
        if down:
            print(f"  WARNING: Services down: {', '.join(down)}")

    def _daily_cleanup(self):
        """Clean up old temporary files"""
        import shutil

        cleanup_paths = [
            (Path('C:/BridgeAI/logs'), 7),  # Logs older than 7 days
            (Path('C:/BridgeAI/Results'), 3),  # Results older than 3 days
            (Path('C:/Windows/Temp'), 1),  # Temp files older than 1 day
        ]

        total_cleaned = 0
        for path, days in cleanup_paths:
            if not path.exists():
                continue

            cutoff = datetime.now() - timedelta(days=days)
            for f in path.rglob('*'):
                try:
                    if f.is_file():
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if mtime < cutoff:
                            f.unlink()
                            total_cleaned += 1
                except:
                    pass

        print(f"  Cleaned {total_cleaned} old files")

    def _optimize_memory(self):
        """Optimize brain memory database"""
        import sqlite3

        db_path = Path('C:/BridgeAI/data/brain_memory.db')
        if db_path.exists():
            with sqlite3.connect(db_path) as conn:
                # Vacuum to reclaim space
                conn.execute('VACUUM')

                # Delete very old, low-importance memories
                cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                conn.execute('''
                    DELETE FROM memories
                    WHERE importance < 0.3
                    AND created_at < ?
                    AND access_count < 2
                ''', (cutoff,))

            print("  Memory optimized")

    def _daily_backup(self):
        """Backup important data"""
        import shutil

        backup_dir = Path('C:/BridgeAI/Backups')
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup brain memory
        src = Path('C:/BridgeAI/data/brain_memory.db')
        if src.exists():
            dst = backup_dir / f"brain_memory_{datetime.now().strftime('%Y%m%d')}.db"
            shutil.copy2(src, dst)
            print(f"  Backed up memory to {dst.name}")

        # Clean old backups (keep last 7)
        backups = sorted(backup_dir.glob('brain_memory_*.db'))
        for old_backup in backups[:-7]:
            old_backup.unlink()

    def add_task(self, name: str, action: Callable, schedule_type: str,
                 schedule_value: Any, enabled: bool = True):
        """Add a new scheduled task"""
        task = Task(name, action, schedule_type, schedule_value, enabled)
        self.tasks[name] = task

        # Register with schedule library
        if schedule_type == "interval":
            schedule.every(schedule_value).minutes.do(task.run).tag(name)
        elif schedule_type == "daily":
            schedule.every().day.at(schedule_value).do(task.run).tag(name)
        elif schedule_type == "weekly":
            day, time_str = schedule_value.split('@')
            getattr(schedule.every(), day.lower()).at(time_str).do(task.run).tag(name)

    def remove_task(self, name: str):
        """Remove a scheduled task"""
        if name in self.tasks:
            del self.tasks[name]
            schedule.clear(name)

    def start(self):
        """Start the scheduler"""
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"Scheduler started with {len(self.tasks)} tasks")

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self):
        """Main scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def status(self) -> Dict:
        """Get scheduler status"""
        return {
            'running': self.running,
            'task_count': len(self.tasks),
            'tasks': {
                name: {
                    'enabled': task.enabled,
                    'schedule': f"{task.schedule_type}:{task.schedule_value}",
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'run_count': task.run_count,
                    'error_count': len(task.errors)
                }
                for name, task in self.tasks.items()
            }
        }

# Singleton instance
_scheduler = None

def get_scheduler() -> Scheduler:
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler

if __name__ == '__main__':
    print("BridgeAI Scheduler")
    print("=" * 40)

    scheduler = get_scheduler()
    scheduler.start()

    print(f"\nScheduled tasks:")
    for name, task in scheduler.tasks.items():
        print(f"  - {name}: {task.schedule_type} @ {task.schedule_value}")

    print("\nScheduler running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
        print("\nScheduler stopped.")
