# Claude Code Standards Setup Guide

## Quick Setup

1. **Copy hooks to your home directory:**
   ```bash
   cp -r .claude ~/.claude
   ```

2. **Make hooks executable:**
   ```bash
   chmod +x ~/.claude/hooks/*.py ~/.claude/hooks/*.sh
   ```

3. **Install dependencies:**
   ```bash
   # For JSON processing in bash hooks
   sudo apt-get install jq  # Linux
   brew install jq         # macOS
   ```

4. **Create log directory:**
   ```bash
   mkdir -p ~/.claude/logs
   ```

## Configuration

The `.claude/settings.json` file controls when hooks run:

- **PreToolUse**: Validates commands before execution
- **PostToolUse**: Logs successful operations
- **Matchers**: Use regex patterns to target specific tools

## Customization

### Adding New Rules

Edit `~/.claude/hooks/validate-bash.py`:
```python
COMMAND_RULES = [
    (r'your-pattern', "Your error message"),
]
```

### Protecting Additional Paths

Edit `~/.claude/hooks/validate-file-ops.py`:
```python
PROTECTED_FILES = [
    (r'your/path/pattern', "Protection reason"),
]
```

### Disabling Hooks Temporarily

Set environment variable:
```bash
export CLAUDE_HOOKS_DISABLED=1
```

## Testing Hooks

Test your hooks with sample inputs:

```bash
# Test bash validation
echo '{
  "tool_name": "Bash",
  "tool_input": {"command": "grep test"},
  "session_id": "test"
}' | python3 ~/.claude/hooks/validate-bash.py

# Test file validation  
echo '{
  "tool_name": "Write",
  "tool_input": {"file_path": "~/.ssh/id_rsa"},
  "session_id": "test"
}' | python3 ~/.claude/hooks/validate-file-ops.py
```

## Monitoring

View logs:
```bash
# All tool usage
tail -f ~/.claude/logs/tool-usage.log

# Bash commands only
tail -f ~/.claude/logs/bash-history.log

# File changes
tail -f ~/.claude/logs/file-changes.log
```

## Troubleshooting

1. **Hooks not running**: Check file permissions and paths in settings.json
2. **Commands blocked incorrectly**: Review patterns in validation scripts
3. **Performance issues**: Simplify regex patterns or reduce logging

## Security Note

Hooks run with your full permissions. Always review hook code before installation.