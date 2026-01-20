#!/bin/bash
# Context bundle tracking hook for Claude Code

# Get session info
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)}"
BUNDLE_DIR="agents/context_bundles"
BUNDLE_FILE="$BUNDLE_DIR/bundle_${SESSION_ID}.md"

# Create directory if it doesn't exist
mkdir -p "$BUNDLE_DIR"

# Initialize bundle file if new
if [ ! -f "$BUNDLE_FILE" ]; then
    echo "# Context Bundle - Session $SESSION_ID" > "$BUNDLE_FILE"
    echo "Started: $(date)" >> "$BUNDLE_FILE"
    echo "" >> "$BUNDLE_FILE"
fi

# Log tool usage based on tool type
case "$TOOL_NAME" in
    "read")
        echo "## Read: $TOOL_INPUT_FILE" >> "$BUNDLE_FILE"
        echo "Lines: $TOOL_INPUT_LINES" >> "$BUNDLE_FILE"
        echo "" >> "$BUNDLE_FILE"
        ;;
    "write")
        echo "## Write: $TOOL_INPUT_FILE" >> "$BUNDLE_FILE"
        echo "Action: Created/Modified" >> "$BUNDLE_FILE"
        echo "" >> "$BUNDLE_FILE"
        ;;
    "bash")
        echo "## Command: $TOOL_INPUT_COMMAND" >> "$BUNDLE_FILE"
        echo "" >> "$BUNDLE_FILE"
        ;;
    "search")
        echo "## Search: '$TOOL_INPUT_PATTERN'" >> "$BUNDLE_FILE"
        echo "Found: $TOOL_RESULT_COUNT matches" >> "$BUNDLE_FILE"
        echo "" >> "$BUNDLE_FILE"
        ;;
esac