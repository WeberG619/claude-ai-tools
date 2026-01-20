@echo off
REM BIM Ops Studio - Windows Backup Launcher
REM Runs the backup script via WSL

echo === BIM Ops Studio Backup ===
echo.

wsl bash /mnt/d/_CLAUDE-TOOLS/backup-system/backup.sh

echo.
echo Backup complete! Press any key to exit...
pause >nul
