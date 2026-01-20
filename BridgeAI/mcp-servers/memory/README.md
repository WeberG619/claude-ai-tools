# Claude Memory MCP Server

Persistent memory storage and retrieval for Claude Code sessions.

## Overview

This MCP server provides Claude with external memory capabilities:
- **Store** decisions, facts, preferences, and context
- **Recall** memories using full-text semantic search
- **Auto-context** loading at session start
- **Project tracking** across all your work

## Installation

```bash
cd /mnt/d/claude-memory-server
pip install -r requirements.txt
```

## MCP Configuration

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "claude-memory": {
      "command": "python",
      "args": ["/mnt/d/claude-memory-server/src/server.py"],
      "env": {}
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `memory_store` | Save a new memory with metadata |
| `memory_recall` | Search memories by query |
| `memory_get_context` | Load session context (call at start) |
| `memory_get_project` | Get all memories for a project |
| `memory_list_projects` | List all tracked projects |
| `memory_update_project` | Create/update project info |
| `memory_forget` | Delete memories |
| `memory_stats` | View system statistics |

## Memory Types

- `decision` - Choices made and why
- `fact` - Important information learned
- `preference` - User preferences and style
- `context` - General context and state
- `outcome` - Results of actions taken
- `error` - Problems encountered and solutions

## Importance Scale

1-3: Low priority, background info
4-6: Normal priority, useful context
7-8: High priority, important to remember
9-10: Critical, must not forget

## Usage Examples

### Store a decision
```
memory_store(
    content="Decided to use SQLite with FTS5 for memory search because it's local, fast, and requires no external dependencies",
    project="claude-memory-server",
    tags=["architecture", "database"],
    importance=8,
    memory_type="decision"
)
```

### Recall memories
```
memory_recall(query="database architecture", project="claude-memory-server")
```

### Get session context
```
memory_get_context(project="RevitMCPBridge2026")
```

## Data Location

All data stored in: `/mnt/d/claude-memory-server/data/memories.db`
