#!/bin/bash
# Claude Memory Backup Script
# Maintains rotating backups with integrity verification
# Run via cron: 0 * * * * /mnt/d/_CLAUDE-TOOLS/claude-memory-server/scripts/backup-memory.sh

set -e

# Configuration
MEMORY_DIR="/mnt/d/_CLAUDE-TOOLS/claude-memory-server"
DB_FILE="$MEMORY_DIR/data/memories.db"
BACKUP_DIR="$MEMORY_DIR/backups"
LOG_FILE="$BACKUP_DIR/backup.log"
MAX_HOURLY=24      # Keep 24 hourly backups
MAX_DAILY=7        # Keep 7 daily backups
MAX_WEEKLY=4       # Keep 4 weekly backups

# Create backup directories
mkdir -p "$BACKUP_DIR/hourly"
mkdir -p "$BACKUP_DIR/daily"
mkdir -p "$BACKUP_DIR/weekly"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "$1"
}

# Verify database integrity before backup
verify_db() {
    log "Verifying database integrity..."
    INTEGRITY=$(sqlite3 "$DB_FILE" "PRAGMA integrity_check;" 2>&1)
    if [ "$INTEGRITY" != "ok" ]; then
        log "ERROR: Database integrity check failed: $INTEGRITY"
        return 1
    fi
    log "Database integrity OK"
    return 0
}

# Create backup using SQLite's online backup API (safe while DB is in use)
create_backup() {
    local backup_path="$1"
    log "Creating backup: $backup_path"

    # Use SQLite's backup command for consistency
    sqlite3 "$DB_FILE" ".backup '$backup_path'"

    # Verify the backup
    BACKUP_INTEGRITY=$(sqlite3 "$backup_path" "PRAGMA integrity_check;" 2>&1)
    if [ "$BACKUP_INTEGRITY" != "ok" ]; then
        log "ERROR: Backup integrity check failed!"
        rm -f "$backup_path"
        return 1
    fi

    # Get record counts for verification
    MEMORY_COUNT=$(sqlite3 "$backup_path" "SELECT COUNT(*) FROM memories;")
    log "Backup verified: $MEMORY_COUNT memories"

    return 0
}

# Rotate old backups
rotate_backups() {
    local dir="$1"
    local max="$2"
    local pattern="$3"

    # Count current backups
    local count=$(ls -1 "$dir"/$pattern 2>/dev/null | wc -l)

    if [ "$count" -gt "$max" ]; then
        local to_delete=$((count - max))
        log "Rotating $to_delete old backups in $dir"
        ls -1t "$dir"/$pattern | tail -n "$to_delete" | while read f; do
            rm -f "$dir/$f"
            log "Deleted old backup: $f"
        done
    fi
}

# Main backup process
main() {
    log "========== Starting backup =========="

    # Check if database exists
    if [ ! -f "$DB_FILE" ]; then
        log "ERROR: Database not found at $DB_FILE"
        exit 1
    fi

    # Verify database before backup
    if ! verify_db; then
        log "Skipping backup due to integrity failure"
        exit 1
    fi

    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    DAY_OF_WEEK=$(date '+%u')  # 1=Monday, 7=Sunday
    HOUR=$(date '+%H')

    # Always create hourly backup
    HOURLY_BACKUP="$BACKUP_DIR/hourly/memory_${TIMESTAMP}.db"
    if create_backup "$HOURLY_BACKUP"; then
        log "Hourly backup successful"
    else
        log "ERROR: Hourly backup failed!"
        exit 1
    fi

    # At midnight, also create daily backup
    if [ "$HOUR" == "00" ]; then
        DAILY_BACKUP="$BACKUP_DIR/daily/memory_$(date '+%Y%m%d').db"
        cp "$HOURLY_BACKUP" "$DAILY_BACKUP"
        log "Daily backup created"

        # On Sunday, also create weekly backup
        if [ "$DAY_OF_WEEK" == "7" ]; then
            WEEKLY_BACKUP="$BACKUP_DIR/weekly/memory_$(date '+%Y_week%W').db"
            cp "$HOURLY_BACKUP" "$WEEKLY_BACKUP"
            log "Weekly backup created"
        fi
    fi

    # Rotate old backups
    rotate_backups "$BACKUP_DIR/hourly" "$MAX_HOURLY" "memory_*.db"
    rotate_backups "$BACKUP_DIR/daily" "$MAX_DAILY" "memory_*.db"
    rotate_backups "$BACKUP_DIR/weekly" "$MAX_WEEKLY" "memory_*.db"

    # Report backup status
    log "Backup complete. Current backup counts:"
    log "  Hourly: $(ls -1 $BACKUP_DIR/hourly/memory_*.db 2>/dev/null | wc -l)"
    log "  Daily:  $(ls -1 $BACKUP_DIR/daily/memory_*.db 2>/dev/null | wc -l)"
    log "  Weekly: $(ls -1 $BACKUP_DIR/weekly/memory_*.db 2>/dev/null | wc -l)"

    # Calculate total backup size
    TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    log "Total backup size: $TOTAL_SIZE"

    log "========== Backup finished =========="
}

# Run main
main
