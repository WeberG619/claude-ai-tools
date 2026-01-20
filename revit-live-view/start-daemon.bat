@echo off
echo Starting Revit Live View Capture Daemon...
echo.
echo This will capture Revit windows every 5 seconds.
echo Screenshots saved to D:\revit_live_view.png
echo.
echo Press Ctrl+C to stop.
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0revit-capture-daemon.ps1" -IntervalSeconds 5 -Verbose
pause
