@echo off
REM Stop Claude Daemon
taskkill /F /IM pythonw.exe 2>nul
echo Claude Daemon stopped.
