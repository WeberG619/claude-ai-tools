#!/usr/bin/env python3
"""
BridgeAI Automation Runner
===========================
Runs all lightweight automation services in a single process.
Designed for 8GB RAM - uses minimal resources.

Services:
- System Monitor (every 60 seconds)
- File Watcher (every 30 seconds)
- Backup Check (checks schedule)
- Device Monitor (every 60 seconds)

Total RAM usage: ~100-200MB
"""

import os
import sys
import time
import json
import threading
import schedule
from datetime import datetime
from pathlib import Path
import logging

# Add automations folder to path
sys.path.insert(0, str(Path(__file__).parent))

from backup_manager import run_backup, get_backup_status
from file_watcher import process_watch_folder, load_config as load_watcher_config, load_processed_files, save_processed_files
from system_monitor import get_system_stats, check_devices, check_services, save_stats, check_thresholds, save_alert, load_config as load_monitor_config
from wol_controller import get_status as get_device_status

# Setup logging
LOG_DIR = Path('C:/BridgeAI/Logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'automation_runner.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('AutomationRunner')


class AutomationRunner:
    """Unified automation runner"""

    def __init__(self):
        self.running = False
        self.stats = {
            'started_at': None,
            'cycles': 0,
            'last_backup': None,
            'last_monitor': None,
            'last_watcher': None
        }
        self.previous_alerts = set()

    def run_monitor_cycle(self):
        """Run one monitoring cycle"""
        try:
            config = load_monitor_config()

            # Get system stats
            stats = get_system_stats()

            # Check devices
            stats['devices'] = check_devices(config.get('devices_to_monitor', []))

            # Check services
            stats['services'] = check_services(config.get('services_to_monitor', []))

            # Check thresholds
            check_thresholds(stats, config.get('thresholds', {}), self.previous_alerts)

            # Save stats
            save_stats(stats, config.get('max_stats_entries', 1440))

            self.stats['last_monitor'] = datetime.now().isoformat()
            log.debug(f"Monitor: CPU {stats['cpu_percent']}%, RAM {stats['memory']['percent']}%")

        except Exception as e:
            log.error(f"Monitor cycle error: {e}")

    def run_watcher_cycle(self):
        """Run one file watcher cycle"""
        try:
            config = load_watcher_config()
            processed_files = load_processed_files(config['processed_files_log'])
            total_processed = 0

            for folder_config in config['watch_folders']:
                if not folder_config.get('enabled', False):
                    continue

                count = process_watch_folder(folder_config, processed_files)
                total_processed += count

            if total_processed > 0:
                save_processed_files(config['processed_files_log'], processed_files)
                log.info(f"File Watcher: Processed {total_processed} files")

            self.stats['last_watcher'] = datetime.now().isoformat()

        except Exception as e:
            log.error(f"Watcher cycle error: {e}")

    def run_backup(self):
        """Run backup (called by scheduler)"""
        log.info("Starting scheduled backup...")
        try:
            result = run_backup()
            self.stats['last_backup'] = datetime.now().isoformat()

            if result.get('success'):
                log.info(f"Backup completed: {result.get('total_copied', 0)} files")
            else:
                log.error("Backup failed")
                save_alert('backup', 'Scheduled backup failed', 'error')

        except Exception as e:
            log.error(f"Backup error: {e}")
            save_alert('backup', f'Backup error: {e}', 'error')

    def setup_schedules(self):
        """Setup scheduled tasks"""
        # Daily backup at 2am
        schedule.every().day.at("02:00").do(self.run_backup)

        # You can add more scheduled tasks here
        log.info("Scheduled tasks configured")

    def run(self):
        """Main run loop"""
        self.running = True
        self.stats['started_at'] = datetime.now().isoformat()

        log.info("=" * 60)
        log.info("  BridgeAI Automation Runner")
        log.info("  Lightweight automation for 8GB RAM systems")
        log.info("=" * 60)

        # Setup schedules
        self.setup_schedules()

        cycle = 0
        while self.running:
            try:
                cycle += 1
                self.stats['cycles'] = cycle

                # Run monitor every cycle (60 seconds)
                self.run_monitor_cycle()

                # Run watcher every cycle
                self.run_watcher_cycle()

                # Run scheduled tasks
                schedule.run_pending()

                # Sleep for 60 seconds
                for _ in range(60):
                    if not self.running:
                        break
                    time.sleep(1)

            except KeyboardInterrupt:
                log.info("Shutdown requested...")
                self.running = False
            except Exception as e:
                log.error(f"Main loop error: {e}")
                time.sleep(60)

        log.info("Automation Runner stopped")

    def stop(self):
        """Stop the runner"""
        self.running = False

    def get_status(self):
        """Get runner status"""
        return {
            'running': self.running,
            'stats': self.stats,
            'backup_status': get_backup_status()[:3] if self.running else [],
            'device_status': get_device_status() if self.running else {}
        }


# Flask API for remote control
def create_api(runner):
    """Create a simple API for the automation runner"""
    from flask import Flask, jsonify

    app = Flask(__name__)

    @app.route('/')
    def home():
        return jsonify({
            'service': 'BridgeAI Automation Runner',
            'status': 'running' if runner.running else 'stopped'
        })

    @app.route('/status')
    def status():
        return jsonify(runner.get_status())

    @app.route('/backup', methods=['POST'])
    def trigger_backup():
        runner.run_backup()
        return jsonify({'status': 'backup_started'})

    return app


def main():
    runner = AutomationRunner()

    # Check if we should run with API
    if '--api' in sys.argv:
        # Run with API server
        api = create_api(runner)

        # Start runner in background thread
        runner_thread = threading.Thread(target=runner.run, daemon=True)
        runner_thread.start()

        # Start API server
        log.info("Starting API server on port 5003...")
        api.run(host='0.0.0.0', port=5003, debug=False)
    else:
        # Run standalone
        runner.run()


if __name__ == '__main__':
    main()
