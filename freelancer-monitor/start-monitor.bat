@echo off
title Freelancer Job Monitor
echo ==========================================
echo   Freelancer Job Monitor - 24/7 Daemon
echo ==========================================
echo.
echo Starting monitor with 5-minute poll interval...
echo Voice alerts enabled.
echo.
echo Press Ctrl+C to stop.
echo.
node "%~dp0monitor.mjs" --interval 300 --voice
pause
