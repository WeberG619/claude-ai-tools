# Background Agent Workflows

## What Are Background Agents?

As of Claude Code 2.0.74+, you can run agents and bash commands in the background. This means:
- Long-running tasks don't block your conversation
- You get notified when they complete
- You can continue working on other things

## How to Use Background Agents

### For Long Builds (Revit, C#, etc.)

Ask Claude to run in background:
```
"Build the RevitMCPBridge2026 project in the background"
```

Claude will use:
```
Bash(command="...", run_in_background=true)
```

### For Parallel Research

Ask for multiple explorations:
```
"In the background, explore how error handling works in this codebase"
```

Claude will use:
```
Task(subagent_type="Explore", run_in_background=true)
```

### For Code Reviews While You Work

```
"Review the security of my auth code in the background while I continue"
```

## Checking Background Task Status

Use these commands:
- `/tasks` - List all running background tasks
- `TaskOutput(task_id="...", block=false)` - Check status without waiting
- `TaskOutput(task_id="...", block=true)` - Wait for completion

## Practical Examples for BIM Workflows

### Example 1: Build + Continue Working
```
User: "Build RevitMCPBridge2026 in the background, I want to keep discussing the architecture"

Claude runs build in background, continues conversation, notifies when complete.
```

### Example 2: Parallel Agent Deployment
```
User: "I need security review, tests written, and documentation - run all in parallel"

Claude spawns 3 background agents:
- security-reviewer agent
- test-writer agent
- doc-author agent

All run simultaneously, results collected when ready.
```

### Example 3: Long Revit Operations
```
User: "Extract all walls from the CAD import in the background"

Claude runs the extraction pipeline in background while you can discuss other aspects.
```

## Tips

1. **Use for anything > 30 seconds** - If you expect a task to take a while, run it in background
2. **Combine with parallel execution** - Multiple background tasks can run simultaneously
3. **Check status anytime** - Use `/tasks` to see what's running
4. **Results persist** - Background task outputs are saved to files you can read later

## Keywords to Trigger Background Mode

Say any of these to have me run tasks in background:
- "in the background"
- "while I continue"
- "don't wait for this"
- "run this async"
- "start this and let me know when done"
