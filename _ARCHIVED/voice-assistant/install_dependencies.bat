@echo off
echo Installing Claude Voice Assistant Dependencies...
echo.

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)

echo Installing Python packages...
pip install SpeechRecognition pyaudio edge-tts pystray pillow

if errorlevel 1 (
    echo.
    echo NOTE: If pyaudio fails, you may need to install it manually:
    echo   pip install pipwin
    echo   pipwin install pyaudio
    echo.
)

echo.
echo Installation complete!
echo.
echo To start the voice assistant:
echo   - Console mode: python voice_service.py
echo   - Background mode: pythonw voice_tray.pyw
echo.
pause
