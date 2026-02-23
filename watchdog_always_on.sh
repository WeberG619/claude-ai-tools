#!/bin/bash
# ============================================
# ALWAYS-ON WATCHDOG - Cron Health Monitor
# ============================================
# Checks all services every 5 minutes.
# Auto-restarts dead services. Kills runaways.
#
# Install:
#   crontab -e
#   */5 * * * * /mnt/d/_CLAUDE-TOOLS/watchdog_always_on.sh >> /mnt/d/_CLAUDE-TOOLS/gateway/logs/watchdog.log 2>&1
# ============================================

TOOLS_DIR="/mnt/d/_CLAUDE-TOOLS"
PID_DIR="$TOOLS_DIR/gateway/pids"
LOG_DIR="$TOOLS_DIR/gateway/logs"

# Load environment
if [ -f "$TOOLS_DIR/.env" ]; then
    set -a
    source "$TOOLS_DIR/.env"
    set +a
fi

NOW=$(date '+%Y-%m-%d %H:%M:%S')
RESTARTED=()

log() {
    echo "[$NOW] $*"
}

# ── Check & Restart Function ──

check_service() {
    local name=$1
    local pidfile="$PID_DIR/$name.pid"

    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Running
        fi
        rm -f "$pidfile"
    fi
    return 1  # Dead
}

restart_service() {
    local name=$1
    log "RESTART: $name is dead, restarting..."
    RESTARTED+=("$name")
}

# ── Check Gateway Services ──

GATEWAY_SERVICES="ps-bridge gateway-hub telegram-bot proactive email-watcher"
GATEWAY_DEAD=false

for svc in $GATEWAY_SERVICES; do
    if ! check_service "$svc"; then
        GATEWAY_DEAD=true
        log "DEAD: gateway service '$svc'"
    fi
done

if [ "$GATEWAY_DEAD" = true ]; then
    log "Restarting gateway services..."
    "$TOOLS_DIR/gateway/daemon.sh" start >> "$LOG_DIR/watchdog.log" 2>&1
    RESTARTED+=("gateway")
fi

# ── Check Autonomous Agent ──

if ! check_service "autonomous-agent"; then
    log "DEAD: autonomous-agent, restarting..."
    (
        while true; do
            cd "$TOOLS_DIR/autonomous-agent" && python3 -u core/agent.py
            sleep 5
        done
    ) >> "$LOG_DIR/autonomous-agent.log" 2>&1 &
    echo $! > "$PID_DIR/autonomous-agent.pid"
    RESTARTED+=("autonomous-agent")
fi

# ── Check OpportunityEngine ──

if ! check_service "opportunityengine"; then
    log "DEAD: opportunityengine, restarting..."
    (
        while true; do
            cd "$TOOLS_DIR/opportunityengine" && python3 -u daemon.py
            sleep 5
        done
    ) >> "$LOG_DIR/opportunityengine.log" 2>&1 &
    echo $! > "$PID_DIR/opportunityengine.pid"
    RESTARTED+=("opportunityengine")
fi

# ── Kill Runaway Claude Processes (>30 minutes) ──

RUNAWAY_KILLED=0
while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $1}')
    etime=$(echo "$line" | awk '{print $2}')

    # Parse elapsed time (formats: MM:SS, HH:MM:SS, D-HH:MM:SS)
    minutes=0
    if echo "$etime" | grep -q '-'; then
        # Days format: D-HH:MM:SS
        minutes=9999
    elif echo "$etime" | grep -qP '^\d+:\d+:\d+$'; then
        # HH:MM:SS
        hours=$(echo "$etime" | cut -d: -f1)
        mins=$(echo "$etime" | cut -d: -f2)
        minutes=$((hours * 60 + mins))
    else
        # MM:SS
        mins=$(echo "$etime" | cut -d: -f1)
        minutes=$mins
    fi

    if [ "$minutes" -gt 30 ]; then
        log "RUNAWAY: Killing claude process PID $pid (running $etime)"
        kill "$pid" 2>/dev/null
        sleep 1
        kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
        RUNAWAY_KILLED=$((RUNAWAY_KILLED + 1))
    fi
done < <(pgrep -f "claude.*--dangerously-skip-permissions" -a 2>/dev/null | while read -r cpid rest; do
    etime=$(ps -o etime= -p "$cpid" 2>/dev/null | tr -d ' ')
    [ -n "$etime" ] && echo "$cpid $etime"
done)

# ── Notify if anything happened ──

if [ ${#RESTARTED[@]} -gt 0 ] || [ "$RUNAWAY_KILLED" -gt 0 ]; then
    MSG="Watchdog Report ($NOW):"
    if [ ${#RESTARTED[@]} -gt 0 ]; then
        MSG="$MSG\nRestarted: ${RESTARTED[*]}"
    fi
    if [ "$RUNAWAY_KILLED" -gt 0 ]; then
        MSG="$MSG\nKilled $RUNAWAY_KILLED runaway Claude process(es)"
    fi

    # Send to Telegram
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=$(echo -e "$MSG")" \
            > /dev/null 2>&1
    fi

    log "$MSG"
else
    log "OK: All services healthy"
fi
