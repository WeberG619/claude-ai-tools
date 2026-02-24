# Cognitive Core

The thinking layer for Weber's Claude Code system. Provides autonomous reasoning, self-evaluation, goal decomposition, learning compilation, task routing, and cross-session reflection.

## Modules

| Module | Purpose | Key Class |
|--------|---------|-----------|
| `core.py` | Main orchestrator, OODA loop | `CognitiveCore` |
| `evaluator.py` | Self-evaluation after actions | `Evaluator` |
| `decomposer.py` | Goal → task tree with dependencies | `GoalDecomposer` |
| `compiler.py` | Corrections → enforced rules | `LearningCompiler` |
| `meta_router.py` | Task → framework/model routing | `MetaRouter` |
| `reflector.py` | Session reflection, goal tracking | `SessionReflector` |
| `dispatcher.py` | Event → think → route → queue bridge | `CognitiveDispatcher` |
| `watcher.py` | File/system event monitor, daemon | `CognitiveWatcher` |

## Quick Usage

```python
from core import CognitiveCore
brain = CognitiveCore(project="ResidentialA")

# Think through a goal
result = brain.think("Set up CD sheets for residential project")

# Self-evaluate
ev = brain.evaluate(action, result, goal)

# Route a task
rd = brain.route("Fix wall join at B-3")

# End-of-session
reflection = brain.reflect(session_data)

# Compile learnings
rules = brain.compile()
```

## CLI

```bash
python core.py think "Build CD sheet set" --create-tasks
python core.py evaluate --action "..." --result "..." --goal "..."
python core.py compile
python core.py status
python core.py goals
python core.py goal "Complete CD set for ResidentialA"
```

## Event System

```python
from cognitive_core import CognitiveDispatcher, CognitiveWatcher

# Dispatch a single event through the thinking layer
dispatcher = CognitiveDispatcher(project="ResidentialA")
result = dispatcher.dispatch({"type": "build_failed", "data": {"error": "..."}})

# Run the watcher daemon (checks files, system state, scheduled events)
watcher = CognitiveWatcher()
watcher.run_daemon(interval=30)
```

```bash
# Watcher CLI
python watcher.py --daemon              # Run as background daemon
python watcher.py --check               # One-shot check cycle
python watcher.py --watch /path --patterns "*.cs" --label "My Code"
python watcher.py --stats               # Show dispatch statistics
```

## Data

All data stored in `cognitive.db` (SQLite). Tables: evaluations, calibration_log, decompositions, compiled_rules, compilation_log, routing_decisions, routing_outcomes, session_reflections, persistent_goals, goal_progress_log, dispatch_log, event_patterns.

## Integration Points

- **strong_agent.md**: Phase 4.5 Self-Evaluate added
- **Task board**: `decomposer.create_board_tasks()` creates board entries
- **Memory DB**: `compiler.compile()` reads corrections from memories.db
- **Skill**: `/think` skill invokes the cognitive core
- **Autonomous agent**: `dispatcher._queue_in_agent_db()` queues tasks for background execution
- **System bridge**: `watcher.check_system_state()` reads live_state.json for Revit/Bluebeam/memory events
- **Compiled rules**: `compiled_rules.md` auto-generated, 37 rules from 63 corrections
