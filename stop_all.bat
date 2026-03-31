@echo off
setlocal

echo ========================================
echo   智能问数系统 - 停止所有服务
echo ========================================
echo.

echo [INFO] 正在查找并停止后端服务...
taskkill /f /im python.exe /fi "windowtitle eq 智能问数-后端*" 2>nul

echo [INFO] 正在查找并停止前端服务...
taskkill /f /im node.exe /fi "windowtitle eq 智能问数-前端*" 2>nul

echo [INFO] 正在清理其他相关进程...
taskkill /f /im python.exe /fi "windowtitle eq 智能问数-飞书同步*" 2>nul

echo.
echo ========================================
echo   服务停止完成
echo ========================================
echo.

pause
