# AGENTS.md - Weber's AI Infrastructure

> Master instructions for AI agents working across Weber Gouin's tool ecosystem.

## System Overview

This directory contains Weber Gouin's AI infrastructure for BIM Ops Studio - a comprehensive system of MCP servers, autonomous agents, and automation tools.

## Directory Structure

```
_CLAUDE-TOOLS/
├── autonomous-agent/       # Background daemon with triggers and task execution
├── agent-dashboard/        # Visual command center (localhost:8888)
├── system-bridge/          # System state monitoring (live_state.json)
├── brain-state/            # Session memory and state persistence
├── claude-memory-server/   # MCP server for persistent memory
├── RevitMCPBridge2026/     # Revit API integration via named pipes
├── RevitMCPBridge2025/     # Revit 2025 version
├── voice-mcp/              # Text-to-speech via Edge TTS
├── google-calendar-mcp/    # Calendar integration
├── gmail-attachments/      # Email attachment processing
├── floor-plan-vision/      # PDF floor plan extraction
├── playwright-mcp/         # Browser automation
└── [other MCP servers]
```

## Agent Fleet

Weber has 51 agents across 10 squads defined in `~/.claude/agents/`:

| Squad | Count | Key Agents |
|-------|-------|------------|
| Revit/BIM | 20 | revit-builder, revit-developer, view-agent, sheet-layout |
| Development | 5 | code-architect, fullstack-dev, python-engineer, csharp-developer |
| AI/Agent | 3 | ml-engineer, prompt-engineer, agent-builder |
| Business | 4 | proposal-writer, invoice-tracker, client-liaison, project-manager |
| Research | 2 | tech-scout, market-analyst |
| Quality | 5 | bim-validator, qc-agent, cd-reviewer |
| Documentation | 3 | schedule-builder, excel-reporter |
| Workflow | 4 | orchestrator, learning-agent, floor-plan-processor |
| Code | 4 | code-simplifier, code-analyzer, test-runner |

## Key Integration Points

### 1. Revit Integration
- **Method**: Named pipes (NOT HTTP)
- **Bridge**: RevitMCPBridge2026 C# add-in
- **Protocol**: JSON-RPC over named pipe `RevitMCP`

### 2. Memory System
- **MCP Server**: claude-memory-server
- **Functions**: store, recall, corrections, patterns
- **Self-improvement**: Pre-action checks for past mistakes

### 3. System Awareness
- **Daemon**: system-bridge/claude_daemon.py
- **Output**: live_state.json (updated every 30 seconds)
- **Data**: Active apps, clipboard, monitors, recent files

### 4. Task Queue
- **CLI**: `weber-task "description"`
- **Storage**: autonomous-agent/queues/tasks.db
- **Execution**: Claude Code CLI with --dangerously-skip-permissions

## Working in This Ecosystem

### Critical Rules
1. **User name is Weber Gouin** (never "Rick")
2. **Email via Gmail in Chrome** (never Outlook)
3. **Revit via named pipes** (never HTTP)
4. **Sign communications as "Weber Gouin"**

### Key Contacts
- Isa Fantal: ifantal@lesfantal.com
- Bruce Davis: bruce@bdarchitect.net
- Paola Gomez: paola@bdarchitect.net
- Rachelle (AFURI): rachelle@afuriaesthetics.com

### Common Workflows
See `/mnt/d/_CLAUDE-TOOLS/WEBER_WORKFLOWS.md` for established patterns.

## Running Services

| Service | Port/Method | Start Command |
|---------|-------------|---------------|
| Dashboard | localhost:8888 | `python agent-dashboard/server.py` |
| System Bridge | live_state.json | `python system-bridge/claude_daemon.py` |
| Autonomous Agent | Background | `python autonomous-agent/core/agent.py` |
| Voice TTS | CLI | `python voice-mcp/speak.py "text"` |

## Configuration Files

- `~/.claude/settings.json` - User-level Claude Code settings with hooks
- `~/.claude/agents/*.md` - Agent definition files
- `~/.claude/CLAUDE.md` - Global instructions for Claude Code

## Owner

Weber Gouin / BIM Ops Studio
weberg619@gmail.com
