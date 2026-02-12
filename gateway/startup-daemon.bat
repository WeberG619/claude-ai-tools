@echo off
REM ============================================
REM CLAUDE ASSISTANT - AUTO-START AT LOGIN
REM ============================================
REM Place a shortcut to this file in:
REM   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
REM
REM Or add via Task Scheduler:
REM   schtasks /create /tn "Claude Assistant Daemon" /tr "D:\_CLAUDE-TOOLS\gateway\startup-daemon.bat" /sc onlogon /rl highest
REM ============================================

echo Starting Claude Assistant Daemon via WSL...
wsl.exe -d Ubuntu bash -c "/mnt/d/_CLAUDE-TOOLS/gateway/daemon.sh start"
echo Daemon started. This window will close in 5 seconds.
timeout /t 5 > nul
