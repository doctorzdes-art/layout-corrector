@echo off
cd /d "%~dp0"
if not exist venv (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Make sure Python is installed and in your PATH.
        pause
        exit /b 1
    )
)

echo [INFO] Installing/updating dependencies...
call .\venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [INFO] Starting Keyboard Layout Corrector in background...
start "" ".\venv\Scripts\pythonw.exe" main.py
echo [SUCCESS] Application has been launched in the system tray (near the clock).
echo You can close this command window.
timeout /t 5
