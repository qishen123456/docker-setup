param(
    [switch]$NoBuild
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

Write-Host "SmartAsk Docker deploy script" -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"

$envPath = Join-Path $ProjectRoot ".env"
$envExamplePath = Join-Path $ProjectRoot ".env.example"

Write-Step "Check Docker Desktop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker command not found. Please install and start Docker Desktop first."
}

docker info | Out-Null

Write-Step "Check environment file"
if (-not (Test-Path -LiteralPath $envPath)) {
    if (Test-Path -LiteralPath $envExamplePath) {
        Copy-Item -LiteralPath $envExamplePath -Destination $envPath -Force
        throw ".env was missing. .env.example has been copied to .env. Fill in the real values and run deploy.ps1 again."
    }

    throw ".env is missing and .env.example was not found."
}

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "backend\\logs") | Out-Null

$frontendPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_FRONTEND_PORT" -DefaultValue "8080"
$backendPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_BACKEND_PORT" -DefaultValue "5002"
$pgPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_DOCKER_PG_PORT" -DefaultValue "5433"

Write-Step "Start containers"
if ($NoBuild) {
    docker compose up -d
}
else {
    docker compose up -d --build
}

Write-Step "Show container status"
docker compose ps

Write-Host ""
Write-Host "Deployment completed." -ForegroundColor Green
Write-Host "Frontend: http://localhost:$frontendPort"
Write-Host "Backend: http://localhost:$backendPort"
Write-Host "PostgreSQL port: $pgPort"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  Update project: .\\update.ps1"
Write-Host "  Stop containers: docker compose down"
Write-Host "  View logs: docker compose logs -f"
