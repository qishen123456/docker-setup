<template>
  <section v-if="dataset || report" class="sa-digest-card">
    <div class="sa-digest-head">
      <div class="sa-digest-copy">
        <span class="sa-digest-kicker">执行摘要</span>
        <h3 class="sa-digest-title">{{ title }}</h3>
        <p class="sa-digest-desc">{{ description }}</p>
      </div>

      <div class="sa-digest-state">已生成</div>
    </div>

    <div class="sa-digest-meta">
      <div class="sa-meta-chip">{{ dataset?.dataset_name || '经营分析结果' }}</div>
      <div class="sa-meta-chip subtle">{{ attachmentCount }} 项结果</div>
      <div class="sa-meta-chip subtle">{{ datasetCount }} 个数据集</div>
    </div>

    <div class="sa-digest-stats">
      <div class="sa-stat-tile">
        <div class="sa-stat-value">{{ rowCount }}</div>
        <div class="sa-stat-label">结果行数</div>
      </div>
      <div class="sa-stat-tile">
        <div class="sa-stat-value">{{ columnCount }}</div>
        <div class="sa-stat-label">字段数量</div>
      </div>
      <div class="sa-stat-tile">
        <div class="sa-stat-value">{{ reviewStatusText }}</div>
        <div class="sa-stat-label">SQL复核</div>
      </div>
    </div>

    <div v-if="summaryLines.length" class="sa-digest-summary">
      <div v-for="(line, index) in summaryLines" :key="index" class="sa-summary-line">
        <span class="sa-summary-dot"></span>
        <span>{{ line }}</span>
      </div>
    </div>

    <div class="sa-digest-next">
      <div class="sa-digest-next-label">下一步</div>
      <button class="sa-digest-next-btn" @click="$emit('viewDetails')">
        查看执行详情与完整结果
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '本月公司经营表现分析',
  },
  report: {
    type: String,
    default: '',
  },
  dataset: {
    type: Object,
    default: null,
  },
  datasets: {
    type: Array,
    default: () => [],
  },
  route: {
    type: Object,
    default: null,
  },
})

defineEmits(['viewDetails'])

const normalizeScore = (value, fallback = 0) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return fallback
  return Math.max(0, Math.min(100, Math.round(numeric)))
}

const datasetList = computed(() => {
  if (Array.isArray(props.datasets) && props.datasets.length) return props.datasets
  return props.dataset ? [props.dataset] : []
})

const rowCount = computed(() => {
  if (props.dataset?.row_count) return Number(props.dataset.row_count) || 0
  return props.dataset?.rows?.length || 0
})

const columnCount = computed(() => props.dataset?.columns?.length || 0)
const datasetCount = computed(() => datasetList.value.length || (props.dataset ? 1 : 0))

const attachmentCount = computed(() => {
  let count = 1
  if (props.dataset) count += 1
  if (datasetCount.value > 1) count += datasetCount.value - 1
  return count + 1
})

const reviewStats = computed(() => {
  const reviews = datasetList.value
    .map(item => item?.agent3_review)
    .filter(Boolean)

  const approvedCount = reviews.filter(item => item?.approved !== false).length
  const riskCount = reviews.reduce((sum, item) => sum + (Array.isArray(item?.risks) ? item.risks.length : 0), 0)
  return {
    reviews,
    approvedCount,
    riskCount,
  }
})

const reviewStatusText = computed(() => {
  if (!reviewStats.value.reviews.length) return '待复核'
  if (reviewStats.value.riskCount > 0) return `${reviewStats.value.riskCount} 项风险`
  return '已通过'
})

const description = computed(() => {
  if (props.dataset?.dataset_name) {
    return `已基于 ${props.dataset.dataset_name} 完成结果整理，并同步生成当前经营分析摘要。`
  }
  return '当前任务结果已经整理完成，可继续查看报告、结果数据与执行明细。'
})

const summaryLines = computed(() => {
  return String(props.report || '')
    .replace(/^#+\s*/gm, '')
    .replace(/\*\*/g, '')
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 3)
})
</script>

<style scoped>
.sa-digest-card {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(245, 249, 255, 0.96) 0%, rgba(255, 255, 255, 1) 42%),
    #ffffff;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05);
}

.sa-digest-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.sa-digest-copy {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.sa-digest-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #165dff;
}

.sa-digest-title {
  margin: 0;
  font-size: 16px;
  line-height: 1.45;
  color: #1d2129;
}

.sa-digest-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
  color: #4e5969;
}

.sa-digest-state {
  height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: #e8ffea;
  color: #00b42a;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.sa-digest-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.sa-meta-chip {
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: #edf4ff;
  color: #165dff;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}

.sa-meta-chip.subtle {
  background: #f2f3f5;
  color: #4e5969;
}

.sa-digest-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.sa-stat-tile {
  padding: 11px;
  border-radius: 11px;
  background: #ffffff;
  border: 1px solid rgba(29, 33, 41, 0.08);
}

.sa-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #1d2129;
}

.sa-stat-label {
  margin-top: 4px;
  font-size: 11px;
  color: #86909c;
}

.sa-confidence-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.sa-confidence-card {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #ffffff;
}

.sa-confidence-card.is-success {
  background: linear-gradient(180deg, #f7fff9 0%, #ffffff 100%);
  border-color: rgba(0, 180, 42, 0.16);
}

.sa-confidence-card.is-info {
  background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%);
  border-color: rgba(22, 93, 255, 0.16);
}

.sa-confidence-card.is-warning {
  background: linear-gradient(180deg, #fffaf2 0%, #ffffff 100%);
  border-color: rgba(255, 125, 0, 0.16);
}

.sa-confidence-label {
  font-size: 11px;
  color: #86909c;
}

.sa-confidence-value {
  margin-top: 6px;
  font-size: 18px;
  font-weight: 700;
  color: #1d2129;
}

.sa-confidence-desc {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.6;
  color: #4e5969;
}

.sa-confidence-notes {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 1px 2px 0;
}

.sa-confidence-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 11px;
  line-height: 1.65;
  color: #4e5969;
}

.sa-confidence-note-dot {
  width: 6px;
  height: 6px;
  margin-top: 6px;
  border-radius: 50%;
  background: #165dff;
  flex-shrink: 0;
}

.sa-digest-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px 2px 0;
}

.sa-summary-line {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  font-size: 12px;
  line-height: 1.65;
  color: #1d2129;
}

.sa-summary-dot {
  width: 7px;
  height: 7px;
  margin-top: 6px;
  border-radius: 50%;
  background: #165dff;
  flex-shrink: 0;
}

.sa-digest-next {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 1px;
}

.sa-digest-next-label {
  font-size: 11px;
  color: #86909c;
}

.sa-digest-next-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 9px;
  border: 1px solid rgba(22, 93, 255, 0.18);
  background: #ffffff;
  color: #165dff;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.sa-digest-next-btn:hover {
  background: #f8fbff;
  border-color: rgba(22, 93, 255, 0.28);
}

@media (max-width: 900px) {
  .sa-digest-stats,
  .sa-confidence-grid {
    grid-template-columns: 1fr;
  }

  .sa-digest-head,
  .sa-digest-next {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
