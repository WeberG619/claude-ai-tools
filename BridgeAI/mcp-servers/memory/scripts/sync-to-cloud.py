#!/usr/bin/env python3
"""
Claude Memory Cloud Sync Script
Syncs memory database to cloud storage for offsite backup.

Supports:
- Dropbox (if dropbox folder exists)
- OneDrive (if onedrive folder exists)
- Custom network path

Run manually or via cron: 0 */6 * * * /usr/bin/python3 /mnt/d/_CLAUDE-TOOLS/claude-memory-server/scripts/sync-to-cloud.py
"""

import shutil
import os
from datetime import datetime
from pathlib import Path

# Configuration
MEMORY_DIR = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server")
DB_FILE = MEMORY_DIR / "data" / "memories.db"
BACKUP_DIR = MEMORY_DIR / "backups"

# Cloud sync destinations (in order of preference)
CLOUD_DESTINATIONS = [
    Path("/mnt/d/Dropbox (Personal)/Claude-Memory-Backup"),
    Path("/mnt/d/Dropbox/Claude-Memory-Backup"),
    Path("/mnt/c/Users/weber/OneDrive/Claude-Memory-Backup"),
    Path("/mnt/c/Users/weber/Dropbox/Claude-Memory-Backup"),
]

# Network backup location (optional)
NETWORK_BACKUP = os.environ.get("CLAUDE_MEMORY_NETWORK_BACKUP", None)

LOG_FILE = BACKUP_DIR / "cloud-sync.log"


def log(message: str):
    """Log message to file and stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def find_cloud_destination() -> Path | None:
    """Find available cloud sync destination."""
    for dest in CLOUD_DESTINATIONS:
        # Check parent directory exists (cloud folder)
        if dest.parent.exists():
            return dest
    return None


def sync_to_destination(dest: Path):
    """Sync database and recent backups to destination."""
    dest.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Sync main database
    if DB_FILE.exists():
        dest_db = dest / "memories.db"
        shutil.copy2(DB_FILE, dest_db)
        log(f"Synced main database to: {dest_db}")

        # Also keep timestamped copy
        timestamped_db = dest / f"memories_{timestamp}.db"
        shutil.copy2(DB_FILE, timestamped_db)

        # Keep only last 5 timestamped copies
        existing = sorted(dest.glob("memories_*.db"), reverse=True)
        for old in existing[5:]:
            old.unlink()
            log(f"Removed old cloud backup: {old.name}")

    # Sync latest daily backup if exists
    daily_dir = BACKUP_DIR / "daily"
    if daily_dir.exists():
        daily_backups = sorted(daily_dir.glob("memory_*.db"), reverse=True)
        if daily_backups:
            cloud_daily = dest / "daily"
            cloud_daily.mkdir(exist_ok=True)
            shutil.copy2(daily_backups[0], cloud_daily / daily_backups[0].name)
            log(f"Synced daily backup: {daily_backups[0].name}")

    # Sync latest weekly backup if exists
    weekly_dir = BACKUP_DIR / "weekly"
    if weekly_dir.exists():
        weekly_backups = sorted(weekly_dir.glob("memory_*.db"), reverse=True)
        if weekly_backups:
            cloud_weekly = dest / "weekly"
            cloud_weekly.mkdir(exist_ok=True)
            shutil.copy2(weekly_backups[0], cloud_weekly / weekly_backups[0].name)
            log(f"Synced weekly backup: {weekly_backups[0].name}")


def main():
    """Main sync process."""
    log("=" * 50)
    log("Starting Claude Memory cloud sync")

    if not DB_FILE.exists():
        log("ERROR: Database not found!")
        return

    # Find cloud destination
    cloud_dest = find_cloud_destination()

    if cloud_dest:
        log(f"Found cloud destination: {cloud_dest}")
        try:
            sync_to_destination(cloud_dest)
            log("Cloud sync completed successfully")
        except Exception as e:
            log(f"ERROR during cloud sync: {e}")
    else:
        log("No cloud sync destination found. Checked:")
        for dest in CLOUD_DESTINATIONS:
            log(f"  - {dest.parent} (not found)")

    # Network backup if configured
    if NETWORK_BACKUP:
        network_dest = Path(NETWORK_BACKUP)
        if network_dest.parent.exists():
            log(f"Syncing to network backup: {network_dest}")
            try:
                sync_to_destination(network_dest)
                log("Network sync completed successfully")
            except Exception as e:
                log(f"ERROR during network sync: {e}")
        else:
            log(f"Network backup path not accessible: {NETWORK_BACKUP}")

    log("=" * 50)


if __name__ == "__main__":
    main()
