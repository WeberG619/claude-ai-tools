#!/usr/bin/env python3
"""
File operation validation hook for Claude Code
Protects sensitive files and enforces file operation standards
"""

import json
import sys
import os
import re

# Protected file patterns
PROTECTED_FILES = [
    # System files
    (r'^/etc/', "System configuration files require explicit approval"),
    (r'^/sys/', "System files are read-only"),
    (r'^/boot/', "Boot files require explicit approval"),
    (r'^/usr/bin/', "System binaries cannot be modified"),
    (r'^/usr/sbin/', "System admin binaries cannot be modified"),
    
    # User sensitive files
    (r'~/.ssh/', "SSH configuration is highly sensitive"),
    (r'~/.aws/', "AWS credentials must not be modified"),
    (r'~/.env', "Environment files may contain secrets"),
    (r'.git/config', "Git configuration requires careful handling"),
    (r'~/.bashrc', "Shell configuration requires approval"),
    (r'~/.zshrc', "Shell configuration requires approval"),
    
    # Security files
    (r'\.pem$', "Certificate files require explicit approval"),
    (r'\.key$', "Private key files are sensitive"),
    (r'id_rsa', "SSH private keys must not be modified"),
    (r'credentials', "Credential files are sensitive"),
    (r'secrets', "Secret files require explicit handling"),
]

# File creation restrictions
RESTRICTED_EXTENSIONS = [
    ('.exe', "Executable files require explicit approval"),
    ('.dll', "Library files require explicit approval"),
    ('.so', "Shared object files require explicit approval"),
    ('.sys', "System files cannot be created"),
]

# Documentation file patterns
DOCUMENTATION_PATTERNS = [
    r'README\.md$',
    r'readme\.md$',
    r'CONTRIBUTING\.md$',
    r'CHANGELOG\.md$',
    r'docs/.*\.md$',
    r'.*\.md$',  # Any markdown file
]

def expand_path(path):
    """Expand ~ and environment variables in paths"""
    return os.path.expanduser(os.path.expandvars(path))

def check_protected_files(file_path):
    """Check if file path matches protected patterns"""
    expanded_path = expand_path(file_path)
    
    for pattern, message in PROTECTED_FILES:
        if re.search(pattern.replace('~/', os.path.expanduser('~/'), 1), expanded_path):
            return False, message
    
    return True, None

def check_file_extension(file_path):
    """Check if file has restricted extension"""
    for ext, message in RESTRICTED_EXTENSIONS:
        if file_path.endswith(ext):
            return False, message
    
    return True, None

def check_documentation_creation(tool_name, file_path):
    """Check if creating documentation without request"""
    if tool_name == 'Write':
        for pattern in DOCUMENTATION_PATTERNS:
            if re.search(pattern, file_path, re.IGNORECASE):
                return False, "Never create documentation files unless explicitly requested"
    
    return True, None

def validate_edit_operation(tool_input):
    """Additional validation for edit operations"""
    if 'old_string' in tool_input and 'new_string' in tool_input:
        old_string = tool_input['old_string']
        new_string = tool_input['new_string']
        
        # Check for secret patterns being added
        secret_patterns = [
            r'api[_-]?key\s*=',
            r'password\s*=',
            r'secret\s*=',
            r'token\s*=',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, new_string, re.IGNORECASE):
                return False, "Detected potential secret in edit - use environment variables instead"
    
    return True, None

def main():
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        session_id = input_data.get('session_id', '')
        
        # Only validate file operation tools
        if tool_name not in ['Write', 'Edit', 'MultiEdit']:
            sys.exit(0)
        
        file_path = tool_input.get('file_path', '')
        
        # Check protected files
        valid, message = check_protected_files(file_path)
        if not valid:
            print(f"❌ File operation blocked: {message}", file=sys.stderr)
            print(f"File: {file_path}", file=sys.stderr)
            sys.exit(2)  # Block execution
        
        # Check file extensions
        valid, message = check_file_extension(file_path)
        if not valid:
            print(f"❌ File operation blocked: {message}", file=sys.stderr)
            print(f"File: {file_path}", file=sys.stderr)
            sys.exit(2)  # Block execution
        
        # Check documentation creation
        valid, message = check_documentation_creation(tool_name, file_path)
        if not valid:
            print(f"❌ File operation blocked: {message}", file=sys.stderr)
            print(f"File: {file_path}", file=sys.stderr)
            sys.exit(2)  # Block execution
        
        # Additional validation for edits
        if tool_name in ['Edit', 'MultiEdit']:
            valid, message = validate_edit_operation(tool_input)
            if not valid:
                print(f"❌ Edit operation blocked: {message}", file=sys.stderr)
                sys.exit(2)  # Block execution
        
        # Log allowed operations
        log_file = os.path.expanduser('~/.claude/logs/file-operations.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(f"[ALLOWED] Session: {session_id}, Tool: {tool_name}, File: {file_path}\n")
        
        sys.exit(0)  # Allow execution
        
    except Exception as e:
        # On error, allow execution but log the issue
        print(f"Hook error: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()