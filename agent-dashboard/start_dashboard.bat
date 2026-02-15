@echo off
echo ==========================================
echo    Agent Command Center Dashboard
echo ==========================================
echo.
echo Starting server on http://localhost:8080
echo Press Ctrl+C to stop
echo.

cd /d D:\_CLAUDE-TOOLS\agent-dashboard
python server.py

pause
