param(
    [switch]$NoBuild,
    [switch]$RunTests
)

$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Yellow
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "SmartAsk 智能问数 - Docker 增量更新" -ForegroundColor Green
Write-Host "项目目录: $ProjectRoot"

$envPath = Join-Path $ProjectRoot ".env"

Write-Step "检查 Git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "未检测到 git 命令，请先安装 Git。"
}

Write-Step "检查 Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "未检测到 docker 命令，请先安装并启动 Docker Desktop。"
}
docker info | Out-Null

Write-Step "检查 .env"
if (-not (Test-Path -LiteralPath $envPath)) {
    throw ".env 缺失，请先把 .env 放到项目根目录。"
}

Write-Step "拉取最新代码 (git pull --ff-only)"
git pull --ff-only

Write-Step "重新构建并启动容器"
if ($NoBuild) { docker compose up -d } else { docker compose up -d --build }

Write-Step "等待后端健康检查"
$backendPort = "5002"
$envLine = Select-String -Path $envPath -Pattern "^SMARTASK_BACKEND_PORT=(.*)$" | Select-Object -First 1
if ($envLine) { $backendPort = $envLine.Matches[0].Groups[1].Value.Trim() }

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://localhost:$backendPort/api/health" -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}

Write-Step "容器状态"
docker compose ps

if ($ready) {
    Write-Host ""
    Write-Host "✅ 更新完成。如页面无变化，请在浏览器执行硬刷新 (Ctrl+F5)。" -ForegroundColor Green
    if ($RunTests) {
        Write-Step "运行集成测试"
        $frontendPort = "8080"
        $frontendLine = Select-String -Path $envPath -Pattern "^SMARTASK_FRONTEND_PORT=(.*)$" | Select-Object -First 1
        if ($frontendLine) { $frontendPort = $frontendLine.Matches[0].Groups[1].Value.Trim() }
        docker compose exec -T backend python -m pip install --quiet --disable-pip-version-check requests
        docker compose exec -T backend python /app/scripts/integration_test.py --base-url "http://localhost:5002" --frontend-url "http://frontend" --no-wait
        Write-Host "用户机访问地址: http://localhost:$frontendPort" -ForegroundColor Yellow
    }
}
else {
    Write-Host ""
    Write-Host "⚠️ 后端健康检查失败，请查看 docker compose logs --tail=200 backend" -ForegroundColor Red
    exit 2
}
