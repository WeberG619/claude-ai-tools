# Claude Code Standards Documentation

This documentation provides comprehensive rules and standards for Claude Code to ensure consistent behavior across all development sessions.

## Structure Overview

- **getting-started/** - Initial setup, configuration, and environment standards
- **architecture/** - Code organization patterns and structural guidelines
- **development/** - Coding standards, conventions, and best practices
- **integrations/** - Third-party library usage and external service rules
- **workflows/** - Common task patterns and step-by-step procedures
- **hooks/** - Automated validation and enforcement rules

## Quick Start

1. Review the getting-started documentation
2. Configure hooks using the provided settings.json template
3. Follow architecture patterns for new projects
4. Apply development standards consistently
5. Use workflow templates for common tasks

## Key Principles

1. **Consistency First** - Always follow existing patterns
2. **Security by Default** - Never expose secrets or sensitive data
3. **Minimal Changes** - Edit existing files rather than creating new ones
4. **Explicit Actions** - Never commit or push without explicit request
5. **Validated Output** - Always run linters and type checkers

## Hook Integration

The hooks system enforces these standards automatically. See the hooks folder for configuration details and the .claude/settings.json template.