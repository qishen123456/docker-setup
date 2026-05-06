param(
    [switch]$NoBuild,
    [switch]$ForceImport,
    [switch]$ForceConfig,
    [switch]$RunTests,
    [switch]$RunStreamTests
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg) { Write-Host "  [ERR] $msg" -ForegroundColor Red }

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

function Test-EnvRequired {
    param(
        [string]$FilePath,
        [string]$Key,
        [string[]]$InvalidValues = @()
    )
    $value = Read-EnvValue -FilePath $FilePath -Key $Key -DefaultValue ""
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw ".env is missing required key: $Key"
    }
    if ($InvalidValues -contains $value) {
        throw ".env key $Key still uses a placeholder value. Please fill a real value first."
    }
    if ($value -match "please|fill|change|AI_API_KEY|SECRET_KEY") {
        throw ".env key $Key looks like a placeholder value. Please fill a real value first."
    }
}

function Test-PortHint {
    param(
        [string]$Port,
        [string]$Name
    )
    if ([string]::IsNullOrWhiteSpace($Port)) { return }
    $listeners = netstat -ano | Select-String ":${Port}" | Where-Object { $_.ToString() -match "LISTENING" }
    if ($listeners) {
        Write-Warn2 "$Name port $Port is already listening. Ignore this if it is an old SmartAsk container; otherwise change .env ports or free the port."
    }
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "========================================================" -ForegroundColor Green
Write-Host "  SmartAsk one-click Docker deploy" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Project root: $ProjectRoot"

$envPath = Join-Path $ProjectRoot ".env"
$envExamplePath = Join-Path $ProjectRoot ".env.example"

Write-Step "1/6 Check Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker command not found. Please install and start Docker Desktop."
}
try { docker info | Out-Null; Write-Ok "Docker daemon OK" }
catch { throw "Docker is not running or not available. Please start Docker Desktop first." }

try { docker compose version | Out-Null; Write-Ok "Docker Compose plugin OK" }
catch { throw "docker compose plugin not found. Please upgrade Docker Desktop." }

Write-Step "2/6 Check .env"
if (-not (Test-Path -LiteralPath $envPath)) {
    if (Test-Path -LiteralPath $envExamplePath) {
        Copy-Item -LiteralPath $envExamplePath -Destination $envPath -Force
        Write-Warn2 ".env was missing. A new .env was copied from .env.example. Fill real secrets, then run this script again."
        exit 1
    }
    throw ".env is missing and .env.example was not found. Ask the project admin for a valid .env."
}
Write-Ok ".env exists"

Test-EnvRequired -FilePath $envPath -Key "SMARTASK_SECRET_KEY" -InvalidValues @("please-change-me-to-a-random-32-char-string")
Test-EnvRequired -FilePath $envPath -Key "SMARTASK_AI_API_KEY" -InvalidValues @("please-fill-your-ai-api-key")

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "backend\logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "config") | Out-Null

$frontendPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_FRONTEND_PORT" -DefaultValue "8080"
$backendPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_BACKEND_PORT" -DefaultValue "5002"
$pgPort = Read-EnvValue -FilePath $envPath -Key "SMARTASK_DOCKER_PG_PORT" -DefaultValue "5433"

Test-PortHint -Port $frontendPort -Name "frontend"
Test-PortHint -Port $backendPort -Name "backend"
Test-PortHint -Port $pgPort -Name "postgres"

if ($ForceImport) { $env:SMARTASK_BOOTSTRAP_FORCE_IMPORT = "1"; Write-Warn2 "ForceImport=ON: bootstrap will re-import metadata/business data." }
if ($ForceConfig) { $env:SMARTASK_BOOTSTRAP_FORCE_CONFIG = "1"; Write-Warn2 "ForceConfig=ON: bootstrap will overwrite config/*.json from bundle." }

Write-Step "3/6 Validate docker compose config"
docker compose config | Out-Null
Write-Ok "docker-compose.yml is valid"

Write-Step "4/6 Build and start containers"
if ($NoBuild) { docker compose up -d } else { docker compose up -d --build }

Write-Step "5/6 Wait for backend health, max 240s"
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

Write-Step "6/6 Deploy summary"
if ($ready) {
    Write-Ok "Backend health check passed"
    Write-Host ""
    Write-Host "  Frontend: http://localhost:$frontendPort" -ForegroundColor Yellow
    Write-Host "  Backend:  http://localhost:$backendPort/api/health"
    Write-Host "  Postgres: localhost:$pgPort (container 5432)"
} else {
    Write-Err "Backend health check failed."
    Write-Host "  Run: docker compose logs --tail=200 backend" -ForegroundColor Red
    exit 2
}

if ($RunTests) {
    Write-Step "Run integration tests"
    $streamArgs = @()
    if ($RunStreamTests) { $streamArgs += "--with-stream" }
    $py = (Get-Command python -ErrorAction SilentlyContinue).Path
    if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Path }
    if (-not $py) {
        Write-Warn2 "Host Python not found. Running tests inside backend container."
        docker compose exec -T backend python -m pip install --quiet --disable-pip-version-check requests
        docker compose exec -T backend python /app/scripts/integration_test.py --base-url "http://localhost:5002" --frontend-url "http://frontend" --no-wait @streamArgs
    } else {
        & $py -m pip install --quiet --disable-pip-version-check requests | Out-Null
        & $py "$ProjectRoot\scripts\integration_test.py" --base-url "http://localhost:$backendPort" --frontend-url "http://localhost:$frontendPort" @streamArgs
    }
}

Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Magenta
Write-Host "  Logs:      docker compose logs -f backend"
Write-Host "  Stop:      docker compose down"
Write-Host "  Restart:   .\reset.ps1 -Mode Restart"
Write-Host "  Rebuild:   .\reset.ps1 -Mode Rebuild"
Write-Host "  Diagnose:  .\doctor.ps1"
Write-Host "  Backup:    .\backup.ps1"
Write-Host "  Update:    .\update.ps1"
