param(
    [switch]$NoBuild,
    [switch]$RunTests,
    [switch]$RunStreamTests,
    [switch]$NoPull,
    [switch]$SkipBackup
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Yellow
}

function Write-Warn2([string]$Message) {
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

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

Write-Host "SmartAsk Docker incremental update" -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"

$envPath = Join-Path $ProjectRoot ".env"

Write-Step "Check Git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git command not found. Please install Git first."
}

Write-Step "Check Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker command not found. Please install and start Docker Desktop."
}
docker info | Out-Null
docker compose version | Out-Null

Write-Step "Check .env"
if (-not (Test-Path -LiteralPath $envPath)) {
    throw ".env is missing. Put a valid .env in project root first."
}

if (-not $SkipBackup) {
    Write-Step "Backup before update"
    try {
        & "$ProjectRoot\backup.ps1"
    } catch {
        Write-Warn2 "Backup failed. Update stopped to protect existing data: $($_.Exception.Message)"
        exit 3
    }
}

if ($NoPull) {
    Write-Step "Skip git pull because NoPull=ON"
} else {
    Write-Step "Pull latest code with git pull --ff-only"
    git pull --ff-only
}

Write-Step "Validate docker compose config"
docker compose config | Out-Null

Write-Step "Rebuild and start containers"
if ($NoBuild) { docker compose up -d } else { docker compose up -d --build }

Write-Step "Wait for backend health"
$backendPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_BACKEND_PORT" -DefaultValue "5002"
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://localhost:$backendPort/api/health" -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}

Write-Step "Container status"
docker compose ps

if ($ready) {
    Write-Host ""
    Write-Host "[OK] Update finished. If the page looks stale, hard refresh with Ctrl+F5." -ForegroundColor Green
    Write-Host "     Frontend image was rebuilt unless -NoBuild was used." -ForegroundColor Green
    Write-Host "     SmartAsk history is isolated by login account in the browser." -ForegroundColor Green
    if ($RunTests) {
        Write-Step "Run integration tests"
        $streamArgs = @()
        if ($RunStreamTests) { $streamArgs += "--with-stream" }
        $frontendPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_FRONTEND_PORT" -DefaultValue "8080"
        docker compose exec -T backend python -m pip install --quiet --disable-pip-version-check requests
        docker compose exec -T backend python /app/scripts/integration_test.py --base-url "http://localhost:5002" --frontend-url "http://frontend" --no-wait @streamArgs
        Write-Host "User URL: http://localhost:$frontendPort" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[ERR] Backend health check failed. Run: docker compose logs --tail=200 backend" -ForegroundColor Red
    exit 2
}
