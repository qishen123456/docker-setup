<template>
  <div v-if="report" class="sa-card sa-report-card">
    <div class="sa-report-head">
      <span class="sa-report-icon" aria-hidden="true"></span>
      <span class="sa-report-filename">{{ filename }}.PDF</span>
      <button class="sa-download-btn" title="导出 PDF" @click="$emit('download')">PDF</button>
    </div>
    <div class="sa-report-body">
      <div class="sa-report-label">执行摘要</div>
      <div class="sa-report-preview" v-html="renderedPreview"></div>
      <div class="sa-report-actions">
        <button class="sa-view-btn" @click="$emit('view')">全屏查看</button>
      </div>
      <p class="sa-report-hint">如需正式归档，请通过导出 PDF 保存当前报告。</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  report: {
    type: String,
    default: '',
  },
  question: {
    type: String,
    default: '分析报告',
  },
})

defineEmits(['download', 'view'])

const filename = computed(() => props.question || '分析报告')

const summaryText = computed(() => (
  String(props.report || '')
    .replace(/^#+\s*/gm, '')
    .replace(/\*\*/g, '')
    .replace(/\|/g, ' ')
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 4)
    .join('\n\n')
))

const renderedPreview = computed(() => marked.parse(summaryText.value || ''))
</script>

<style scoped>
.sa-card {
  width: 100%;
  border: 1px solid rgba(22, 93, 255, 0.12);
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035);
}

.sa-report-head {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px 13px;
  background: linear-gradient(180deg, #edf4ff 0%, #f5f8ff 100%);
  border-bottom: 1px solid rgba(22, 93, 255, 0.1);
}

.sa-report-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  width: 32px;
  height: 32px;
  border-radius: 11px;
  background: linear-gradient(180deg, #ffffff 0%, #eef5ff 100%);
  border: 1px solid rgba(22, 93, 255, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.sa-report-icon::before {
  content: '';
  width: 13px;
  height: 15px;
  border-radius: 4px;
  border: 1.5px solid #165dff;
  background: linear-gradient(180deg, rgba(22, 93, 255, 0.08) 0%, rgba(22, 93, 255, 0.02) 100%);
}

.sa-report-icon::after {
  content: '';
  position: absolute;
  top: 9px;
  right: 8px;
  width: 4px;
  height: 4px;
  border-top: 1.5px solid #165dff;
  border-right: 1.5px solid #165dff;
  transform: rotate(45deg);
}

.sa-report-filename {
  flex: 1;
  font-weight: 600;
  font-size: 13px;
  color: var(--color-primary);
}

.sa-download-btn {
  min-width: 42px;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(22, 93, 255, 0.16);
  background: #ffffff;
  cursor: pointer;
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 700;
}

.sa-download-btn:hover {
  opacity: 0.86;
}

.sa-report-body {
  padding: 13px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sa-report-label {
  font-size: 11px;
  font-weight: 700;
  color: #86909c;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.sa-report-preview {
  font-size: 13px;
  line-height: 1.72;
  color: var(--text-title);
}

.sa-report-preview :deep(h1),
.sa-report-preview :deep(h2),
.sa-report-preview :deep(h3) {
  font-size: 15px;
  color: #1d2129;
  margin: 0 0 6px;
}

.sa-report-preview :deep(p) {
  margin: 0;
}

.sa-report-preview :deep(ul),
.sa-report-preview :deep(ol) {
  margin: 0;
  padding-left: 16px;
}

.sa-report-hint {
  margin: 0;
  font-size: 11px;
  color: var(--text-muted);
}

.sa-report-actions {
  display: flex;
  justify-content: flex-end;
}

.sa-view-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 9px;
  border: 1px solid rgba(22, 93, 255, 0.16);
  background: #ffffff;
  color: #165dff;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
}
</style>
