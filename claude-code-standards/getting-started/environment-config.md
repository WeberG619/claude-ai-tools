# Environment Configuration Standards

## Directory Navigation

### Path Handling
- Always use absolute paths for file operations
- Quote paths containing spaces: `cd "/path with spaces/"`
- Verify parent directories exist before creating files
- Use forward slashes for cross-platform compatibility

### Working Directory
- Maintain current directory throughout session
- Use absolute paths instead of `cd` when possible
- Only use `cd` when explicitly requested by user

## Tool Usage Priorities

### Search Operations
1. Use `Task` tool for complex multi-file searches
2. Use `Grep` for content searching within known directories
3. Use `Glob` for file pattern matching
4. Never use `find` or `grep` commands in Bash

### File Operations
1. Use `Read` tool instead of `cat`, `head`, `tail`
2. Use `LS` tool instead of `ls` command
3. Use `MultiEdit` for multiple changes to same file
4. Always read file before editing

## Platform Considerations

### Cross-Platform Support
- Detect platform and adjust commands accordingly
- Use portable commands when possible
- Handle Windows path separators correctly
- Check for WSL environment on Windows

### Command Availability
- Always verify command exists before using
- Prefer `rg` (ripgrep) over `grep`
- Check for tool-specific commands (npm, cargo, etc.)
- Provide alternatives if command not found