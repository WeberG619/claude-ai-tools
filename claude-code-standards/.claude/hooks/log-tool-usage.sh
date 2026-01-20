#!/bin/bash
# Tool usage logging hook for Claude Code
# Logs all tool usage for audit and debugging

# Create log directory if it doesn't exist
LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"

# Read JSON from stdin
input=$(cat)

# Extract fields using jq (install with: apt-get install jq)
tool_name=$(echo "$input" | jq -r '.tool_name // "unknown"')
session_id=$(echo "$input" | jq -r '.session_id // "unknown"')
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Log file paths
USAGE_LOG="$LOG_DIR/tool-usage.log"
DAILY_LOG="$LOG_DIR/tool-usage-$(date +%Y-%m-%d).log"

# Write to main log
echo "[$timestamp] Session: $session_id, Tool: $tool_name" >> "$USAGE_LOG"

# Write detailed entry to daily log
{
    echo "===== Tool Usage Entry ====="
    echo "Timestamp: $timestamp"
    echo "Session: $session_id"
    echo "Tool: $tool_name"
    echo "Input: $input"
    echo ""
} >> "$DAILY_LOG"

# Tool-specific logging
case "$tool_name" in
    "Bash")
        command=$(echo "$input" | jq -r '.tool_input.command // ""')
        echo "[$timestamp] Bash command: $command" >> "$LOG_DIR/bash-history.log"
        ;;
    
    "Write"|"Edit"|"MultiEdit")
        file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')
        echo "[$timestamp] File operation on: $file_path" >> "$LOG_DIR/file-changes.log"
        ;;
    
    "TodoWrite")
        echo "[$timestamp] Todo list updated" >> "$LOG_DIR/todo-updates.log"
        ;;
esac

# Rotate logs if they get too large (>10MB)
if [ -f "$USAGE_LOG" ] && [ $(stat -f%z "$USAGE_LOG" 2>/dev/null || stat -c%s "$USAGE_LOG" 2>/dev/null) -gt 10485760 ]; then
    mv "$USAGE_LOG" "$USAGE_LOG.$(date +%Y%m%d%H%M%S)"
    touch "$USAGE_LOG"
fi

# Always allow execution
exit 0