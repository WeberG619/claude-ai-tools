# Architecture Diagram Notes

## Overview

The Mermaid diagram in `step-5-architecture.mermaid` shows the complete 5-phase Autonomy Engine architecture with the correction flywheel loop.

## Phase Breakdown

### Phase 1: Goals (Blue - #4A90D9)
- User intent enters as a high-level goal
- GoalEngine decomposes into sub-goals with parent-child hierarchy
- Sub-goal progress rolls up automatically to parent goals
- Dependencies between goals prevent premature execution

### Phase 2: Planner (Purple - #7B68EE)
- Goals get decomposed into executable plan steps
- Template matching selects from 4 built-in patterns (build-feature, pdf-to-revit, client-deliverable, research-topic)
- MECE validation ensures steps are mutually exclusive and collectively exhaustive
- Complex steps auto-decompose into sub-plans recursively

### Phase 3: Alignment (Red - #E74C3C)
- **This is the differentiator.** Before any agent executes, AlignmentCore compiles a domain-aware prompt prefix.
- Domain Detector analyzes the task description and routes to the correct correction packs
- 8 domain packs: BIM, git, desktop, filesystem, data, deployment, execution, network, scope, identity
- Corrections + Common Sense Kernel + Strong Agent Framework get merged into a single compiled prefix
- The prefix is injected into the agent's prompt before execution
- Token budget management trims content to stay within limits

### Phase 4: Coordinator (Green - #2ECC71)
- Tracks agent sessions within workflows
- Resource locking prevents conflicts (e.g., two agents modifying same Revit model)
- Shared state allows sequential agents to pass context
- Handoff validation ensures clean transitions between agents
- Stale session cleanup prevents zombie locks

### Phase 5: Execution (Orange - #F39C12)
- Agent executes with compiled alignment prefix
- On success: progress updates cascade to parent goals
- On failure: correction is stored, domain-tagged, and available for future agents
- This is where the flywheel closes — failures become future intelligence

## The Correction Flywheel (Key Loop)

```
Agent executes task
    ↓
Mistake detected (user correction or self-detection)
    ↓
Correction stored with:
  - what_went_wrong
  - correct_approach
  - detection pattern
  - domain tag
  - severity level
    ↓
Future task in same domain triggers alignment compilation
    ↓
Domain detector routes to relevant correction pack
    ↓
Correction injected into agent's prompt prefix
    ↓
Agent avoids the mistake
    ↓
Outcome tracking measures if correction helped
    ↓
High-signal corrections get prioritized
Low-signal corrections get deprioritized
```

## Goal Cascade Flow

```
Top Goal: "Ship v2.0" (0%)
  ├── Sub-Goal 1: "Build API" (active, 0%)
  │     completed → progress = 100%
  │     rollup → parent progress = 33%
  ├── Sub-Goal 2: "Write Tests" (blocked by 1)
  │     unblocked → active → completed → 100%
  │     rollup → parent progress = 66%
  └── Sub-Goal 3: "Deploy" (blocked by 2)
        unblocked → active → completed → 100%
        rollup → parent progress = 100%
        parent auto-completes
```

## Domain-Aware Injection Flow

```
Task: "Create walls from PDF floor plan"
    ↓
Domain Detector scores keywords:
  - "walls" → bim (score: 3)
  - "PDF" → bim (score: 1)
  - "floor plan" → bim (score: 2)
  → Domain = "bim" (highest score)
    ↓
Load BIM corrections from domains/bim.json
Load universal corrections from kernel.md
Load strong agent framework
    ↓
Compile into prompt prefix (budget: ~4000 tokens)
  - Trim corrections if over budget
  - Trim kernel if still over
  - Trim strong agent if still over
    ↓
Inject prefix into agent prompt
Agent executes with full BIM domain knowledge
```

## Color Coding

| Phase | Color | Hex |
|---|---|---|
| Goals | Blue | #4A90D9 |
| Planner | Purple | #7B68EE |
| Alignment | Red | #E74C3C |
| Coordinator | Green | #2ECC71 |
| Execution | Orange | #F39C12 |

## Embedding in README

The diagram is designed to be embedded directly in GitHub README.md files using:

````markdown
```mermaid
[paste contents of step-5-architecture.mermaid]
```
````

GitHub natively renders Mermaid diagrams. The dark theme variant looks best on GitHub's dark mode. For light mode, remove the `%%{init}%%` theme directive.
