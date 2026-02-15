@echo off
title MCP Seatbelt Dashboard
echo.
echo ========================================
echo   MCP Seatbelt Dashboard
echo   Opening http://localhost:5050
echo ========================================
echo.

cd /d "%~dp0"

:: Check for Flask
python -c "import flask" 2>NUL
if errorlevel 1 (
    echo Installing Flask...
    pip install flask
)

:: Start browser after delay
start "" cmd /c "timeout /t 2 >NUL && start http://localhost:5050"

:: Run the dashboard
python app.py

pause
