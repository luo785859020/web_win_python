@echo off
chcp 65001 > nul
echo ========================================
echo    Computer Monitor - Auto Start Setup
echo ========================================
echo.

where python > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python first
    pause
    exit /b 1
)

for /f "delims=" %%i in ('where python') do set "exe_path=%%i"
set "script_path=%~dp0server.py"

echo Found Python: %exe_path%
echo.
echo Creating auto-start registry entry...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "PCMonitorService" /t REG_SZ /d "\"%exe_path%\" \"%script_path%\"" /f

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo PC will auto-start monitor service on boot
echo Access: http://localhost:5000
echo.
echo To cancel auto-start, run: cancel_autostart.bat
echo ========================================
pause