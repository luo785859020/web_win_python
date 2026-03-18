@echo off
chcp 65001 > nul
echo ========================================
echo     电脑监控系统 - 启动器
echo ========================================
echo.
echo 正在启动监控服务...
echo.
cd /d "%~dp0"
python server.py
pause