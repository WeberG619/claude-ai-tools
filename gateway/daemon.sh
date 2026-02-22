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
# SERVICE_OWN_LOG: set to "1" if service writes its own log (daemon redirects to /dev/null)
declare -A SERVICES
declare -A SERVICE_DIRS
declare -A SERVICE_OWN_LOG

SERVICES[gateway-hub]="python3 hub.py"
SERVICE_DIRS[gateway-hub]="$TOOLS_DIR/gateway"

SERVICES[telegram-bot]="python3 bot.py"
SERVICE_DIRS[telegram-bot]="$TOOLS_DIR/telegram-gateway"

# WhatsApp must run on Windows side (Puppeteer needs Windows Chrome)
# Use powershell.exe with -WindowStyle Hidden to prevent visible cmd popup on restart loops
SERVICES[whatsapp-gw]="powershell.exe -WindowStyle Hidden -NoProfile -Command \"node server.js\""
SERVICE_DIRS[whatsapp-gw]="$TOOLS_DIR/whatsapp-gateway"

SERVICES[web-chat]="python3 server.py"
SERVICE_DIRS[web-chat]="$TOOLS_DIR/web-chat"

# Proactive scheduler handles its own FileHandler logging to proactive.log
SERVICES[proactive]="python3 -u scheduler.py"
SERVICE_DIRS[proactive]="$TOOLS_DIR/proactive"
SERVICE_OWN_LOG[proactive]="1"

SERVICES[email-watcher]="python3 -u email_watcher.py"
SERVICE_DIRS[email-watcher]="$TOOLS_DIR/email-watcher"

SERVICES[ps-bridge]="python3 bridge.py"
SERVICE_DIRS[ps-bridge]="$TOOLS_DIR/powershell-bridge"

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
    if [ "${SERVICE_OWN_LOG[$name]}" = "1" ]; then
        # Service handles its own logging - redirect daemon output to /dev/null
        (
            while true; do
                cd "$dir" && $cmd
                sleep 5
            done
        ) > /dev/null 2>&1 &
    else
        # Daemon handles logging via redirect
        (
            while true; do
                echo "[$(date)] Starting $name..."
                cd "$dir" && $cmd
                local exit_code=$?
                echo "[$(date)] $name exited with code $exit_code. Restarting in 5s..."
                sleep 5
            done
        ) >> "$logfile" 2>&1 &
    fi

    local wrapper_pid=$!
    echo $wrapper_pid > "$pidfile"
    echo "  [$name] Started (PID $wrapper_pid)"
}

stop_service() {
    local name=$1
    local pidfile="$PID_DIR/$name.pid"
    local cmd="${SERVICES[$name]}"

    # Extract the executable pattern for pkill fallback (e.g. "scheduler.py" from "python3 -u scheduler.py")
    local exe_pattern=$(echo "$cmd" | grep -oP '\S+\.(py|js)$')

    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            # Kill wrapper and entire process tree
            kill "$pid" 2>/dev/null
            sleep 0.3
            pkill -P "$pid" 2>/dev/null
            sleep 0.3
            # Force kill wrapper if still alive
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$pidfile"
    fi

    # Fallback: kill any orphaned processes matching the service command
    if [ -n "$exe_pattern" ]; then
        pkill -f "$exe_pattern" 2>/dev/null
        sleep 0.2
        pkill -9 -f "$exe_pattern" 2>/dev/null
    fi

    echo "  [$name] Stopped"
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
        for name in ps-bridge gateway-hub telegram-bot whatsapp-gw web-chat proactive email-watcher; do
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
        for name in email-watcher proactive web-chat whatsapp-gw telegram-bot gateway-hub ps-bridge; do
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
        for name in ps-bridge gateway-hub telegram-bot whatsapp-gw web-chat proactive email-watcher; do
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
