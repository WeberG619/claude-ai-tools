# Agent Team - Coding War-Room

A multi-agent voice collaboration system where AI agents debate, build, and validate code together.

## Quick Start

```bash
# Test all agent voices first
python team.py --test-voices

# Run a quick demo
python team.py --demo

# Run a real task (backstage mode - fast, summary only)
python team.py "Build a REST API for user management"

# Run in live mode (all agents speak)
python team.py --live "Create authentication middleware"
```

## The Team

| Agent | Voice | Role |
|-------|-------|------|
| **Planner** | andrew | Breaks down tasks, defines goals |
| **Researcher** | guy | Gathers facts, explores codebase |
| **Builder** | adam | Writes code, executes tools |
| **Critic** | davis | Validates, finds risks |
| **Narrator** | jenny | Summarizes for the user |

## Modes

### Backstage (Default)
- Agents debate internally (fast, text-only)
- Only the Narrator speaks the final summary
- Best for speed and not being annoying

### Live
- Every agent speaks their turn out loud
- Like sitting in on a real team meeting
- More immersive but slower

## Architecture

```
agent-team/
├── team.py              # Main CLI entry point
├── director.py          # Orchestrator - manages turn-taking
├── agent_prompts.py     # System prompts for each agent
├── voice_registry.json  # Agent → voice mapping
├── turn_state.json      # Current session state
├── test_voices.py       # Voice testing utility
├── protocols/
│   ├── backstage.py     # Fast internal + voice summary
│   └── live_meeting.py  # All agents speak
└── logs/                # Session history
```

## Rules Enforced

1. **One Mic Rule**: Only one agent speaks at a time
2. **Timeboxing**: Max 3-4 sentences per turn
3. **Structured Handoffs**: "Builder, implement X" / "Critic, validate"
4. **Stop Conditions**: Consensus, max turns, or user approval needed

## Integration with Claude Code

This system is designed to work with Claude Code's Task tool:

```python
# From Claude Code, you can spawn agents:
Task(code-reviewer): "Review the authentication module"
Task(test-writer): "Write tests for the API"
```

The Agent Team coordinates multiple specialists working together.

## Voice Configuration

Voices are Microsoft Edge TTS (free, unlimited):
- andrew, adam, guy, davis (male)
- jenny, aria, amanda, michelle (female)

Edit `voice_registry.json` to customize agent voices.
