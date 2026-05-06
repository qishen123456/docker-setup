param(
    [string]$OutputDir = "diagnostics"
)

$ErrorActionPreference = 'Continue'

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Redact-Line([string]$Line) {
    if ($Line -match '^\s*#') { return $Line }
    if ($Line -match '^\s*$') { return $Line }
    if ($Line -match '^(.*?(KEY|SECRET|TOKEN|PASSWORD|APP_SECRET|API_KEY).*?=)(.*)$') {
        return "$($Matches[1])***REDACTED***"
    }
    return $Line
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$diagRoot = Join-Path $ProjectRoot $OutputDir
$diagDir = Join-Path $diagRoot "smartask_diagnose_$timestamp"
New-Item -ItemType Directory -Force -Path $diagDir | Out-Null

Write-Host "SmartAsk 诊断包生成器" -ForegroundColor Green
Write-Host "项目目录: $ProjectRoot"
Write-Host "输出目录: $diagDir"

Write-Step "收集系统与 Git 信息"
try { Get-Date | Out-File (Join-Path $diagDir "time.txt") -Encoding UTF8 } catch {}
try { git status --short | Out-File (Join-Path $diagDir "git_status.txt") -Encoding UTF8 } catch { $_ | Out-File (Join-Path $diagDir "git_status_error.txt") -Encoding UTF8 }
try { git rev-parse HEAD | Out-File (Join-Path $diagDir "git_head.txt") -Encoding UTF8 } catch {}
try { Get-ChildItem -Force | Select-Object Name,Mode,Length,LastWriteTime | Out-File (Join-Path $diagDir "root_files.txt") -Encoding UTF8 } catch {}

Write-Step "收集 Docker 信息"
try { docker version | Out-File (Join-Path $diagDir "docker_version.txt") -Encoding UTF8 } catch { $_ | Out-File (Join-Path $diagDir "docker_version_error.txt") -Encoding UTF8 }
try { docker info | Out-File (Join-Path $diagDir "docker_info.txt") -Encoding UTF8 } catch { $_ | Out-File (Join-Path $diagDir "docker_info_error.txt") -Encoding UTF8 }
try { docker compose config | Out-File (Join-Path $diagDir "compose_config.txt") -Encoding UTF8 } catch { $_ | Out-File (Join-Path $diagDir "compose_config_error.txt") -Encoding UTF8 }
try { docker compose ps | Out-File (Join-Path $diagDir "compose_ps.txt") -Encoding UTF8 } catch { $_ | Out-File (Join-Path $diagDir "compose_ps_error.txt") -Encoding UTF8 }

Write-Step "收集服务日志"
foreach ($svc in @("backend", "frontend", "postgres")) {
    try {
        docker compose logs --tail=300 $svc | Out-File (Join-Path $diagDir "logs_$svc.txt") -Encoding UTF8
    } catch {
        $_ | Out-File (Join-Path $diagDir "logs_${svc}_error.txt") -Encoding UTF8
    }
}

Write-Step "收集端口与健康检查"
try { netstat -ano | Select-String ":5002|:5173|:8080|:5432|:5433" | Out-File (Join-Path $diagDir "ports.txt") -Encoding UTF8 } catch {}
try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://localhost:5002/api/health").Content | Out-File (Join-Path $diagDir "backend_health.txt") -Encoding UTF8 } catch { $_ | Out-File (Join-Path $diagDir "backend_health_error.txt") -Encoding UTF8 }
try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://localhost:8080").StatusCode | Out-File (Join-Path $diagDir "frontend_8080_status.txt") -Encoding UTF8 } catch { $_ | Out-File (Join-Path $diagDir "frontend_8080_error.txt") -Encoding UTF8 }
try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://localhost:5173").StatusCode | Out-File (Join-Path $diagDir "frontend_5173_status.txt") -Encoding UTF8 } catch {}

Write-Step "生成脱敏环境摘要"
$envPath = Join-Path $ProjectRoot ".env"
if (Test-Path -LiteralPath $envPath) {
    Get-Content -LiteralPath $envPath -Encoding UTF8 |
        ForEach-Object { Redact-Line $_ } |
        Out-File (Join-Path $diagDir "env_redacted.txt") -Encoding UTF8
} else {
    "missing .env" | Out-File (Join-Path $diagDir "env_redacted.txt") -Encoding UTF8
}

Write-Step "压缩诊断包"
$zipPath = "$diagDir.zip"
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -Path (Join-Path $diagDir "*") -DestinationPath $zipPath -Force

Write-Host ""
Write-Host "诊断包已生成: $zipPath" -ForegroundColor Green
