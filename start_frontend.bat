@echo off
echo ============================================
echo [Vanna 智能问数系统] 正在启动前端 Vue 3 界面...
echo ============================================
cd /d %~dp0frontend
pnpm run dev
pause
