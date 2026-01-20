@echo off
echo ========================================
echo    BridgeAI - Starting All Services
echo ========================================
echo.

cd /d C:\BridgeAI

echo [1/4] Starting Hub Server (port 5000)...
start "BridgeAI Hub" /MIN python hub_server.py
timeout /t 2 /nobreak > nul

echo [2/4] Starting Brain API (port 5001)...
start "BridgeAI Brain" /MIN python core\brain.py
timeout /t 2 /nobreak > nul

echo [3/4] Starting Dashboard (port 5002)...
start "BridgeAI Dashboard" /MIN python core\dashboard.py
timeout /t 2 /nobreak > nul

echo [4/4] Starting Automation Service...
start "BridgeAI Automation" /MIN python automation_service.py
timeout /t 2 /nobreak > nul

echo.
echo ========================================
echo    All Services Started!
echo ========================================
echo.
echo Access Points:
echo   Dashboard:    http://localhost:5002
echo   Hub API:      http://localhost:5000
echo   Brain API:    http://localhost:5001
echo.
echo From other devices: http://192.168.1.31:5002
echo.
echo Press any key to close this window...
pause > nul
