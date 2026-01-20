#!/bin/bash
# Initialize a project with PRD-based Ralph Loop
# Creates PRD.md template and progress.md

set -euo pipefail

PROJECT_NAME="${1:-My Project}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  RALPH PRD - Project Initialization${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Create PRD.md
if [[ ! -f "PRD.md" ]]; then
    cat > PRD.md << EOF
# Product Requirements Document: $PROJECT_NAME

## Overview
[Describe what you're building and why]

## Goals
- [Primary goal]
- [Secondary goal]

## Technical Stack
- [Language/Framework]
- [Database if any]
- [Key dependencies]

---

## Tasks

### Phase 1: Setup
- [ ] Task 1: Initialize project structure and dependencies
- [ ] Task 2: Set up configuration and environment

### Phase 2: Core Features
- [ ] Task 3: [First core feature]
- [ ] Task 4: [Second core feature]
- [ ] Task 5: [Third core feature]

### Phase 3: Polish
- [ ] Task 6: Add error handling and validation
- [ ] Task 7: Write tests
- [ ] Task 8: Documentation and cleanup

---

## Acceptance Criteria
Each task should:
- Have working code committed to git
- Include basic error handling
- Follow existing code patterns

## Notes
[Any additional context or constraints]
EOF
    echo -e "${GREEN}✓ Created PRD.md${NC}"
else
    echo -e "${YELLOW}PRD.md already exists, skipping${NC}"
fi

# Create progress.md
if [[ ! -f "progress.md" ]]; then
    cat > progress.md << 'EOF'
# Progress Log

This file tracks what has been attempted across Ralph iterations.
Each session reads this to avoid repeating failed approaches.

## How This Works
- Each Ralph iteration adds entries here
- If a task fails, document what was tried and why it failed
- The next iteration reads this and tries a different approach

---

EOF
    echo -e "${GREEN}✓ Created progress.md${NC}"
else
    echo -e "${YELLOW}progress.md already exists, skipping${NC}"
fi

# Add to .gitignore if exists
if [[ -f ".gitignore" ]]; then
    if ! grep -q "progress.md" .gitignore 2>/dev/null; then
        echo "progress.md" >> .gitignore
        echo -e "${GREEN}✓ Added progress.md to .gitignore${NC}"
    fi
fi

echo ""
echo -e "${GREEN}Ralph PRD initialized!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit PRD.md with your specific tasks"
echo "     - Add checkboxes: - [ ] Task description"
echo "     - Be specific about what each task should accomplish"
echo "  2. Run: ralph-prd.sh [max_iterations]"
echo ""
echo "Tips:"
echo "  - Break large features into small, discrete tasks"
echo "  - Each task should be completable in one session"
echo "  - Default is 10 iterations (1+ per task if failures)"
echo "  - Ralph will check boxes as tasks complete"
echo ""
