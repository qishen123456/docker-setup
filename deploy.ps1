param(
    [switch]$NoBuild,
    [switch]$ForceImport
)

$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Read-EnvValue {
    param(
        [string]$FilePath,
        [string]$Key,
        [string]$DefaultValue = ""
    )

    if (-not (Test-Path -LiteralPath $FilePath)) {
        return $DefaultValue
    }

    $line = Select-String -Path $FilePath -Pattern "^${Key}=(.*)$" | Select-Object -First 1
    if (-not $line) {
        return $DefaultValue
    }

    return ($line.Matches[0].Groups[1].Value.Trim())
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "==============================================" -ForegroundColor Green
Write-Host "  SmartAsk 智能问数 - 一键 Docker 部署脚本" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host "项目目录: $ProjectRoot"

$envPath = Join-Path $ProjectRoot ".env"
$envExamplePath = Join-Path $ProjectRoot ".env.example"

Write-Step "检查 Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "未检测到 docker 命令。请先安装并启动 Docker Desktop。"
}
try {
    docker info | Out-Null
} catch {
    throw "Docker 未启动或不可用。请先打开 Docker Desktop 并等待其完全启动。"
}

Write-Step "检查 .env 文件"
if (-not (Test-Path -LiteralPath $envPath)) {
    if (Test-Path -LiteralPath $envExamplePath) {
        Copy-Item -LiteralPath $envExamplePath -Destination $envPath -Force
        Write-Host "未发现 .env，已复制 .env.example 为 .env。" -ForegroundColor Yellow
        Write-Host "请打开 .env 填入真实的 AI_API_KEY、数据库密码等，再次运行本脚本。" -ForegroundColor Yellow
        exit 1
    }
    throw ".env 缺失且未找到 .env.example，请向项目管理员索取 .env 文件。"
}

# 创建必要的本地目录
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "backend\logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "config") | Out-Null

$frontendPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_FRONTEND_PORT" -DefaultValue "8080"
$backendPort  = Read-EnvValue -FilePath $envPath -Key "SMARTASK_BACKEND_PORT"  -DefaultValue "5002"
$pgPort       = Read-EnvValue -FilePath $envPath -Key "SMARTASK_DOCKER_PG_PORT" -DefaultValue "5433"

if ($ForceImport) {
    Write-Step "已开启 ForceImport：将覆盖已有元数据/业务数据"
    $env:SMARTASK_BOOTSTRAP_FORCE_IMPORT = "1"
}

Write-Step "构建并启动容器（首次拉取镜像可能需要 3-8 分钟）"
if ($NoBuild) {
    docker compose up -d
}
else {
    docker compose up -d --build
}

Write-Step "等待后端健康检查（最多 180 秒）"
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://localhost:$backendPort/api/health" -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # still starting
    }
}

Write-Step "容器状态"
docker compose ps

if ($ready) {
    Write-Host ""
    Write-Host "✅ 部署完成！数据初始化已由后端 bootstrap 自动完成。" -ForegroundColor Green
    Write-Host ""
    Write-Host "  前端访问:  http://localhost:$frontendPort" -ForegroundColor Yellow
    Write-Host "  后端健康:  http://localhost:$backendPort/api/health"
    Write-Host "  Postgres:  localhost:$pgPort (容器内 5432)"
    Write-Host ""
    Write-Host "常用命令:"
    Write-Host "  查看后端日志:   docker compose logs -f backend"
    Write-Host "  查看初始化日志: docker compose logs backend | findstr bootstrap"
    Write-Host "  停止全部容器:   docker compose down"
    Write-Host "  增量更新代码:   .\update.ps1"
    Write-Host "  强制重新导入:   .\deploy.ps1 -ForceImport"
}
else {
    Write-Host ""
    Write-Host "⚠️ 后端未在限定时间内通过健康检查。" -ForegroundColor Red
    Write-Host "请查看日志定位原因：" -ForegroundColor Red
    Write-Host "  docker compose logs --tail=200 backend"
    exit 2
}
