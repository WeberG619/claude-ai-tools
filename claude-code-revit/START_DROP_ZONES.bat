@echo off
title Revit Drop Zone Monitor
color 0A

echo.
echo =====================================================
echo   REVIT DROP ZONE MONITOR - Ready to Help!
echo =====================================================
echo.

cd /d D:\claude-code-revit

echo Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.7+
    pause
    exit
)

echo.
echo Starting drop zone monitoring...
echo.
echo Drop files into these folders:
echo   [CODE] D:\claude-code-revit\revit_zones\code_generator
echo   [ERROR] D:\claude-code-revit\revit_zones\error_debugger
echo   [TEST] D:\claude-code-revit\dev_zones\test_generator
echo   [DOCS] D:\claude-code-revit\dev_zones\doc_builder
echo.
echo Press Ctrl+C to stop
echo.

python dropzone_monitor.py

pause