#!/usr/bin/env python3
"""
Simple Agent Monitor Server - Polling-based, more reliable.
"""

import json
import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

STATUS_FILE = Path("/tmp/agent_speech_status.json")
TASK_FILE = Path("/tmp/agent_team_status/current_task.json")
PORT = 8891

class MonitorHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            data = {"status": "idle", "agent": None, "role": None, "task": None}

            # Read agent status
            if STATUS_FILE.exists():
                try:
                    with open(STATUS_FILE) as f:
                        status_data = json.load(f)
                        data.update(status_data)
                except:
                    pass

            # Read task
            if TASK_FILE.exists():
                try:
                    with open(TASK_FILE) as f:
                        task_data = json.load(f)
                        data['task'] = task_data.get('task')
                except:
                    pass

            self.wfile.write(json.dumps(data).encode())

        elif parsed.path == '/' or parsed.path == '/index.html':
            # Serve the simple monitor
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()

            html_file = Path(__file__).parent / 'simple_monitor.html'
            self.wfile.write(html_file.read_bytes())

        else:
            super().do_GET()

    def log_message(self, format, *args):
        pass  # Suppress logging


def main():
    os.chdir(Path(__file__).parent)
    server = HTTPServer(('0.0.0.0', PORT), MonitorHandler)
    print(f"\n{'='*50}")
    print(f"🖥️  Agent Monitor running at http://localhost:{PORT}")
    print(f"{'='*50}\n")
    server.serve_forever()


if __name__ == '__main__':
    main()
