@echo off
setlocal

echo ========================================
echo   智能问数系统 - 飞书同步服务启动
echo ========================================
echo.

cd /d "%~dp0backend"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3.11 --version >nul 2>nul
  if %errorlevel%==0 (
    echo [INFO] 使用 Python 3.11 启动飞书同步...
    py -3.11 start_feishu_sync.py
    goto :end
  )
)

echo [WARN] Python 3.11 未找到，使用默认 python
python start_feishu_sync.py

:end
pause
