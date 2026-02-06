# Claude Code Reference Guide (On-Demand)
> Load this file only when needed. NOT auto-injected into sessions.

## MCP SERVER CAPABILITIES

### Active MCP Servers

| Server | Purpose | When to Use |
|--------|---------|-------------|
| **claude-memory** | Persistent memory | Always - every session |
| **floor-plan-vision** | PDF floor plan extraction | When processing architectural PDFs |
| **playwright** | Browser automation | Web scraping, testing web apps |
| **sqlite-server** | Database operations | Data storage, queries |
| **Aider (x3)** | AI code editing | Multi-file refactoring |
| **excel-mcp** | Excel automation | Spreadsheet operations |
| **word-mcp** | Word doc automation | Document creation |
| **powerpoint-mcp** | PowerPoint automation | Presentation creation |
| **youtube-mcp** | YouTube metadata | Video info, transcripts |
| **financial-mcp** | Investment research | Stock quotes, analysis |
| **visual-memory** | Screenshot capture | Visual search |
| **bluebeam** | Bluebeam Revu | PDF markup |
| **voice** | Text-to-speech | Summaries |

### Floor Plan Vision Workflow
```
1. mcp__floor-plan-vision__get_pdf_info - Check PDF details
2. mcp__floor-plan-vision__analyze_floor_plan - Full analysis
3. mcp__floor-plan-vision__build_revit_spec - Generate Revit spec
```

### Playwright for Web Tasks
```
1. mcp__playwright__browser_navigate - Go to URL
2. mcp__playwright__browser_snapshot - Capture state
3. mcp__playwright__browser_click/type - Interact
```

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
- `~/.claude/settings.json` - User-level settings with hooks and permissions
- `~/.claude/agents/*.md` - Custom agent definitions
- `/mnt/d/.claude/settings.json` - Project-level settings for /mnt/d
- `/mnt/d/RevitMCPBridge2026/.claude/settings.json` - Auto-loads revit-developer agent
- `/mnt/d/_CLAUDE-TOOLS/Claude_Skills/*.skill` - Domain expertise files

---

## INTELLIGENT TASK ROUTING

### Decision Matrix - When to Use What

| Task Type | Tool/Agent | Trigger Keywords |
|-----------|------------|------------------|
| **Code Review** | `Task(code-reviewer)` | "review", "check this code", "is this good" |
| **Security Audit** | `Task(security-reviewer)` | "security", "vulnerabilities", "is this safe" |
| **Write Tests** | `Task(test-writer)` | "write tests", "add coverage", "test this" |
| **Documentation** | `Task(doc-author)` | "document", "add comments", "explain this code" |
| **Performance** | `Task(performance-optimizer)` | "slow", "optimize", "speed up", "profile" |
| **Simplify Code** | `Task(code-simplifier)` | "simplify", "refactor", "clean up" |
| **Architecture** | `Task(tech-lead)` | "design", "architecture", "how should I structure" |
| **UX Review** | `Task(ux-reviewer)` | "UI", "UX", "user interface", "accessibility" |
| **Revit Development** | `Task(revit-developer)` | "Revit", "add-in", "BIM", "Autodesk" |
| **Codebase Exploration** | `Task(Explore)` | "find", "where is", "how does X work" |
| **Multi-file Edits** | Aider MCP | 3+ files need changes, refactoring across codebase |
| **Quick Single Edits** | Direct Edit tool | 1-2 files, simple changes |

### SUB-AGENT COMMON SENSE INJECTION

**Every sub-agent prompt MUST include this line:**
```
Before starting, read and internalize /mnt/d/_CLAUDE-TOOLS/agent-common-sense/kernel.md —
apply its decision loop (classify → check → simulate) to every action.
```

### AUTOMATIC SUB-AGENT DEPLOYMENT

**Deploy sub-agents automatically when:**

1. **After Writing Significant Code (50+ lines)**
   - Spawn code-reviewer agent to check quality
   - If security-sensitive: also spawn security-reviewer

2. **After Completing a Feature**
   - Spawn test-writer to generate tests
   - Spawn doc-author if public API changed

3. **When User Reports Performance Issues**
   - Spawn performance-optimizer to analyze
   - Spawn Explore agent to find bottlenecks

4. **When Starting Work on New Codebase**
   - Spawn Explore agent to understand structure
   - Spawn tech-lead for architectural overview

5. **For Revit Development Tasks**
   - Always use revit-developer agent
   - Run builds through Bash after code changes

### PARALLEL AGENT EXECUTION

When user requests multiple independent things, run agents IN PARALLEL:
```
# Execute as ONE message with THREE Task tool calls:
Task(security-reviewer): "Review auth code at /path/to/auth"
Task(test-writer): "Write tests for API at /path/to/api"
Task(doc-author): "Document database schema at /path/to/schema"
```
NEVER do these sequentially when they can be parallel.

---

## AIDER MCP STRATEGY

3 Aider instances available:
- `mcp__aider-mcp-server-quasar__aider_ai_code` - Quasar model (best for C#)
- `mcp__aider-mcp-server-ollama__aider_ai_code` - Ollama models (good for Python)
- `mcp__aider-mcp-server-llama4__aider_ai_code` - Llama4 model (fast for JS/TS)

### When to Use Aider vs Direct Edit

| Scenario | Use Aider | Use Direct Edit |
|----------|-----------|-----------------|
| Change 1-2 files | No | Yes |
| Change 3+ files | Yes | No |
| Refactor across codebase | Yes | No |
| Complex multi-step changes | Yes | No |
| Simple text replacement | No | Yes |
| Adding new feature spanning files | Yes | No |
| Bug fix in single function | No | Yes |

### Parallel Aider Usage

When refactoring affects multiple independent modules:
```
mcp__aider-mcp-server-quasar__aider_ai_code: Refactor Module A
mcp__aider-mcp-server-ollama__aider_ai_code: Refactor Module B
mcp__aider-mcp-server-llama4__aider_ai_code: Refactor Module C
```

---

## PROACTIVE BEHAVIORS

### Auto-Trigger Conditions

**When Revit is open (detected via system bridge):**
- Load RevitMCPBridge2026 project context automatically
- Pre-fetch Revit API documentation if needed
- Suggest Revit-related actions based on current view

**When Bluebeam is open with a PDF:**
- Offer to extract floor plan data using floor-plan-vision MCP
- Suggest processing workflows

**When VS Code shows a specific project:**
- Auto-load that project's CLAUDE.md if it exists
- Recall project-specific memories

**When clipboard contains code:**
- Proactively offer to analyze/review it

**When system memory > 80%:**
- Warn user about resource pressure
- Suggest closing unused applications

### End-of-Task Automation

After completing any significant task:
1. Store outcome in memory
2. If code was written: spawn code-reviewer
3. If feature complete: spawn test-writer
4. Update todo list
5. Suggest next logical step

---

## MEMORY MANAGEMENT

### Store Corrections (CRITICAL)
When user corrects you:
```python
mcp__claude-memory__memory_store_correction(
    what_claude_said="What you incorrectly stated or did",
    what_was_wrong="Why it was wrong",
    correct_approach="The right way to handle this",
    project="project-name",
    category="code|architecture|workflow|preferences"
)
```

### Continuous Memory Storage
Store after:
- Completing significant actions
- Making important decisions
- Encountering and solving errors
- Learning user preferences
- Natural breakpoints in work

### Session Summarization
At end of significant sessions:
```python
mcp__claude-memory__memory_summarize_session(
    project="project-name",
    summary="Brief overall summary",
    key_outcomes=["Outcome 1", "Outcome 2"],
    decisions_made=["Decision 1"],
    problems_solved=["Problem 1 and solution"],
    open_questions=["Unresolved question"],
    next_steps=["Next action 1", "Next action 2"]
)
```

### Memory Database Backups
Backups are automated by the claude-memory-server:
- **Hourly**: `/mnt/d/_CLAUDE-TOOLS/claude-memory-server/backups/hourly/`
- **Daily**: `/mnt/d/_CLAUDE-TOOLS/claude-memory-server/backups/daily/`
- **Weekly**: `/mnt/d/_CLAUDE-TOOLS/claude-memory-server/backups/weekly/`
- **Source DB**: `/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db`

To verify backups are current: check the latest file timestamps in the backup dirs.

---

## COMMON SENSE ENGINE

> **Location:** `/mnt/d/_CLAUDE-TOOLS/agent-common-sense/`
> **Kernel:** `kernel.md` (loaded at startup)
> **Seeds:** `seeds.json` (15 universal corrections)

### The Loop

| Trigger | Action | Tool |
|---------|--------|------|
| Before ANY significant action | Run decision loop silently | (internal — from kernel.md) |
| User corrects you | Store correction | `memory_store_correction` |
| Before destructive/shared action | Check past corrections | `memory_check_before_action` |
| Correction helped | Reinforce it | `memory_correction_helped` |
| Caught yourself before mistake | Log it | `memory_log_avoided_mistake` |
| Succeeded at something new | Store as known-good | `memory_store` with tag `known-good` |
| Weekly / on request | Find patterns | `memory_synthesize_patterns` |

### CLI Maintenance
```bash
python3 /mnt/d/_CLAUDE-TOOLS/agent-common-sense/sense.py check --action "description"
python3 /mnt/d/_CLAUDE-TOOLS/agent-common-sense/sense.py seed
python3 /mnt/d/_CLAUDE-TOOLS/agent-common-sense/sense.py synthesize
```

---

## WORKFLOW CAPTURE SYSTEM (ACTIVE)

### End-of-Session Capture
At the end of every significant session:

1. **SCAN** session for sequential action patterns (3+ steps)
2. **COMPARE** against existing `workflow-candidate` memories
3. **STORE** new candidates with tag `workflow-candidate`
4. **DRAFT** skill file when pattern hits 2+ occurrences
5. On approval, create skill in `~/.claude/skills/` and register

### Detection Criteria
- 3+ sequential steps in a specific order
- Cross-tool sequences (Revit + email, extract + transform + load)
- Manual repetition within a single session

---

## VOICE SUMMARY (MANDATORY)

After completing ANY significant task:
```
mcp__voice__speak(text="Your summary here", voice="andrew")
```
Include: what was done, issues found, recommendations, next steps.

---

## HOOK ERROR LOG

All hook errors are logged to: `/mnt/d/_CLAUDE-TOOLS/logs/hooks.log`
Check this file when hooks seem to not be working correctly.
