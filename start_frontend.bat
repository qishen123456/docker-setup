@echo off
setlocal

echo ========================================
echo   智能问数系统 - 前端服务启动
echo ========================================

cd /d "%~dp0frontend"

where npm >nul 2>nul
if not %errorlevel%==0 (
  echo [ERROR] 未检测到 npm，请先安装 Node.js 20+。
  goto :end
)

if not exist "node_modules" (
  echo [INFO] 首次启动，正在安装前端依赖...
  npm install
)

echo [INFO] 启动前端开发服务...
npm run dev

:end
pause
