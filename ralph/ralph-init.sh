#!/bin/bash
# Initialize Ralph in a project directory
# Creates PROMPT.md template and .ralph directory

set -euo pipefail

PROJECT_DIR="${1:-.}"
TEMPLATE_DIR="$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  RALPH - Project Initialization${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$PROJECT_DIR"

# Create .ralph directory for logs and state
mkdir -p .ralph

# Create PROMPT.md if it doesn't exist
if [[ ! -f "PROMPT.md" ]]; then
    cat > PROMPT.md << 'EOF'
# Project Task

## Objective
[Describe what you want to build or accomplish]

## Context
- Check existing files before creating new ones
- Follow existing code patterns and conventions
- Run tests after making changes
- Commit working changes to git with clear messages

## Current State
[Ralph will see previous work via files and git history]

## Instructions
1. Read and understand the existing codebase
2. Make incremental progress on the objective
3. Test your changes
4. If tests pass, commit and move to next step
5. If tests fail, fix issues before proceeding

## Quality Standards
- Code should be clean and well-documented
- All tests must pass
- No hardcoded secrets or credentials
- Follow project's existing style

## When Done
Create a DONE.md file summarizing what was accomplished.
EOF
    echo -e "${GREEN}✓ Created PROMPT.md${NC}"
else
    echo -e "${YELLOW}PROMPT.md already exists, skipping${NC}"
fi

# Create .gitignore entry for ralph logs
if [[ -f ".gitignore" ]]; then
    if ! grep -q ".ralph" .gitignore 2>/dev/null; then
        echo ".ralph/" >> .gitignore
        echo -e "${GREEN}✓ Added .ralph/ to .gitignore${NC}"
    fi
else
    echo ".ralph/" > .gitignore
    echo -e "${GREEN}✓ Created .gitignore with .ralph/${NC}"
fi

echo ""
echo -e "${GREEN}Ralph initialized in: $(pwd)${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit PROMPT.md with your specific task"
echo "  2. Run: ralph.sh"
echo ""
echo "Tips for good prompts:"
echo "  - Be specific about the objective"
echo "  - Include quality standards"
echo "  - Tell Claude to check existing files first"
echo "  - Tell Claude to commit working changes"
echo ""
