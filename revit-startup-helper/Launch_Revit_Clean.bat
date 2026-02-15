@echo off
:: Launch Revit with Dialog Auto-Dismisser v2.0
:: Use this instead of the regular Revit shortcut
:: Author: BIM Ops Studio

echo ========================================
echo   Launching Revit with Auto-Dismisser
echo   v2.0 - Enhanced Dialog Detection
echo ========================================
echo.

:: Launch Revit FIRST, then start dismisser
echo Launching Revit...
if exist "C:\Program Files\Autodesk\Revit 2026\Revit.exe" (
    start "" "C:\Program Files\Autodesk\Revit 2026\Revit.exe"
    echo Revit 2026 starting...
) else if exist "C:\Program Files\Autodesk\Revit 2025\Revit.exe" (
    start "" "C:\Program Files\Autodesk\Revit 2025\Revit.exe"
    echo Revit 2025 starting...
) else (
    echo ERROR: Revit not found!
    pause
    exit /b 1
)

:: Small delay for Revit to begin loading
timeout /t 2 /nobreak > nul

:: Start the enhanced dialog dismisser in background
echo Starting enhanced dialog auto-dismisser...
start "" /MIN powershell.exe -ExecutionPolicy Bypass -File "%~dp0smart_dismiss_dialogs.ps1" -Quiet

echo.
echo Dialog auto-dismisser is running in background.
echo It will actively find and close Revit startup dialogs.
echo.
