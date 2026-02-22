#!/bin/bash
# OpportunityEngine watchdog - restarts daemon if it dies
# Usage: nohup bash watchdog.sh &

OE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$OE_DIR/daemon.pid"
LOGFILE="$OE_DIR/daemon.log"

echo "[$(date)] Watchdog started for OpportunityEngine" >> "$LOGFILE"

while true; do
    # Check if daemon is running
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            # Still running, check again in 60 seconds
            sleep 60
            continue
        fi
    fi

    # Daemon is not running - start it
    echo "[$(date)] Watchdog: starting daemon..." >> "$LOGFILE"
    cd "$OE_DIR"
    python3 daemon.py &
    echo $! > "$PIDFILE"
    echo "[$(date)] Watchdog: daemon started with PID $(cat "$PIDFILE")" >> "$LOGFILE"

    # Wait before checking again
    sleep 60
done
