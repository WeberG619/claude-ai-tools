@echo off
title Revit Drop Zone Monitor
color 0A

echo.
echo =====================================================
echo   REVIT DROP ZONE MONITOR - Development Assistant
echo =====================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or later
    pause
    exit /b 1
)

REM Set the paths
set MONITOR_SCRIPT=D:\claude-code-revit\dropzone_monitor.py
set CONFIG_FILE=D:\claude-code-revit\config\dropzone_config.json

REM Check if files exist
if not exist "%MONITOR_SCRIPT%" (
    echo ERROR: Monitor script not found at %MONITOR_SCRIPT%
    pause
    exit /b 1
)

if not exist "%CONFIG_FILE%" (
    echo ERROR: Config file not found at %CONFIG_FILE%
    pause
    exit /b 1
)

echo Starting drop zone monitoring...
echo.
echo Drop files into these folders:
echo   - Code Generator: revit_zones\code_generator
echo   - Error Debugger: revit_zones\error_debugger
echo   - Test Generator: dev_zones\test_generator
echo   - Doc Builder: dev_zones\doc_builder
echo.
echo Press Ctrl+C to stop monitoring
echo.

REM Start the monitor
python "%MONITOR_SCRIPT%"

pause
