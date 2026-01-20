# AEC Drafting AI - Beta Distribution Package

**Version**: 0.1.0-beta
**Requires**: Revit 2026, Claude Code CLI, Python 3.10+

---

## What is AEC Drafting AI?

An autonomous AI system that controls Autodesk Revit through natural language. Tell it what you want in plain English, and it executes the drafting work.

### Capabilities

| Feature | Status | Description |
|---------|--------|-------------|
| **Element Creation** | ✅ Working | Walls, doors, windows, text, lines |
| **Schedules** | ✅ Working | Create, modify, read, export schedules |
| **Project Management** | ✅ Working | Open/close/switch projects by name |
| **View Control** | ✅ Working | Zoom, pan, activate, capture views |
| **Annotations** | ✅ Working | Text notes, tags, dimensions |
| **Life Safety Legends** | ✅ Working | Auto-generate code analysis tables |
| **Self-Healing** | ✅ Working | Undo, recover from errors |
| **Batch Operations** | 🟡 Partial | Individual ops work, batching in progress |

---

## Quick Start

### Prerequisites

1. **Revit 2026** installed
2. **Claude Code CLI** installed (`npm install -g @anthropic/claude-code`)
3. **Python 3.10+** installed
4. **Anthropic API Key** (get from console.anthropic.com)

### Installation

```powershell
# 1. Clone or extract this package
cd C:\AEC-Drafting-AI

# 2. Run the setup script
.\scripts\install.ps1

# 3. Restart Revit

# 4. Launch Claude Code in any terminal
claude
```

### First Test

```
# In Claude Code, say:
"Open Avon Park and show me the door schedule"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLAUDE CODE CLI                          │
│  (Natural Language Interface - you talk to this)            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Memory MCP   │  │ Floor Plan   │  │ Voice MCP    │       │
│  │ (context)    │  │ Vision MCP   │  │ (TTS output) │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                   REVIT MCP BRIDGE                           │
│  (449 API endpoints for Revit control)                      │
│                                                              │
│  Named Pipe: \\.\pipe\RevitMCPBridge2026                    │
├─────────────────────────────────────────────────────────────┤
│                   AUTODESK REVIT 2026                        │
│  (Your BIM model)                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Package Contents

```
aec-drafting-ai/
├── beta-package/
│   ├── README.md              # This file
│   ├── CHANGELOG.md           # Version history
│   └── KNOWN_ISSUES.md        # Current limitations
├── scripts/
│   ├── install.ps1            # Windows installer
│   ├── install.sh             # Linux/WSL installer
│   └── verify_install.py      # Check installation
├── config/
│   ├── claude_settings.json   # Claude Code config template
│   ├── mcp_servers.json       # MCP server definitions
│   └── project_registry.json  # Project name mappings (customize)
├── revit-addin/
│   ├── RevitMCPBridge2026.dll # The Revit add-in
│   └── RevitMCPBridge2026.addin # Add-in manifest
├── mcp-servers/
│   ├── claude-memory/         # Persistent memory
│   ├── floor-plan-vision/     # PDF extraction
│   └── voice-mcp/             # Text-to-speech
└── docs/
    ├── GETTING_STARTED.md
    ├── API_REFERENCE.md
    └── TROUBLESHOOTING.md
```

---

## Configuration

### Project Registry

Edit `config/project_registry.json` to map your project names:

```json
{
  "projects": {
    "My Project": {
      "path": "D:\\Projects\\MyProject.rvt",
      "aliases": ["my proj", "mp"],
      "type": "commercial"
    }
  }
}
```

### Claude Code Settings

The installer configures these automatically, but you can customize in `~/.claude/settings.json`.

---

## Example Commands

### Basic Operations
```
"Open the church project"
"Show me all door schedules"
"Create a door schedule for this project"
"Add the Mark field to the door schedule"
"Export the room schedule to CSV"
```

### Advanced Operations
```
"Create a life safety legend with code analysis, egress, and plumbing tables"
"Place text notes for all room names"
"Switch to the second floor plan"
"Take a screenshot of the current view"
```

### Autonomous Workflows
```
"Review the door schedule and fix any missing marks"
"Generate a complete sheet set for floor plans"
"Check if all rooms are tagged"
```

---

## Known Limitations (Beta)

1. **Cloud families** - Cannot load from Autodesk cloud library (local .rfa only)
2. **Modal dialogs** - Commands timeout if a dialog is open in Revit
3. **Large batches** - 100+ operations may need to be split
4. **Workshared models** - Limited testing with worksharing

---

## Feedback

Report issues to: [your-feedback-channel]

Include:
- What you tried to do
- What happened
- Revit version
- Any error messages

---

## License

Beta software - not for commercial distribution.
For evaluation and testing purposes only.

---

*Built with Claude Code by Anthropic*
