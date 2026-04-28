<template>
  <div v-if="sql" class="sa-sql-block">
    <div class="sa-sql-header">
      <div class="sa-sql-meta">
        <span class="sa-sql-chip">SQL</span>
        <span class="sa-sql-caption">{{ lineCount }} 行查询片段</span>
      </div>
      <button class="sa-copy-btn" @click="handleCopy">
        <span class="sa-copy-icon" aria-hidden="true"></span>
        {{ copied ? '已复制' : '复制' }}
      </button>
    </div>

    <div class="sa-sql-surface">
      <div class="sa-sql-gutter" aria-hidden="true">
        <span v-for="line in lineCount" :key="line">{{ line }}</span>
      </div>
      <pre class="sa-sql-pre"><code ref="codeRef" class="language-sql"></code></pre>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
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

const lineCount = computed(() => {
  const total = String(props.sql || '')
    .split('\n')
    .filter(line => line.trim().length > 0).length
  return Math.max(total, 1)
})

const highlightCode = () => {
  if (codeRef.value && props.sql) {
    codeRef.value.textContent = props.sql
    hljs.highlightElement(codeRef.value)
  }
}

const handleCopy = () => {
  navigator.clipboard.writeText(props.sql)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 1500)
}

onMounted(() => {
  highlightCode()
})

watch(() => props.sql, () => {
  highlightCode()
})
</script>

<style scoped>
.sa-sql-block {
  border: 1px solid rgba(201, 205, 212, 0.9);
  border-radius: 12px;
  overflow: hidden;
  margin: 8px 0;
  background:
    linear-gradient(180deg, rgba(247, 249, 252, 0.96) 0%, rgba(255, 255, 255, 0.98) 28%),
    #ffffff;
  box-shadow:
    0 10px 26px rgba(15, 23, 42, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.sa-sql-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 40px;
  padding: 0 12px;
  background: rgba(248, 250, 252, 0.92);
  border-bottom: 1px solid rgba(229, 230, 235, 0.92);
}

.sa-sql-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.sa-sql-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(22, 93, 255, 0.08);
  color: #165dff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.sa-sql-caption {
  font-size: 10px;
  color: #86909c;
  font-weight: 500;
  white-space: nowrap;
}

.sa-copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #ffffff;
  border: 1px solid #d9dde4;
  color: #4e5969;
  border-radius: 999px;
  height: 26px;
  padding: 0 10px;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.sa-copy-btn:hover {
  border-color: rgba(22, 93, 255, 0.4);
  color: #165dff;
  background: #f5f8ff;
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
  grid-template-columns: 36px 1fr;
  align-items: stretch;
}

.sa-sql-gutter {
  padding: 12px 0 12px 10px;
  border-right: 1px solid rgba(229, 230, 235, 0.82);
  background: linear-gradient(180deg, rgba(247, 248, 250, 0.95) 0%, rgba(252, 253, 255, 1) 100%);
  color: #c9cdd4;
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 10px;
  line-height: 1.75;
  user-select: none;
}

.sa-sql-gutter span {
  display: block;
  height: 19px;
}

.sa-sql-pre {
  margin: 0;
  padding: 12px 14px 14px;
  background: transparent;
  overflow-x: auto;
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 11px;
  line-height: 1.72;
}

.sa-sql-pre code {
  display: block;
  min-width: max-content;
  background: transparent;
  padding: 0;
}

.sa-sql-pre .hljs {
  background: transparent;
  color: #1d2129;
}

.sa-sql-pre .hljs-keyword,
.sa-sql-pre .hljs-selector-tag {
  color: #165dff;
  font-weight: 700;
}

.sa-sql-pre .hljs-string {
  color: #a05a00;
}

.sa-sql-pre .hljs-number,
.sa-sql-pre .hljs-literal {
  color: #0f7b6c;
}

.sa-sql-pre .hljs-comment {
  color: #94a0b2;
  font-style: italic;
}

.sa-sql-pre .hljs-function,
.sa-sql-pre .hljs-title.function_ {
  color: #3b4a68;
}

.sa-sql-pre .hljs-operator,
.sa-sql-pre .hljs-punctuation {
  color: #72809a;
}
</style>
