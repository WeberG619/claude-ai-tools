#!/usr/bin/env python3
"""
Agent Dashboard Server
======================
Visual command center for Weber's autonomous agent fleet.

Run: python server.py
Open: http://localhost:8080

Author: Weber Gouin
"""

import asyncio
import json
import os
import sys
import subprocess
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import hashlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import re

# ============================================
# CONFIGURATION
# ============================================

AGENTS_DIR = Path("/home/weber/.claude/agents")
LIVE_STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
AUTONOMOUS_AGENT_DIR = Path("/mnt/d/_CLAUDE-TOOLS/autonomous-agent")
TASK_DB = AUTONOMOUS_AGENT_DIR / "queues" / "tasks.db"
AGENT_LOG = AUTONOMOUS_AGENT_DIR / "logs" / "agent.log"
MCP_HEALTH_REPORT = AUTONOMOUS_AGENT_DIR / "reports" / "mcp_health_check.md"

# ============================================
# DATA MODELS
# ============================================

@dataclass
class AgentDefinition:
    """An agent definition from the agents directory."""
    name: str
    file_path: str
    description: str
    category: str
    status: str  # idle, working, error
    current_task: Optional[str] = None
    tasks_completed: int = 0
    last_active: Optional[str] = None

@dataclass
class RunningDaemon:
    """A running background daemon."""
    name: str
    pid: int
    status: str
    uptime: str
    description: str

@dataclass
class TaskItem:
    """A task in the queue."""
    id: int
    title: str
    status: str
    priority: int
    created_at: str
    assigned_agent: Optional[str] = None

# ============================================
# AGENT MANAGER
# ============================================

class AgentManager:
    """Manages all agent definitions and their status."""

    CATEGORIES = {
        "revit": ["revit-builder", "revit-developer", "view-agent", "sheet-layout",
                  "annotation-agent", "dimensioning-agent", "family-agent", "link-agent",
                  "floor-ceiling-agent", "roof-agent", "stair-railing-agent", "site-agent",
                  "mep-agent", "structural-agent", "phase-agent", "workset-agent",
                  "material-agent", "legend-agent", "detail-agent", "export-agent"],
        "quality": ["bim-validator", "qc-agent", "cd-reviewer", "code-compliance-agent",
                    "clash-detection-agent"],
        "documentation": ["schedule-builder", "quantity-takeoff-agent", "excel-reporter"],
        "workflow": ["orchestrator", "learning-agent", "floor-plan-processor",
                     "project-librarian"],
        "development": ["code-architect", "fullstack-dev", "python-engineer",
                        "csharp-developer", "devops-agent"],
        "ai_agents": ["ml-engineer", "prompt-engineer", "agent-builder"],
        "business": ["proposal-writer", "invoice-tracker", "client-liaison", "project-manager"],
        "research": ["tech-scout", "market-analyst"],
        "code": ["code-simplifier", "code-analyzer", "test-runner", "doc-scraper"]
    }

    def __init__(self):
        self.agents: Dict[str, AgentDefinition] = {}
        self.active_tasks: Dict[str, str] = {}  # agent_name -> task_id
        self._load_agents()

    def _load_agents(self):
        """Load all agent definitions from disk."""
        if not AGENTS_DIR.exists():
            return

        for file in AGENTS_DIR.glob("*.md"):
            name = file.stem
            content = file.read_text()[:500]  # First 500 chars for description

            # Extract description from first paragraph
            lines = content.split('\n')
            desc = ""
            for line in lines[1:10]:
                if line.strip() and not line.startswith('#'):
                    desc = line.strip()[:100]
                    break

            # Determine category
            category = "other"
            for cat, agents in self.CATEGORIES.items():
                if name in agents:
                    category = cat
                    break

            self.agents[name] = AgentDefinition(
                name=name,
                file_path=str(file),
                description=desc or f"Agent: {name}",
                category=category,
                status="idle",
                tasks_completed=0
            )

        # Also load yaml agents
        for file in AGENTS_DIR.glob("*.yaml"):
            name = file.stem
            self.agents[name] = AgentDefinition(
                name=name,
                file_path=str(file),
                description=f"YAML Agent: {name}",
                category="code",
                status="idle",
                tasks_completed=0
            )

    def get_all_agents(self) -> List[dict]:
        """Get all agents as dicts."""
        return [asdict(a) for a in self.agents.values()]

    def get_agents_by_category(self) -> Dict[str, List[dict]]:
        """Get agents grouped by category."""
        result = {}
        for agent in self.agents.values():
            if agent.category not in result:
                result[agent.category] = []
            result[agent.category].append(asdict(agent))
        return result

    def assign_task(self, agent_name: str, task: str) -> bool:
        """Assign a task to an agent."""
        if agent_name not in self.agents:
            return False

        self.agents[agent_name].status = "working"
        self.agents[agent_name].current_task = task
        self.agents[agent_name].last_active = datetime.now().isoformat()
        return True

    def complete_task(self, agent_name: str):
        """Mark an agent's task as complete."""
        if agent_name in self.agents:
            self.agents[agent_name].status = "idle"
            self.agents[agent_name].current_task = None
            self.agents[agent_name].tasks_completed += 1

# ============================================
# SYSTEM MONITOR
# ============================================

class SystemMonitor:
    """Monitors running daemons and system state."""

    def get_running_daemons(self) -> List[dict]:
        """Get all running daemons related to the agent system."""
        daemons = []

        # Check autonomous agent
        pid_file = AUTONOMOUS_AGENT_DIR / "agent.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                # Check if process is running
                result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "pid,etime,comm", "--no-headers"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split()
                    uptime = parts[1] if len(parts) > 1 else "unknown"
                    daemons.append({
                        "name": "Autonomous Agent",
                        "pid": pid,
                        "status": "running",
                        "uptime": uptime,
                        "description": "Watches system, sends notifications, routes tasks"
                    })
            except:
                pass

        # Check system bridge daemon
        try:
            result = subprocess.run(
                ["pgrep", "-f", "claude_daemon.py"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                pid = int(result.stdout.strip().split()[0])
                daemons.append({
                    "name": "System Bridge",
                    "pid": pid,
                    "status": "running",
                    "uptime": "persistent",
                    "description": "Monitors active window, clipboard, system state"
                })
        except:
            pass

        return daemons

    def get_live_state(self) -> dict:
        """Get current system state."""
        if LIVE_STATE_FILE.exists():
            try:
                return json.loads(LIVE_STATE_FILE.read_text())
            except:
                pass
        return {}

    def get_recent_logs(self, lines: int = 20) -> List[str]:
        """Get recent log entries."""
        if AGENT_LOG.exists():
            try:
                result = subprocess.run(
                    ["tail", f"-{lines}", str(AGENT_LOG)],
                    capture_output=True, text=True
                )
                return result.stdout.strip().split('\n')
            except:
                pass
        return []

# ============================================
# TASK QUEUE
# ============================================

class TaskQueue:
    """Interface to the task database."""

    def get_tasks(self, limit: int = 50) -> List[dict]:
        """Get recent tasks."""
        if not TASK_DB.exists():
            return []

        try:
            conn = sqlite3.connect(str(TASK_DB))
            cur = conn.cursor()
            cur.execute("""
                SELECT id, title, status, priority, created_at
                FROM tasks
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            conn.close()

            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "status": r[2],
                    "priority": r[3],
                    "created_at": r[4]
                }
                for r in rows
            ]
        except Exception as e:
            return []

    def add_task(self, title: str, description: str, priority: int = 5) -> int:
        """Add a new task to the queue."""
        if not TASK_DB.exists():
            return -1

        try:
            conn = sqlite3.connect(str(TASK_DB))
            cur = conn.cursor()
            now = datetime.now().isoformat()
            cur.execute("""
                INSERT INTO tasks (title, description, priority, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
            """, (title, description, priority, now))
            task_id = cur.lastrowid
            conn.commit()
            conn.close()
            return task_id
        except Exception as e:
            print(f"Error adding task: {e}")
            return -1

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(title="Agent Dashboard")

# Mount static files directory
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Global instances
agent_manager = AgentManager()
system_monitor = SystemMonitor()
task_queue = TaskQueue()

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text())
    return HTMLResponse(content="<h1>Dashboard not found</h1>")

EXECUTOR_STATUS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/agent-dashboard/executor_status.json")

def get_executor_status() -> dict:
    """Get autonomous executor status."""
    try:
        if EXECUTOR_STATUS_FILE.exists():
            return json.loads(EXECUTOR_STATUS_FILE.read_text())
    except:
        pass
    return {"running": False, "active_agents": {}, "completed_tasks": []}

@app.get("/api/status")
async def get_status():
    """Get full system status."""
    live_state = system_monitor.get_live_state()
    executor_status = get_executor_status()

    # Update agent statuses from executor
    for agent_name, agent_info in executor_status.get("active_agents", {}).items():
        if agent_name in agent_manager.agents:
            agent_manager.agents[agent_name].status = "working"
            agent_manager.agents[agent_name].current_task = agent_info.get("task", "")

    return {
        "timestamp": datetime.now().isoformat(),
        "daemons": system_monitor.get_running_daemons(),
        "agents": agent_manager.get_agents_by_category(),
        "agent_count": len(agent_manager.agents),
        "tasks": task_queue.get_tasks(20),
        "logs": system_monitor.get_recent_logs(15),
        "executor": {
            "running": executor_status.get("running", False),
            "active_agents": executor_status.get("active_agents", {}),
            "completed_tasks": executor_status.get("completed_tasks", [])[:5],
            "pending_triggers": executor_status.get("pending_triggers", [])[:5]
        },
        "system": {
            "active_window": live_state.get("active_window", "Unknown"),
            "memory_percent": live_state.get("system", {}).get("memory_percent", 0),
            "cpu_percent": live_state.get("system", {}).get("cpu_percent", 0),
            "revit_open": "Revit" in live_state.get("active_window", ""),
            "monitors": live_state.get("monitors", {}).get("count", 0)
        }
    }

@app.get("/api/agents")
async def get_agents():
    """Get all agents."""
    return agent_manager.get_agents_by_category()

@app.get("/api/daemons")
async def get_daemons():
    """Get running daemons."""
    return system_monitor.get_running_daemons()

@app.get("/api/tasks")
async def get_tasks():
    """Get task queue."""
    return task_queue.get_tasks()

@app.get("/api/logs")
async def get_logs():
    """Get recent logs."""
    return system_monitor.get_recent_logs(50)


def parse_mcp_health_report() -> dict:
    """Parse the MCP health check markdown report into structured JSON."""
    if not MCP_HEALTH_REPORT.exists():
        return {
            "error": "Health report not found",
            "generated_at": None,
            "total_servers": 0,
            "summary": {"healthy": 0, "failing": 0, "disabled": 0, "error": 0},
            "servers": []
        }

    try:
        content = MCP_HEALTH_REPORT.read_text()

        # Extract generation timestamp
        generated_match = re.search(r'\*\*Generated:\*\* (.+)', content)
        generated_at = generated_match.group(1) if generated_match else None

        # Extract total servers
        total_match = re.search(r'\*\*Total Servers:\*\* (\d+)', content)
        total_servers = int(total_match.group(1)) if total_match else 0

        # Extract summary counts
        summary = {"healthy": 0, "failing": 0, "disabled": 0, "error": 0}
        summary_section = re.search(r'## Summary.*?\n\n(.*?)\n\n---', content, re.DOTALL)
        if summary_section:
            summary_text = summary_section.group(1)
            for status in ["Healthy", "Failing", "Disabled", "Error"]:
                match = re.search(rf'\| {status} \| (\d+) \|', summary_text)
                if match:
                    summary[status.lower()] = int(match.group(1))

        # Parse individual servers from the Configuration Details table
        servers = []
        config_section = re.search(r'## Configuration Details\n\n\|.*?\n\|.*?\n(.*?)(?:\n\n---|\Z)', content, re.DOTALL)
        if config_section:
            table_rows = config_section.group(1).strip().split('\n')
            for row in table_rows:
                if row.startswith('|') and not row.startswith('|--'):
                    parts = [p.strip() for p in row.split('|')[1:-1]]
                    if len(parts) >= 4:
                        server_name = parts[0]
                        command = parts[1].strip('`')
                        source = parts[2]
                        status_raw = parts[3].strip()

                        # Determine status
                        if 'healthy' in status_raw.lower():
                            status = 'healthy'
                        elif 'disabled' in status_raw.lower():
                            status = 'disabled'
                        elif 'failing' in status_raw.lower():
                            status = 'failing'
                        else:
                            status = 'error'

                        servers.append({
                            "name": server_name,
                            "command": command,
                            "source": source,
                            "status": status,
                            "purpose": "",
                            "script_path": "",
                            "error_message": None
                        })

        # Enrich with details from Healthy/Failing/Disabled sections
        for server in servers:
            # Look for server details in the markdown
            detail_pattern = rf'- \*\*{re.escape(server["name"])}\*\* \(([^)]+)\)\n((?:  - .+\n?)+)?'
            detail_match = re.search(detail_pattern, content)
            if detail_match:
                details = detail_match.group(2) or ""

                # Extract purpose
                purpose_match = re.search(r'  - Purpose: (.+)', details)
                if purpose_match:
                    server["purpose"] = purpose_match.group(1)

                # Extract script path
                path_match = re.search(r'  - (?:Script exists.*?|Server directory.*?|Module exists.*?|Command found.*?): (.+)', details)
                if path_match:
                    server["script_path"] = path_match.group(1)

        return {
            "generated_at": generated_at,
            "total_servers": total_servers,
            "summary": summary,
            "servers": servers
        }

    except Exception as e:
        return {
            "error": str(e),
            "generated_at": None,
            "total_servers": 0,
            "summary": {"healthy": 0, "failing": 0, "disabled": 0, "error": 0},
            "servers": []
        }


@app.get("/api/mcp-health")
async def get_mcp_health():
    """Get MCP server health status as JSON."""
    return parse_mcp_health_report()


class CommandRequest(BaseModel):
    command: str
    agents: List[str] = []
    priority: int = 5

@app.post("/api/command")
async def send_command(request: CommandRequest):
    """Send a command to agents."""
    # Add as task
    task_id = task_queue.add_task(
        title=request.command,
        description=f"Assigned to: {', '.join(request.agents) if request.agents else 'auto'}",
        priority=request.priority
    )

    # Assign to agents
    for agent_name in request.agents:
        agent_manager.assign_task(agent_name, request.command)

    # Broadcast update to all clients
    await broadcast_update()

    return {
        "status": "queued",
        "task_id": task_id,
        "agents": request.agents
    }

# ============================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        # Send initial state
        status = await get_status()
        await websocket.send_json({"type": "status", "data": status})

        # Keep connection alive and send updates
        while True:
            try:
                # Wait for messages from client
                data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)

                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "command":
                    # Handle command
                    cmd = CommandRequest(**data.get("data", {}))
                    result = await send_command(cmd)
                    await websocket.send_json({"type": "command_result", "data": result})

            except asyncio.TimeoutError:
                # Send periodic updates
                status = await get_status()
                await websocket.send_json({"type": "status", "data": status})

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        connected_clients.discard(websocket)

async def broadcast_update():
    """Broadcast status update to all connected clients."""
    status = await get_status()
    disconnected = set()

    for client in connected_clients:
        try:
            await client.send_json({"type": "status", "data": status})
        except:
            disconnected.add(client)

    connected_clients.difference_update(disconnected)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Agent Dashboard Starting...")
    print("=" * 50)
    print(f"📊 Loaded {len(agent_manager.agents)} agent definitions")
    print(f"🔗 Open http://localhost:8888 in your browser")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="warning")
