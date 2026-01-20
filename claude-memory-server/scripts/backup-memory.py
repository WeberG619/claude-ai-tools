#!/usr/bin/env python3
"""
Claude Memory Backup Script
Maintains rotating backups with integrity verification
Run via cron: 0 * * * * /usr/bin/python3 /mnt/d/_CLAUDE-TOOLS/claude-memory-server/scripts/backup-memory.py
"""

import sqlite3
import shutil
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuration
MEMORY_DIR = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server")
DB_FILE = MEMORY_DIR / "data" / "memories.db"
BACKUP_DIR = MEMORY_DIR / "backups"
LOG_FILE = BACKUP_DIR / "backup.log"

MAX_HOURLY = 24   # Keep 24 hourly backups
MAX_DAILY = 7     # Keep 7 daily backups
MAX_WEEKLY = 4    # Keep 4 weekly backups


def log(message: str):
    """Log message to file and stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def verify_db(db_path: Path) -> tuple[bool, str]:
    """Verify database integrity."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()[0]
        conn.close()
        return result == "ok", result
    except Exception as e:
        return False, str(e)


def get_memory_count(db_path: Path) -> int:
    """Get count of memories in database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories;")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        return -1


def create_backup(source: Path, dest: Path) -> bool:
    """Create backup using SQLite's backup API for consistency."""
    try:
        # Use SQLite's online backup for safe backup while DB might be in use
        source_conn = sqlite3.connect(source)
        dest_conn = sqlite3.connect(dest)

        # Perform the backup
        source_conn.backup(dest_conn)

        source_conn.close()
        dest_conn.close()

        return True
    except Exception as e:
        log(f"ERROR creating backup: {e}")
        return False


def rotate_backups(directory: Path, max_count: int, pattern: str = "memory_*.db"):
    """Remove old backups beyond max_count."""
    import glob

    backups = sorted(
        glob.glob(str(directory / pattern)),
        key=os.path.getmtime,
        reverse=True
    )

    if len(backups) > max_count:
        for old_backup in backups[max_count:]:
            try:
                os.remove(old_backup)
                log(f"Rotated old backup: {Path(old_backup).name}")
            except Exception as e:
                log(f"ERROR removing old backup: {e}")


def main():
    """Main backup process."""
    log("=" * 50)
    log("Starting Claude Memory backup")

    # Create backup directories
    (BACKUP_DIR / "hourly").mkdir(parents=True, exist_ok=True)
    (BACKUP_DIR / "daily").mkdir(parents=True, exist_ok=True)
    (BACKUP_DIR / "weekly").mkdir(parents=True, exist_ok=True)

    # Check if database exists
    if not DB_FILE.exists():
        log(f"ERROR: Database not found at {DB_FILE}")
        sys.exit(1)

    # Verify source database
    log("Verifying source database integrity...")
    ok, result = verify_db(DB_FILE)
    if not ok:
        log(f"ERROR: Database integrity check failed: {result}")
        sys.exit(1)
    log("Source database integrity: OK")

    # Get current memory count
    memory_count = get_memory_count(DB_FILE)
    log(f"Current memory count: {memory_count}")

    # Create timestamp
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    day_of_week = now.isoweekday()  # 1=Monday, 7=Sunday
    hour = now.hour

    # Create hourly backup
    hourly_backup = BACKUP_DIR / "hourly" / f"memory_{timestamp}.db"
    log(f"Creating hourly backup: {hourly_backup.name}")

    if not create_backup(DB_FILE, hourly_backup):
        log("ERROR: Failed to create hourly backup!")
        sys.exit(1)

    # Verify backup
    ok, result = verify_db(hourly_backup)
    if not ok:
        log(f"ERROR: Backup integrity check failed: {result}")
        hourly_backup.unlink()
        sys.exit(1)

    backup_count = get_memory_count(hourly_backup)
    if backup_count != memory_count:
        log(f"WARNING: Memory count mismatch! Source: {memory_count}, Backup: {backup_count}")
    else:
        log(f"Backup verified: {backup_count} memories")

    # At midnight, create daily backup
    if hour == 0:
        daily_backup = BACKUP_DIR / "daily" / f"memory_{now.strftime('%Y%m%d')}.db"
        shutil.copy2(hourly_backup, daily_backup)
        log(f"Daily backup created: {daily_backup.name}")

        # On Sunday, create weekly backup
        if day_of_week == 7:
            weekly_backup = BACKUP_DIR / "weekly" / f"memory_{now.strftime('%Y_week%W')}.db"
            shutil.copy2(hourly_backup, weekly_backup)
            log(f"Weekly backup created: {weekly_backup.name}")

    # Rotate old backups
    rotate_backups(BACKUP_DIR / "hourly", MAX_HOURLY)
    rotate_backups(BACKUP_DIR / "daily", MAX_DAILY)
    rotate_backups(BACKUP_DIR / "weekly", MAX_WEEKLY)

    # Report status
    import glob
    hourly_count = len(glob.glob(str(BACKUP_DIR / "hourly" / "memory_*.db")))
    daily_count = len(glob.glob(str(BACKUP_DIR / "daily" / "memory_*.db")))
    weekly_count = len(glob.glob(str(BACKUP_DIR / "weekly" / "memory_*.db")))

    log(f"Backup complete. Counts: Hourly={hourly_count}, Daily={daily_count}, Weekly={weekly_count}")

    # Total backup size
    total_size = sum(f.stat().st_size for f in BACKUP_DIR.rglob("*.db"))
    log(f"Total backup size: {total_size / 1024 / 1024:.2f} MB")

    log("Backup finished successfully")
    log("=" * 50)


if __name__ == "__main__":
    main()
