# Claude Code Reference Guide (On-Demand)
> Load this file only when needed for task routing, Aider strategy, or proactive behaviors.

---

## PROJECT-SPECIFIC AUTO-DETECTION

If current directory is `/mnt/d/RevitMCPBridge2026`:
1. Call `mcp__claude-memory__memory_get_project(project="RevitMCPBridge2026")`
2. Read `/mnt/d/RevitMCPBridge2026/CLAUDE.md`
3. Use revit-developer agent for all code tasks

### Project Templates
- Revit projects: Use revit-developer agent, MSBuild for builds
- Python projects: Use performance-optimizer for profiling
- Web projects: Use ux-reviewer for UI work

---

## SKILL FILES (Domain Expertise)

Skills are reference documents in `/mnt/d/_CLAUDE-TOOLS/Claude_Skills/`.

### Revit/BIM Skills
| Skill File | Purpose |
|------------|---------|
| `revit-model-builder.skill` | Wall patterns, coordinate systems, placement strategies |
| `pdf-to-revit.skill` | Complete PDF extraction to Revit pipeline |
| `bim-quality-validator.skill` | Validation checklists, error recovery |
| `cd-set-assembly.skill` | Construction document set creation |
| `revit-mcp-gotchas.skill` | 29 corrections + pre-flight checklists |

### Workflow Skills
| Skill File | Purpose |
|------------|---------|
| `context-management.skill` | Context pruning, memory patterns |
| `claude-orchestration.skill` | Sub-agent deployment, parallel execution |
| `autonomous-pipeline.skill` | Multi-step operation framework |

### General Skills
| Skill File | Purpose |
|------------|---------|
| `code-review-helper.skill` | Code quality checklists |
| `product-manager.skill` | PRDs, roadmaps, user stories |
| `product-designer.skill` | UX patterns, accessibility |
| `marketing-writer.skill` | Copy formulas, channel guidelines |

Usage: `Read /mnt/d/_CLAUDE-TOOLS/Claude_Skills/<skill-name>.skill`

---

## CONTEXT WINDOW OPTIMIZATION

### The 39% Rule
Memory + context editing = 39% performance improvement.

### Pruning Triggers
- After large tool results (>500 lines)
- After completing a task batch
- After 10+ tool calls
- When changing topics

### What to Keep vs Prune
| Keep | Prune |
|------|-------|
| Current task requirements | Old tool results |
| Recent corrections (last 5) | Intermediate search results |
| Active project context | Resolved error messages |
| Unfinished work items | Completed task details |

---

## CONFIGURATION FILES
- `~/.claude/settings.json` — User-level settings with hooks and permissions
- `~/.claude/agents/*.md` — Custom agent definitions
- `/mnt/d/.claude/settings.json` — Project-level settings for /mnt/d
- `/mnt/d/RevitMCPBridge2026/.claude/settings.json` — Auto-loads revit-developer agent
- `/mnt/d/_CLAUDE-TOOLS/Claude_Skills/*.skill` — Domain expertise files

---

## INTELLIGENT TASK ROUTING

### Decision Matrix

| Task Type | Tool/Agent | Trigger Keywords |
|-----------|------------|------------------|
| Code Review | `Task(code-reviewer)` | "review", "check this code" |
| Security Audit | `Task(security-reviewer)` | "security", "vulnerabilities" |
| Write Tests | `Task(test-writer)` | "write tests", "add coverage" |
| Documentation | `Task(doc-author)` | "document", "add comments" |
| Performance | `Task(performance-optimizer)` | "slow", "optimize", "profile" |
| Simplify Code | `Task(code-simplifier)` | "simplify", "refactor" |
| Architecture | `Task(tech-lead)` | "design", "architecture" |
| UX Review | `Task(ux-reviewer)` | "UI", "UX", "accessibility" |
| Revit Dev | `Task(revit-developer)` | "Revit", "add-in", "BIM" |
| Codebase Exploration | `Task(Explore)` | "find", "where is", "how does X work" |
| Multi-file Edits | Aider MCP | 3+ files need changes |
| Quick Single Edits | Direct Edit tool | 1-2 files, simple changes |

### Automatic Sub-Agent Deployment

Deploy sub-agents automatically when:
1. **After writing 50+ lines of code** — spawn code-reviewer (+ security-reviewer if security-sensitive)
2. **After completing a feature** — spawn test-writer (+ doc-author if public API changed)
3. **When user reports performance issues** — spawn performance-optimizer
4. **When starting on a new codebase** — spawn Explore agent
5. **For Revit tasks** — always use revit-developer agent

### Parallel Agent Execution
When user requests multiple independent things, run agents IN PARALLEL in ONE message.

---

## AIDER MCP STRATEGY

3 Aider instances available:
- `mcp__aider-mcp-server-quasar__aider_ai_code` — Quasar model (best for C#)
- `mcp__aider-mcp-server-ollama__aider_ai_code` — Ollama models (good for Python)
- `mcp__aider-mcp-server-llama4__aider_ai_code` — Llama4 model (fast for JS/TS)

### When to Use Aider vs Direct Edit

| Scenario | Aider | Direct Edit |
|----------|-------|-------------|
| 1-2 files | No | Yes |
| 3+ files / refactoring | Yes | No |
| Complex multi-step | Yes | No |
| Simple text replacement | No | Yes |
| Bug fix in single function | No | Yes |

---

## PROACTIVE BEHAVIORS

### System State Triggers
- **Revit open + no recent saves:** Suggest checking model status
- **Uncommitted git changes 30+ min:** Offer to commit
- **Memory > 80%:** Warn about resource pressure
- **Urgent emails:** Offer to summarize

### Work Pattern Triggers
- **Extended time on one task:** Offer to break down or parallelize
- **Switching between same files:** Offer side-by-side or summary
- **Similar to recent task:** Reference previous approach

### Timing
- Offer at natural breaks (after task completion, commits, session start)
- Don't interrupt mid-task
- Limit to 1 proactive suggestion per break

---

## WORKFLOW CAPTURE SYSTEM

### End-of-Session Capture
1. Scan session for sequential action patterns (3+ steps)
2. Compare against existing `workflow-candidate` memories
3. Store new candidates with tag `workflow-candidate`
4. Draft skill file when pattern hits 2+ occurrences
5. On approval, create skill in `~/.claude/skills/` and register

### Detection Criteria
- 3+ sequential steps in a specific order
- Cross-tool sequences (Revit + email, extract + transform + load)
- Manual repetition within a single session

---

## HOOK ERROR LOG

All hook errors logged to: `/mnt/d/_CLAUDE-TOOLS/logs/hooks.log`
