param(
    [switch]$SkipDbDump,
    [string]$OutputDir = "backups"
)

$ErrorActionPreference = 'Continue'

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Warn2([string]$Message) {
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path $ProjectRoot $OutputDir
$backupDir = Join-Path $backupRoot $timestamp
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

Write-Host "SmartAsk backup" -ForegroundColor Green
Write-Host "Output directory: $backupDir"

Write-Step "Copy config and env template"
try {
    if (Test-Path ".\config") { Copy-Item ".\config" (Join-Path $backupDir "config") -Recurse -Force }
    if (Test-Path ".\.env.example") { Copy-Item ".\.env.example" (Join-Path $backupDir ".env.example") -Force }
} catch {
    Write-Warn2 "Config backup failed: $($_.Exception.Message)"
}

Write-Step "Export runtime bundles"
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { $pythonCmd = Get-Command py -ErrorAction SilentlyContinue }
if ($pythonCmd) {
    try {
        & $pythonCmd.Path ".\scripts\backup_all.py"
        $latestBundleDir = Get-ChildItem ".\backups" -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestBundleDir) {
            Copy-Item $latestBundleDir.FullName (Join-Path $backupDir "bundles") -Recurse -Force
        }
    } catch {
        Write-Warn2 "Host bundle export failed. Trying container export: $($_.Exception.Message)"
        try {
            docker compose exec -T backend python /app/scripts/backup_all.py
        } catch {
            Write-Warn2 "Container bundle export failed: $($_.Exception.Message)"
        }
    }
} else {
    Write-Warn2 "Host Python not found. Trying container bundle export."
    try { docker compose exec -T backend python /app/scripts/backup_all.py } catch { Write-Warn2 "Container bundle export failed: $($_.Exception.Message)" }
}

if (-not $SkipDbDump) {
    Write-Step "Export PostgreSQL SQL dump"
    $dumpPath = Join-Path $backupDir "postgres.sql"
    try {
        docker compose exec -T postgres pg_dump -U postgres -d postgres | Out-File -LiteralPath $dumpPath -Encoding UTF8
        Write-Host "  [OK] PostgreSQL dump: $dumpPath" -ForegroundColor Green
    } catch {
        Write-Warn2 "PostgreSQL dump failed. The containers may be stopped, or DB credentials may differ from defaults: $($_.Exception.Message)"
    }
}

Write-Step "Write backup README"
$readme = @"
SmartAsk backup
Time: $timestamp
Project: $ProjectRoot

Contents:
- config/
- .env.example
- bundles/ from scripts/backup_all.py when available
- postgres.sql unless -SkipDbDump was used
"@
$readme | Out-File (Join-Path $backupDir "README.txt") -Encoding UTF8

Write-Host ""
Write-Host "Backup finished: $backupDir" -ForegroundColor Green
