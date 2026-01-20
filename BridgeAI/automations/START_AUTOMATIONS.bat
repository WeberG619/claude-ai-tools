@echo off
echo ========================================
echo   BridgeAI Lightweight Automations
echo   Optimized for 8GB RAM
echo ========================================
echo.

cd /d C:\BridgeAI\automations

echo Starting Automation Runner with API...
echo (This runs: Monitor, File Watcher, Backups)
echo.

python automation_runner.py --api

pause
