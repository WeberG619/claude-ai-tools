@echo off
REM Spine Passive Learner - Overnight Extraction
REM Run this from Windows (not WSL) to extract from Revit projects

echo =============================================
echo  SPINE PASSIVE LEARNER - OVERNIGHT TRAINING
echo =============================================
echo.

cd /d "D:\_CLAUDE-TOOLS\spine-passive"

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH
    echo Install Python or add it to PATH
    pause
    exit /b 1
)

echo Starting overnight extraction...
echo This will process all pending Revit projects.
echo.
echo Press Ctrl+C to stop at any time.
echo.

set PYTHONPATH=src
python -m spine_passive extract --overnight --revit-version 2026

echo.
echo =============================================
echo  EXTRACTION COMPLETE
echo =============================================
echo.
echo Run "python -m spine_passive stats" to see results.
echo Run "python -m spine_passive analyze" to see patterns.
echo.
pause
