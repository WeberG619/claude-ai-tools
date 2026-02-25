@echo off
REM Business Pulse Heartbeat - Start Script
REM Run this to start the heartbeat daemon, or schedule via Task Scheduler
REM
REM To schedule hourly:
REM   schtasks /create /tn "BIMOps-BusinessPulse" /tr "python D:\_CLAUDE-TOOLS\business-pulse\heartbeat.py" /sc hourly /st 00:00

echo Starting Business Pulse Heartbeat...
cd /d D:\_CLAUDE-TOOLS\business-pulse
python heartbeat.py --daemon
