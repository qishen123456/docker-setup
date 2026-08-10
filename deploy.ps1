# =========================
# SmartAsk 部署切换脚本 (Windows PowerShell)
# 用途：快速在本地开发 / 生产环境之间切换
#
# 使用方式：
#   .\deploy.ps1 -Mode local       # 切换到本地开发模式
#   .\deploy.ps1 -Mode production  # 切换到生产环境模式
#   .\deploy.ps1 -Status           # 查看当前模式
# =========================

param(
    [ValidateSet("local", "production", "status")]
    [string]$Mode = "status"
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
if (-not $projectRoot) { $projectRoot = Get-Location }
Set-Location $projectRoot

# 颜色函数
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# 获取当前模式
function Get-CurrentMode {
    if (Test-Path .env) {
        $content = Get-Content .env -Raw
        if ($content -match "DEPLOY_MODE=production") { return "production" }
        else { return "local" }
    } else {
        return "未配置"
    }
}

# 打印状态
function Show-Status {
    $current = Get-CurrentMode

    Write-Host ""
    Write-ColorOutput "========================================" "Cyan"
    Write-ColorOutput "  SmartAsk 当前部署模式：$($current.ToUpper())" "Cyan"
    Write-ColorOutput "========================================" "Cyan"
    Write-Host ""

    if (Test-Path .env) {
        Write-ColorOutput "当前环境变量：" "Yellow"
        $envContent = Get-Content .env | Select-String "^(DEPLOY_MODE|BACKEND_URL|FRONTEND_URL|PUBLIC_DOMAIN)="
        foreach ($line in $envContent) {
            Write-Host "  $($line.Line)" -ForegroundColor Gray
        }
        Write-Host ""
    }

    # 检查 Docker 容器状态
    try {
        Write-ColorOutput "Docker 容器状态：" "Yellow"
        docker-compose ps 2>$null
        Write-Host ""
    } catch {
        Write-ColorOutput "  Docker Compose 未运行或未安装" "Gray"
    }
}

# 切换到本地模式
function Switch-ToLocal {
    Write-Host ""
    Write-ColorOutput ">>> 切换到本地开发模式..." "Green"
    Write-Host ""

    # 备份当前 .env
    if (Test-Path .env) {
        $backupName = ".env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item .env $backupName
        Write-ColorOutput "  已备份当前 .env 文件 → $backupName" "Yellow"
    }

    # 复制本地配置
    Copy-Item .env.local .env -Force

    Write-ColorOutput "  ✓ 已应用本地配置" "Green"
    Write-ColorOutput "  ✓ 后端端口：5002（直接访问）" "Green"
    Write-ColorOutput "  ✓ 前端端口：8888（直接访问）" "Green"
    Write-ColorOutput "  ✓ Nginx：未启用" "Green"

    Write-Host ""
    Write-ColorOutput "启动命令：docker-compose up -d --build" "Cyan"
    Write-Host ""
}

# 切换到生产模式
function Switch-ToProduction {
    Write-Host ""
    Write-ColorOutput ">>> 切换到生产环境模式..." "Green"
    Write-Host ""

    # 检查是否已配置域名
    $prodContent = Get-Content .env.production -Raw -ErrorAction SilentlyContinue
    if (-not $prodContent -or $prodContent -match "PUBLIC_DOMAIN=your-domain\.com") {
        Write-ColorOutput "错误：请先修改 .env.production 中的 PUBLIC_DOMAIN！" "Red"
        exit 1
    }

    # 备份当前 .env
    if (Test-Path .env) {
        $backupName = ".env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item .env $backupName
        Write-ColorOutput "  已备份当前 .env 文件 → $backupName" "Yellow"
    }

    # 复制生产配置
    Copy-Item .env.production .env -Force

    # 提取域名显示
    $domain = ($prodContent | Select-String "PUBLIC_DOMAIN=(.+)").Matches.Groups[1].Value

    Write-ColorOutput "  ✓ 已应用生产配置" "Green"
    Write-ColorOutput "  ✓ 公网域名：$domain" "Green"
    Write-ColorOutput "  ✓ 后端 API：通过 Nginx :80/api/ 代理" "Green"
    Write-ColorOutput "  ✓ 前端页面：通过 Nginx :80/ 代理" "Green"
    Write-ColorOutput "  ✓ Nginx：已启用（单公网端口）" "Green"
    Write-ColorOutput "  ✓ 端口覆盖：已自动禁用 backend/frontend 直接暴露" "Green"

    Write-Host ""
    Write-ColorOutput "启动命令：" "Cyan"
    Write-Host "  docker-compose --profile production -f docker-compose.yml -f docker-compose.prod.yml up -d --build"
    Write-Host ""
}

# 主逻辑
switch ($Mode) {
    "local" {
        Switch-ToLocal
    }
    "production" {
        Switch-ToProduction
    }
    "status" {
        Show-Status
    }
}
