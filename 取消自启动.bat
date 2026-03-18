@echo off
chcp 65001 > nul
echo ========================================
echo    Cancel Auto-Start
echo ========================================
echo.

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "PCMonitorService" /f

echo.
echo ========================================
echo    Done!
echo ========================================
echo.
echo Auto-start has been cancelled
pause