@echo off
setlocal

echo ========================================
echo   Smart Query - Start All Services
echo ========================================
echo.

echo [INFO] Starting backend service...
start "SmartQuery-Backend" /D "%~dp0backend" cmd /k "call ..\start_backend.bat"

timeout /t 3 /nobreak >nul

echo [INFO] Starting frontend service...
start "SmartQuery-Frontend" /D "%~dp0frontend" cmd /k "call ..\start_frontend.bat"

echo.
echo ========================================
echo   Startup Commands Sent
echo ========================================
echo.
echo Frontend: http://localhost:5173
echo Backend : http://localhost:5002
echo.
echo Tip: Close service windows to stop services.
echo.

pause
