#!/bin/bash
# Background agent runner script

TASK_NAME="$1"
PROMPT="$2"
MODEL="${3:-claude-3-5-sonnet-20241022}"

# Validate inputs
if [ -z "$TASK_NAME" ] || [ -z "$PROMPT" ]; then
    echo "Usage: $0 <task_name> <prompt> [model]"
    exit 1
fi

# Create output directory
OUTPUT_DIR="agents/background"
mkdir -p "$OUTPUT_DIR"

# Generate timestamp and output file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/${TASK_NAME}_${TIMESTAMP}.md"
PROGRESS_FILE="$OUTPUT_DIR/${TASK_NAME}_${TIMESTAMP}_progress.md"

# Create initial progress file
cat > "$PROGRESS_FILE" << EOF
# Background Task: $TASK_NAME
Started: $(date)
Status: RUNNING
Model: $MODEL

## Task Description
$PROMPT

## Progress
Initializing agent...
EOF

# Run background agent
echo "Starting background agent for: $TASK_NAME"
echo "Output will be saved to: $OUTPUT_FILE"
echo "Monitor progress at: $PROGRESS_FILE"

# Launch claude in background
nohup claude \
    --model "$MODEL" \
    --yolo \
    --output "$OUTPUT_FILE" \
    "$PROMPT" \
    > "$OUTPUT_DIR/${TASK_NAME}_${TIMESTAMP}.log" 2>&1 &

AGENT_PID=$!
echo "Background agent launched with PID: $AGENT_PID"

# Update progress file with PID
echo "Agent PID: $AGENT_PID" >> "$PROGRESS_FILE"