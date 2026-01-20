#!/bin/bash
# Ralph Hierarchical - Multi-agent orchestration
#
# Uses multiple prompt files for different phases:
# - PLAN.md    -> High-level planning
# - BUILD.md   -> Implementation
# - TEST.md    -> Testing and validation
# - REVIEW.md  -> Code review and refinement
#
# Each phase runs until a completion marker is found in output

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PHASE_DIR="${1:-.}"
LOG_DIR="$PHASE_DIR/.ralph-logs"
mkdir -p "$LOG_DIR"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  RALPH HIERARCHICAL - Multi-Phase Orchestration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Define phases in order
PHASES=("PLAN" "BUILD" "TEST" "REVIEW")

run_phase() {
    local phase="$1"
    local prompt_file="$PHASE_DIR/${phase}.md"
    local log_file="$LOG_DIR/${phase}_$(date +%Y%m%d_%H%M%S).log"
    local iteration=0
    local max_iterations=10  # Safety limit per phase

    if [[ ! -f "$prompt_file" ]]; then
        echo -e "${YELLOW}Skipping $phase - no ${phase}.md found${NC}"
        return 0
    fi

    echo -e "${CYAN}━━━ PHASE: $phase ━━━${NC}"
    echo -e "Prompt: $prompt_file"
    echo -e "Log: $log_file"
    echo ""

    while [[ $iteration -lt $max_iterations ]]; do
        iteration=$((iteration + 1))
        echo -e "${GREEN}[$phase] Iteration $iteration${NC}"

        # Run claude and capture output
        cat "$prompt_file" | claude 2>&1 | tee -a "$log_file"

        # Check for phase completion marker in the log
        if grep -q "PHASE_COMPLETE:$phase" "$log_file" 2>/dev/null; then
            echo -e "${GREEN}✓ Phase $phase complete${NC}"
            echo ""
            return 0
        fi

        sleep 2
    done

    echo -e "${YELLOW}⚠ Phase $phase hit iteration limit ($max_iterations)${NC}"
    return 0
}

# Run each phase in sequence
for phase in "${PHASES[@]}"; do
    run_phase "$phase"
done

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  RALPH HIERARCHICAL COMPLETE${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
