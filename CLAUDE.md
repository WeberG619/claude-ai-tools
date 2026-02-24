# CLAUDE.md -- _CLAUDE-TOOLS

## Overview
Weber Gouin's master agent tooling ecosystem. This is the central nervous system for all Claude Code sessions -- it contains MCP servers, hooks, brain state, system bridge, autonomous agents, memory infrastructure, and workflow definitions. Changes here propagate to every active session.

## Tech Stack
- **Python 3.8+** (majority of tools, MCP servers, daemons)
- **Node.js/TypeScript** (some MCP servers like claude-code-action, playwright-mcp)
- **PowerShell** (Windows system bridge scripts, desktop automation helpers)
- **Bash** (startup scripts, daemon management)
- **SQLite** (memory persistence, file index, task queues, workflow state)
- **JSON/NDJSON** (live state, brain state, event logs)

## Project Structure
```
_CLAUDE-TOOLS/
├── system-bridge/          # Live system state daemon (live_state.json, watchdog, file indexer)
├── brain-state/            # Session memory persistence (brain.json, conversation logs, daily summaries)
├── agent-boost/            # Strong agent framework + agent preamble + worktree policy
├── agent-common-sense/     # Common sense engine (kernel, corrections, alignment, planner, router)
├── claude-memory-server/   # MCP server for persistent cross-session memory (memories.db)
├── voice-mcp/              # Edge TTS voice output MCP server
├── Claude_Skills/          # Domain expertise .skill files (Revit, orchestration, product, marketing)
├── autonomous-agent/       # Background daemon with trigger-based task execution
├── agent-dashboard/        # Visual command center (localhost:8888)
├── code_memory_system/     # Code indexing + embedding-based retrieval
├── ClaudeSTT/              # Speech-to-text input system (Python + wake word)
├── claude-code-revit/      # Revit-specific code generation handlers
├── claude-code-standards/  # Coding standards, hooks, validation rules
├── claude-code-action/     # GitHub Actions integration for Claude Code
├── context-triggers/       # Context-aware trigger system
├── self-improvement-hooks/ # Self-learning hook infrastructure
├── security-hooks/         # Pre-commit secret detection, MCP seatbelts
├── proactive/              # Proactive behavior engine
├── proactive-memory/       # Proactive memory pattern recognition
├── pipelines/              # Multi-step workflow pipelines
├── orchestration/          # Task orchestration layer
├── _ARCHIVED/              # Deprecated tools (do not use)
├── CLAUDE_REFERENCE.md     # On-demand reference (task routing, Aider strategy, context optimization)
├── WEBER_WORKFLOWS.md      # Email, contacts, calendar, Revit pipes, project paths
├── DESKTOP.md              # Desktop automation patterns (DPI-aware, window management)
├── AGENTS.md               # Agent fleet overview (51 agents, 10 squads)
└── [60+ other MCP servers and tools]
```

## Conventions
- **Progressive loading**: Only load reference docs when their trigger is hit (see global CLAUDE.md)
- **Session start**: Always read `system-bridge/live_state.json` first, then load memory context
- **Corrections file**: `agent-common-sense/kernel-corrections.md` is auto-generated -- do NOT edit manually. Regenerate with `python kernel_gen.py`
- **MCP server pattern**: Each MCP server lives in its own subdirectory with its own requirements.txt/package.json
- **Naming**: User is Weber Gouin (NEVER "Rick"). Business is BIM Ops Studio
- **Revit pipes**: Named `RevitMCPBridge2025` / `RevitMCPBridge2026` (NEVER abbreviate)
- **Email**: Gmail via Chrome (NEVER Outlook, NEVER Edge)

## Known Gotchas
- **This IS the system** -- any breaking change here affects ALL Claude Code sessions immediately
- **kernel-corrections.md** is auto-generated from 62+ corrections. Manual edits get overwritten
- **live_state.json** is written by the system-bridge daemon every 30 seconds. Do not write to it from Claude sessions
- **brain-state/brain.json** persists across sessions -- corrupting it loses accumulated context
- **memories.db** (in claude-memory-server) is the single source of truth for long-term memory. Back up before schema changes
- **_ARCHIVED/** contains deprecated tools. Never reference or import from there
- **agent-common-sense** has extensive Python modules (alignment, coherence, planner, router, etc.) with their own test suite. Run tests before modifying

## Related Agents
All agents interact with this ecosystem. Key ones:
- **orchestrator** -- routes tasks to sub-agents, uses strong agent framework
- **agent-builder** -- creates new agent definitions
- **prompt-engineer** -- optimizes skill files and agent prompts
- **learning-agent** -- feeds corrections back into the common sense engine

## Key Files
- `/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json` -- real-time system state
- `/mnt/d/_CLAUDE-TOOLS/brain-state/brain.json` -- persistent brain state
- `/mnt/d/_CLAUDE-TOOLS/agent-boost/strong_agent.md` -- 5-phase sub-agent execution framework
- `/mnt/d/_CLAUDE-TOOLS/agent-common-sense/kernel-corrections.md` -- compiled safety corrections (62+)
- `/mnt/d/_CLAUDE-TOOLS/claude-memory-server/memories.db` -- long-term memory database
- `/mnt/d/_CLAUDE-TOOLS/CLAUDE_REFERENCE.md` -- task routing and context optimization guide
- `/mnt/d/_CLAUDE-TOOLS/WEBER_WORKFLOWS.md` -- contacts, email patterns, project paths
- `/mnt/d/_CLAUDE-TOOLS/DESKTOP.md` -- DPI-aware desktop automation patterns
- `/mnt/d/_CLAUDE-TOOLS/AGENTS.md` -- full agent fleet reference (51 agents, 10 squads)
