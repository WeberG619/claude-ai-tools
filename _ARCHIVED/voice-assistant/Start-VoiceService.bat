@echo off
title Claude Voice Service
cd /d "D:\_CLAUDE-TOOLS\voice-assistant"
echo Starting Claude Voice Service (Console Mode)...
echo Say "Hey Claude" followed by your command
echo Say "Goodbye" to exit
echo.
python voice_service.py
pause
