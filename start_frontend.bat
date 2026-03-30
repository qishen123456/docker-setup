@echo off
echo ========================================
echo   智能问数系统 - 前端服务启动
echo ========================================
cd /d "%~dp0frontend"
npm run dev
pause
