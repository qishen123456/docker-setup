<template>
  <div v-if="sql" class="sa-sql-block">
    <div class="sa-sql-header">
      <div class="sa-sql-meta">
        <span class="sa-sql-icon">SQL</span>
        <div class="sa-sql-title-wrap">
          <span class="sa-sql-title">PostgreSQL 查询</span>
          <span class="sa-sql-caption">{{ lineCount }} 行 · 已格式化</span>
        </div>
      </div>
      <div class="sa-sql-actions">
        <span class="sa-sql-state">
          <span class="sa-sql-state-dot"></span>
          已生成
        </span>
        <button class="sa-copy-btn" @click="handleCopy" type="button" :aria-label="copied ? '已复制 SQL' : '复制 SQL'">
          <span class="sa-copy-icon" aria-hidden="true"></span>
          {{ copied ? '已复制' : '复制' }}
        </button>
      </div>
    </div>

    <div class="sa-sql-surface">
      <div class="sa-sql-gutter" aria-hidden="true">
        <span v-for="line in lineCount" :key="line">{{ String(line).padStart(2, '0') }}</span>
      </div>
      <pre class="sa-sql-pre"><code ref="codeRef" class="language-sql"></code></pre>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import hljs from 'highlight.js/lib/core'
import sql from 'highlight.js/lib/languages/sql'

hljs.registerLanguage('sql', sql)

const props = defineProps({
  sql: {
    type: String,
    default: ''
  }
})

const copied = ref(false)
const codeRef = ref(null)

const stripCodeFence = (value) => String(value || '')
  .replace(/^```(?:sql|json)?\s*/i, '')
  .replace(/```$/i, '')
  .trim()

const maybeExtractSql = (value) => {
  const source = stripCodeFence(value)
  try {
    const parsed = JSON.parse(source)
    return parsed?.final_sql || parsed?.sql || parsed?.query || source
  } catch (error) {
    return source
  }
}

const normalizeSqlText = (value) => {
  const source = maybeExtractSql(value)
  return String(source || '')
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '  ')
    .replace(/\\"/g, '"')
    .trim()
}

const formatSqlForDisplay = (value) => {
  const raw = normalizeSqlText(value)
  if (!raw) return ''

  const compact = raw
    .replace(/\r\n/g, '\n')
    .replace(/\s+/g, ' ')
    .trim()

  const broken = compact
    .replace(/\b(UNION ALL|UNION)\b/gi, '\n$1')
    .replace(/\b(WITH|SELECT|FROM|WHERE|GROUP BY|HAVING|ORDER BY|LIMIT|OFFSET)\b/gi, '\n$1')
    .replace(/\b(LEFT JOIN|RIGHT JOIN|INNER JOIN|FULL OUTER JOIN|FULL JOIN|CROSS JOIN|JOIN)\b/gi, '\n$1')
    .replace(/\s+(AND|OR)\s+/gi, '\n  $1 ')
    .replace(/,\s*/g, ',\n  ')
    .replace(/\(\s*SELECT\b/gi, '(\nSELECT')
    .replace(/\)\s*,/g, '),')
    .trim()

  let depth = 0
  return broken
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map((line) => {
      const closeCount = (line.match(/\)/g) || []).length
      const openCount = (line.match(/\(/g) || []).length
      if (/^\)/.test(line)) depth = Math.max(depth - 1, 0)

      const isRootKeyword = /^(WITH|SELECT|FROM|WHERE|GROUP BY|HAVING|ORDER BY|LIMIT|OFFSET|UNION|UNION ALL)\b/i.test(line)
      const isJoinOrPredicate = /^(LEFT JOIN|RIGHT JOIN|INNER JOIN|FULL OUTER JOIN|FULL JOIN|CROSS JOIN|JOIN|AND|OR)\b/i.test(line)
      const baseDepth = isRootKeyword ? Math.max(depth - 1, 0) : depth
      const indentDepth = isJoinOrPredicate ? Math.max(baseDepth, 1) : baseDepth
      const formatted = `${'  '.repeat(indentDepth)}${line}`

      depth = Math.max(depth + openCount - closeCount, 0)
      return formatted
    })
    .join('\n')
}

const displaySql = computed(() => formatSqlForDisplay(props.sql))

const lineCount = computed(() => {
  const total = String(displaySql.value || '')
    .split('\n')
    .length
  return Math.max(total, 1)
})

const highlightCode = async () => {
  await nextTick()
  if (codeRef.value && displaySql.value) {
    codeRef.value.removeAttribute('data-highlighted')
    codeRef.value.textContent = displaySql.value
    hljs.highlightElement(codeRef.value)
  }
}

const handleCopy = () => {
  navigator.clipboard.writeText(displaySql.value || props.sql)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 1500)
}

onMounted(() => {
  highlightCode()
})

watch(displaySql, () => {
  highlightCode()
})
</script>

<style scoped>
.sa-sql-block {
  border: 1px solid rgba(229, 230, 235, 0.95);
  border-radius: 12px;
  overflow: hidden;
  margin: 9px 0;
  background: #f7f8fa;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.sa-sql-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 44px;
  padding: 8px 12px 7px;
  background: #ffffff;
  border-bottom: 1px solid rgba(229, 230, 235, 0.9);
}

.sa-sql-meta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.sa-sql-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 31px;
  height: 31px;
  border-radius: 9px;
  border: 1px solid rgba(22, 93, 255, 0.16);
  background: #edf4ff;
  color: #165dff;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.sa-sql-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.sa-sql-title {
  font-size: 12px;
  line-height: 1.35;
  font-weight: 700;
  color: #1d2129;
}

.sa-sql-caption {
  font-size: 10px;
  color: #86909c;
  font-weight: 500;
  white-space: nowrap;
}

.sa-sql-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.sa-sql-state {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: #e8ffea;
  color: #00b42a;
  font-size: 10px;
  font-weight: 700;
}

.sa-sql-state-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.sa-copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #ffffff;
  border: 1px solid rgba(22, 93, 255, 0.18);
  color: #165dff;
  border-radius: 8px;
  height: 28px;
  padding: 0 9px;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.sa-copy-btn:hover {
  border-color: rgba(22, 93, 255, 0.36);
  color: #0e42d2;
  background: #edf4ff;
  transform: translateY(-1px);
}

.sa-copy-icon {
  position: relative;
  width: 11px;
  height: 11px;
}

.sa-copy-icon::before,
.sa-copy-icon::after {
  content: '';
  position: absolute;
  border: 1.4px solid currentColor;
  border-radius: 3px;
}

.sa-copy-icon::before {
  inset: 2px 0 0 2px;
  opacity: 0.65;
}

.sa-copy-icon::after {
  inset: 0 2px 2px 0;
  background: rgba(255, 255, 255, 0.96);
}

.sa-sql-surface {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: stretch;
  max-height: 360px;
  overflow: auto;
  margin: 10px;
  border-radius: 9px;
  border: 1px solid rgba(229, 230, 235, 0.82);
  background: #f4f5f7;
}

.sa-sql-gutter {
  padding: 14px 0 14px 8px;
  border-right: 1px solid rgba(229, 230, 235, 0.9);
  background: #f0f2f5;
  color: #a9b0bd;
  font-family: var(--font-mono, 'JetBrains Mono', 'Cascadia Code', Consolas, monospace);
  font-size: 10px;
  line-height: 1.72;
  user-select: none;
  position: sticky;
  left: 0;
  z-index: 1;
}

.sa-sql-gutter span {
  display: block;
  height: 19px;
}

.sa-sql-pre {
  margin: 0;
  padding: 14px 16px 16px;
  background: transparent;
  overflow: visible;
  font-family: var(--font-mono, 'JetBrains Mono', 'Cascadia Code', Consolas, monospace);
  font-size: 11px;
  line-height: 1.72;
  color: #252b3a;
}

.sa-sql-pre code {
  display: block;
  min-width: 620px;
  background: transparent;
  padding: 0;
  tab-size: 2;
}

:deep(.sa-sql-pre .hljs) {
  background: transparent;
  color: #252b3a;
}

:deep(.sa-sql-pre .hljs-keyword),
:deep(.sa-sql-pre .hljs-selector-tag) {
  color: #c02fd6;
  font-weight: 800;
}

:deep(.sa-sql-pre .hljs-string) {
  color: #159947;
}

:deep(.sa-sql-pre .hljs-number),
:deep(.sa-sql-pre .hljs-literal) {
  color: #f59f00;
}

:deep(.sa-sql-pre .hljs-comment) {
  color: #9aa3b2;
  font-style: italic;
}

:deep(.sa-sql-pre .hljs-built_in),
:deep(.sa-sql-pre .hljs-function),
:deep(.sa-sql-pre .hljs-title.function_) {
  color: #168cff;
  font-weight: 700;
}

:deep(.sa-sql-pre .hljs-operator),
:deep(.sa-sql-pre .hljs-punctuation) {
  color: #7b8496;
}

.sa-sql-surface::-webkit-scrollbar {
  height: 8px;
  width: 8px;
}

.sa-sql-surface::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.38);
}

.sa-sql-surface::-webkit-scrollbar-track {
  background: transparent;
}

@media (max-width: 760px) {
  .sa-sql-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .sa-sql-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
