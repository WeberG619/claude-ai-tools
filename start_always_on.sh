#!/bin/bash
# ============================================
# ALWAYS-ON AI SYSTEM - MASTER STARTUP
# ============================================
# Starts all services in dependency order:
#   1. Gateway (Telegram, email, web chat, proactive scheduler)
#   2. Autonomous Agent (task queue, triggers, dispatching)
#   3. OpportunityEngine (scouts, proposals, pipeline)
#
# Idempotent: won't double-start running services.
#
# Usage:
#   ./start_always_on.sh          - Start everything
#   ./start_always_on.sh stop     - Stop everything
#   ./start_always_on.sh status   - Check all services
# ============================================

set -euo pipefail

TOOLS_DIR="/mnt/d/_CLAUDE-TOOLS"
LOG_DIR="$TOOLS_DIR/gateway/logs"
PID_DIR="$TOOLS_DIR/gateway/pids"
ALWAYS_ON_LOG="$LOG_DIR/always_on.log"

mkdir -p "$LOG_DIR" "$PID_DIR"

# Load environment variables
if [ -f "$TOOLS_DIR/.env" ]; then
    set -a
    source "$TOOLS_DIR/.env"
    set +a
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$ALWAYS_ON_LOG"
}

is_running() {
    local pidfile="$PID_DIR/$1.pid"
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        rm -f "$pidfile"
    fi
    return 1
}

wait_for_service() {
    local name=$1
    local max_wait=${2:-10}
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if is_running "$name"; then
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

start_daemon_service() {
    local name=$1
    local cmd=$2
    local dir=$3
    local pidfile="$PID_DIR/$name.pid"
    local logfile="$LOG_DIR/$name.log"

    if is_running "$name"; then
        log "  [$name] Already running (PID $(cat "$pidfile"))"
        return 0
    fi

    (
        # Source env inside subprocess so child processes inherit vars
        if [ -f "$TOOLS_DIR/.env" ]; then
            set -a; source "$TOOLS_DIR/.env"; set +a
        fi
        while true; do
            echo "[$(date)] Starting $name..."
            cd "$dir" && eval "$cmd"
            exit_code=$?
            echo "[$(date)] $name exited with code $exit_code. Restarting in 5s..."
            sleep 5
        done
    ) >> "$logfile" 2>&1 &

    echo $! > "$pidfile"
    log "  [$name] Started (PID $!)"
}

# ============================================
# STOP
# ============================================

stop_all() {
    log "============================================"
    log "ALWAYS-ON AI SYSTEM - STOPPING"
    log "============================================"

    # Stop in reverse order
    for name in opportunityengine autonomous-agent; do
        local pidfile="$PID_DIR/$name.pid"
        if [ -f "$pidfile" ]; then
            local pid
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null
                sleep 0.5
                pkill -P "$pid" 2>/dev/null
                sleep 0.5
                kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
            fi
            rm -f "$pidfile"
            log "  [$name] Stopped"
        else
            log "  [$name] Not running"
        fi
    done

    # Stop gateway services
    "$TOOLS_DIR/gateway/daemon.sh" stop

    log "All services stopped."
}

# ============================================
# STATUS
# ============================================

status_all() {
    echo "============================================"
    echo "ALWAYS-ON AI SYSTEM - STATUS"
    echo "$(date)"
    echo "============================================"
    echo ""

    echo "--- Gateway Services ---"
    "$TOOLS_DIR/gateway/daemon.sh" status
    echo ""

    echo "--- Autonomous Agent ---"
    if is_running "autonomous-agent"; then
        local pid
        pid=$(cat "$PID_DIR/autonomous-agent.pid")
        local uptime
        uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
        echo "  [OK] autonomous-agent (PID $pid, uptime: $uptime)"
    else
        echo "  [--] autonomous-agent - Not running"
    fi

    echo ""
    echo "--- OpportunityEngine ---"
    if is_running "opportunityengine"; then
        local pid
        pid=$(cat "$PID_DIR/opportunityengine.pid")
        local uptime
        uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
        echo "  [OK] opportunityengine (PID $pid, uptime: $uptime)"
    else
        echo "  [--] opportunityengine - Not running"
    fi

    echo ""
    echo "============================================"
}

# ============================================
# START
# ============================================

start_all() {
    log "============================================"
    log "ALWAYS-ON AI SYSTEM - STARTING"
    log "============================================"
    log ""

    # ── Step 1: Gateway Services ──
    log "Step 1/3: Starting Gateway Services..."
    "$TOOLS_DIR/gateway/daemon.sh" start
    sleep 2

    # Health check: verify Telegram bot is up
    if is_running "telegram-bot"; then
        log "  Telegram bot confirmed running"
    else
        log "  WARNING: Telegram bot may not have started"
    fi
    log ""

    # ── Step 2: Autonomous Agent ──
    log "Step 2/3: Starting Autonomous Agent..."
    start_daemon_service "autonomous-agent" \
        "python3 -u core/agent.py" \
        "$TOOLS_DIR/autonomous-agent"

    if wait_for_service "autonomous-agent" 5; then
        log "  Autonomous Agent confirmed running"
    else
        log "  WARNING: Autonomous Agent may not have started"
    fi
    log ""

    # ── Step 3: OpportunityEngine ──
    log "Step 3/3: Starting OpportunityEngine..."
    start_daemon_service "opportunityengine" \
        "python3 -u daemon.py" \
        "$TOOLS_DIR/opportunityengine"

    if wait_for_service "opportunityengine" 5; then
        log "  OpportunityEngine confirmed running"
    else
        log "  WARNING: OpportunityEngine may not have started"
    fi
    log ""

    log "============================================"
    log "ALL SERVICES STARTED"
    log "============================================"
    log "Use '$0 status' to verify."
    log "Logs: $LOG_DIR/"
}

# ============================================
# MAIN
# ============================================

case "${1:-start}" in
    start)   start_all ;;
    stop)    stop_all ;;
    status)  status_all ;;
    restart)
        stop_all
        sleep 3
        start_all
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
