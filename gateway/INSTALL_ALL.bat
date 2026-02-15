@echo off
echo ============================================
echo CLAUDE PERSONAL ASSISTANT - INSTALL
echo ============================================
echo.

echo Installing Gateway Hub dependencies...
cd /d D:\_CLAUDE-TOOLS\gateway
pip install -r requirements.txt
echo.

echo Installing Web Chat dependencies...
cd /d D:\_CLAUDE-TOOLS\web-chat
pip install -r requirements.txt
echo.

echo Installing Telegram Bot dependencies...
cd /d D:\_CLAUDE-TOOLS\telegram-gateway
pip install -r requirements.txt
echo.

echo Installing WhatsApp Gateway dependencies...
cd /d D:\_CLAUDE-TOOLS\whatsapp-gateway
call npm install
echo.

echo ============================================
echo INSTALLATION COMPLETE
echo ============================================
echo.
echo Next steps:
echo 1. Configure Telegram: Get bot token from @BotFather
echo 2. Edit telegram-gateway/bot.py - set BOT_TOKEN and ALLOWED_USERS
echo 3. Run START_ALL.bat to launch all services
echo 4. For WhatsApp: Run start.bat and scan QR code
echo.
pause
