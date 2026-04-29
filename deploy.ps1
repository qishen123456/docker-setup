param(
    [switch]$NoBuild,
    [switch]$ForceImport,
    [switch]$ForceConfig,
    [switch]$RunTests
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg){ Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg)  { Write-Host "  [XX] $msg" -ForegroundColor Red }

function Read-EnvValue {
    param(
        [string]$FilePath,
        [string]$Key,
        [string]$DefaultValue = ""
    )
    if (-not (Test-Path -LiteralPath $FilePath)) { return $DefaultValue }
    $line = Select-String -Path $FilePath -Pattern "^${Key}=(.*)$" | Select-Object -First 1
    if (-not $line) { return $DefaultValue }
    return ($line.Matches[0].Groups[1].Value.Trim())
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "========================================================" -ForegroundColor Green
Write-Host "  SmartAsk 智能问数 - 一键 Docker 部署脚本 v2.0" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Project root: $ProjectRoot"

$envPath = Join-Path $ProjectRoot ".env"
$envExamplePath = Join-Path $ProjectRoot ".env.example"

# ---------- 1. 前置检查 ----------
Write-Step "1/5 检查 Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "未检测到 docker 命令。请先安装并启动 Docker Desktop。"
}
try { docker info | Out-Null; Write-Ok "Docker daemon OK" }
catch { throw "Docker 未启动或不可用。请先打开 Docker Desktop 并等待其启动。" }

Write-Step "2/5 检查 .env"
if (-not (Test-Path -LiteralPath $envPath)) {
    if (Test-Path -LiteralPath $envExamplePath) {
        Copy-Item -LiteralPath $envExamplePath -Destination $envPath -Force
        Write-Warn2 "未发现 .env，已自动复制 .env.example。请填入真实密钥后再次运行。"
        exit 1
    }
    throw ".env 缺失且未找到 .env.example，请向项目管理员索取 .env。"
}
Write-Ok ".env 存在"

# 创建挂载目录
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "backend\logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "config") | Out-Null

$frontendPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_FRONTEND_PORT" -DefaultValue "8080"
$backendPort  = Read-EnvValue -FilePath $envPath -Key "SMARTASK_BACKEND_PORT"  -DefaultValue "5002"
$pgPort       = Read-EnvValue -FilePath $envPath -Key "SMARTASK_DOCKER_PG_PORT" -DefaultValue "5433"

if ($ForceImport) { $env:SMARTASK_BOOTSTRAP_FORCE_IMPORT = "1"; Write-Warn2 "ForceImport=ON：将覆盖式重新导入元数据/业务数据" }
if ($ForceConfig) { $env:SMARTASK_BOOTSTRAP_FORCE_CONFIG = "1"; Write-Warn2 "ForceConfig=ON：将覆盖式重新写入 config/*.json" }

# ---------- 2. 构建 + 启动 ----------
Write-Step "3/5 构建并启动容器（首次拉取镜像可能 3-8 分钟）"
if ($NoBuild) { docker compose up -d } else { docker compose up -d --build }

# ---------- 3. 等待健康检查 ----------
Write-Step "4/5 等待后端健康检查（最多 240 秒）"
$ready = $false
for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://localhost:$backendPort/api/health" -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}

Write-Host ""
docker compose ps

# ---------- 4. 报告 ----------
Write-Step "5/5 部署摘要"
if ($ready) {
    Write-Ok "后端健康检查通过"
    Write-Host ""
    Write-Host "  前端访问:  http://localhost:$frontendPort" -ForegroundColor Yellow
    Write-Host "  后端健康:  http://localhost:$backendPort/api/health"
    Write-Host "  Postgres:  localhost:$pgPort (容器内 5432)"
    Write-Host ""
    Write-Host "  数据初始化（schema 迁移 + bookshelf + angel_group_data）已由 bootstrap 自动完成。"
}
else {
    Write-Err "后端未在限定时间内通过健康检查。"
    Write-Host "  请查看日志：" -ForegroundColor Red
    Write-Host "    docker compose logs --tail=200 backend"
    exit 2
}

# ---------- 5. 可选：跑集成测试 ----------
if ($RunTests) {
    Write-Step "运行集成测试（scripts/integration_test.py）"
    $py = (Get-Command python -ErrorAction SilentlyContinue).Path
    if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Path }
    if (-not $py) {
        Write-Warn2 "未发现宿主机 Python，使用容器内 Python 跑测试"
        docker compose exec -T backend python -m pip install --quiet --disable-pip-version-check requests
        docker compose exec -T backend python /app/backend/../scripts/integration_test.py --base-url "http://localhost:5002" --frontend-url "http://nginx-not-resolvable" --no-wait
    } else {
        & $py -m pip install --quiet --disable-pip-version-check requests | Out-Null
        & $py "$ProjectRoot\scripts\integration_test.py" --base-url "http://localhost:$backendPort" --frontend-url "http://localhost:$frontendPort"
    }
}

Write-Host ""
Write-Host "常用命令:" -ForegroundColor Magenta
Write-Host "  日志:   docker compose logs -f backend"
Write-Host "  停止:   docker compose down"
Write-Host "  彻底重置(含数据): docker compose down -v"
Write-Host "  覆盖式重导入:     .\deploy.ps1 -ForceImport"
Write-Host "  增量更新:         .\update.ps1"
Write-Host "  自检:             python scripts\verify_deployment.py"
Write-Host "  集成测试:         python scripts\integration_test.py"
Write-Host "  全量备份:         python scripts\backup_all.py"
