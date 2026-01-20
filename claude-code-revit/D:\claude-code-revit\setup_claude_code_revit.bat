@echo off
echo.
echo =====================================================
echo   Claude Code + Revit Drop Zones Setup
echo =====================================================
echo.

REM Create the setup
python -c "from claude_code_revit_setup import ClaudeCodeRevitSetup; setup = ClaudeCodeRevitSetup(); setup.create_complete_setup()"

echo.
echo Setup Complete!
echo.
echo Next Steps:
echo 1. Add integration to PowerShell profile (see add_to_profile.ps1)
echo 2. Start drop zone monitor
echo 3. Try: New-RevitTool "Your first tool idea"
echo.
pause
