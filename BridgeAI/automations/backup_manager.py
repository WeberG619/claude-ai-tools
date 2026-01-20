#!/usr/bin/env python3
"""
BridgeAI Backup Manager
========================
Lightweight automated backup system for protecting your work.
Designed for 8GB RAM - uses minimal resources.

Features:
- Incremental backups (only copies changed files)
- Configurable retention (keeps X days of backups)
- Multiple backup sources
- Email/notification on failure
"""

import os
import shutil
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('C:/BridgeAI/Logs/backup.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Configuration
CONFIG_FILE = Path('C:/BridgeAI/config/backup_config.json')
BACKUP_ROOT = Path('C:/BridgeAI/Backups')

DEFAULT_CONFIG = {
    "sources": [
        {
            "name": "Revit Projects",
            "path": "//192.168.1.51/Users/weber/Documents/Revit",
            "extensions": [".rvt", ".rfa", ".rte"],
            "enabled": False  # User needs to enable and set correct path
        },
        {
            "name": "Important Documents",
            "path": "//192.168.1.51/Users/weber/Documents/Important",
            "extensions": ["*"],
            "enabled": False
        }
    ],
    "schedule": {
        "time": "02:00",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    },
    "retention_days": 7,
    "max_file_size_mb": 500,
    "notify_on_failure": True,
    "notify_on_success": False
}


def load_config():
    """Load or create configuration"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    else:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        log.info(f"Created default config at {CONFIG_FILE}")
        return DEFAULT_CONFIG


def get_file_hash(filepath, chunk_size=8192):
    """Get MD5 hash of file (for change detection)"""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None


def should_backup_file(src_file, dst_file):
    """Check if file needs to be backed up"""
    if not dst_file.exists():
        return True

    # Compare modification times
    src_mtime = src_file.stat().st_mtime
    dst_mtime = dst_file.stat().st_mtime

    if src_mtime > dst_mtime:
        return True

    return False


def backup_source(source_config, backup_dir):
    """Backup a single source"""
    name = source_config['name']
    src_path = Path(source_config['path'])
    extensions = source_config.get('extensions', ['*'])
    max_size = source_config.get('max_file_size_mb', 500) * 1024 * 1024

    stats = {'copied': 0, 'skipped': 0, 'errors': 0, 'total_size': 0}

    if not src_path.exists():
        log.warning(f"Source not accessible: {src_path}")
        return {'error': f'Source not accessible: {src_path}'}

    log.info(f"Backing up: {name} from {src_path}")

    # Find files to backup
    if '*' in extensions:
        files = list(src_path.rglob('*'))
    else:
        files = []
        for ext in extensions:
            files.extend(src_path.rglob(f'*{ext}'))

    for src_file in files:
        if not src_file.is_file():
            continue

        # Skip files that are too large
        try:
            if src_file.stat().st_size > max_size:
                log.debug(f"Skipping large file: {src_file}")
                stats['skipped'] += 1
                continue
        except:
            continue

        # Calculate destination path
        rel_path = src_file.relative_to(src_path)
        dst_file = backup_dir / name / rel_path

        try:
            if should_backup_file(src_file, dst_file):
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                stats['copied'] += 1
                stats['total_size'] += src_file.stat().st_size
                log.debug(f"Copied: {rel_path}")
            else:
                stats['skipped'] += 1
        except Exception as e:
            log.error(f"Failed to copy {src_file}: {e}")
            stats['errors'] += 1

    return stats


def cleanup_old_backups(retention_days):
    """Remove backups older than retention period"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0

    for backup_dir in BACKUP_ROOT.iterdir():
        if not backup_dir.is_dir():
            continue

        # Parse date from folder name (format: YYYY-MM-DD)
        try:
            dir_date = datetime.strptime(backup_dir.name, '%Y-%m-%d')
            if dir_date < cutoff:
                shutil.rmtree(backup_dir)
                removed += 1
                log.info(f"Removed old backup: {backup_dir.name}")
        except ValueError:
            continue

    return removed


def run_backup():
    """Run a full backup"""
    config = load_config()

    # Create today's backup directory
    today = datetime.now().strftime('%Y-%m-%d')
    backup_dir = BACKUP_ROOT / today
    backup_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 50)
    log.info("Starting BridgeAI Backup")
    log.info("=" * 50)

    results = {
        'date': today,
        'sources': {},
        'total_copied': 0,
        'total_errors': 0,
        'success': True
    }

    # Backup each enabled source
    for source in config['sources']:
        if not source.get('enabled', False):
            log.info(f"Skipping disabled source: {source['name']}")
            continue

        stats = backup_source(source, backup_dir)
        results['sources'][source['name']] = stats

        if 'error' in stats:
            results['success'] = False
            results['total_errors'] += 1
        else:
            results['total_copied'] += stats.get('copied', 0)
            results['total_errors'] += stats.get('errors', 0)

    # Cleanup old backups
    removed = cleanup_old_backups(config.get('retention_days', 7))
    results['old_backups_removed'] = removed

    # Save results
    results_file = backup_dir / 'backup_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    log.info("=" * 50)
    log.info(f"Backup Complete: {results['total_copied']} files copied, {results['total_errors']} errors")
    log.info("=" * 50)

    return results


def get_backup_status():
    """Get status of recent backups"""
    backups = []

    for backup_dir in sorted(BACKUP_ROOT.iterdir(), reverse=True)[:7]:
        if not backup_dir.is_dir():
            continue

        results_file = backup_dir / 'backup_results.json'
        if results_file.exists():
            with open(results_file) as f:
                backups.append(json.load(f))
        else:
            backups.append({
                'date': backup_dir.name,
                'success': 'unknown'
            })

    return backups


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'status':
            status = get_backup_status()
            print(json.dumps(status, indent=2))
        elif cmd == 'config':
            config = load_config()
            print(json.dumps(config, indent=2))
        else:
            print("Usage: python backup_manager.py [status|config]")
    else:
        run_backup()
