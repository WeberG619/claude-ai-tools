#!/bin/bash
# BIM Ops Studio - Automated Backup Script
# Backs up critical AI infrastructure to local and cloud storage

set -e

# Configuration
BACKUP_ROOT="/mnt/d/BACKUP"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== BIM Ops Studio Backup ===${NC}"
echo "Timestamp: $TIMESTAMP"

# Create backup directories
mkdir -p "$BACKUP_ROOT/databases"
mkdir -p "$BACKUP_ROOT/claude-config"
mkdir -p "$BACKUP_ROOT/git-snapshots"

# 1. Backup Memory Database (CRITICAL)
echo -e "${YELLOW}[1/5] Backing up memory database...${NC}"
MEMORY_DB="/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"
if [ -f "$MEMORY_DB" ]; then
    cp "$MEMORY_DB" "$BACKUP_ROOT/databases/memories_$DATE_ONLY.db"
    echo "  ✓ Memory database backed up ($(du -h "$MEMORY_DB" | cut -f1))"
else
    echo "  ✗ Memory database not found!"
fi

# 2. Backup Claude Config (agents, skills, settings)
echo -e "${YELLOW}[2/5] Backing up Claude config...${NC}"
CLAUDE_CONFIG="/home/weber/.claude"
if [ -d "$CLAUDE_CONFIG" ]; then
    cp -r "$CLAUDE_CONFIG/agents" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp -r "$CLAUDE_CONFIG/commands" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp -r "$CLAUDE_CONFIG/mcp-configs" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp "$CLAUDE_CONFIG/settings.json" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp "$CLAUDE_CONFIG/CLAUDE.md" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    # Skills symlink - copy actual content
    if [ -L "$CLAUDE_CONFIG/skills" ]; then
        cp -rL "$CLAUDE_CONFIG/skills" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    fi
    echo "  ✓ Claude config backed up"
else
    echo "  ✗ Claude config not found!"
fi

# 3. Git push RevitMCPBridge2026
echo -e "${YELLOW}[3/5] Pushing RevitMCPBridge2026 to GitHub...${NC}"
if [ -d "/mnt/d/RevitMCPBridge2026/.git" ]; then
    cd /mnt/d/RevitMCPBridge2026
    git add -A 2>/dev/null || true
    git commit -m "Auto-backup: $TIMESTAMP" 2>/dev/null || echo "  (No changes to commit)"
    git push origin master 2>/dev/null && echo "  ✓ RevitMCPBridge2026 pushed" || echo "  (Push skipped or failed)"
else
    echo "  ✗ RevitMCPBridge2026 not a git repo"
fi

# 4. Git push Claude Tools
echo -e "${YELLOW}[4/5] Pushing Claude Tools to GitHub...${NC}"
if [ -d "/mnt/d/_CLAUDE-TOOLS/.git" ]; then
    cd /mnt/d/_CLAUDE-TOOLS
    git add -A 2>/dev/null || true
    git commit -m "Auto-backup: $TIMESTAMP" 2>/dev/null || echo "  (No changes to commit)"
    git push origin master 2>/dev/null && echo "  ✓ Claude Tools pushed" || echo "  (Push skipped or failed)"
else
    echo "  ✗ Claude Tools not a git repo"
fi

# 5. Cleanup old backups (keep last 7 days of databases)
echo -e "${YELLOW}[5/5] Cleaning up old backups...${NC}"
find "$BACKUP_ROOT/databases" -name "memories_*.db" -mtime +7 -delete 2>/dev/null || true
echo "  ✓ Old backups cleaned"

# Summary
echo ""
echo -e "${GREEN}=== Backup Complete ===${NC}"
echo "Local backup location: $BACKUP_ROOT"
echo ""
echo "GitHub repositories:"
echo "  - https://github.com/WeberG619/RevitMCPBridge2026"
echo "  - https://github.com/WeberG619/claude-ai-tools"
echo ""
echo "To sync to Google Drive:"
echo "  1. Open Google Drive in browser"
echo "  2. Upload $BACKUP_ROOT/databases/ folder"
echo "  Or install rclone: sudo apt install rclone && rclone config"
