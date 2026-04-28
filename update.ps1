$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Yellow
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "SmartAsk Docker update script" -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"

$envPath = Join-Path $ProjectRoot ".env"

Write-Step "Check Git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git command not found. Please install Git first."
}

Write-Step "Check Docker Desktop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker command not found. Please install and start Docker Desktop first."
}

docker info | Out-Null

Write-Step "Check .env"
if (-not (Test-Path -LiteralPath $envPath)) {
    throw ".env is missing. Put the environment file in the project root first."
}

Write-Step "Pull latest code"
git pull

Write-Step "Rebuild and start containers"
docker compose up -d --build

Write-Step "Show container status"
docker compose ps

Write-Host ""
Write-Host "Update completed." -ForegroundColor Green
Write-Host "If the page does not refresh immediately, do a hard refresh in the browser."
