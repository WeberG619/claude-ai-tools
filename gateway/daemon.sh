#!/bin/bash
# ============================================
# CLAUDE PERSONAL ASSISTANT - 24/7 DAEMON
# ============================================
# Starts all services and keeps them alive with auto-restart.
#
# Usage:
#   ./daemon.sh start    - Start all services in background
#   ./daemon.sh stop     - Stop all services
#   ./daemon.sh status   - Check service status
#   ./daemon.sh restart  - Restart all services
#   ./daemon.sh logs     - Tail all logs
#
# Auto-start at WSL boot:
#   Add to /etc/wsl.conf [boot] section or ~/.bashrc
# ============================================

TOOLS_DIR="/mnt/d/_CLAUDE-TOOLS"
LOG_DIR="$TOOLS_DIR/gateway/logs"
PID_DIR="$TOOLS_DIR/gateway/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

# Service definitions: name, command, working directory
declare -A SERVICES
declare -A SERVICE_DIRS

SERVICES[gateway-hub]="python3 hub.py"
SERVICE_DIRS[gateway-hub]="$TOOLS_DIR/gateway"

SERVICES[telegram-bot]="python3 bot.py"
SERVICE_DIRS[telegram-bot]="$TOOLS_DIR/telegram-gateway"

# WhatsApp must run on Windows side (Puppeteer needs Windows Chrome)
SERVICES[whatsapp-gw]="cmd.exe /c node server.js"
SERVICE_DIRS[whatsapp-gw]="$TOOLS_DIR/whatsapp-gateway"

SERVICES[web-chat]="python3 server.py"
SERVICE_DIRS[web-chat]="$TOOLS_DIR/web-chat"

SERVICES[proactive]="python3 scheduler.py"
SERVICE_DIRS[proactive]="$TOOLS_DIR/proactive"

# ============================================
# FUNCTIONS
# ============================================

start_service() {
    local name=$1
    local cmd="${SERVICES[$name]}"
    local dir="${SERVICE_DIRS[$name]}"
    local pidfile="$PID_DIR/$name.pid"
    local logfile="$LOG_DIR/$name.log"

    # Check if already running
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  [$name] Already running (PID $pid)"
            return 0
        fi
        rm -f "$pidfile"
    fi

    # Start with auto-restart wrapper
    (
        while true; do
            echo "[$(date)] Starting $name..." >> "$logfile"
            cd "$dir" && $cmd >> "$logfile" 2>&1
            local exit_code=$?
            echo "[$(date)] $name exited with code $exit_code. Restarting in 5s..." >> "$logfile"
            sleep 5
        done
    ) &

    local wrapper_pid=$!
    echo $wrapper_pid > "$pidfile"
    echo "  [$name] Started (PID $wrapper_pid)"
}

stop_service() {
    local name=$1
    local pidfile="$PID_DIR/$name.pid"

    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            # Kill the wrapper and all children
            pkill -P "$pid" 2>/dev/null
            kill "$pid" 2>/dev/null
            rm -f "$pidfile"
            echo "  [$name] Stopped"
        else
            rm -f "$pidfile"
            echo "  [$name] Was not running (stale PID)"
        fi
    else
        echo "  [$name] Not running"
    fi
}

status_service() {
    local name=$1
    local pidfile="$PID_DIR/$name.pid"
    local logfile="$LOG_DIR/$name.log"

    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
            local last_log=""
            if [ -f "$logfile" ]; then
                last_log=$(tail -1 "$logfile" 2>/dev/null | head -c 80)
            fi
            echo "  [OK] $name (PID $pid, uptime: $uptime)"
            [ -n "$last_log" ] && echo "        Last: $last_log"
        else
            rm -f "$pidfile"
            echo "  [!!] $name - Dead (stale PID $pid, removed)"
        fi
    else
        echo "  [--] $name - Not running"
    fi
}

# ============================================
# COMMANDS
# ============================================

case "${1:-status}" in
    start)
        echo "============================================"
        echo "CLAUDE ASSISTANT DAEMON - STARTING"
        echo "============================================"
        echo ""
        for name in gateway-hub telegram-bot whatsapp-gw web-chat proactive; do
            start_service "$name"
        done
        echo ""
        echo "All services started. Use '$0 status' to check."
        echo "Logs: $LOG_DIR/"
        echo "============================================"
        ;;

    stop)
        echo "============================================"
        echo "CLAUDE ASSISTANT DAEMON - STOPPING"
        echo "============================================"
        echo ""
        for name in proactive web-chat whatsapp-gw telegram-bot gateway-hub; do
            stop_service "$name"
        done
        echo ""
        echo "All services stopped."
        echo "============================================"
        ;;

    restart)
        echo "Restarting all services..."
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        echo "============================================"
        echo "CLAUDE ASSISTANT - SERVICE STATUS"
        echo "$(date)"
        echo "============================================"
        echo ""
        for name in gateway-hub telegram-bot whatsapp-gw web-chat proactive; do
            status_service "$name"
        done
        echo ""
        echo "Logs: $LOG_DIR/"
        echo "============================================"
        ;;

    logs)
        echo "Tailing all service logs (Ctrl+C to stop)..."
        tail -f "$LOG_DIR"/*.log
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
