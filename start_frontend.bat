@echo off
setlocal

echo ========================================
echo   智能问数系统 - 前端服务启动
echo ========================================

cd /d "%~dp0frontend"

if exist "C:\nvm4w\nodejs\node.exe" (
  if exist "node_modules\vite\bin\vite.js" (
    echo [INFO] 使用 Node.js 启动前端...
    "C:\nvm4w\nodejs\node.exe" node_modules\vite\bin\vite.js
    goto :end
  )
)

if exist "C:\Users\12421\AppData\Roaming\npm\node_modules\pnpm\bin\pnpm.cjs" (
  echo [INFO] 使用 pnpm 启动前端...
  "C:\nvm4w\nodejs\node.exe" "C:\Users\12421\AppData\Roaming\npm\node_modules\pnpm\bin\pnpm.cjs" run dev
  goto :end
)

echo [WARN] 首选启动方式不可用，回退到 npm run dev
npm run dev

:end
pause
