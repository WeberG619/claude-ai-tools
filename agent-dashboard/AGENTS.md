# AGENTS.md - Agent Dashboard

> Instructions for AI agents working in this codebase.

## Overview

Visual command center for Weber Gouin's autonomous agent fleet. A FastAPI web application that displays agent status, task queues, and system state in real-time.

## Architecture

```
agent-dashboard/
├── server.py              # FastAPI server (port 8888)
├── dashboard.html         # Main UI
├── executor_status.json   # Real-time status snapshot
└── AGENTS.md              # This file
```

## Key Components

### server.py
- **AgentManager**: Loads and tracks all agent definitions from ~/.claude/agents/
- **SystemMonitor**: Checks running daemons and live system state
- **TaskQueue**: Interface to the SQLite task database
- **WebSocket**: Real-time updates to connected clients

### dashboard.html
- Single-page app with live updates
- Agent cards grouped by squad/category
- Command bar for sending tasks
- Activity log and system status

### executor_status.json
Written by the autonomous executor to communicate:
- Running state
- Active agents
- Completed tasks
- Pending triggers

## Agent Categories

| Category | Agents | Purpose |
|----------|--------|---------|
| revit | 20 | BIM/Revit operations |
| development | 5 | Code architecture, fullstack, Python, C#, DevOps |
| ai_agents | 3 | ML, prompts, agent building |
| business | 4 | Proposals, invoices, clients, projects |
| research | 2 | Tech scouting, market analysis |
| quality | 5 | BIM validation, QC, compliance |
| documentation | 3 | Schedules, reports, takeoffs |
| workflow | 4 | Orchestration, learning, processing |
| code | 4 | Simplification, analysis, testing |

## API Endpoints

```
GET  /                  # Dashboard HTML
GET  /api/status        # Full system status
GET  /api/agents        # All agents by category
GET  /api/daemons       # Running daemons
GET  /api/tasks         # Task queue
GET  /api/logs          # Recent log entries
POST /api/command       # Send command to agents
WS   /ws                # WebSocket for real-time updates
```

## Working in This Codebase

### DO:
- Keep the API fast (dashboard polls every 5 seconds)
- Use the existing category system for new agents
- Update executor_status.json format carefully
- Test WebSocket connections

### DON'T:
- Add heavy computation to API endpoints
- Change the HTML structure without updating JS
- Block the event loop

## Running

```bash
python server.py
# Opens on http://localhost:8888
```

## Dependencies

- fastapi
- uvicorn
- pydantic

## Owner

Weber Gouin / BIM Ops Studio
