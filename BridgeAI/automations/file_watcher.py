#!/usr/bin/env python3
"""
BridgeAI File Watcher
======================
Watches folders and automatically organizes files.
Lightweight - uses polling instead of heavy filesystem events.

Features:
- Watch multiple folders
- Auto-sort by file type
- Move old files to archive
- Trigger actions when files appear
"""

import os
import shutil
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('C:/BridgeAI/Logs/file_watcher.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

CONFIG_FILE = Path('C:/BridgeAI/config/file_watcher_config.json')

DEFAULT_CONFIG = {
    "watch_folders": [
        {
            "name": "Downloads Organizer",
            "watch_path": "C:/Users/weber/Downloads",
            "enabled": False,
            "rules": [
                {
                    "extensions": [".rvt", ".rfa"],
                    "destination": "C:/Users/weber/Documents/Revit/Incoming",
                    "action": "move"
                },
                {
                    "extensions": [".pdf"],
                    "destination": "C:/Users/weber/Documents/PDFs/Incoming",
                    "action": "move"
                },
                {
                    "extensions": [".dwg", ".dxf"],
                    "destination": "C:/Users/weber/Documents/CAD/Incoming",
                    "action": "move"
                }
            ]
        },
        {
            "name": "Project Archive",
            "watch_path": "C:/Projects",
            "enabled": False,
            "archive_after_days": 90,
            "archive_destination": "C:/BridgeAI/Archive"
        }
    ],
    "scan_interval_seconds": 30,
    "processed_files_log": "C:/BridgeAI/data/processed_files.json"
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


def load_processed_files(log_path):
    """Load list of already processed files"""
    log_path = Path(log_path)
    if log_path.exists():
        with open(log_path) as f:
            return set(json.load(f))
    return set()


def save_processed_files(log_path, processed):
    """Save list of processed files"""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w') as f:
        json.dump(list(processed), f)


def process_watch_folder(folder_config, processed_files):
    """Process a single watch folder"""
    name = folder_config['name']
    watch_path = Path(folder_config['watch_path'])

    if not watch_path.exists():
        log.debug(f"Watch path not accessible: {watch_path}")
        return 0

    processed_count = 0

    # Handle rule-based organization
    if 'rules' in folder_config:
        for rule in folder_config['rules']:
            extensions = rule.get('extensions', [])
            destination = Path(rule.get('destination', ''))
            action = rule.get('action', 'move')

            for ext in extensions:
                for file_path in watch_path.glob(f'*{ext}'):
                    if not file_path.is_file():
                        continue

                    file_key = str(file_path)
                    if file_key in processed_files:
                        continue

                    # Skip files modified in last 10 seconds (still being written)
                    if time.time() - file_path.stat().st_mtime < 10:
                        continue

                    try:
                        destination.mkdir(parents=True, exist_ok=True)
                        dest_file = destination / file_path.name

                        # Handle duplicates
                        if dest_file.exists():
                            stem = dest_file.stem
                            suffix = dest_file.suffix
                            counter = 1
                            while dest_file.exists():
                                dest_file = destination / f"{stem}_{counter}{suffix}"
                                counter += 1

                        if action == 'move':
                            shutil.move(str(file_path), str(dest_file))
                            log.info(f"Moved: {file_path.name} -> {destination}")
                        elif action == 'copy':
                            shutil.copy2(str(file_path), str(dest_file))
                            log.info(f"Copied: {file_path.name} -> {destination}")

                        processed_files.add(file_key)
                        processed_count += 1

                    except Exception as e:
                        log.error(f"Failed to process {file_path}: {e}")

    # Handle archive-based organization
    if 'archive_after_days' in folder_config:
        days = folder_config['archive_after_days']
        archive_dest = Path(folder_config.get('archive_destination', 'C:/BridgeAI/Archive'))
        cutoff = time.time() - (days * 86400)

        for file_path in watch_path.rglob('*'):
            if not file_path.is_file():
                continue

            try:
                if file_path.stat().st_mtime < cutoff:
                    rel_path = file_path.relative_to(watch_path)
                    dest_file = archive_dest / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    shutil.move(str(file_path), str(dest_file))
                    log.info(f"Archived: {file_path.name}")
                    processed_count += 1
            except:
                pass

    return processed_count


def run_watcher(single_pass=False):
    """Run the file watcher"""
    config = load_config()
    processed_files = load_processed_files(config['processed_files_log'])

    log.info("=" * 50)
    log.info("BridgeAI File Watcher Started")
    log.info("=" * 50)

    enabled_folders = [f for f in config['watch_folders'] if f.get('enabled', False)]
    log.info(f"Watching {len(enabled_folders)} folders")

    while True:
        try:
            total_processed = 0

            for folder_config in config['watch_folders']:
                if not folder_config.get('enabled', False):
                    continue

                count = process_watch_folder(folder_config, processed_files)
                total_processed += count

            if total_processed > 0:
                save_processed_files(config['processed_files_log'], processed_files)
                log.info(f"Processed {total_processed} files this cycle")

            if single_pass:
                break

            time.sleep(config.get('scan_interval_seconds', 30))

        except KeyboardInterrupt:
            log.info("File watcher stopped")
            break
        except Exception as e:
            log.error(f"Error in watcher loop: {e}")
            time.sleep(60)


def get_status():
    """Get watcher status"""
    config = load_config()
    processed = load_processed_files(config['processed_files_log'])

    return {
        'enabled_folders': len([f for f in config['watch_folders'] if f.get('enabled', False)]),
        'total_folders': len(config['watch_folders']),
        'processed_files_count': len(processed),
        'scan_interval': config.get('scan_interval_seconds', 30)
    }


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'status':
            print(json.dumps(get_status(), indent=2))
        elif cmd == 'once':
            run_watcher(single_pass=True)
        elif cmd == 'config':
            config = load_config()
            print(json.dumps(config, indent=2))
        else:
            print("Usage: python file_watcher.py [status|once|config]")
    else:
        run_watcher()
