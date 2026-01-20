@echo off
REM Claude Services Startup Script
REM Starts the daemon watchdog (which in turn starts the daemon)

cd /d D:\_CLAUDE-TOOLS\system-bridge

REM Start watchdog in background (it will start daemon if needed)
start "" /B pythonw watchdog.py

REM Brief delay
timeout /t 2 /nobreak > nul

echo Claude services started.
