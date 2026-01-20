#!/bin/bash
# Ralph PRD Loop - The Proper Implementation
# Based on the original technique with PRD + progress tracking
#
# This version:
# - Starts a FRESH Claude session each iteration (new context window)
# - Uses PRD.md with checkboxed tasks
# - Tracks progress in progress.md
# - Stops when all tasks complete or max iterations hit

set -euo pipefail

MAX_ITERATIONS="${1:-10}"
ITERATION=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  RALPH PRD LOOP - The Proper Implementation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check for PRD.md
if [[ ! -f "PRD.md" ]]; then
    echo -e "${RED}Error: PRD.md not found${NC}"
    echo ""
    echo "Create a PRD.md file with checkboxed tasks like:"
    echo ""
    echo "  ## Tasks"
    echo "  - [ ] Task 1: Initialize project structure"
    echo "  - [ ] Task 2: Create database schema"
    echo "  - [ ] Task 3: Build API endpoints"
    echo ""
    echo "Or use: ralph-prd-init to generate one"
    exit 1
fi

# Create progress.md if it doesn't exist
if [[ ! -f "progress.md" ]]; then
    cat > progress.md << 'EOF'
# Progress Log

This file tracks what has been attempted across Ralph iterations.
Each session reads this to avoid repeating failed approaches.

---

EOF
    echo -e "${GREEN}✓ Created progress.md${NC}"
fi

echo -e "PRD file: ${YELLOW}PRD.md${NC}"
echo -e "Progress file: ${YELLOW}progress.md${NC}"
echo -e "Max iterations: ${YELLOW}$MAX_ITERATIONS${NC}"
echo -e "Working dir: ${YELLOW}$(pwd)${NC}"
echo ""

# Function to count incomplete tasks
count_incomplete() {
    grep -c "^\s*- \[ \]" PRD.md 2>/dev/null || echo "0"
}

# Function to count complete tasks
count_complete() {
    grep -c "^\s*- \[x\]" PRD.md 2>/dev/null || echo "0"
}

# The prompt we send to Claude each iteration
RALPH_PROMPT='You are in a Ralph Loop - an iterative development system.

## Your Mission
1. Read PRD.md to find the FIRST unchecked task (- [ ])
2. Read progress.md to see what has been tried before
3. Work on that ONE task only
4. When done:
   - If SUCCESS: Check the box in PRD.md (change - [ ] to - [x])
   - Update progress.md with what you did
   - If FAILED: Update progress.md with what you tried and errors encountered

## Critical Rules
- Only work on ONE task per session
- Check the box ONLY if the task is truly complete
- Document everything in progress.md for future iterations
- If progress.md shows previous failures, try a DIFFERENT approach
- Commit working code to git after each successful task

## Files to Read First
1. PRD.md - Find your task
2. progress.md - Learn from previous attempts

Begin by reading PRD.md to identify your task.'

# Main loop
while [[ $ITERATION -lt $MAX_ITERATIONS ]]; do
    ITERATION=$((ITERATION + 1))
    INCOMPLETE=$(count_incomplete)
    COMPLETE=$(count_complete)

    # Check if all tasks complete
    if [[ "$INCOMPLETE" -eq 0 ]]; then
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  ALL TASKS COMPLETE!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "Total iterations: ${CYAN}$ITERATION${NC}"
        echo -e "Tasks completed: ${GREEN}$COMPLETE${NC}"
        exit 0
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  RALPH ITERATION #$ITERATION of $MAX_ITERATIONS${NC}"
    echo -e "${CYAN}  $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "Tasks remaining: ${YELLOW}$INCOMPLETE${NC} | Completed: ${GREEN}$COMPLETE${NC}"
    echo ""

    # Log iteration start to progress.md
    echo -e "\n## Iteration $ITERATION - $(date '+%Y-%m-%d %H:%M:%S')\n" >> progress.md

    # THE KEY: Fresh Claude session each iteration
    echo "$RALPH_PROMPT" | claude

    echo ""
    echo -e "${YELLOW}Iteration #$ITERATION complete.${NC}"

    # Brief pause between iterations
    if [[ $ITERATION -lt $MAX_ITERATIONS ]]; then
        INCOMPLETE_NOW=$(count_incomplete)
        if [[ "$INCOMPLETE_NOW" -gt 0 ]]; then
            echo -e "${YELLOW}$INCOMPLETE_NOW tasks remaining. Next iteration in 3 seconds...${NC}"
            echo -e "${YELLOW}(Ctrl+C to stop)${NC}"
            sleep 3
        fi
    fi
done

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  MAX ITERATIONS REACHED ($MAX_ITERATIONS)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
INCOMPLETE=$(count_incomplete)
COMPLETE=$(count_complete)
echo -e "Tasks remaining: ${RED}$INCOMPLETE${NC}"
echo -e "Tasks completed: ${GREEN}$COMPLETE${NC}"
echo ""
echo "To continue, run: ./ralph-prd.sh [more_iterations]"
