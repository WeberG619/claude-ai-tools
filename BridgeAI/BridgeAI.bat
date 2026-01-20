@echo off
title BridgeAI - Your Personal AI Assistant
color 0B

echo.
echo  ============================================
echo       BridgeAI - Your AI Assistant
echo  ============================================
echo.
echo  Starting up... Please wait.
echo.

cd /d D:\_CLAUDE-TOOLS\BridgeAI

:: Check if Claude Code is installed
where claude >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Claude Code is not installed.
    echo.
    echo  Please install it first:
    echo    npm install -g @anthropic-ai/claude-code
    echo.
    pause
    exit /b 1
)

:: Start Claude Code in the BridgeAI directory
claude

echo.
echo  BridgeAI session ended.
echo.
pause
