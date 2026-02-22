# Claude Memory MCP

**What if Claude Code remembered everything and learned from its mistakes?**

Claude Memory MCP gives Claude Code a persistent memory that survives across sessions. It stores decisions, corrections, project context, and patterns — then retrieves them exactly when needed. Over time, Claude gets better at your specific workflows because it remembers what worked and what didn't.

## Quickstart (5 minutes)

```bash
# Clone
git clone https://github.com/BIMOpsStudio/claude-memory-mcp.git
cd claude-memory-mcp

# Install
pip install -e .

# Run the setup wizard (registers with Claude Code, creates DB)
python install.py
```

Or manually add to `~/.config/claude/settings.json`:

```json
{
  "mcpServers": {
    "claude-memory": {
      "type": "stdio",
      "command": "python3",
      "args": ["/path/to/claude-memory-mcp/src/claude_memory/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/claude-memory-mcp/src"
      }
    }
  }
}
```

Restart Claude Code. That's it — you now have persistent memory.

## What It Does

- **Remembers across sessions** — decisions, facts, preferences, and context persist in a local SQLite database with FTS5 full-text search
- **Learns from mistakes** — when Claude gets corrected, it stores the correction and checks for it before repeating the same error (60+ corrections and counting)
- **Tracks projects** — knows what you're working on, what's active, and loads relevant context automatically at session start
- **Gets smarter over time** — tracks which corrections actually help, decays the ones that don't, and synthesizes patterns from recurring issues

## Feature Highlights

### Persistent Memory (FTS5 Search)
Every memory is stored with content, tags, project, importance, and timestamps. Search uses SQLite FTS5 for fast full-text retrieval, plus optional semantic embeddings for meaning-based search.

### Self-Improvement Correction Loop
When Claude makes a mistake and you correct it, `memory_store_correction` captures exactly what went wrong and what's right. Before future actions, `memory_check_before_action` surfaces relevant past corrections. The system tracks whether corrections actually helped (`memory_correction_helped`) and decays unhelpful ones.

### Semantic Search (Optional)
Install with `pip install claude-memory-mcp[semantic]` to enable embedding-based search using fastembed. This finds memories by meaning, not just keyword overlap — useful when you don't remember exact phrasing.

### Engram Cache Layer
Inspired by DeepSeek's Engram architecture: O(1) hash-based fast path for repeated queries, hot cache for high-importance corrections, and context-aware gating for memory retrieval.

### Auto-Backup
Built-in backup scripts for hourly/daily/weekly snapshots of the memory database.

## Tool Reference (33 tools)

### Core Memory

| Tool | Description |
|------|-------------|
| `memory_store` | Store a new memory with metadata (tags, project, importance, type) |
| `memory_store_enhanced` | Store with automatic cache invalidation |
| `memory_recall` | Search memories using full-text search (FTS5) |
| `memory_recall_fast` | Enhanced recall with O(1) hash cache for repeated queries |
| `memory_semantic_search` | Search by meaning using embeddings (requires `[semantic]` extras) |
| `memory_smart_recall` | Context-aware recall with gating |
| `memory_forget` | Delete memories (requires confirmation) |
| `memory_verify` | Mark a memory as verified or unverified |
| `memory_compact` | Clean up expired and low-value memories |
| `memory_stats` | Get system statistics (memory count, DB size, categories) |

### Context & Sessions

| Tool | Description |
|------|-------------|
| `memory_get_context` | Load relevant context at session start |
| `memory_smart_context` | Intelligently load context based on current directory and situation |
| `memory_summarize_session` | Capture session value at the end of significant work |

### Projects

| Tool | Description |
|------|-------------|
| `memory_get_project` | Get complete history for a project |
| `memory_list_projects` | List all tracked projects with status and memory counts |
| `memory_update_project` | Create or update a project record |

### Knowledge Graph

| Tool | Description |
|------|-------------|
| `memory_link` | Create relationships between memories |
| `memory_get_related` | Traverse the knowledge graph from a memory |
| `memory_find_patterns` | Analyze memories to find recurring patterns |

### Self-Improvement (Correction Loop)

| Tool | Description |
|------|-------------|
| `memory_store_correction` | Store a correction when Claude makes a mistake |
| `memory_get_corrections` | Retrieve past corrections and learnings |
| `memory_corrections_instant` | O(1) instant access to corrections from hot cache |
| `memory_check_before_action` | Check for relevant corrections before acting |
| `memory_correction_helped` | Record whether a correction actually helped |
| `memory_log_avoided_mistake` | Log when a known mistake was successfully avoided |
| `memory_auto_capture_correction` | Auto-capture corrections from conversation |
| `memory_synthesize_patterns` | Find root causes across all corrections |
| `memory_get_improvement_stats` | Get self-improvement loop performance stats |
| `memory_decay_corrections` | Decay importance of unhelpful corrections |
| `memory_archive_old_corrections` | Archive old, low-effectiveness corrections |
| `memory_retire_correction` | Manually retire a fully-learned correction |

### Engram Cache

| Tool | Description |
|------|-------------|
| `memory_engram_stats` | Get Engram cache statistics |
| `memory_invalidate_cache` | Invalidate caches after manual data changes |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_MEMORY_DATA` | Override data directory path | (auto-detected) |
| `CLAUDE_USER_ID` | Override user identity | `~/.claude/user.json` → system user |
| `XDG_DATA_HOME` | XDG base directory for new installs | `~/.local/share` |

### Data Path Resolution

The database location is resolved in this order:
1. `CLAUDE_MEMORY_DATA` environment variable (if set)
2. Package-relative `data/` directory (if it exists — current/legacy layout)
3. `$XDG_DATA_HOME/claude-memory/` (created for new installs)

### User Identity

User ID is resolved in this order:
1. `CLAUDE_USER_ID` environment variable
2. `~/.claude/user.json` → `user_id` field
3. System username (fallback)

## Architecture

```
Claude Code ──(stdio)──> Claude Memory MCP Server
                              │
                              ├── SQLite + FTS5 (memories.db)
                              ├── Engram Cache (in-memory)
                              └── fastembed (optional, for semantic search)
```

The server runs as an MCP (Model Context Protocol) stdio server. Claude Code launches it as a subprocess and communicates via JSON-RPC over stdin/stdout. All data is stored locally in a single SQLite database.

### Memory Types

| Type | Purpose |
|------|---------|
| `decision` | Choices made and reasoning |
| `fact` | Important information learned |
| `preference` | User preferences and style |
| `context` | General context and state |
| `outcome` | Results of actions taken |
| `error` | Problems encountered and solutions |
| `correction` | Specific corrections to Claude's behavior |

### Importance Scale

| Range | Priority | Description |
|-------|----------|-------------|
| 1-3 | Low | Background info |
| 4-6 | Normal | Useful context |
| 7-8 | High | Important to remember |
| 9-10 | Critical | Must not forget |

## Kernel Evolution

The correction database can auto-generate a supplementary "common sense" file:

```bash
python -m claude_memory.kernel_gen
```

This reads all stored corrections, categorizes them by domain (window management, Excel, Revit, git, etc.), and generates a concise rule file weighted by effectiveness scores. See `kernel_gen.py` for details.

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/backup-memory.py` | Manual and scheduled database backups |
| `scripts/maintenance.py` | Database maintenance (vacuum, integrity check) |
| `scripts/sync-to-cloud.py` | Sync memories to cloud storage |

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/BIMOpsStudio/claude-memory-mcp.git
cd claude-memory-mcp
pip install -e ".[all]"

# Run the server directly
python -m claude_memory.server

# Run kernel generation
python -m claude_memory.kernel_gen

# Run maintenance
python scripts/maintenance.py
```

### Project Structure

```
claude-memory-mcp/
├── pyproject.toml          # Package metadata & build config
├── README.md
├── LICENSE                 # MIT
├── install.py              # Setup wizard
├── src/
│   └── claude_memory/
│       ├── __init__.py     # Version
│       ├── server.py       # MCP server (33 tools)
│       ├── engram.py       # Engram cache layer
│       └── kernel_gen.py   # Correction → kernel rules
├── scripts/
│   ├── backup-memory.py
│   ├── maintenance.py
│   └── sync-to-cloud.py
└── data/                   # .gitignored, created at runtime
    └── memories.db
```

## License

MIT — Weber Gouin / BIM Ops Studio
