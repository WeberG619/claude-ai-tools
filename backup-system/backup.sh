#!/bin/bash
# BIM Ops Studio - Automated Backup Script
# Backs up critical AI infrastructure to local storage + pushes to GitHub
# Runs daily via cron at 4 AM

set -e

# Configuration
BACKUP_ROOT="/mnt/d/BACKUP"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)
LOG="$BACKUP_ROOT/backup.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== BIM Ops Studio Backup ===${NC}"
echo "Timestamp: $TIMESTAMP"

# Create backup directories
mkdir -p "$BACKUP_ROOT/databases"
mkdir -p "$BACKUP_ROOT/claude-config"
mkdir -p "$BACKUP_ROOT/brain-state"
mkdir -p "$BACKUP_ROOT/system-bridge"
mkdir -p "$BACKUP_ROOT/reference-docs"

# 1. Backup Memory Database (CRITICAL)
echo -e "${YELLOW}[1/7] Backing up memory database...${NC}"
MEMORY_DB="/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"
if [ -f "$MEMORY_DB" ]; then
    cp "$MEMORY_DB" "$BACKUP_ROOT/databases/memories_$DATE_ONLY.db"
    echo "  Memory database backed up ($(du -h "$MEMORY_DB" | cut -f1))"
else
    echo -e "  ${RED}Memory database not found!${NC}"
fi

# 2. Backup Claude Config (agents, skills, settings, commands)
echo -e "${YELLOW}[2/7] Backing up Claude config...${NC}"
CLAUDE_CONFIG="/home/weber/.claude"
if [ -d "$CLAUDE_CONFIG" ]; then
    cp -r "$CLAUDE_CONFIG/agents" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp -r "$CLAUDE_CONFIG/commands" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp -r "$CLAUDE_CONFIG/mcp-configs" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp "$CLAUDE_CONFIG/settings.json" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp "$CLAUDE_CONFIG/CLAUDE.md" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    cp "$CLAUDE_CONFIG/user.json" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    if [ -d "$CLAUDE_CONFIG/skills" ]; then
        cp -rL "$CLAUDE_CONFIG/skills" "$BACKUP_ROOT/claude-config/" 2>/dev/null || true
    fi
    echo "  Claude config backed up"
else
    echo -e "  ${RED}Claude config not found!${NC}"
fi

# 3. Backup Brain State (session persistence)
echo -e "${YELLOW}[3/7] Backing up brain state...${NC}"
BRAIN="/mnt/d/_CLAUDE-TOOLS/brain-state"
if [ -d "$BRAIN" ]; then
    cp "$BRAIN/brain.json" "$BACKUP_ROOT/brain-state/brain_$DATE_ONLY.json" 2>/dev/null || true
    cp "$BRAIN/live_checkpoint.json" "$BACKUP_ROOT/brain-state/" 2>/dev/null || true
    echo "  Brain state backed up"
else
    echo "  Brain state directory not found"
fi

# 4. Backup System Bridge data (workflows, persistent state)
echo -e "${YELLOW}[4/7] Backing up system bridge data...${NC}"
BRIDGE="/mnt/d/_CLAUDE-TOOLS/system-bridge"
if [ -d "$BRIDGE" ]; then
    cp "$BRIDGE/persistent_state.json" "$BACKUP_ROOT/system-bridge/" 2>/dev/null || true
    cp "$BRIDGE/workflows.db" "$BACKUP_ROOT/system-bridge/workflows_$DATE_ONLY.db" 2>/dev/null || true
    cp "$BRIDGE/intelligence.json" "$BACKUP_ROOT/system-bridge/" 2>/dev/null || true
    echo "  System bridge data backed up"
else
    echo "  System bridge directory not found"
fi

# 5. Backup key reference docs
echo -e "${YELLOW}[5/7] Backing up reference documents...${NC}"
TOOLS="/mnt/d/_CLAUDE-TOOLS"
cp "$TOOLS/WEBER_WORKFLOWS.md" "$BACKUP_ROOT/reference-docs/" 2>/dev/null || true
cp "$TOOLS/CLAUDE_REFERENCE.md" "$BACKUP_ROOT/reference-docs/" 2>/dev/null || true
cp "$TOOLS/WINDOW_MANAGEMENT.md" "$BACKUP_ROOT/reference-docs/" 2>/dev/null || true
cp "$TOOLS/agent-common-sense/kernel.md" "$BACKUP_ROOT/reference-docs/kernel.md" 2>/dev/null || true
cp "$TOOLS/agent-common-sense/kernel-corrections.md" "$BACKUP_ROOT/reference-docs/kernel-corrections.md" 2>/dev/null || true
cp "$TOOLS/agent-boost/strong_agent.md" "$BACKUP_ROOT/reference-docs/strong_agent.md" 2>/dev/null || true
echo "  Reference docs backed up"

# 6. Git push repos (skip if no changes)
echo -e "${YELLOW}[6/7] Pushing to GitHub...${NC}"
for REPO in "/mnt/d/RevitMCPBridge2026" "/mnt/d/_CLAUDE-TOOLS"; do
    REPO_NAME=$(basename "$REPO")
    if [ -d "$REPO/.git" ]; then
        cd "$REPO"
        if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
            git add -A 2>/dev/null || true
            git commit -m "Auto-backup: $TIMESTAMP" 2>/dev/null || true
            git push 2>/dev/null && echo "  $REPO_NAME pushed" || echo "  $REPO_NAME push failed"
        else
            echo "  $REPO_NAME: no changes"
        fi
    fi
done

# 7. Cleanup old backups (keep last 14 days)
echo -e "${YELLOW}[7/7] Cleaning up old backups...${NC}"
find "$BACKUP_ROOT/databases" -name "memories_*.db" -mtime +14 -delete 2>/dev/null || true
find "$BACKUP_ROOT/brain-state" -name "brain_*.json" -mtime +14 -delete 2>/dev/null || true
find "$BACKUP_ROOT/system-bridge" -name "workflows_*.db" -mtime +14 -delete 2>/dev/null || true
echo "  Old backups cleaned (kept last 14 days)"

# Summary
echo ""
echo -e "${GREEN}=== Backup Complete ===${NC}"
echo "Location: $BACKUP_ROOT"
echo "Date: $DATE_ONLY"
echo "$(date)" >> "$LOG"
