@echo off
REM Claude Gateway Daemon - Auto-start via WSL
REM Starts all gateway services: telegram-bot, proactive, email-watcher, hub, web-chat
REM Waits for WSL to be ready, then launches daemon.sh

REM Wait a moment for WSL to initialize on boot
timeout /t 10 /nobreak > nul

REM Start the gateway daemon in WSL (background, no window)
wsl -d Ubuntu bash -c "/mnt/d/_CLAUDE-TOOLS/gateway/daemon.sh start >> /mnt/d/_CLAUDE-TOOLS/gateway/logs/startup.log 2>&1"

echo Claude Gateway started.
