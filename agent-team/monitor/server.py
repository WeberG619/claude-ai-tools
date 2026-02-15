#!/usr/bin/env python3
"""
Agent Team Live Monitor - Real-time visualization of agent activity.

Features:
- Live agent status (speaking, waiting, idle)
- Real-time code display as files are written
- Conversation transcript
- File tree updates
- WebSocket for instant updates

Run: python server.py
Open: http://localhost:8890
"""

import asyncio
import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Set
import threading

from aiohttp import web
import aiohttp

# Paths
SCRIPT_DIR = Path(__file__).parent.parent
PROJECTS_DIR = SCRIPT_DIR / "projects"
STATUS_FILE = Path("/tmp/agent_speech_status.json")
MONITOR_PORT = 8890

# Track connected WebSocket clients
clients: Set[web.WebSocketResponse] = set()

# Activity log
activity_log = []
MAX_LOG_ENTRIES = 100

# Session state
session_state = {
    "active": False,
    "paused": False,
    "task": None,
    "mode": "work",  # work, discuss, parallel
    "started_at": None
}

# Execution state
execution_state = {
    "enabled": False,  # False = simulation mode, True = real execution
    "workspace": None,
    "pending_approvals": []  # List of actions awaiting approval
}

# Approval queue for async processing
approval_responses = {}  # action_id -> (approved: bool, event: asyncio.Event)


class FileWatcher:
    """Watch project directories for changes."""

    def __init__(self):
        self.last_scan = {}
        self.watching = True

    def scan_directory(self, path: Path) -> Dict:
        """Scan directory and return file info."""
        files = {}
        try:
            for f in path.rglob("*"):
                if f.is_file() and not any(p.startswith('.') for p in f.parts):
                    rel_path = str(f.relative_to(path))
                    try:
                        stat = f.stat()
                        files[rel_path] = {
                            "path": rel_path,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "modified_str": datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M:%S")
                        }
                    except:
                        pass
        except:
            pass
        return files

    def get_changes(self, project: str) -> Dict:
        """Get file changes since last scan."""
        project_path = PROJECTS_DIR / project
        if not project_path.exists():
            return {"new": [], "modified": [], "deleted": []}

        current = self.scan_directory(project_path)
        previous = self.last_scan.get(project, {})

        new_files = [f for f in current if f not in previous]
        deleted_files = [f for f in previous if f not in current]
        modified_files = [
            f for f in current
            if f in previous and current[f]["modified"] > previous[f]["modified"]
        ]

        self.last_scan[project] = current

        return {
            "new": new_files,
            "modified": modified_files,
            "deleted": deleted_files,
            "all_files": list(current.keys())
        }


file_watcher = FileWatcher()


def get_agent_status() -> Dict:
    """Get current agent speech status."""
    try:
        if STATUS_FILE.exists():
            with open(STATUS_FILE) as f:
                data = json.load(f)

                # Handle Unix timestamp (float) or ISO string
                if "timestamp" in data:
                    ts = data["timestamp"]
                    if isinstance(ts, (int, float)):
                        age = time.time() - ts
                    else:
                        status_time = datetime.fromisoformat(str(ts))
                        age = (datetime.now() - status_time).total_seconds()

                    # If stale, mark as idle
                    if age > 30:
                        data["speaking"] = False

                # Convert 'speaking' boolean to 'status' string for monitor
                if data.get("speaking"):
                    data["status"] = "speaking"
                else:
                    data["status"] = "idle"

                return data
    except Exception as e:
        print(f"Status read error: {e}")
    return {"status": "idle", "agent": None, "role": None, "activity": None}


def get_current_activity() -> Dict:
    """Get current activity from status file."""
    try:
        if STATUS_FILE.exists():
            with open(STATUS_FILE) as f:
                data = json.load(f)
                return {
                    "agent": data.get("agent"),
                    "activity": data.get("activity"),
                    "timestamp": data.get("activity_timestamp", data.get("timestamp"))
                }
    except Exception as e:
        print(f"Activity read error: {e}")
    return {"agent": None, "activity": None, "timestamp": None}


def read_file_content(project: str, filepath: str, max_lines: int = 50) -> str:
    """Read file content for preview."""
    try:
        full_path = PROJECTS_DIR / project / filepath
        if full_path.exists() and full_path.stat().st_size < 100000:  # Max 100KB
            content = full_path.read_text()
            lines = content.split('\n')
            if len(lines) > max_lines:
                return '\n'.join(lines[:max_lines]) + f"\n\n... ({len(lines) - max_lines} more lines)"
            return content
    except:
        pass
    return "Unable to read file"


def log_activity(activity_type: str, message: str, details: Dict = None):
    """Log an activity event."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "time_str": datetime.now().strftime("%H:%M:%S"),
        "type": activity_type,
        "message": message,
        "details": details or {}
    }
    activity_log.append(entry)
    if len(activity_log) > MAX_LOG_ENTRIES:
        activity_log.pop(0)
    return entry


async def broadcast(message: Dict):
    """Broadcast message to all connected clients."""
    if clients:
        data = json.dumps(message)
        await asyncio.gather(
            *[client.send_str(data) for client in clients if not client.closed],
            return_exceptions=True
        )


async def status_broadcaster():
    """Periodically broadcast status updates."""
    last_status = None
    last_activity = None
    last_files = {}

    while True:
        try:
            # Get current status
            status = get_agent_status()

            # Check for status changes
            if status != last_status:
                await broadcast({
                    "type": "agent_status",
                    "data": status
                })

                if status.get("status") == "speaking":
                    log_activity("speech", f"{status.get('role', 'Agent')} speaking", status)

                last_status = status.copy() if status else None

            # Check for activity changes
            activity = status.get("activity") if status else None
            if activity and activity != last_activity:
                await broadcast({
                    "type": "activity",
                    "data": activity
                })

                # Log based on activity type
                activity_type = activity.get("type", "")
                if activity_type == "browser_navigate":
                    log_activity("navigate", f"Navigate: {activity.get('title', activity.get('url', ''))}")
                elif activity_type == "browser_search":
                    log_activity("search", f"Search: {activity.get('query', '')}")
                elif activity_type == "code_write":
                    log_activity("code", f"Writing: {activity.get('file_path', '')}")
                elif activity_type == "terminal_run":
                    log_activity("terminal", f"Command: {activity.get('command', '')}")

                last_activity = activity.copy() if activity else None

            # Check for file changes in active projects
            for project in ["cd_validator", "pdf_markup_analyzer", "side_hustle_dashboard"]:
                changes = file_watcher.get_changes(project)

                if changes["new"] or changes["modified"]:
                    await broadcast({
                        "type": "file_changes",
                        "project": project,
                        "data": changes
                    })

                    for f in changes["new"]:
                        log_activity("file_created", f"New file: {project}/{f}")
                    for f in changes["modified"]:
                        log_activity("file_modified", f"Modified: {project}/{f}")

            await asyncio.sleep(0.3)  # Check every 300ms for snappier updates

        except Exception as e:
            print(f"Broadcaster error: {e}")
            await asyncio.sleep(1)


async def websocket_handler(request):
    """Handle WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    clients.add(ws)
    print(f"Client connected. Total: {len(clients)}")

    # Send initial state
    await ws.send_json({
        "type": "init",
        "data": {
            "status": get_agent_status(),
            "activity_log": activity_log[-20:],
            "projects": ["cd_validator", "pdf_markup_analyzer"]
        }
    })

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)

                # Handle requests
                if data.get("action") == "get_file":
                    content = read_file_content(data["project"], data["filepath"])
                    await ws.send_json({
                        "type": "file_content",
                        "project": data["project"],
                        "filepath": data["filepath"],
                        "content": content
                    })

                elif data.get("action") == "get_files":
                    project_path = PROJECTS_DIR / data["project"]
                    files = file_watcher.scan_directory(project_path)
                    await ws.send_json({
                        "type": "file_list",
                        "project": data["project"],
                        "files": list(files.keys())
                    })

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f"WebSocket error: {ws.exception()}")
    finally:
        clients.discard(ws)
        print(f"Client disconnected. Total: {len(clients)}")

    return ws


async def index_handler(request):
    """Serve the main page."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Team Live Monitor</title>
    <style>
        :root {
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --bg-hover: #21262d;
            --border: #30363d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-yellow: #d29922;
            --accent-red: #f85149;
            --accent-purple: #a371f7;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
        }

        .container {
            display: grid;
            grid-template-columns: 300px 1fr 350px;
            grid-template-rows: auto 1fr;
            height: 100vh;
            gap: 1px;
            background: var(--border);
        }

        .header {
            grid-column: 1 / -1;
            background: var(--bg-card);
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header h1 {
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .panel {
            background: var(--bg-card);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .panel-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
        }

        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
        }

        /* Agent Status Panel */
        .agent-card {
            background: var(--bg-hover);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            border-left: 3px solid var(--border);
            transition: all 0.3s ease;
        }

        .agent-card.speaking {
            border-left-color: var(--accent-green);
            background: rgba(63, 185, 80, 0.1);
        }

        .agent-card.waiting {
            border-left-color: var(--accent-yellow);
        }

        .agent-name {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
        }

        .agent-status {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .agent-status.speaking {
            color: var(--accent-green);
        }

        /* Code Panel */
        .code-view {
            background: #0d1117;
            border-radius: 6px;
            font-family: 'Cascadia Code', 'Fira Code', monospace;
            font-size: 12px;
            line-height: 1.5;
            overflow: auto;
            height: 100%;
        }

        .code-view pre {
            padding: 12px;
            margin: 0;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .file-tabs {
            display: flex;
            gap: 4px;
            padding: 8px;
            background: var(--bg-dark);
            overflow-x: auto;
            border-bottom: 1px solid var(--border);
        }

        .file-tab {
            padding: 6px 12px;
            background: var(--bg-hover);
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
            white-space: nowrap;
            border: 1px solid transparent;
        }

        .file-tab:hover {
            background: var(--bg-card);
        }

        .file-tab.active {
            background: var(--accent-blue);
            color: white;
        }

        .file-tab.new {
            border-color: var(--accent-green);
        }

        /* Activity Log */
        .activity-item {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
        }

        .activity-item:last-child {
            border-bottom: none;
        }

        .activity-time {
            color: var(--text-secondary);
            font-size: 11px;
            margin-right: 8px;
        }

        .activity-item.speech {
            background: rgba(88, 166, 255, 0.1);
        }

        .activity-item.file_created {
            background: rgba(63, 185, 80, 0.1);
        }

        .activity-item.file_modified {
            background: rgba(210, 153, 34, 0.1);
        }

        /* File Tree */
        .file-tree {
            font-size: 13px;
        }

        .file-tree-item {
            padding: 4px 8px;
            cursor: pointer;
            border-radius: 4px;
        }

        .file-tree-item:hover {
            background: var(--bg-hover);
        }

        .file-tree-item.new {
            color: var(--accent-green);
        }

        /* Speaking Animation */
        .speaking-wave {
            display: inline-flex;
            gap: 2px;
            margin-left: 8px;
        }

        .speaking-wave span {
            width: 3px;
            height: 12px;
            background: var(--accent-green);
            animation: wave 0.5s ease-in-out infinite;
        }

        .speaking-wave span:nth-child(2) { animation-delay: 0.1s; }
        .speaking-wave span:nth-child(3) { animation-delay: 0.2s; }
        .speaking-wave span:nth-child(4) { animation-delay: 0.3s; }

        @keyframes wave {
            0%, 100% { transform: scaleY(0.5); }
            50% { transform: scaleY(1); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>
                <span class="status-indicator"></span>
                Agent Team Live Monitor
            </h1>
            <div id="current-task" style="flex:1; text-align:center; color:var(--accent-yellow); font-size:14px;">
                Waiting for task...
            </div>
            <span id="connection-status">Connecting...</span>
        </header>

        <!-- Left: Agents -->
        <div class="panel">
            <div class="panel-header">Agents</div>
            <div class="panel-content" id="agents-panel">
                <div class="agent-card" data-agent="planner">
                    <div class="agent-name">🎯 PLANNER (Andrew)</div>
                    <div class="agent-status">Idle</div>
                </div>
                <div class="agent-card" data-agent="researcher">
                    <div class="agent-name">🔍 RESEARCHER (Guy)</div>
                    <div class="agent-status">Idle</div>
                </div>
                <div class="agent-card" data-agent="builder">
                    <div class="agent-name">🔨 BUILDER (Christopher)</div>
                    <div class="agent-status">Idle</div>
                </div>
                <div class="agent-card" data-agent="critic">
                    <div class="agent-name">🔬 CRITIC (Eric)</div>
                    <div class="agent-status">Idle</div>
                </div>
                <div class="agent-card" data-agent="narrator">
                    <div class="agent-name">📢 NARRATOR (Jenny)</div>
                    <div class="agent-status">Idle</div>
                </div>
            </div>
        </div>

        <!-- Center: Code View -->
        <div class="panel">
            <div class="panel-header">Live Code View</div>
            <div class="file-tabs" id="file-tabs"></div>
            <div class="code-view">
                <pre id="code-content">Select a file to view its contents...</pre>
            </div>
        </div>

        <!-- Right: Activity Log -->
        <div class="panel">
            <div class="panel-header">Activity Log</div>
            <div class="panel-content" id="activity-log"></div>
        </div>
    </div>

    <script>
        let ws;
        let currentFile = null;
        let currentProject = 'cd_validator';
        let recentFiles = new Set();

        function connect() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);

            ws.onopen = () => {
                document.getElementById('connection-status').textContent = 'Connected';
                document.querySelector('.status-indicator').style.background = 'var(--accent-green)';
            };

            ws.onclose = () => {
                document.getElementById('connection-status').textContent = 'Disconnected - Reconnecting...';
                document.querySelector('.status-indicator').style.background = 'var(--accent-red)';
                setTimeout(connect, 2000);
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                handleMessage(msg);
            };
        }

        function handleMessage(msg) {
            switch (msg.type) {
                case 'init':
                    // Load initial activity log
                    msg.data.activity_log.forEach(addActivityItem);
                    break;

                case 'agent_status':
                    updateAgentStatus(msg.data);
                    break;

                case 'file_changes':
                    handleFileChanges(msg.project, msg.data);
                    break;

                case 'file_content':
                    document.getElementById('code-content').textContent = msg.content;
                    break;

                case 'file_list':
                    updateFileTabs(msg.project, msg.files);
                    break;
            }
        }

        function updateAgentStatus(status) {
            // Reset all cards
            document.querySelectorAll('.agent-card').forEach(card => {
                card.classList.remove('speaking', 'waiting');
                card.querySelector('.agent-status').textContent = 'Idle';
                card.querySelector('.agent-status').classList.remove('speaking');

                // Remove wave animation if present
                const wave = card.querySelector('.speaking-wave');
                if (wave) wave.remove();
            });

            if (status.status === 'speaking' && status.agent) {
                const card = document.querySelector(`[data-agent="${status.agent}"]`);
                if (card) {
                    card.classList.add('speaking');
                    const statusEl = card.querySelector('.agent-status');
                    statusEl.textContent = 'Speaking';
                    statusEl.classList.add('speaking');

                    // Add wave animation
                    const wave = document.createElement('div');
                    wave.className = 'speaking-wave';
                    wave.innerHTML = '<span></span><span></span><span></span><span></span>';
                    statusEl.appendChild(wave);
                }

                // Log speech activity
                addActivityItem({
                    type: 'speech',
                    time_str: new Date().toLocaleTimeString(),
                    message: `${status.role} speaking...`
                });
            }
        }

        function handleFileChanges(project, changes) {
            // Add new files to tabs
            changes.new.forEach(file => {
                recentFiles.add(`${project}/${file}`);
                addActivityItem({
                    type: 'file_created',
                    time_str: new Date().toLocaleTimeString(),
                    message: `Created: ${file}`
                });
            });

            changes.modified.forEach(file => {
                addActivityItem({
                    type: 'file_modified',
                    time_str: new Date().toLocaleTimeString(),
                    message: `Modified: ${file}`
                });

                // Auto-refresh if viewing this file
                if (currentFile === `${project}/${file}`) {
                    requestFile(project, file);
                }
            });

            // Update tabs
            updateFileTabs(project, changes.all_files);
        }

        function updateFileTabs(project, files) {
            const container = document.getElementById('file-tabs');

            // Filter to show Python files
            const pyFiles = files.filter(f => f.endsWith('.py')).slice(-10);

            container.innerHTML = pyFiles.map(file => {
                const fullPath = `${project}/${file}`;
                const isNew = recentFiles.has(fullPath);
                const isActive = currentFile === fullPath;
                return `<div class="file-tab ${isNew ? 'new' : ''} ${isActive ? 'active' : ''}"
                             onclick="requestFile('${project}', '${file}')">${file.split('/').pop()}</div>`;
            }).join('');
        }

        function requestFile(project, filepath) {
            currentFile = `${project}/${filepath}`;
            currentProject = project;
            ws.send(JSON.stringify({
                action: 'get_file',
                project: project,
                filepath: filepath
            }));

            // Update tab styling
            document.querySelectorAll('.file-tab').forEach(tab => tab.classList.remove('active'));
            event?.target?.classList?.add('active');
        }

        function addActivityItem(item) {
            const container = document.getElementById('activity-log');
            const div = document.createElement('div');
            div.className = `activity-item ${item.type}`;
            div.innerHTML = `<span class="activity-time">${item.time_str}</span>${item.message}`;
            container.insertBefore(div, container.firstChild);

            // Limit items
            while (container.children.length > 50) {
                container.removeChild(container.lastChild);
            }
        }

        // Initial connection
        connect();

        // Request file list on load
        setTimeout(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: 'get_files', project: 'cd_validator' }));
                ws.send(JSON.stringify({ action: 'get_files', project: 'pdf_markup_analyzer' }));
            }
        }, 1000);
    </script>
</body>
</html>"""
    return web.Response(text=html, content_type='text/html')


async def api_status_handler(request):
    """API endpoint for agent status (for full_monitor.html)."""
    status = get_agent_status()
    return web.json_response(status)


async def api_global_handler(request):
    """API endpoint for global state (for full_monitor.html)."""
    # Find most recently modified project
    active_project = None
    active_file = None
    last_update = 0
    content = ""
    projects = []

    try:
        if PROJECTS_DIR.exists():
            for project_dir in PROJECTS_DIR.iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith('.'):
                    project_name = project_dir.name
                    files = list(project_dir.rglob("*"))
                    if files:
                        # Get most recent file
                        latest_file = max(
                            [f for f in files if f.is_file()],
                            key=lambda x: x.stat().st_mtime,
                            default=None
                        )
                        if latest_file:
                            mtime = latest_file.stat().st_mtime
                            if mtime > last_update:
                                last_update = mtime
                                active_project = project_name
                                active_file = latest_file.name
                                try:
                                    content = latest_file.read_text()[:10000]  # Max 10KB
                                except:
                                    content = "Unable to read file"

                            # Add project with its files
                            file_list = [
                                {"name": f.name, "path": str(f.relative_to(project_dir))}
                                for f in files if f.is_file()
                            ]
                            projects.append({
                                "name": project_name,
                                "files": file_list
                            })
    except Exception as e:
        print(f"Global handler error: {e}")

    return web.json_response({
        "active_project": active_project,
        "active_file": active_file,
        "last_update": last_update,
        "is_new": True,  # Always indicate new for poll-based updates
        "content": content,
        "projects": projects
    })


async def full_monitor_handler(request):
    """Serve the full monitor HTML."""
    html_path = Path(__file__).parent / "full_monitor.html"
    if html_path.exists():
        return web.FileResponse(html_path)
    return web.Response(text="full_monitor.html not found", status=404)


async def live_dashboard_handler(request):
    """Serve the new live visual dashboard."""
    html_path = Path(__file__).parent / "live_dashboard.html"
    if html_path.exists():
        return web.FileResponse(html_path)
    return web.Response(text="live_dashboard.html not found", status=404)


async def api_activity_handler(request):
    """API endpoint for current activity (for live_dashboard.html)."""
    status = get_agent_status()
    activity = get_current_activity()
    return web.json_response({
        "agent": status.get("agent"),
        "speaking": status.get("speaking", False),
        "text": status.get("text", ""),
        "activity": activity.get("activity"),
        "timestamp": activity.get("timestamp")
    })


async def api_screenshot_handler(request):
    """API endpoint for browser screenshot (if available)."""
    screenshot_path = Path("/tmp/browser_screenshot.png")
    if screenshot_path.exists():
        # Check if screenshot is fresh (less than 10 seconds old)
        if time.time() - screenshot_path.stat().st_mtime < 10:
            return web.FileResponse(screenshot_path)

    # Return empty response if no screenshot
    return web.Response(status=204)


async def api_push_handler(request):
    """
    POST /api/push - Instant status broadcast from agents.
    Agents push their status directly, server broadcasts to all clients.
    """
    try:
        data = await request.json()

        # Determine message type
        msg_type = data.get("type", "activity")
        if "agent" in data and "speaking" in data:
            msg_type = "agent_status"
        elif "activity" in data:
            msg_type = "activity"
        elif data.get("type") == "execution_result":
            msg_type = "execution_result"
        elif data.get("type") == "approval_request":
            msg_type = "approval_request"
        elif data.get("type") == "execution_mode":
            msg_type = "execution_mode"

        # Broadcast to all WebSocket clients
        await broadcast({
            "type": msg_type,
            "data": data
        })

        # Also log activity
        if msg_type == "activity" and data.get("activity"):
            activity = data["activity"]
            activity_type = activity.get("type", "unknown")
            log_activity(activity_type, f"{data.get('agent', 'Agent')}: {activity_type}")
        elif msg_type == "execution_result":
            action_type = data.get("action_type", "unknown")
            success = "SUCCESS" if data.get("success") else "FAILED"
            log_activity("execution", f"{data.get('agent', 'Agent')}: {action_type} - {success}")
        elif msg_type == "approval_request":
            log_activity("approval", f"Approval requested: {data.get('action_type', 'unknown')}")

        return web.json_response({"status": "ok", "clients": len(clients)})

    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)


async def api_session_start_handler(request):
    """POST /api/session/start - Start a new session with task and mode."""
    global session_state
    try:
        data = await request.json()
        session_state = {
            "active": True,
            "paused": False,
            "task": data.get("task", ""),
            "mode": data.get("mode", "work"),
            "started_at": time.time()
        }

        # Broadcast session start
        await broadcast({
            "type": "session_state",
            "data": session_state
        })

        log_activity("session", f"Session started: {session_state['task'][:50]}")

        return web.json_response({"status": "ok", "session": session_state})

    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)


async def api_session_pause_handler(request):
    """POST /api/session/pause - Toggle pause/resume."""
    global session_state
    session_state["paused"] = not session_state["paused"]

    # Broadcast state change
    await broadcast({
        "type": "session_state",
        "data": session_state
    })

    status = "paused" if session_state["paused"] else "resumed"
    log_activity("session", f"Session {status}")

    return web.json_response({"status": "ok", "paused": session_state["paused"]})


async def api_session_stop_handler(request):
    """POST /api/session/stop - Stop the current session."""
    global session_state
    session_state = {
        "active": False,
        "paused": False,
        "task": None,
        "mode": "work",
        "started_at": None
    }

    # Broadcast session stop
    await broadcast({
        "type": "session_state",
        "data": session_state
    })

    log_activity("session", "Session stopped")

    return web.json_response({"status": "ok"})


async def api_session_state_handler(request):
    """GET /api/session - Get current session state."""
    return web.json_response(session_state)


async def api_execution_mode_handler(request):
    """POST /api/execution-mode - Toggle execution mode."""
    global execution_state
    try:
        data = await request.json()
        enabled = data.get("enabled", False)
        workspace = data.get("workspace")

        execution_state["enabled"] = enabled
        if workspace:
            execution_state["workspace"] = workspace

        # Broadcast to all clients
        await broadcast({
            "type": "execution_mode",
            "data": {
                "enabled": enabled,
                "workspace": workspace
            }
        })

        log_activity("execution", f"Execution mode {'enabled' if enabled else 'disabled'}")

        return web.json_response({
            "status": "ok",
            "execution_enabled": enabled,
            "workspace": workspace
        })

    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)


async def api_execution_state_handler(request):
    """GET /api/execution - Get current execution state."""
    return web.json_response(execution_state)


async def api_approve_handler(request):
    """POST /api/approve - Handle approval/denial of dangerous actions."""
    global execution_state
    try:
        data = await request.json()
        action_id = data.get("action_id")
        approved = data.get("approved", False)

        if not action_id:
            return web.json_response({"status": "error", "message": "action_id required"}, status=400)

        # Store the approval response
        approval_responses[action_id] = approved

        # Remove from pending approvals
        execution_state["pending_approvals"] = [
            a for a in execution_state["pending_approvals"]
            if a.get("id") != action_id
        ]

        # Broadcast approval result
        await broadcast({
            "type": "approval_response",
            "data": {
                "action_id": action_id,
                "approved": approved
            }
        })

        status = "approved" if approved else "denied"
        log_activity("approval", f"Action {action_id} {status}")

        return web.json_response({"status": "ok", "action_id": action_id, "approved": approved})

    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)


async def api_pending_approvals_handler(request):
    """GET /api/approvals - Get pending approval requests."""
    return web.json_response({
        "pending": execution_state["pending_approvals"]
    })


async def api_request_approval_handler(request):
    """POST /api/request-approval - Queue an action for approval."""
    global execution_state
    try:
        data = await request.json()
        action_id = data.get("action_id") or f"action_{int(time.time() * 1000)}"
        action_type = data.get("action_type", "unknown")
        content = data.get("content", "")
        agent = data.get("agent", "unknown")

        approval_request = {
            "id": action_id,
            "action_type": action_type,
            "content": content[:500],
            "agent": agent,
            "timestamp": time.time()
        }

        execution_state["pending_approvals"].append(approval_request)

        # Broadcast to dashboard
        await broadcast({
            "type": "approval_request",
            "data": approval_request
        })

        log_activity("approval_request", f"Action pending approval: {action_type}")

        return web.json_response({
            "status": "ok",
            "action_id": action_id,
            "queued": True
        })

    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)


async def init_app():
    """Initialize the web application."""
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/api/status', api_status_handler)
    app.router.add_get('/api/global', api_global_handler)
    app.router.add_get('/api/activity', api_activity_handler)
    app.router.add_get('/api/screenshot', api_screenshot_handler)
    # Push endpoint for instant broadcasts
    app.router.add_post('/api/push', api_push_handler)
    # Session control endpoints
    app.router.add_post('/api/session/start', api_session_start_handler)
    app.router.add_post('/api/session/pause', api_session_pause_handler)
    app.router.add_post('/api/session/stop', api_session_stop_handler)
    app.router.add_get('/api/session', api_session_state_handler)
    # Execution mode endpoints
    app.router.add_post('/api/execution-mode', api_execution_mode_handler)
    app.router.add_get('/api/execution', api_execution_state_handler)
    # Approval workflow endpoints
    app.router.add_post('/api/approve', api_approve_handler)
    app.router.add_get('/api/approvals', api_pending_approvals_handler)
    app.router.add_post('/api/request-approval', api_request_approval_handler)
    # Legacy routes
    app.router.add_get('/monitor/full_monitor.html', full_monitor_handler)
    app.router.add_get('/monitor/live_dashboard.html', live_dashboard_handler)
    app.router.add_get('/live', live_dashboard_handler)  # Shortcut URL
    return app


async def main():
    """Start the server."""
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', MONITOR_PORT)
    await site.start()

    print(f"\n{'='*60}")
    print(f"[*] Agent Team Live Monitor")
    print(f"{'='*60}")
    print(f"Open in browser: http://localhost:{MONITOR_PORT}")
    print(f"{'='*60}\n")

    # Start the status broadcaster
    asyncio.create_task(status_broadcaster())

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
