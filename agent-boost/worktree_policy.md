# Worktree Isolation Policy

When sub-agents perform risky or multi-file operations in git repos,
use git worktree isolation to protect the main working tree.

## When to Use Worktree

- Modifying 3+ files in a single task
- Risky refactoring (rename, restructure, rewrite)
- Experimental approach (might need to discard)
- Concurrent agent work (two agents editing same repo)
- Any operation the user flags as "try it, but I might want to undo"

## When NOT to Use Worktree

- Single-file edits
- Read-only research tasks
- Non-git directories
- Trivial changes (typos, config tweaks)
- Operations outside of code repos

## Pattern

```bash
# Create isolated worktree
git worktree add /tmp/worktree-<task-id> -b task/<task-id>

# Work in the worktree
cd /tmp/worktree-<task-id>
# ... make changes ...

# On success: merge back
git checkout main
git merge task/<task-id>
git worktree remove /tmp/worktree-<task-id>

# On failure: discard
git worktree remove --force /tmp/worktree-<task-id>
git branch -D task/<task-id>
```

## Claude Code Integration

When using the Task tool with `isolation: "worktree"`:
- Claude Code creates the worktree automatically
- The sub-agent works on an isolated copy
- If no changes: worktree is auto-cleaned
- If changes: worktree path and branch are returned in result

Prefer `isolation: "worktree"` in the Task tool call over manual git commands.
