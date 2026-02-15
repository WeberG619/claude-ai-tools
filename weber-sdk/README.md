# Weber SDK

Unified Python SDK wrapping all MCP (Model Context Protocol) servers for Weber's automation environment.

## Features

- **Auto-Discovery**: Automatically discovers MCP servers from `~/.claude/settings.local.json` and `~/.claude/mcp-configs/*.json`
- **Unified Interface**: Access all servers through a single, intuitive API
- **Async-First**: Built with async/await, with sync wrappers available
- **Type Hints**: Full type annotations for IDE support
- **Connection Management**: Automatic connection handling with retries
- **Service Wrappers**: Typed service classes for Voice, Excel, Revit, and more

## Installation

```bash
# From source
pip install -e /mnt/d/_CLAUDE-TOOLS/weber-sdk

# Or with development dependencies
pip install -e "/mnt/d/_CLAUDE-TOOLS/weber-sdk[dev]"
```

## Quick Start

### Basic Usage

```python
from weber_sdk import Weber
import asyncio

async def main():
    async with Weber() as w:
        # Voice
        await w.voice.speak("Hello, Weber!")

        # Excel
        status = await w.excel.get_status()
        print(f"Excel running: {status.get('running')}")

        # Revit 2026
        walls = await w.revit2026.get_walls()
        print(f"Found {len(walls)} walls")

asyncio.run(main())
```

### List Available Servers

```python
from weber_sdk import Weber

w = Weber()
print("Available servers:", w.list_servers())
```

### Service Access Patterns

```python
from weber_sdk import Weber

async def example():
    w = Weber()

    # Access services by name
    await w.voice.speak("Hello")
    await w.excel.get_status()
    await w.revit2026.get_walls()

    # Or use aliases
    await w.voice.speak("Using voice alias")

    # Generic access for any server
    result = await w.floor_plan_vision.analyze_floor_plan(pdf_path="plan.pdf")
```

## Services

### Voice Service

```python
async with Weber() as w:
    # Speak text (default: Andrew voice)
    await w.voice.speak("Hello!")

    # Use different voice
    await w.voice.speak("Hi!", voice="en-US-JennyNeural")

    # Listen for voice input
    text = await w.voice.listen(max_duration=10)

    # Conversation (speak then listen)
    response = await w.voice.conversation(
        prompt="What would you like?",
        max_duration=10
    )
```

### Excel Service

```python
async with Weber() as w:
    # Check status
    status = await w.excel.get_status()

    # Read/write cells
    value = await w.excel.read_cell("A1")
    await w.excel.write_cell("A1", "Hello")

    # Read/write ranges
    data = await w.excel.read_range("A1:C10")
    await w.excel.write_range("E1", [["a", "b"], [1, 2]])

    # Work with tables
    table = await w.excel.read_table("A1:C10", has_headers=True)
    await w.excel.write_table("A1", [{"Name": "Alice", "Age": 30}])

    # Formatting
    await w.excel.format_range("A1:C1", bold=True, bg_color="#4472C4")
    await w.excel.auto_fit_columns()
```

### Revit Service

```python
async with Weber() as w:
    # Document info
    doc = await w.revit2026.get_document_info()
    view = await w.revit2026.get_active_view()

    # Query elements
    levels = await w.revit2026.get_levels()
    walls = await w.revit2026.get_walls(level_name="Level 1")
    rooms = await w.revit2026.get_rooms()

    # Create elements (within transaction)
    await w.revit2026.start_transaction("Create Wall")
    wall = await w.revit2026.create_wall(
        start_point=(0, 0, 0),
        end_point=(20, 0, 0),
        level_name="Level 1"
    )
    await w.revit2026.commit_transaction()

    # Modify elements
    await w.revit2026.set_parameter(wall_id, "Mark", "W-001")
```

## Server Discovery

The SDK automatically discovers MCP servers from:

1. `~/.claude/settings.local.json` - Main configuration
2. `~/.claude/mcp-configs/*.json` - Modular configurations

```python
from weber_sdk import discover_servers

# List all servers
servers = discover_servers()
for name, config in servers.items():
    print(f"{name}: {config.command}")

# Include disabled servers
all_servers = discover_servers(include_disabled=True)
```

## Configuration

### Discovered Servers

Current servers discovered from your configuration:

| Server | Description | Platform |
|--------|-------------|----------|
| `voice-input-mcp` | Voice input/output with TTS | Unix |
| `excel-mcp` | Excel automation via xlwings | Windows |
| `word-mcp` | Word automation | Windows |
| `powerpoint-mcp` | PowerPoint automation | Windows |
| `autocad-mcp` | AutoCAD automation | Windows |
| `revit` | Revit via RevitMCPBridge | Windows |
| `floor-plan-vision` | PDF floor plan extraction | Unix |
| `ai-render-mcp` | AI rendering with Flux | Unix |
| `autonomous-browser` | Stealth browser automation | Windows |

### Aliases

| Alias | Actual Server |
|-------|---------------|
| `voice` | `voice-input-mcp` |
| `excel` | `excel-mcp` |
| `word` | `word-mcp` |
| `powerpoint` | `powerpoint-mcp` |
| `autocad` | `autocad-mcp` |
| `revit2025` | `revit` |
| `revit2026` | `revit` |

## Examples

See the `examples/` folder for complete examples:

- `basic_usage.py` - Getting started
- `excel_automation.py` - Excel operations
- `revit_automation.py` - Revit model manipulation
- `voice_assistant.py` - Voice interactions
- `multi_server.py` - Using multiple servers together

## Architecture

```
weber_sdk/
├── __init__.py          # Main exports
├── client.py            # Weber client class
├── discovery.py         # MCP server discovery
├── exceptions.py        # Custom exceptions
├── transports/
│   ├── base.py          # Transport interface
│   └── stdio.py         # STDIO transport (JSON-RPC)
├── services/
│   ├── base.py          # Base service class
│   ├── generic.py       # Generic service wrapper
│   ├── voice.py         # Voice service
│   ├── excel.py         # Excel service
│   └── revit.py         # Revit service
└── utils/
    └── sync.py          # Sync execution helpers
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy weber_sdk

# Linting
ruff check weber_sdk
```

## Error Handling

```python
from weber_sdk import Weber
from weber_sdk.exceptions import (
    ServerNotFoundError,
    ConnectionError,
    ToolNotFoundError,
    ToolExecutionError,
)

async def safe_example():
    try:
        async with Weber() as w:
            await w.nonexistent.some_tool()
    except ServerNotFoundError as e:
        print(f"Server not found: {e}")
    except ConnectionError as e:
        print(f"Connection failed: {e}")
    except ToolExecutionError as e:
        print(f"Tool failed: {e}")
```

## License

MIT License - See LICENSE file for details.

## Author

Weber Gouin (weberg619@gmail.com)
