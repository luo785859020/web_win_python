@echo off
chcp 65001 > nul
echo ========================================
echo    PC Monitor - Installation Script
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python environment...
where python > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.7+
    echo Download: https://www.python.org/downloads/
    echo.
    echo Or manually install dependencies:
    echo python -m pip install flask psutil
    pause
    exit /b 1
)
echo [OK] Python detected

echo.
echo [2/3] Installing dependencies...
python -m pip install psutil flask
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

echo.
echo [3/3] Starting monitor service...
echo.
echo ========================================
echo    Installation Complete!
echo ========================================
echo.
echo Access:
echo   Local: http://localhost:5000
echo   LAN: http://YOUR_IP:5000
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

python server.py

pause