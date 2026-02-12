@echo off
echo ============================================
echo CLAUDE PERSONAL ASSISTANT - STARTUP
echo ============================================
echo.

echo Creating log directories...
if not exist "D:\_CLAUDE-TOOLS\gateway\logs" mkdir "D:\_CLAUDE-TOOLS\gateway\logs"
echo.

echo [1/4] Starting Gateway Hub...
start "Gateway Hub" cmd /k "cd /d D:\_CLAUDE-TOOLS\gateway && python hub.py"
timeout /t 2 > nul

echo [2/4] Starting Web Chat Server...
start "Web Chat" cmd /k "cd /d D:\_CLAUDE-TOOLS\web-chat && python server.py"
timeout /t 2 > nul

echo [3/4] Starting Proactive Scheduler...
start "Proactive" cmd /k "cd /d D:\_CLAUDE-TOOLS\proactive && python scheduler.py"
timeout /t 2 > nul

echo [4/5] Starting Telegram Bot...
start "Telegram Bot" cmd /k "cd /d D:\_CLAUDE-TOOLS\telegram-gateway && python bot.py"
timeout /t 2 > nul

echo [5/5] Starting WhatsApp Gateway...
start "WhatsApp" cmd /k "cd /d D:\_CLAUDE-TOOLS\whatsapp-gateway && node server.js"
timeout /t 2 > nul

echo.
echo ============================================
echo          ALL SERVICES STARTED
echo ============================================
echo.
echo ACTIVE SERVICES:
echo   [OK] Gateway Hub          : ws://127.0.0.1:18789
echo   [OK] Web Chat             : http://localhost:5555
echo   [OK] Proactive Scheduler  : Morning briefing at 7 AM
echo   [OK] Telegram Bot         : @YourBot (polling)
echo   [OK] WhatsApp Gateway     : Linked device
echo.
echo WEB CHAT ACCESS (bookmark this):
echo   http://localhost:5555?token=mDtQP460ym6iOHQmtMvASMCYFbfCRe1nurFEPVitDp0
echo.
echo FEATURES:
echo   [X] Voice input/output (click mic/speaker buttons)
echo   [X] Prompt injection protection
echo   [X] Email security scanning
echo   [X] Smart notifications
echo   [X] Morning briefing at 7 AM (via voice + Telegram)
echo   [X] Telegram commands: /quick /email /revit /screenshot
echo   [X] WhatsApp commands: /quick /email /revit /screenshot
echo.
echo STATUS DASHBOARD: python D:\_CLAUDE-TOOLS\gateway\status.py
echo LOGS: D:\_CLAUDE-TOOLS\gateway\logs\
echo ============================================
echo.
echo Press any key to exit this launcher...
pause > nul
