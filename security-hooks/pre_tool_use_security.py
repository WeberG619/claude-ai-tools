#!/usr/bin/env python3
"""
Pre-Tool Use Security Hook for Claude Code
==========================================
Blocks dangerous commands BEFORE execution.

Exit codes:
- 0: Allow (tool proceeds)
- 2: Block (stderr shown to Claude, tool blocked)

Environment variables (set by Claude Code):
- CLAUDE_TOOL_NAME: The tool being called (Bash, Read, Edit, Write, etc.)
- CLAUDE_TOOL_INPUT: JSON string of tool parameters

Author: Weber Gouin
"""

import json
import os
import re
import sys
from typing import Tuple

# ============================================================================
# CONFIGURATION - Customize these rules
# ============================================================================

# Dangerous Bash patterns (regex)
DANGEROUS_BASH_PATTERNS = [
    # Destructive file operations
    (r'rm\s+(-[rf]+\s+)*/', "Blocked: rm with absolute path - too dangerous"),
    (r'rm\s+-rf\s+', "Blocked: rm -rf is too dangerous"),
    (r'rm\s+-fr\s+', "Blocked: rm -fr is too dangerous"),
    (r'rm\s+.*\*', "Blocked: rm with wildcard - too dangerous"),
    (r'>\s*/dev/sd', "Blocked: writing to block device"),
    (r'mkfs\.', "Blocked: filesystem formatting"),
    (r'dd\s+.*of=/dev/', "Blocked: dd to device"),

    # Git dangerous operations
    (r'git\s+push\s+.*--force\s+.*main', "Blocked: force push to main"),
    (r'git\s+push\s+.*--force\s+.*master', "Blocked: force push to master"),
    (r'git\s+push\s+-f\s+.*main', "Blocked: force push to main"),
    (r'git\s+push\s+-f\s+.*master', "Blocked: force push to master"),
    (r'git\s+reset\s+--hard\s+origin', "Blocked: git reset --hard origin (destructive)"),
    (r'git\s+clean\s+-fd', "Blocked: git clean -fd removes untracked files"),

    # Credential/secret exposure
    (r'curl.*\|\s*sh', "Blocked: curl pipe to shell"),
    (r'wget.*\|\s*sh', "Blocked: wget pipe to shell"),
    (r'curl.*\|\s*bash', "Blocked: curl pipe to bash"),
    (r'wget.*\|\s*bash', "Blocked: wget pipe to bash"),

    # System modification
    (r'chmod\s+777', "Blocked: chmod 777 is insecure"),
    (r'chmod\s+-R\s+777', "Blocked: recursive chmod 777"),
    (r'chown\s+-R\s+root', "Blocked: recursive chown to root"),

    # Package manager dangers (could install malware)
    (r'pip\s+install\s+--pre', "Warning: installing pre-release packages"),

    # History/audit evasion
    (r'history\s+-c', "Blocked: clearing history"),
    (r'shred\s+.*\.bash_history', "Blocked: shredding bash history"),

    # Crypto mining indicators
    (r'xmrig', "Blocked: cryptocurrency miner detected"),
    (r'minerd', "Blocked: cryptocurrency miner detected"),
    (r'stratum\+tcp', "Blocked: mining pool connection"),
]

# Sensitive files that should never be read/edited/written
SENSITIVE_FILE_PATTERNS = [
    # Environment and secrets
    r'\.env$',
    r'\.env\.',
    r'\.env\.local$',
    r'\.env\.production$',
    r'secrets\.json$',
    r'secrets\.ya?ml$',
    r'credentials\.json$',
    r'\.credentials',
    r'service[_-]?account.*\.json$',

    # SSH and crypto keys
    r'id_rsa$',
    r'id_ed25519$',
    r'id_dsa$',
    r'\.pem$',
    r'\.key$',
    r'private[_-]?key',

    # Cloud credentials
    r'\.aws/credentials$',
    r'\.azure/',
    r'gcloud.*credentials',

    # Password files
    r'/etc/passwd$',
    r'/etc/shadow$',
    r'\.htpasswd$',
    r'passwd\.txt$',
    r'passwords?\.(txt|json|csv)$',

    # Database files with potentially sensitive data
    r'\.sqlite3?$',  # Can contain sensitive app data - warn but allow

    # Token files
    r'token\.json$',
    r'\.token$',
    r'access_token',
    r'refresh_token',
]

# Files that are sensitive but we allow with a warning (not blocked)
WARN_FILE_PATTERNS = [
    r'\.sqlite3?$',
    r'config\.(json|ya?ml|toml)$',
    r'settings\.(json|ya?ml)$',
]

# Allowlisted paths (always allowed even if they match sensitive patterns)
ALLOWLISTED_PATHS = [
    '/mnt/d/_CLAUDE-TOOLS/',
    '/home/weber/.claude/',
    '/mnt/d/.claude/',
]


# ============================================================================
# SECURITY CHECKS
# ============================================================================

def check_bash_command(command: str) -> Tuple[bool, str]:
    """
    Check if a Bash command is dangerous.
    Returns (is_blocked, reason).
    """
    command_lower = command.lower()

    for pattern, reason in DANGEROUS_BASH_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, reason

    return False, ""


def check_file_access(file_path: str, tool_name: str) -> Tuple[bool, str]:
    """
    Check if file access should be blocked.
    Returns (is_blocked, reason).
    """
    if not file_path:
        return False, ""

    # Normalize path
    file_path_lower = file_path.lower()

    # Check allowlist first
    for allowed in ALLOWLISTED_PATHS:
        if file_path.startswith(allowed):
            return False, ""

    # Check sensitive patterns
    for pattern in SENSITIVE_FILE_PATTERNS:
        if re.search(pattern, file_path_lower):
            # Special handling for warn-only patterns
            is_warn_only = any(re.search(wp, file_path_lower) for wp in WARN_FILE_PATTERNS)

            if is_warn_only:
                # Print warning but don't block
                print(f"[SECURITY WARNING] Accessing potentially sensitive file: {file_path}", file=sys.stderr)
                return False, ""
            else:
                return True, f"Blocked: {tool_name} access to sensitive file matching '{pattern}'"

    return False, ""


def check_edit_content(file_path: str, old_string: str, new_string: str) -> Tuple[bool, str]:
    """
    Check if an Edit operation is trying to inject dangerous content.
    """
    # Check for secret injection
    dangerous_injections = [
        (r'password\s*=\s*["\'][^"\']+["\']', "Blocked: hardcoding password"),
        (r'api[_-]?key\s*=\s*["\'][A-Za-z0-9]{20,}["\']', "Blocked: hardcoding API key"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "Blocked: hardcoding secret"),
    ]

    for pattern, reason in dangerous_injections:
        if re.search(pattern, new_string, re.IGNORECASE):
            # Only block if it's a new addition (not already in old_string)
            if not re.search(pattern, old_string or "", re.IGNORECASE):
                return True, reason

    return False, ""


# ============================================================================
# MAIN HOOK LOGIC
# ============================================================================

def main():
    tool_name = os.environ.get('CLAUDE_TOOL_NAME', '')
    tool_input_raw = os.environ.get('CLAUDE_TOOL_INPUT', '{}')

    try:
        tool_input = json.loads(tool_input_raw)
    except json.JSONDecodeError:
        tool_input = {}

    blocked = False
    reason = ""

    # Route to appropriate security check based on tool
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        blocked, reason = check_bash_command(command)

    elif tool_name == 'Read':
        file_path = tool_input.get('file_path', '')
        blocked, reason = check_file_access(file_path, 'Read')

    elif tool_name == 'Edit':
        file_path = tool_input.get('file_path', '')
        blocked, reason = check_file_access(file_path, 'Edit')

        if not blocked:
            old_string = tool_input.get('old_string', '')
            new_string = tool_input.get('new_string', '')
            blocked, reason = check_edit_content(file_path, old_string, new_string)

    elif tool_name == 'Write':
        file_path = tool_input.get('file_path', '')
        blocked, reason = check_file_access(file_path, 'Write')

        if not blocked:
            content = tool_input.get('content', '')
            blocked, reason = check_edit_content(file_path, '', content)

    # Output result
    if blocked:
        print(f"[SECURITY BLOCK] {reason}", file=sys.stderr)
        print(f"Tool: {tool_name}", file=sys.stderr)
        if tool_name == 'Bash':
            print(f"Command: {tool_input.get('command', '')[:200]}", file=sys.stderr)
        else:
            print(f"File: {tool_input.get('file_path', '')}", file=sys.stderr)
        sys.exit(2)  # Exit code 2 = block the tool, show error to Claude
    else:
        # Allowed - exit 0
        sys.exit(0)


if __name__ == '__main__':
    main()
