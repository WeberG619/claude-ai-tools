#!/usr/bin/env python3
"""
BridgeAI Master Controller
===========================
The main entry point that starts and manages all BridgeAI services.
"""

import os
import sys
import time
import signal
import threading
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class BridgeAIMaster:
    """
    Master controller that orchestrates all BridgeAI services.
    """

    def __init__(self):
        self.base_dir = Path('C:/BridgeAI')
        self.processes = {}
        self.running = False

        # Service definitions
        self.services = {
            'ollama': {
                'name': 'Ollama Local AI',
                'command': ['ollama', 'serve'],
                'port': 11434,
                'required': False,
                'startup_delay': 3
            },
            'hub': {
                'name': 'Smart Hub',
                'command': [sys.executable, str(self.base_dir / 'hub_server.py')],
                'port': 5000,
                'required': True,
                'startup_delay': 2
            },
            'brain': {
                'name': 'AI Brain',
                'command': [sys.executable, str(self.base_dir / 'core' / 'brain.py')],
                'port': 5001,
                'required': True,
                'startup_delay': 2
            },
            'dashboard': {
                'name': 'Command Center',
                'command': [sys.executable, str(self.base_dir / 'core' / 'dashboard.py')],
                'port': 5002,
                'required': False,
                'startup_delay': 1
            },
            'automation': {
                'name': 'Automation Service',
                'command': [sys.executable, str(self.base_dir / 'automation_service.py')],
                'port': None,
                'required': False,
                'startup_delay': 1
            }
        }

    def log(self, msg: str, level: str = 'INFO'):
        """Log a message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {msg}")

        # Also write to log file
        log_file = self.base_dir / 'logs' / 'master.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {msg}\n")

    def start_service(self, name: str) -> bool:
        """Start a single service"""
        if name not in self.services:
            self.log(f"Unknown service: {name}", 'ERROR')
            return False

        svc = self.services[name]
        self.log(f"Starting {svc['name']}...")

        try:
            # Start the process
            process = subprocess.Popen(
                svc['command'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            self.processes[name] = process
            time.sleep(svc['startup_delay'])

            # Check if still running
            if process.poll() is None:
                self.log(f"  {svc['name']} started (PID: {process.pid})")
                return True
            else:
                self.log(f"  {svc['name']} failed to start", 'ERROR')
                return False

        except Exception as e:
            self.log(f"  Error starting {svc['name']}: {e}", 'ERROR')
            return False

    def stop_service(self, name: str):
        """Stop a single service"""
        if name in self.processes:
            process = self.processes[name]
            if process.poll() is None:
                self.log(f"Stopping {self.services[name]['name']}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            del self.processes[name]

    def start_all(self):
        """Start all services"""
        self.log("=" * 50)
        self.log("BridgeAI Master Controller Starting")
        self.log("=" * 50)

        self.running = True

        # Start services in order
        for name in ['ollama', 'hub', 'brain', 'dashboard', 'automation']:
            svc = self.services[name]
            success = self.start_service(name)

            if not success and svc['required']:
                self.log(f"Required service {name} failed to start!", 'CRITICAL')
                self.stop_all()
                return False

        self.log("=" * 50)
        self.log("All services started!")
        self.log("")
        self.log("Access points:")
        self.log("  Dashboard:  http://localhost:5002")
        self.log("  Smart Hub:  http://localhost:5000")
        self.log("  AI Brain:   http://localhost:5001")
        self.log("")
        self.log("From other devices: http://192.168.1.31:5002")
        self.log("=" * 50)

        return True

    def stop_all(self):
        """Stop all services"""
        self.log("Stopping all services...")
        self.running = False

        for name in list(self.processes.keys()):
            self.stop_service(name)

        self.log("All services stopped.")

    def monitor(self):
        """Monitor services and restart if needed"""
        while self.running:
            for name, process in list(self.processes.items()):
                if process.poll() is not None:
                    # Process died
                    svc = self.services[name]
                    self.log(f"{svc['name']} died, restarting...", 'WARNING')
                    del self.processes[name]
                    self.start_service(name)

            time.sleep(10)

    def run(self):
        """Main run loop"""
        # Handle Ctrl+C
        def signal_handler(sig, frame):
            self.log("\nShutdown requested...")
            self.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        if self.start_all():
            # Start monitoring thread
            monitor_thread = threading.Thread(target=self.monitor, daemon=True)
            monitor_thread.start()

            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

            self.stop_all()

def main():
    master = BridgeAIMaster()
    master.run()

if __name__ == '__main__':
    main()
