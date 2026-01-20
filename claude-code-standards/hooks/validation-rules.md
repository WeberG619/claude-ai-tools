# Hook Validation Rules

## Overview

Hooks enforce coding standards automatically by intercepting Claude Code's tool usage. They run with full user permissions, so security and correctness are critical.

## Hook Events

### PreToolUse
Runs before tool execution - ideal for validation and blocking dangerous operations.

### PostToolUse  
Runs after successful tool completion - useful for logging and notifications.

### Notification
Triggered on Claude Code notifications - can intercept and modify messages.

### Stop
Runs when Claude Code finishes responding - good for cleanup tasks.

## Common Validation Rules

### 1. Command Safety
Block dangerous commands before execution:

```python
DANGEROUS_PATTERNS = [
    (r'\brm\s+-rf\s+/', "Dangerous rm -rf on root detected"),
    (r'\bsudo\s+rm', "Sudo rm commands are not allowed"),
    (r'\b>\s*/dev/sd[a-z]', "Direct disk write detected"),
    (r'\bdd\s+.*of=/dev/', "Dangerous dd command detected")
]
```

### 2. Path Protection
Protect sensitive directories:

```python
PROTECTED_PATHS = [
    '/etc',
    '/sys',
    '/boot',
    '~/.ssh',
    '~/.aws'
]
```

### 3. Best Practice Enforcement
Enforce tool usage standards:

```python
TOOL_RULES = [
    (r'\bgrep\b(?!.*\|)', "Use 'rg' instead of grep"),
    (r'\bfind\s+.*-name', "Use Glob tool instead of find"),
    (r'\bcat\s+', "Use Read tool instead of cat"),
    (r'\bls\s+', "Use LS tool instead of ls command")
]
```

### 4. Git Safety
Prevent accidental commits:

```python
GIT_RULES = [
    (r'git\s+push\s+--force', "Force push requires explicit approval"),
    (r'git\s+reset\s+--hard', "Hard reset requires confirmation"),
    (r'git\s+clean\s+-fd', "Git clean requires explicit approval")
]
```

## Implementation Strategy

### 1. Start Conservative
Begin with logging only, then gradually add blocking rules.

### 2. Provide Clear Feedback
Always explain why a command was blocked and suggest alternatives.

### 3. Allow Overrides
Consider environment variables for bypassing rules when needed.

### 4. Performance Considerations
Keep validation fast - hooks run on every tool call.