param(
    [ValidateSet("Restart", "Rebuild", "Data")]
    [string]$Mode = "Restart",
    [switch]$ConfirmDataReset
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "SmartAsk reset tool" -ForegroundColor Green
Write-Host "Mode: $Mode"

if ($Mode -eq "Restart") {
    Write-Step "Soft restart containers. Images and data volumes stay unchanged."
    docker compose restart
    docker compose ps
    exit 0
}

if ($Mode -eq "Rebuild") {
    Write-Step "Rebuild and start containers. Data volumes stay unchanged."
    docker compose up -d --build
    docker compose ps
    exit 0
}

if ($Mode -eq "Data") {
    if (-not $ConfirmDataReset) {
        throw "Data mode runs docker compose down -v and clears database/vector volumes. Add -ConfirmDataReset if you really want this."
    }
    Write-Step "Danger: clearing data volumes and bootstrapping from scratch."
    docker compose down -v
    docker compose up -d --build
    docker compose ps
}
