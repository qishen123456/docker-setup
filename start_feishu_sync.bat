@echo off
cd /d "%~dp0"

echo ========================================
echo 启动飞书同步服务
echo ========================================
echo.

python start_feishu_sync.py

pause
