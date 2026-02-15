#!/bin/bash
# Office Command Center - Launch Script
# Starts the Electron dashboard and optionally runs a task

cd "$(dirname "$0")"

echo "🏢 Office Command Center Starting..."

# Start Electron dashboard in background
cd electron-dashboard
npm start &
ELECTRON_PID=$!

cd ..

# Wait for dashboard to load
sleep 3

echo "✓ Dashboard running (PID: $ELECTRON_PID)"
echo ""
echo "Commands:"
echo "  python3 run_team.py --task 'Your task here'"
echo "  python3 run_team.py --email --to 'email@example.com' --subject 'Subject'"
echo "  python3 run_team.py --calendar"
echo "  python3 run_team.py --followup 'Task title' --due '2026-02-06'"
echo ""
echo "Press Ctrl+C to stop"

# Keep running
wait $ELECTRON_PID
