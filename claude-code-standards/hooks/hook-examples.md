# Hook Implementation Examples

## Python Validation Hook

```python
#!/usr/bin/env python3
import json
import sys
import re

# Validation rules
BASH_RULES = [
    (r'\bgrep\b(?!.*\|)', "Use 'rg' (ripgrep) instead of 'grep' for better performance"),
    (r'\bfind\s+\S+\s+-name\b', "Use 'rg --files | rg pattern' or Glob tool instead"),
    (r'\bcat\s+', "Use Read tool instead of 'cat' command"),
    (r'\brm\s+-rf\s+/', "Dangerous rm -rf detected - use with caution"),
    (r'\bsudo\b', "Sudo commands require explicit user approval")
]

PATH_RULES = [
    (r'/etc/', "System configuration directory - requires approval"),
    (r'~/.ssh/', "SSH configuration - highly sensitive"),
    (r'~/.aws/', "AWS credentials - never modify directly")
]

def validate_bash_command(command):
    """Validate bash commands against rules"""
    for pattern, message in BASH_RULES:
        if re.search(pattern, command):
            return False, message
    return True, None

def validate_file_path(path):
    """Validate file operations against protected paths"""
    for pattern, message in PATH_RULES:
        if pattern in path:
            return False, message
    return True, None

def main():
    # Read input from stdin
    input_data = json.loads(sys.stdin.read())
    
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    
    # Validate based on tool
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        valid, message = validate_bash_command(command)
        if not valid:
            print(f"Command blocked: {message}", file=sys.stderr)
            sys.exit(2)  # Block execution
    
    elif tool_name in ['Write', 'Edit', 'MultiEdit']:
        file_path = tool_input.get('file_path', '')
        valid, message = validate_file_path(file_path)
        if not valid:
            print(f"File operation blocked: {message}", file=sys.stderr)
            sys.exit(2)  # Block execution
    
    # Log all tool usage
    with open('/tmp/claude-tool-usage.log', 'a') as f:
        f.write(f"{tool_name}: {json.dumps(tool_input)}\n")
    
    sys.exit(0)  # Allow execution

if __name__ == '__main__':
    main()
```

## Bash Logging Hook

```bash
#!/bin/bash
# Simple logging hook for all tool usage

# Read JSON from stdin
input=$(cat)

# Extract tool name and session ID
tool_name=$(echo "$input" | jq -r '.tool_name')
session_id=$(echo "$input" | jq -r '.session_id')

# Log to file with timestamp
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Session: $session_id, Tool: $tool_name" >> ~/.claude/tool-usage.log

# Always allow execution
exit 0
```

## Node.js Advanced Hook

```javascript
#!/usr/bin/env node
const fs = require('fs');

// Read input
let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
    const data = JSON.parse(input);
    
    // Advanced decision logic
    if (data.tool_name === 'Bash') {
        const command = data.tool_input.command || '';
        
        // Check for production paths
        if (command.includes('/production/')) {
            // Return JSON decision
            console.log(JSON.stringify({
                decision: 'block',
                continue: false,
                reason: 'Production directory access requires manual approval'
            }));
            process.exit(0);
        }
    }
    
    // Default: allow
    process.exit(0);
});
```

## Testing Hooks

```bash
# Test hook with sample input
echo '{
  "session_id": "test-123",
  "tool_name": "Bash",
  "tool_input": {
    "command": "grep -r password ."
  }
}' | python3 validation-hook.py

# Expected output: Command blocked: Use 'rg' (ripgrep) instead
```