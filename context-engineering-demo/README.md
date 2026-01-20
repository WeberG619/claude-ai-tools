# Claude Code Context Engineering Implementation

Based on the R&D framework: **Reduce** and **Delegate** context to maximize agent performance.

## Quick Start

1. **Check current context usage:**
   ```bash
   claude /context
   ```

2. **Load MCP servers on-demand:**
   ```bash
   claude --mcp-config mcp-configs/web-scraping.json
   ```

## Key Techniques Implemented

### 1. Minimal CLAUDE.md (Reduce)
- Only universal essentials (~15 lines)
- No project-specific details
- Located at: `CLAUDE.md`

### 2. Context Priming Commands (Reduce)
Instead of large memory files, use focused priming:

```bash
# General understanding
claude
> /prime

# Feature development
claude
> /prime-feature

# Bug investigation
claude
> /prime-bug
```

### 3. Context Bundle Tracking (Reduce)
Automatically tracks agent work for session replay:
- Hook: `claude/hooks/tool-use-hook.sh`
- Bundles saved to: `agents/context_bundles/`
- Reload with: `/loadbundle <path>`

### 4. Specialized Sub-Agents (Delegate)
Delegated focused work to specialized agents:
- `doc-scraper` - Documentation fetching
- `test-runner` - Test execution and analysis
- `code-analyzer` - Deep code analysis

Usage: `/delegate <agent-type> "<task>"`

### 5. Background Agents (Delegate)
Run long tasks out-of-loop:

```bash
# Using command
claude
> /background "Create API client for service X"

# Using script
./claude/scripts/run-background.sh "task-name" "prompt"
```

### 6. On-Demand MCP Servers (Reduce)
Load only what you need:

```bash
# Web scraping tasks
claude --mcp-config mcp-configs/web-scraping.json

# Database tasks
claude --mcp-config mcp-configs/database.json
```

## Workflow Examples

### Feature Development
```bash
# 1. Start clean
claude

# 2. Prime for feature work
> /prime-feature

# 3. Delegate research
> /delegate doc-scraper "Get latest React hooks documentation"

# 4. Implement feature
> implement user authentication with React hooks
```

### Bug Investigation
```bash
# 1. Start with minimal context
claude --mcp-config mcp-configs/database.json

# 2. Prime for debugging
> /prime-bug

# 3. Run tests in background
> /background "Run full test suite and analyze failures"

# 4. Focus on specific issue
> investigate database connection timeout errors
```

### Multi-Agent Workflow
```bash
# 1. Main agent delegates planning
claude
> /background "Create implementation plan for payment system"

# 2. While planning runs, analyze existing code
> /delegate code-analyzer "Analyze existing payment modules"

# 3. Check background results
> read agents/background/plan_*.md

# 4. Execute plan with focused context
> implement payment gateway integration
```

## Best Practices

1. **Start Clean**: Don't load MCP servers by default
2. **Prime Purposefully**: Use specific priming for task type
3. **Delegate Early**: Move independent work to sub-agents
4. **Track Context**: Monitor with `/context` frequently
5. **Bundle Sessions**: Use hooks to enable work continuity

## Measuring Success

- Context usage < 20% at start
- Specialized agents complete focused tasks
- Background agents handle long-running work
- Context bundles enable seamless handoffs

## Advanced Tips

1. **Chain Agents**: Background agent can spawn sub-agents
2. **Parallel Work**: Run multiple background agents
3. **Custom Priming**: Create task-specific prime commands
4. **Hook Extensions**: Add custom tracking to hooks

## Directory Structure
```
context-engineering-demo/
├── CLAUDE.md                 # Minimal memory file
├── claude/
│   ├── commands/            # Priming and utility commands
│   ├── hooks/              # Context tracking hooks
│   └── scripts/            # Background agent runners
├── agents/
│   ├── background/         # Background task outputs
│   ├── context_bundles/    # Session tracking
│   └── *.yaml             # Sub-agent definitions
└── mcp-configs/            # On-demand MCP configs
```

## Next Steps

1. Copy this structure to your projects
2. Customize prime commands for your workflows
3. Create specialized sub-agents for repetitive tasks
4. Set up team-shared MCP configurations
5. Build agent experts for domain-specific work

Remember: **A focused engineer is a performant engineer, and a focused agent is a performant agent.**