# Pipeline Executor

Autonomous workflow runner with checkpoint gates for Claude Code workflows.

## Quick Start

```bash
# List available pipelines
python executor.py --list

# Run a pipeline in dry-run mode (preview)
python executor.py cd-set --dry-run

# Run a pipeline with auto-approval
python executor.py cd-set --auto-approve

# Resume a pipeline from saved state
python executor.py cd-set --resume

# Run interactively (pause at checkpoints)
python executor.py cd-set
```

## Features

- **Pipeline JSON Parsing**: Loads and executes `.pipeline.json` files
- **Checkpoint Gates**: Pauses for human approval at critical points
- **State Persistence**: Saves progress to resume interrupted workflows
- **Memory Integration**: Surfaces relevant corrections before risky operations
- **Dry-Run Mode**: Preview execution without making changes
- **Auto-Approve Mode**: Skip checkpoints for trusted operations
- **CLI Interface**: User-friendly command-line interface with colored output

## Pipeline JSON Schema

```json
{
  "id": "unique-pipeline-id",
  "name": "Human Readable Name",
  "version": "1.0.0",
  "description": "What this pipeline does",

  "prerequisites": {
    "revit_running": true,
    "required_tools": ["RevitMCPBridge"]
  },

  "phases": [
    {
      "id": "P1",
      "name": "Phase Name",
      "description": "What this phase does",
      "steps": [
        {
          "id": "P1.1",
          "action": "action_name",
          "method": "mcpMethodName",
          "params": {},
          "store_result": "variable_name"
        }
      ],
      "checkpoint": {
        "name": "Checkpoint Name",
        "requires_approval": true,
        "user_prompt": "Message shown to user"
      }
    }
  ],

  "on_success": {
    "memory": { "action": "store", "type": "outcome" },
    "voice": { "message": "Pipeline complete" }
  },

  "corrections_to_apply": [
    {"id": 123, "rule": "Rule description"}
  ]
}
```

## Checkpoint Types

| Type | Purpose | When to Use |
|------|---------|-------------|
| **Confirmation** | Verify understanding before starting | Beginning of workflows |
| **Validation** | Verify results match expectations | After significant changes |
| **Decision** | Choose between approaches | Architecture decisions |
| **Safety** | Prevent irreversible changes | Before deletions |

## State Files

State is saved to `pipelines/state/<pipeline-id>.state.json` containing:
- Current phase and step
- Stored variable results
- Checkpoints passed
- Errors encountered

## Available Pipelines

1. **cd-set** - Construction Document Set Generation
2. **markup-to-model** - PDF Markup to Revit Model Changes
3. **pdf-to-revit** - PDF Floor Plan to Revit Model

## Testing

```bash
python test_executor.py
```

## Integration with Claude Code

The executor is designed to be called by Claude Code during conversations:

```python
# In Claude's workflow
import subprocess
result = subprocess.run([
    "python3", "/mnt/d/_CLAUDE-TOOLS/pipelines/executor.py",
    "cd-set", "--auto-approve"
], capture_output=True, text=True)
```

Or via the `/pipeline` command (when implemented).

---

*Created by Ralph Loop - 2026-01-11*
