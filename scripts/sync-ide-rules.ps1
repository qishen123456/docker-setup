# sync-ide-rules.ps1
# Sync IDE rule dirs from the single source of truth: .agents/rules/
# Generated files are marked DO NOT EDIT. Edit .agents/rules/ then rerun this script.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/sync-ide-rules.ps1          # generate
#   powershell -ExecutionPolicy Bypass -File scripts/sync-ide-rules.ps1 -Check   # verify only, exit 1 if stale
#
# To support a new IDE: add one entry to $targets below (dir + per-file frontmatter).
# NOTE: keep this script ASCII-only. Windows PowerShell 5.1 misreads
#       UTF-8-no-BOM scripts containing non-ASCII characters.

param([switch]$Check)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$srcDir = Join-Path $root '.agents\rules'

# --- IDE targets: one entry per IDE rule directory -------------------------
$traeFrontmatter = @{
    'backend.md' = @"
---
# Trae rule - backend only
alwaysApply: false
globs:
  - "backend/**/*.py"
---
"@
    'frontend.md' = @"
---
# Trae rule - frontend only
alwaysApply: false
globs:
  - "frontend/**/*.{vue,js,ts,css}"
---
"@
    'project-conventions.md' = @"
---
# Trae rule - global conventions (always applied)
alwaysApply: true
---
"@
}

$targets = @(
    @{ Dir = '.trae\rules'; Frontmatter = $traeFrontmatter }
    # Example for Cursor (uncomment when .cursor is adopted):
    # @{ Dir = '.cursor\rules'; Frontmatter = @{} }
)
# ----------------------------------------------------------------------------

$generatedHeader = '<!-- AUTO-GENERATED from .agents/rules/ - DO NOT EDIT. Edit the source and rerun scripts/sync-ide-rules.ps1 -->'

if (-not (Test-Path $srcDir)) { throw "Source dir not found: $srcDir" }
$sourceFiles = Get-ChildItem -Path $srcDir -Filter '*.md' -File
$staleFound = $false

foreach ($t in $targets) {
    $dstDir = Join-Path $root $t.Dir
    if ($Check -and -not (Test-Path $dstDir)) {
        Write-Host "STALE: missing dir $($t.Dir)"
        $staleFound = $true
        continue
    }
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }

    # expected contents per source file
    $expected = @{}
    foreach ($src in $sourceFiles) {
        $body = Get-Content -Raw -Encoding UTF8 $src.FullName
        $fm = $t.Frontmatter[$src.Name]
        $expected[$src.Name] = if ($fm) { "$generatedHeader`n$fm`n`n$body" } else { "$generatedHeader`n`n$body" }
    }

    if ($Check) {
        foreach ($name in $expected.Keys) {
            $dstPath = Join-Path $dstDir $name
            if (-not (Test-Path $dstPath)) { Write-Host "STALE: missing $($t.Dir)\$name"; $staleFound = $true; continue }
            $actual = [System.IO.File]::ReadAllText($dstPath)
            if ($actual -ne $expected[$name]) { Write-Host "STALE: out of sync $($t.Dir)\$name"; $staleFound = $true }
        }
        $staleExtra = @(Get-ChildItem -Path $dstDir -Filter '*.md' -File | Where-Object { -not $expected.ContainsKey($_.Name) })
        foreach ($f in $staleExtra) { Write-Host "STALE: extra file $($t.Dir)\$($f.Name)"; $staleFound = $true }
        continue
    }

    # generate/update copies
    foreach ($name in $expected.Keys) {
        $dstPath = Join-Path $dstDir $name
        [System.IO.File]::WriteAllText($dstPath, $expected[$name], (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "synced: .agents/rules/$name -> $($t.Dir)/$name"
    }
    # remove stale copies whose source no longer exists
    $stale = @(Get-ChildItem -Path $dstDir -Filter '*.md' -File | Where-Object { -not $expected.ContainsKey($_.Name) })
    foreach ($f in $stale) {
        Remove-Item $f.FullName -Force
        Write-Host "removed stale: $($t.Dir)/$($f.Name)"
    }
}

if ($Check) {
    if ($staleFound) { Write-Host "IDE rules are STALE. Run: powershell -ExecutionPolicy Bypass -File scripts/sync-ide-rules.ps1"; exit 1 }
    Write-Host "IDE rules in sync."
    exit 0
}
Write-Host "done. sources: $($sourceFiles.Count) rule file(s), targets: $($targets.Count) IDE dir(s)."
