@echo off
REM Start Claude Daemon as background process
REM This runs continuously and tracks system state

cd /d D:\_CLAUDE-TOOLS\system-bridge
start /B pythonw claude_daemon.py

echo Claude Daemon started in background.
echo State file: D:\_CLAUDE-TOOLS\system-bridge\live_state.json
echo Event log: D:\_CLAUDE-TOOLS\system-bridge\events.jsonl
echo.
echo To stop: taskkill /F /IM pythonw.exe
