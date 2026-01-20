# Context Engineering Quick Reference

## R&D Framework Commands

### REDUCE Context
```bash
# Check current usage
claude /context

# Start with specific MCP only
claude --mcp-config mcp-configs/web-scraping.json

# Prime for specific task
/prime          # General understanding
/prime-feature  # Feature development
/prime-bug      # Bug investigation
```

### DELEGATE Work
```bash
# Sub-agents (keeps main context clean)
/delegate doc-scraper "Scrape API docs from https://..."
/delegate test-runner "Run integration tests"
/delegate code-analyzer "Find performance bottlenecks"

# Background agents (out-of-loop)
/background "Create comprehensive test suite for auth module"
./claude/scripts/run-background.sh "refactor" "Refactor database layer"
```

## Session Management
```bash
# Context bundles auto-tracked to:
agents/context_bundles/bundle_[SESSION_ID].md

# Reload previous session
/loadbundle agents/context_bundles/bundle_20240115_143022.md
```

## Token Savings
- No default MCP: ~24K tokens saved
- Minimal CLAUDE.md: ~20K tokens saved
- Sub-agent delegation: ~40K tokens per task
- Total potential: 80K+ tokens (40% of context)