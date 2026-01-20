#!/bin/bash
# Claude Code Conversation Cleanup Script
# Prevents heap overflow by archiving old/large conversations
# Your project context is preserved in claude-memory MCP (separate from conversations)

CLAUDE_DIR="$HOME/.claude/projects/-mnt-d"
ARCHIVE_DIR="$CLAUDE_DIR/archive"
DAYS_TO_KEEP=7
MAX_SIZE_MB=100

echo "=== Claude Code Conversation Cleanup ==="
echo "Archive directory: $ARCHIVE_DIR"
echo "Keeping conversations from last $DAYS_TO_KEEP days"
echo "Archiving files larger than ${MAX_SIZE_MB}MB"
echo ""

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Get current sizes
BEFORE_ACTIVE=$(du -sh "$CLAUDE_DIR" --exclude="$ARCHIVE_DIR" 2>/dev/null | cut -f1)
BEFORE_ARCHIVE=$(du -sh "$ARCHIVE_DIR" 2>/dev/null | cut -f1)

echo "Before cleanup:"
echo "  Active: $BEFORE_ACTIVE"
echo "  Archive: $BEFORE_ARCHIVE"
echo ""

# Archive old conversations (older than X days)
echo "Archiving conversations older than $DAYS_TO_KEEP days..."
OLD_COUNT=$(find "$CLAUDE_DIR" -maxdepth 1 -name "*.jsonl" -mtime +$DAYS_TO_KEEP | wc -l)
find "$CLAUDE_DIR" -maxdepth 1 -name "*.jsonl" -mtime +$DAYS_TO_KEEP -exec mv {} "$ARCHIVE_DIR/" \;
echo "  Moved $OLD_COUNT old conversations"

# Archive oversized conversations (regardless of age)
echo "Archiving conversations larger than ${MAX_SIZE_MB}MB..."
LARGE_COUNT=$(find "$CLAUDE_DIR" -maxdepth 1 -name "*.jsonl" -size +${MAX_SIZE_MB}M | wc -l)
find "$CLAUDE_DIR" -maxdepth 1 -name "*.jsonl" -size +${MAX_SIZE_MB}M -exec mv {} "$ARCHIVE_DIR/" \;
echo "  Moved $LARGE_COUNT oversized conversations"

# Get new sizes
AFTER_ACTIVE=$(du -sh "$CLAUDE_DIR" --exclude="$ARCHIVE_DIR" 2>/dev/null | cut -f1)
AFTER_ARCHIVE=$(du -sh "$ARCHIVE_DIR" 2>/dev/null | cut -f1)
ACTIVE_COUNT=$(find "$CLAUDE_DIR" -maxdepth 1 -name "*.jsonl" | wc -l)

echo ""
echo "After cleanup:"
echo "  Active: $AFTER_ACTIVE ($ACTIVE_COUNT conversations)"
echo "  Archive: $AFTER_ARCHIVE"
echo ""
echo "Your project context is preserved in claude-memory MCP."
echo "Run 'claude' and /resume should work now!"
