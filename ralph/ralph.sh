#!/bin/bash
# Ralph - The Original Technique
# By Geoff Huntley (ghuntley.com/ralph)
#
# "In its purest form, Ralph is a Bash loop."
#
# Usage: ./ralph.sh [PROMPT_FILE]
#        Default: PROMPT.md in current directory

set -euo pipefail

PROMPT_FILE="${1:-PROMPT.md}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  RALPH - The Original Technique${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if prompt file exists
if [[ ! -f "$PROMPT_FILE" ]]; then
    echo -e "${RED}Error: $PROMPT_FILE not found${NC}"
    echo ""
    echo "Create a PROMPT.md file with your task instructions."
    echo "Example:"
    echo ""
    echo "  echo 'Build a REST API for todos.' > PROMPT.md"
    echo "  ./ralph.sh"
    echo ""
    exit 1
fi

echo -e "Prompt file: ${YELLOW}$PROMPT_FILE${NC}"
echo -e "Working dir: ${YELLOW}$(pwd)${NC}"
echo ""
echo -e "${YELLOW}Contents of $PROMPT_FILE:${NC}"
echo -e "${BLUE}─────────────────────────────────────────${NC}"
cat "$PROMPT_FILE"
echo ""
echo -e "${BLUE}─────────────────────────────────────────${NC}"
echo ""
echo -e "${GREEN}Starting Ralph loop...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Track iterations
ITERATION=0

# The loop - this is Ralph in its purest form
while :; do
    ITERATION=$((ITERATION + 1))

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  RALPH ITERATION #$ITERATION${NC}"
    echo -e "${BLUE}  $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # The magic line - pipe prompt to claude
    cat "$PROMPT_FILE" | claude

    echo ""
    echo -e "${YELLOW}Iteration #$ITERATION complete. Starting next iteration in 3 seconds...${NC}"
    echo -e "${YELLOW}(Ctrl+C to stop)${NC}"
    sleep 3
done
