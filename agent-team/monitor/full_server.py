#!/usr/bin/env python3
"""
Full Agent Monitor Server - With LIVE auto-switching code view.
"""

import json
import os
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

STATUS_FILE = Path("/tmp/agent_speech_status.json")
TASK_FILE = Path("/tmp/agent_team_status/current_task.json")
PROJECTS_DIR = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/projects")
PORT = 8892

# Track the last known state to detect changes
last_global_update = 0
last_active_project = None
last_active_file = None


class FullMonitorHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == '/api/status':
            self.send_json(self.get_status())

        elif parsed.path == '/api/global':
            # NEW: Scan ALL projects, return the most recently changed file
            self.send_json(self.get_global_state())

        elif parsed.path == '/api/files':
            project = query.get('project', ['cd_validator'])[0]
            files, latest_file, file_times = self.get_files(project)
            self.send_json({
                "files": files,
                "latest_file": latest_file,
                "file_times": file_times
            })

        elif parsed.path == '/api/file':
            project = query.get('project', ['cd_validator'])[0]
            filepath = query.get('path', [''])[0]
            content = self.read_file(project, filepath)
            self.send_json({"content": content})

        elif parsed.path == '/' or parsed.path == '/index.html':
            self.serve_html()

        else:
            super().do_GET()

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def serve_html(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        html_file = Path(__file__).parent / 'full_monitor.html'
        self.wfile.write(html_file.read_bytes())

    def get_status(self):
        data = {"status": "idle", "agent": None, "role": None, "task": None}

        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE) as f:
                    status_data = json.load(f)
                    data.update(status_data)
            except:
                pass

        if TASK_FILE.exists():
            try:
                with open(TASK_FILE) as f:
                    task_data = json.load(f)
                    data['task'] = task_data.get('task')
            except:
                pass

        return data

    def get_global_state(self):
        """Scan ALL projects and find the most recently modified file."""
        global last_global_update, last_active_project, last_active_file

        all_projects = []
        global_latest_time = 0
        global_latest_project = None
        global_latest_file = None

        # Scan all project directories
        if PROJECTS_DIR.exists():
            for project_dir in PROJECTS_DIR.iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith('.'):
                    project_name = project_dir.name
                    all_projects.append(project_name)

                    # Find newest file in this project
                    for f in project_dir.rglob("*.py"):
                        if '__pycache__' not in str(f):
                            try:
                                mtime = f.stat().st_mtime
                                if mtime > global_latest_time:
                                    global_latest_time = mtime
                                    global_latest_project = project_name
                                    global_latest_file = str(f.relative_to(project_dir))
                            except:
                                pass

        # Check if there's a new update
        is_new_update = global_latest_time > last_global_update

        if is_new_update:
            last_global_update = global_latest_time
            last_active_project = global_latest_project
            last_active_file = global_latest_file

        # Read the content of the latest file
        content = ""
        if global_latest_project and global_latest_file:
            content = self.read_file(global_latest_project, global_latest_file)

        return {
            "projects": sorted(all_projects),
            "active_project": global_latest_project,
            "active_file": global_latest_file,
            "last_update": global_latest_time,
            "is_new": is_new_update,
            "content": content,
            "timestamp": time.time()
        }

    def get_files(self, project):
        project_path = PROJECTS_DIR / project
        if not project_path.exists():
            return [], None, {}

        files = []
        file_times = {}
        latest_file = None
        latest_time = 0

        for f in project_path.rglob("*.py"):
            if '__pycache__' not in str(f):
                rel = str(f.relative_to(project_path))
                files.append(rel)
                try:
                    mtime = f.stat().st_mtime
                    file_times[rel] = mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_file = rel
                except:
                    pass

        return sorted(files), latest_file, file_times

    def read_file(self, project, filepath):
        try:
            full_path = PROJECTS_DIR / project / filepath
            if full_path.exists() and full_path.stat().st_size < 100000:
                return full_path.read_text()
        except:
            pass
        return "// File not found or too large"

    def log_message(self, format, *args):
        pass


def main():
    os.chdir(Path(__file__).parent)
    server = HTTPServer(('0.0.0.0', PORT), FullMonitorHandler)
    print(f"\n{'='*50}")
    print(f"🖥️  Full Agent Monitor: http://localhost:{PORT}")
    print(f"   Auto-switches to show live code changes!")
    print(f"{'='*50}\n")
    server.serve_forever()


if __name__ == '__main__':
    main()
