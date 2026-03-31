@echo off
setlocal

echo ========================================
echo   智能问数系统 - 后端服务启动
echo ========================================

cd /d "%~dp0backend"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3.11 --version >nul 2>nul
  if %errorlevel%==0 (
    echo [INFO] 使用 Python 3.11 启动后端...
    py -3.11 app.py
    goto :end
  )
)

echo [WARN] Python 3.11 未找到，使用默认 python
echo [WARN] 如果遇到依赖错误，请安装 Python 3.11
python app.py

:end
pause
