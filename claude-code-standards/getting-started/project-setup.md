# Project Setup Standards

## Initial Project Structure

When creating a new project, always follow this structure:

```
project-root/
├── src/              # Source code
├── tests/            # Test files
├── docs/             # Documentation (only if requested)
├── scripts/          # Build and utility scripts
├── .claude/          # Claude Code configuration
└── README.md         # Project overview (only if requested)
```

## Configuration Rules

### 1. Environment Setup

- Always check for existing configuration files before creating new ones
- Use existing package managers (npm, pip, cargo, etc.) found in the project
- Never assume a specific framework or library is available

### 2. File Creation Rules

- NEVER create documentation files unless explicitly requested
- ALWAYS prefer editing existing files over creating new ones
- Check parent directory exists before creating files
- Use absolute paths when creating directories

### 3. Git Configuration

- NEVER update git config
- NEVER commit unless explicitly asked
- Always run git status before suggesting commits
- Include co-author attribution when requested

## Project Detection

Before starting work:

1. Check if directory is a git repository
2. Identify the primary language/framework
3. Look for configuration files (package.json, Cargo.toml, etc.)
4. Review existing code style and conventions
5. Check for test frameworks and linting tools

## Standard Commands

Always verify these commands exist before using:

```bash
# Node.js projects
npm run lint
npm run test
npm run build
npm run typecheck

# Python projects
pytest
ruff check
mypy

# Rust projects
cargo test
cargo clippy
cargo fmt --check
```