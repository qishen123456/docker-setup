<template>
  <section v-if="dataset || report" class="sa-boss-answer">
    <div class="sa-boss-answer-mainline">
      <div class="sa-boss-answer-copy">
        <div class="sa-boss-answer-row">
          <span class="sa-boss-answer-label">问题：</span>
          <span class="sa-boss-answer-question">{{ questionLabel }}</span>
        </div>
        <div class="sa-boss-answer-row">
          <span class="sa-boss-answer-label">结论：</span>
          <span class="sa-boss-answer-conclusion">{{ directAnswer }}</span>
        </div>
      </div>

      <button class="sa-boss-answer-link" @click="$emit('viewDetails')">查看详情</button>
    </div>

    <div v-if="supportLines.length" class="sa-boss-answer-points">
      <span v-for="(line, index) in supportLines.slice(0, 2)" :key="index">{{ line }}</span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '本轮问数结论',
  },
  question: {
    type: String,
    default: '',
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

const datasetList = computed(() => {
  if (Array.isArray(props.datasets) && props.datasets.length) return props.datasets
  return props.dataset ? [props.dataset] : []
})

const rowCount = computed(() => {
  if (props.dataset?.row_count) return Number(props.dataset.row_count) || 0
  return props.dataset?.rows?.length || 0
})

const reviewStats = computed(() => {
  const reviews = datasetList.value.map(item => item?.agent3_review).filter(Boolean)
  return {
    reviews,
    riskCount: reviews.reduce((sum, item) => sum + (Array.isArray(item?.risks) ? item.risks.length : 0), 0),
  }
})

const reviewStatusText = computed(() => {
  if (!reviewStats.value.reviews.length) return '已完成'
  if (reviewStats.value.riskCount > 0) return `${reviewStats.value.riskCount} 项风险`
  return 'SQL通过'
})

const questionLabel = computed(() => cleanText(props.question || props.title || '本轮问数'))

const rows = computed(() => (Array.isArray(props.dataset?.rows) ? props.dataset.rows : []))

const cleanText = (value) => String(value ?? '').trim()
const toNumber = (value) => {
  if (value === null || value === undefined || value === '') return null
  const numeric = Number(String(value).replace(/[%万,，\s]/g, ''))
  return Number.isFinite(numeric) ? numeric : null
}

const findColumn = (row, matchers = []) => {
  const keys = Object.keys(row || {})
  return keys.find(key => matchers.some(matcher => matcher.test(key))) || ''
}

const rateText = (row) => {
  const key = findColumn(row, [/达成率/, /completion.*rate/i, /\brate\b/i])
  const value = toNumber(key ? row[key] : null)
  if (value === null) return ''
  return `${value.toFixed(2).replace(/\.?0+$/, '')}%`
}

const normalizedRows = computed(() => rows.value.map((row) => {
  const nameKey = findColumn(row, [/节点名称/, /^name$/i, /名称/, /分公司|代表处|业务代表/])
  const parentKey = findColumn(row, [/上级名称/, /parent/i, /分公司/])
  const levelKey = findColumn(row, [/层级/, /^level$/i])
  const rateKey = findColumn(row, [/达成率/, /completion.*rate/i, /\brate\b/i])
  return {
    name: cleanText(nameKey ? row[nameKey] : ''),
    parent: cleanText(parentKey ? row[parentKey] : ''),
    level: cleanText(levelKey ? row[levelKey] : ''),
    rate: toNumber(rateKey ? row[rateKey] : null),
    rateText: rateText(row),
  }
}).filter(item => item.name))

const questionText = computed(() => cleanText(props.question || props.title))
const asksLowest = computed(() => /最低|最差|不好|垫底|落后|风险/.test(questionText.value))
const asksRepresentative = computed(() => /代表处/.test(questionText.value))
const asksBusinessPerson = computed(() => /业务代表|业务员/.test(questionText.value))
const asksLowerNode = computed(() => asksRepresentative.value || asksBusinessPerson.value)
const lowerNodeLabel = computed(() => (asksBusinessPerson.value ? '业务代表' : '代表处'))

const targetRows = computed(() => {
  if (!asksLowerNode.value) return normalizedRows.value
  const label = lowerNodeLabel.value
  const filtered = normalizedRows.value.filter(item => item.level === label || item.name.includes(label))
  return filtered.length ? filtered : normalizedRows.value
})

const sortedByRateAsc = computed(() => (
  [...targetRows.value]
    .filter(item => item.rate !== null)
    .sort((a, b) => a.rate - b.rate)
))

const sortedByRateDesc = computed(() => [...sortedByRateAsc.value].reverse())

const levelSummary = computed(() => {
  const counts = new Map()
  normalizedRows.value.forEach((item) => {
    const key = item.level || '明细'
    counts.set(key, (counts.get(key) || 0) + 1)
  })
  return Array.from(counts.entries()).map(([level, count]) => `${level}${count}个`).join('、')
})

const riskRows = computed(() => normalizedRows.value.filter(item => item.rate !== null && item.rate < 80))

const groupedWorstLines = computed(() => {
  if (!asksLowerNode.value || !asksLowest.value) return []
  const groups = new Map()
  targetRows.value.forEach((item) => {
    if (!item.parent || item.rate === null) return
    const current = groups.get(item.parent)
    if (!current || item.rate < current.rate) groups.set(item.parent, item)
  })
  return Array.from(groups.entries())
    .map(([parent, item]) => `${parent} 下最低是 ${item.name}${item.rateText ? `，达成率 ${item.rateText}` : ''}`)
    .slice(0, 2)
})

const usefulReportLines = computed(() => (
  String(props.report || '')
    .replace(/^#+\s*/gm, '')
    .replace(/\*\*/g, '')
    .split('\n')
    .map(item => item.replace(/^[-*•\s]+/, '').trim())
    .filter(Boolean)
    .filter(line => !/^(业绩分析报告|核心结论|亮点分析|问题诊断|改进建议|报告内容|节点摘要)$/i.test(line))
    .filter(line => !/^SQL|^数据集|^报告模板|^当前/.test(line))
    .slice(0, 4)
))

const directAnswer = computed(() => {
  if (asksLowerNode.value && asksLowest.value && groupedWorstLines.value.length) {
    return `已按上级组织拆开看，不能把所有${lowerNodeLabel.value}直接混在一起比。`
  }
  const worst = sortedByRateAsc.value[0]
  if (worst && asksLowest.value) return `最低的是 ${worst.name}${worst.rateText ? `，达成率 ${worst.rateText}` : ''}。`
  const best = sortedByRateDesc.value[0]
  if (best && worst) {
    return `本轮返回 ${rowCount.value || normalizedRows.value.length} 行结果，${best.name}达成最好${best.rateText ? `（${best.rateText}）` : ''}，${worst.name}压力最大${worst.rateText ? `（${worst.rateText}）` : ''}。`
  }
  return usefulReportLines.value[0] || props.title || '本轮问数已完成。'
})

const supportLines = computed(() => {
  if (groupedWorstLines.value.length) return groupedWorstLines.value
  const worst = sortedByRateAsc.value[0]
  const second = sortedByRateAsc.value[1]
  if (worst && asksLowest.value) {
    return [
      second ? `次低是 ${second.name}${second.rateText ? `，达成率 ${second.rateText}` : ''}` : '',
      '右侧可查看完整明细、SQL 和报告。',
    ].filter(Boolean)
  }
  if (normalizedRows.value.length) {
    return [
      levelSummary.value ? `覆盖层级：${levelSummary.value}` : '',
      riskRows.value.length ? `低于80%的风险节点 ${riskRows.value.length} 个，建议先看右侧下钻明细。` : '暂无低于80%的明显风险节点。',
    ].filter(Boolean)
  }
  return usefulReportLines.value.slice(1, 3)
})
</script>

<style scoped>
.sa-boss-answer {
  width: 100%;
  padding: 11px 13px;
  border-radius: 13px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: #ffffff;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}

.sa-boss-answer-mainline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.sa-boss-answer-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sa-boss-answer-row {
  display: flex;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
}

.sa-boss-answer-label {
  flex-shrink: 0;
  font-size: 13px;
  line-height: 1.55;
  font-weight: 700;
  color: #1d2129;
}

.sa-boss-answer-question {
  min-width: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #1d2129;
}

.sa-boss-answer-conclusion {
  min-width: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #1d2129;
  font-weight: 700;
}

.sa-boss-answer-link {
  flex-shrink: 0;
  height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  border: 1px solid rgba(22, 93, 255, 0.18);
  background: #f8fbff;
  color: #165dff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.sa-boss-answer-points {
  display: flex;
  flex-wrap: wrap;
  gap: 7px 12px;
  margin-top: 8px;
  font-size: 11px;
  color: #86909c;
}

.sa-boss-answer-points span:not(:last-child)::after {
  content: '·';
  margin-left: 12px;
  color: #c9cdd4;
}

@media (max-width: 760px) {
  .sa-boss-answer-mainline {
    flex-direction: column;
  }
}
</style>
