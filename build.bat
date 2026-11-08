@echo off
cd /d "%~dp0"
if not exist venv (
    echo [ERROR] Virtual environment not found. Please run run.bat first.
    pause
    exit /b 1
)

echo [INFO] Installing PyInstaller...
call .\venv\Scripts\pip install pyinstaller

echo [INFO] Packaging application into a single EXE file...
call .\venv\Scripts\pyinstaller --noconsole --onefile --name "LayoutCorrector v1.14" --icon="logo.ico" --add-data "logo.png;." --add-data "logo.ico;." --add-data "fonts;fonts" --add-data "icons;icons" --add-data "shapes;shapes" --add-data "theme.qss;." --add-data "design_tokens.json;." --clean main.py

if errorlevel 1 (
    echo [ERROR] Packaging failed.
    pause
    exit /b 1
)

copy /y "dist\LayoutCorrector v1.14.exe" "LayoutCorrector v1.14.exe"

echo [SUCCESS] Packaging complete!
echo Your standalone executable is located in:
echo   %~dp0dist\LayoutCorrector v1.14.exe
echo   %~dp0LayoutCorrector v1.14.exe
echo You can move this file anywhere and run it.
pause
