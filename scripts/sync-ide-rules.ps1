# sync-ide-rules.ps1
# Sync .trae/rules/ from the single source of truth: .agents/rules/
# Files under .trae/rules/ are GENERATED - do not edit by hand.
# Edit .agents/rules/ instead, then rerun this script.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/sync-ide-rules.ps1
# NOTE: keep this script ASCII-only. Windows PowerShell 5.1 misreads
#       UTF-8-no-BOM scripts containing non-ASCII characters.

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$srcDir = Join-Path $root '.agents\rules'
$dstDir = Join-Path $root '.trae\rules'

# Trae frontmatter per rule file (controls how Trae loads each rule)
$frontmatterMap = @{
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

if (-not (Test-Path $srcDir)) { throw "Source dir not found: $srcDir" }
if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir | Out-Null }

$generatedHeader = '<!-- AUTO-GENERATED from .agents/rules/ - DO NOT EDIT. Edit the source and rerun scripts/sync-ide-rules.ps1 -->'

# 1. Generate/update copies
$sourceFiles = Get-ChildItem -Path $srcDir -Filter '*.md' -File
foreach ($src in $sourceFiles) {
    $body = Get-Content -Raw -Encoding UTF8 $src.FullName
    $fm = $frontmatterMap[$src.Name]
    $content = if ($fm) { "$generatedHeader`n$fm`n`n$body" } else { "$generatedHeader`n`n$body" }
    $dstPath = Join-Path $dstDir $src.Name
    [System.IO.File]::WriteAllText($dstPath, $content, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "synced: .agents/rules/$($src.Name) -> .trae/rules/$($src.Name)"
}

# 2. Remove stale copies whose source no longer exists
$srcNames = $sourceFiles | ForEach-Object { $_.Name }
$stale = @(Get-ChildItem -Path $dstDir -Filter '*.md' -File | Where-Object { $srcNames -notcontains $_.Name })
foreach ($f in $stale) {
    Remove-Item $f.FullName -Force
    Write-Host "removed stale: .trae/rules/$($f.Name)"
}

Write-Host "done. synced $($sourceFiles.Count) file(s), removed $($stale.Count) stale file(s)."
