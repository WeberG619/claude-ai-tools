# Delegate - Strong Agent Deployment

## Purpose
Deploy sub-agents with full context injection and structured execution methodology.
Every agent launched through this skill operates at maximum capability.

## Pre-Launch Protocol (Primary Agent MUST do this)

Before calling Task tool, the primary agent MUST:

1. **Load the strong agent framework:**
   ```
   Read /mnt/d/_CLAUDE-TOOLS/agent-boost/strong_agent.md
   ```

2. **Load memory context for the task:**
   ```
   mcp__claude-memory__memory_smart_recall(query="<task topic>", current_context="<what we're doing>")
   mcp__claude-memory__memory_check_before_action(action_description="<what the agent will do>")
   ```

3. **Build the prompt** using this template:
   ```
   [STRONG AGENT FRAMEWORK - paste from strong_agent.md]

   [CORRECTIONS - paste any relevant memory corrections]

   [CONVERSATION CONTEXT - summarize what the user and I discussed that's relevant]

   [TASK - the specific task for this agent]
   ```

4. **Set parameters:**
   - `model`: "opus" (always — never downgrade agents)
   - `max_turns`: 25 minimum for research, 30+ for implementation tasks
   - `run_in_background`: true for long tasks, false for blocking needs

## Agent Type Selection

| Task Type | Agent Type | Why |
|-----------|-----------|-----|
| Research / exploration | `general-purpose` | Broadest tool access |
| Code quality check | `code-reviewer` | Domain-specific prompting |
| Write tests | `test-writer` | Test pattern knowledge |
| Security audit | `security-reviewer` | Vulnerability expertise |
| Architecture decisions | `tech-lead` | Strategic thinking |
| Performance issues | `performance-optimizer` | Profiling methodology |
| Documentation | `doc-author` | Doc structure expertise |
| Simple code cleanup | `code-simplifier` | Focused refactoring |
| UI/UX feedback | `ux-reviewer` | Design + accessibility |
| Quick file search | `Explore` | Fast, lightweight |
| Implementation planning | `Plan` | Architecture-first |

## Multi-Agent Patterns

### Parallel Research (launch in same message)
```
Agent A: "Research approach 1 for <problem>"
Agent B: "Research approach 2 for <problem>"
→ Synthesize both results
```

### Pipeline (sequential)
```
Agent 1 (general-purpose): Research and understand the problem
→ Feed results to:
Agent 2 (Plan): Design the implementation
→ Primary agent implements
→ Agent 3 (code-reviewer): Review the implementation
→ Agent 4 (test-writer): Write tests
```

### Follow-up (resume)
```
Agent returns partial results
→ Resume same agent with: resume: "<agent_id>"
→ Agent continues with full prior context
```

## Post-Agent Protocol

After agent returns:
1. **Summarize results** to user concisely
2. **Store important findings** in memory if agent didn't
3. **Suggest next steps** proactively
4. **Voice summary** for significant completions
