#!/usr/bin/env python3
"""
Bash command validation hook for Claude Code
Enforces best practices and blocks dangerous commands
"""

import json
import sys
import re
import os

# Command validation rules
COMMAND_RULES = [
    # Tool usage enforcement
    (r'\bgrep\b(?!.*\|)', "Use 'rg' (ripgrep) instead of 'grep' for better performance"),
    (r'\bfind\s+\S+\s+-name\b', "Use Glob tool or 'rg --files' instead of 'find'"),
    (r'\bcat\s+', "Use Read tool instead of 'cat' command"),
    (r'\bhead\s+', "Use Read tool with offset/limit instead of 'head'"),
    (r'\btail\s+', "Use Read tool with offset instead of 'tail'"),
    (r'\bls\s+(?!.*\.)', "Use LS tool instead of 'ls' command"),
    
    # Dangerous operations
    (r'\brm\s+-rf\s+/', "Dangerous 'rm -rf /' detected - this could destroy your system"),
    (r'\brm\s+-rf\s+~/', "Dangerous 'rm -rf ~/' detected - this would delete your home directory"),
    (r'\bsudo\s+rm', "Sudo rm commands require explicit user approval"),
    (r'\b>\s*/dev/sd[a-z]', "Direct disk write detected - extremely dangerous"),
    (r'\bdd\s+.*of=/dev/', "Dangerous dd command to device detected"),
    (r'\bmkfs\b', "Filesystem format command detected - requires approval"),
    
    # Git safety
    (r'git\s+push\s+--force(?!-with-lease)', "Use 'git push --force-with-lease' instead of '--force'"),
    (r'git\s+reset\s+--hard\s+HEAD~[0-9]+', "Hard reset to previous commits requires confirmation"),
    (r'git\s+clean\s+-[fd]+', "Git clean can delete untracked files - requires approval"),
    
    # Security concerns
    (r'curl.*\|\s*bash', "Piping curl to bash is dangerous - download and review first"),
    (r'wget.*\|\s*sh', "Piping wget to shell is dangerous - download and review first"),
    (r'chmod\s+777', "Setting 777 permissions is insecure - use more restrictive permissions"),
    (r'disable.*firewall', "Disabling firewall requires explicit approval"),
]

# Path-based restrictions
RESTRICTED_PATHS = [
    ('/etc/', "System configuration directory"),
    ('/sys/', "System directory"),
    ('/boot/', "Boot directory"),
    ('~/.ssh/', "SSH configuration"),
    ('~/.aws/', "AWS credentials"),
    ('/usr/bin/', "System binaries"),
    ('/usr/sbin/', "System admin binaries"),
]

def expand_path(path):
    """Expand ~ and environment variables in paths"""
    return os.path.expanduser(os.path.expandvars(path))

def check_command_rules(command):
    """Check command against validation rules"""
    for pattern, message in COMMAND_RULES:
        if re.search(pattern, command, re.IGNORECASE):
            return False, message
    return True, None

def check_path_restrictions(command):
    """Check if command operates on restricted paths"""
    command_expanded = expand_path(command)
    
    for restricted_path, description in RESTRICTED_PATHS:
        expanded_restricted = expand_path(restricted_path)
        if expanded_restricted in command_expanded:
            return False, f"Command operates on {description}: {restricted_path}"
    
    return True, None

def main():
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        session_id = input_data.get('session_id', '')
        
        # Only validate Bash commands
        if tool_name != 'Bash':
            sys.exit(0)
        
        command = tool_input.get('command', '')
        
        # Check command rules
        valid, message = check_command_rules(command)
        if not valid:
            print(f"❌ Command blocked: {message}", file=sys.stderr)
            print(f"Command: {command}", file=sys.stderr)
            sys.exit(2)  # Block execution
        
        # Check path restrictions
        valid, message = check_path_restrictions(command)
        if not valid:
            print(f"❌ Command blocked: {message}", file=sys.stderr)
            print(f"Command: {command}", file=sys.stderr)
            sys.exit(2)  # Block execution
        
        # Log allowed commands
        log_file = os.path.expanduser('~/.claude/logs/bash-commands.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(f"[ALLOWED] Session: {session_id}, Command: {command}\n")
        
        sys.exit(0)  # Allow execution
        
    except Exception as e:
        # On error, allow execution but log the issue
        print(f"Hook error: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()