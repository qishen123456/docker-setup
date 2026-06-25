# ANGEL brand visual cleanup - final pass
# Only modify <style scoped> blocks in Vue SFCs
$files = @(
    "src/views/SmartAsk.vue",
    "src/components/smartask/AgentDoneBar.vue",
    "src/components/smartask/ArtifactStrip.vue",
    "src/components/smartask/ChatHeader.vue",
    "src/components/smartask/ComposerArea.vue",
    "src/components/smartask/LiveExecutionFeed.vue",
    "src/components/smartask/LogTimeline.vue",
    "src/components/smartask/PlanCard.vue",
    "src/components/smartask/ResultDigestCard.vue",
    "src/components/smartask/SqlBlock.vue",
    "src/components/smartask/TabNav.vue",
    "src/components/smartask/ThinkingCard.vue",
    "src/components/smartask/TypewriterLine.vue",
    "src/components/smartask/UserBubble.vue",
    "src/components/smartask/WelcomeScreen.vue",
    "src/components/SqlDebugFloat.vue"
)

$base = Split-Path -Parent $MyInvocation.MyCommand.Path

# 6-digit HEX mapping
$hex6 = [ordered]@{
    '#3370ff' = '#E61F24'; '#165dff' = '#E61F24'; '#2860e1' = '#E61F24'; '#1f4fca' = '#E61F24'
    '#4f8cff' = '#E61F24'; '#7bb0ff' = '#E61F24'; '#8fb8ff' = '#E61F24'; '#bcd2ff' = '#E61F24'
    '#6e99ff' = '#E61F24'; '#2563eb' = '#E61F24'; '#2a6cff' = '#E61F24'; '#114fd6' = '#cc181d'
    '#0e42d2' = '#cc181d'; '#2f5fd7' = '#E61F24'; '#245bd6' = '#6B7280'; '#168cff' = '#111827'
    '#78a9ff' = '#E61F24'; '#7ba8ff' = '#E61F24'; '#8db7ff' = '#E61F24'

    '#122033' = '#111827'; '#123f68' = '#111827'; '#12304f' = '#111827'; '#172033' = '#111827'
    '#1d2129' = '#111827'; '#20242b' = '#111827'; '#171a20' = '#111827'; '#101828' = '#111827'
    '#252b3a' = '#111827'; '#1f2937' = '#111827'
    '#1e293b' = '#1A1A1A'; '#0f172a' = '#1A1A1A'; '#334155' = '#1A1A1A'

    '#4e5969' = '#6B7280'; '#667085' = '#6B7280'; '#6b7785' = '#6B7280'; '#7a818d' = '#6B7280'
    '#7a8494' = '#6B7280'; '#4b5563' = '#6B7280'; '#475569' = '#6B7280'
    '#86909c' = '#9CA3AF'; '#98a2b3' = '#9CA3AF'; '#9aa2ad' = '#9CA3AF'; '#9aa3b2' = '#9CA3AF'
    '#a0a7b2' = '#9CA3AF'; '#a0a7b4' = '#9CA3AF'; '#a9b0bd' = '#9CA3AF'; '#b0b8c4' = '#9CA3AF'
    '#b8c2d0' = '#9CA3AF'; '#c7ced8' = '#9CA3AF'; '#94a3b8' = '#9CA3AF'
    '#344054' = '#374151'; '#3d4756' = '#374151'; '#243041' = '#374151'; '#7b8496' = '#6B7280'

    '#e5e6eb' = '#E5E7EB'; '#e5e7eb' = '#E5E7EB'; '#c9cdd4' = '#D1D5DB'; '#d1d5db' = '#D1D5DB'
    '#d8dee8' = '#D1D5DB'; '#dfe3eb' = '#E5E7EB'

    '#f2f3f5' = '#F3F4F6'; '#f7f9fc' = '#F8F9FA'; '#f8fafc' = '#F8F9FA'; '#f9fafb' = '#F8F9FA'
    '#f4f8fb' = '#F8F9FA'; '#eef5f3' = '#F8F9FA'; '#f6f8fb' = '#F8F9FA'; '#f0f1f3' = '#F3F4F6'
    '#edf0f5' = '#F3F4F6'; '#f4f5f7' = '#F3F4F6'; '#f0f2f5' = '#F3F4F6'; '#f7f8fa' = '#F8F9FA'
    '#fafbfc' = '#F8F9FA'; '#eef5ff' = '#F8F9FA'; '#dfe9ff' = '#F3F4F6'; '#f2f6ff' = '#F8F9FA'
    '#fbfcfe' = '#FFFFFF'; '#fbfcff' = '#FFFFFF'; '#fbfdff' = '#FFFFFF'; '#f8fbff' = '#F8F9FA'
    '#f7faff' = '#F8F9FA'; '#f4f8ff' = '#F8F9FA'; '#f5f9ff' = '#F8F9FA'
    '#f5f8ff' = '#FEF2F2'; '#e8f3ff' = '#FEF2F2'; '#eef4ff' = '#FEF2F2'; '#edf4ff' = '#FEF2F2'

    '#0f766e' = '#E61F24'; '#0b625d' = '#E61F24'; '#084f4b' = '#E61F24'; '#0f9f94' = '#E61F24'
    '#7de0d4' = '#FEF2F2'; '#75e0d3' = '#FEF2F2'; '#ccfbf1' = '#FEF2F2'; '#e8f6f4' = '#FEF2F2'
    '#f0fdfa' = '#FEF2F2'; '#f1faf9' = '#FEF2F2'; '#effaf8' = '#FEF2F2'

    '#00b42a' = '#10B981'; '#00a63e' = '#10B981'; '#00a870' = '#10B981'; '#009a29' = '#10B981'
    '#178a3b' = '#10B981'; '#008f62' = '#10B981'; '#22a35a' = '#10B981'; '#00a321' = '#10B981'
    '#e8ffea' = '#ECFDF5'; '#ecfdf3' = '#ECFDF5'; '#f2fff7' = '#ECFDF5'; '#f3fff7' = '#ECFDF5'
    '#d9f7e7' = '#ECFDF5'

    '#f53f3f' = '#E61F24'; '#d92d20' = '#E61F24'; '#c73737' = '#E61F24'
    '#fff1f0' = '#FEF2F2'; '#fff4f0' = '#FEF2F2'; '#fff5f5' = '#FEF2F2'; '#fff7f7' = '#FEF2F2'
    '#ffe0d6' = '#FEF2F2'

    '#ff7d00' = '#F59E0B'; '#d46b08' = '#B45309'; '#b45f00' = '#B45309'; '#d97706' = '#B45309'
    '#fbbf24' = '#F59E0B'; '#f59f00' = '#F59E0B'; '#ffd36f' = '#E61F24'
    '#fff7e8' = '#FFFBEB'; '#fff8f0' = '#FFFBEB'; '#fffaf2' = '#FFFBEB'; '#ffe9c7' = '#FFFBEB'

    '#d39cff' = '#9CA3AF'; '#863bff' = '#9CA3AF'; '#722ed1' = '#6B7280'; '#6d3cc7' = '#6B7280'
    '#c02fd6' = '#6B7280'; '#159947' = '#059669'

    '#0040ff' = '#E61F24'; '#255ee8' = '#E61F24'; '#1d4ed8' = '#E61F24'; '#2f6dff' = '#E61F24'; '#8aa8ff' = '#E61F24'
    '#102a4c' = '#111827'; '#19365f' = '#111827'; '#53657c' = '#6B7280'
    '#14b8a6' = '#E61F24'; '#059669' = '#10B981'; '#16a34a' = '#10B981'
    '#8a4b05' = '#B45309'; '#ff9a2e' = '#F59E0B'; '#ffb020' = '#F59E0B'
    '#97a0b3' = '#9CA3AF'; '#a9b1bc' = '#9CA3AF'; '#d9dde4' = '#D1D5DB'
    '#e8eefc' = '#FEF2F2'; '#eef2f7' = '#FEF2F2'; '#eef2f8' = '#FEF2F2'; '#eef6ff' = '#FEF2F2'; '#f2f7ff' = '#FEF2F2'
    '#f4f1ff' = '#FEF2F2'; '#e4dcff' = '#FEF2F2'; '#f7f9ff' = '#FEF2F2'; '#f7fbff' = '#FEF2F2'; '#f7fff9' = '#ECFDF5'
    '#fcfdff' = '#FEF2F2'; '#fbfcfd' = '#F8F9FA'; '#fffafa' = '#FEF2F2'; '#ffece8' = '#FEF2F2'; '#ffccc7' = '#FEF2F2'; '#fff6e8' = '#FFFBEB'
}

# 3-digit HEX mapping
$hex3 = [ordered]@{
    '#888' = '#6B7280'
}

function Apply-Replacements([string]$block) {
    # Process rgba values first to avoid PowerShell replace quirk after large hex loop
    $block = $block -replace 'rgba\(\s*15\s*,\s*23\s*,\s*42\s*,\s*([0-9.]+)\s*\)', 'rgba(0, 0, 0, $1)'
    $block = $block -replace 'rgba\(\s*29\s*,\s*33\s*,\s*41\s*,\s*([0-9.]+)\s*\)', 'rgba(0, 0, 0, $1)'
    $block = $block -replace 'rgba\(\s*18\s*,\s*48\s*,\s*79\s*,\s*([0-9.]+)\s*\)', 'rgba(0, 0, 0, $1)'
    $block = $block -replace 'rgba\(\s*18\s*,\s*63\s*,\s*104\s*,\s*([0-9.]+)\s*\)', 'rgba(0, 0, 0, $1)'
    $block = $block -replace 'rgba\(\s*18\s*,\s*32\s*,\s*51\s*,\s*([0-9.]+)\s*\)', 'rgba(0, 0, 0, $1)'
    $block = $block -replace 'rgba\(\s*30\s*,\s*41\s*,\s*59\s*,\s*([0-9.]+)\s*\)', 'rgba(0, 0, 0, $1)'

    $block = $block -replace 'rgba\(\s*22\s*,\s*93\s*,\s*255\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'
    $block = $block -replace 'rgba\(\s*37\s*,\s*99\s*,\s*235\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'
    $block = $block -replace 'rgba\(\s*51\s*,\s*112\s*,\s*255\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'
    $block = $block -replace 'rgba\(\s*24\s*,\s*144\s*,\s*255\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'
    $block = $block -replace 'rgba\(\s*30\s*,\s*64\s*,\s*175\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'

    $block = $block -replace 'rgba\(\s*15\s*,\s*118\s*,\s*110\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'
    $block = $block -replace 'rgba\(\s*20\s*,\s*184\s*,\s*166\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'
    $block = $block -replace 'rgba\(\s*0\s*,\s*168\s*,\s*112\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'

    $block = $block -replace 'rgba\(\s*0\s*,\s*180\s*,\s*42\s*,\s*([0-9.]+)\s*\)', 'rgba(16, 185, 129, $1)'
    $block = $block -replace 'rgba\(\s*22\s*,\s*163\s*,\s*74\s*,\s*([0-9.]+)\s*\)', 'rgba(16, 185, 129, $1)'

    $block = $block -replace 'rgba\(\s*255\s*,\s*125\s*,\s*0\s*,\s*([0-9.]+)\s*\)', 'rgba(245, 158, 11, $1)'
    $block = $block -replace 'rgba\(\s*217\s*,\s*119\s*,\s*6\s*,\s*([0-9.]+)\s*\)', 'rgba(245, 158, 11, $1)'

    $block = $block -replace 'rgba\(\s*245\s*,\s*63\s*,\s*63\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'

    $block = $block -replace 'rgba\(\s*114\s*,\s*46\s*,\s*209\s*,\s*([0-9.]+)\s*\)', 'rgba(107, 114, 128, $1)'
    $block = $block -replace 'rgba\(\s*124\s*,\s*58\s*,\s*237\s*,\s*([0-9.]+)\s*\)', 'rgba(107, 114, 128, $1)'

    $block = $block -replace 'rgba\(\s*255\s*,\s*181\s*,\s*71\s*,\s*([0-9.]+)\s*\)', 'rgba(230, 31, 36, $1)'

    $block = $block -replace 'rgba\(\s*201\s*,\s*205\s*,\s*212\s*,\s*([0-9.]+)\s*\)', 'rgba(156, 163, 175, $1)'
    $block = $block -replace 'rgba\(\s*71\s*,\s*85\s*,\s*105\s*,\s*([0-9.]+)\s*\)', 'rgba(107, 114, 128, $1)'
    $block = $block -replace 'rgba\(\s*148\s*,\s*163\s*,\s*184\s*,\s*([0-9.]+)\s*\)', 'rgba(156, 163, 175, $1)'

    $block = $block -replace 'rgba\(\s*240\s*,\s*243\s*,\s*255\s*,\s*([0-9.]+)\s*\)', 'rgba(254, 242, 242, $1)'
    $block = $block -replace 'rgba\(\s*240\s*,\s*245\s*,\s*255\s*,\s*([0-9.]+)\s*\)', 'rgba(254, 242, 242, $1)'
    $block = $block -replace 'rgba\(\s*245\s*,\s*248\s*,\s*255\s*,\s*([0-9.]+)\s*\)', 'rgba(254, 242, 242, $1)'
    $block = $block -replace 'rgba\(\s*247\s*,\s*250\s*,\s*255\s*,\s*([0-9.]+)\s*\)', 'rgba(254, 242, 242, $1)'
    $block = $block -replace 'rgba\(\s*248\s*,\s*250\s*,\s*255\s*,\s*([0-9.]+)\s*\)', 'rgba(254, 242, 242, $1)'

    # HEX 6
    foreach ($kv in $hex6.GetEnumerator()) { $block = $block -replace ([regex]::Escape($kv.Key) + '\b'), $kv.Value }
    # HEX 3
    foreach ($kv in $hex3.GetEnumerator()) { $block = $block -replace ([regex]::Escape($kv.Key) + '\b'), $kv.Value }

    # 圆角
    $block = $block -replace '\b999px\b', '8px'

    return $block
}

foreach ($rel in $files) {
    $path = Join-Path $base $rel
    if (-not (Test-Path $path)) { Write-Host "Not found: $path"; continue }
    $text = [System.IO.File]::ReadAllText($path)
    $start = $text.IndexOf('<style scoped>')
    if ($start -lt 0) { Write-Host "Skip (no scoped style): $rel"; continue }
    $end = $text.LastIndexOf('</style>')
    if ($end -lt $start) { Write-Host "Skip (unclosed style): $rel"; continue }
    $end += 8  # </style>

    $before = $text.Substring(0, $start)
    $style = $text.Substring($start, $end - $start)
    $after = $text.Substring($end)

    $newStyle = Apply-Replacements $style
    if ($newStyle -ne $style) {
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($path, $before + $newStyle + $after, $utf8NoBom)
        Write-Host "Updated: $rel"
    } else {
        Write-Host "No change: $rel"
    }
}
