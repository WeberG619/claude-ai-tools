@echo off
:: Revit Dialog Auto-Closer
:: Run this when Revit is starting up to auto-dismiss add-in dialogs
:: Author: BIM Ops Studio

echo.
echo ========================================
echo   Revit Dialog Auto-Closer
echo   Will close startup dialogs for you
echo ========================================
echo.

:: Try Python version first (more reliable)
python "%~dp0click_close_button.py" %*
if %ERRORLEVEL% EQU 0 goto :done

:: Fallback to PowerShell version
echo Python version failed, trying PowerShell...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0click_close_button.ps1" %*

:done
echo.
pause
