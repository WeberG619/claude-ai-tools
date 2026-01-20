# Extended Thinking Guide for Claude Code

## What Is Extended Thinking?

Extended thinking allows Claude to "think harder" about complex problems. Instead of immediately responding, Claude takes time to reason through the problem step by step.

**Available on:** Claude Opus 4.5, Sonnet 4.5, Haiku 4.5 (all Claude 4 models)

## How to Activate

### Method 1: Tab Key (Quick Toggle)
Press `Tab` during a conversation to toggle extended thinking on/off.

### Method 2: Via /config
Run `/config` and set extended thinking preferences.

### Method 3: Explicit Request
Just ask: "Think carefully about this" or "Take your time reasoning through this"

## When to Use Extended Thinking

### IDEAL for:
- Complex Revit API decisions (transaction strategies, multi-element operations)
- Debugging difficult issues with multiple potential causes
- Architecture decisions with trade-offs
- Code that needs to handle many edge cases
- Multi-step BIM workflows (PDF -> extraction -> validation -> Revit)
- Security reviews
- Performance optimization analysis

### SKIP for:
- Simple file reads/writes
- Straightforward questions with obvious answers
- Quick lookups or searches
- Routine operations you've done many times

## Interleaved Thinking (Advanced)

New in late 2025: **Interleaved thinking** allows Claude to think BETWEEN tool calls, not just before.

### Why This Matters for Revit Workflows

Old way:
```
Think -> Call MCP -> Get Result -> Respond
```

New way (interleaved):
```
Think -> Call MCP -> Think about result -> Call another MCP -> Think again -> Respond
```

This is powerful for:
- Analyzing Revit element data, then deciding what to do
- Iterative refinement based on model state
- Complex validation chains

## Token Budgets

You can control how much thinking Claude does:
- **Minimum:** 1,024 tokens
- **Default:** Model decides based on complexity
- **Maximum:** Can be set via API (budget_tokens parameter)

More thinking = better results on complex problems, but costs more.

## Practical Examples

### Example 1: Revit Transaction Strategy
```
User: "I need to place 500 doors, update their parameters, and ensure they're all in the right rooms. Think through the best approach."

[Extended thinking analyzes:]
- Transaction grouping strategies
- Batch vs individual operations
- Error recovery approaches
- Performance implications
- Room boundary checking methods

Result: More robust implementation plan
```

### Example 2: Debugging MCP Issues
```
User: [Tab to enable thinking] "The wall placement keeps failing at coordinate (45.5, 23.2). Help me figure out why."

[Extended thinking considers:]
- Coordinate system issues
- Level associations
- Wall type constraints
- Existing geometry conflicts
- Parameter format issues

Result: Systematic diagnosis instead of guessing
```

### Example 3: PDF to Revit Pipeline
```
User: "Think carefully about how to extract this floor plan and build it in Revit."

[Extended thinking plans:]
- Image analysis approach
- Wall detection algorithms
- Coordinate transformation
- Element type mapping
- Validation checkpoints
- Error handling strategy

Result: Complete pipeline design before execution
```

## Quick Reference

| Shortcut | Action |
|----------|--------|
| `Tab` | Toggle extended thinking |
| `Shift+Tab` | Toggle plan mode |
| "think carefully" | Triggers deeper reasoning |
| "take your time" | Same effect |

## Cost Consideration

Extended thinking uses more tokens. For routine tasks, normal mode is fine. Save extended thinking for problems that actually need it.

## Best Practice

Start complex sessions with: "Let's use extended thinking for this session - I have some tricky problems to solve."

This sets the expectation and Claude will reason more thoroughly throughout.
