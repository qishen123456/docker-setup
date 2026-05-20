<template>
  <section v-if="dataset || report" class="sa-boss-answer">
    <div class="sa-boss-answer-head">
      <div class="sa-boss-answer-title-block">
        <div class="sa-boss-answer-kicker-row">
          <span class="sa-boss-answer-kicker">经营分析报告</span>
          <span v-if="flowLabel" class="sa-report-flow-badge" :class="flowClass">{{ flowLabel }}</span>
          <small v-if="flowLabel && flowHint" class="sa-report-flow-hint">{{ flowHint }}</small>
        </div>
        <h3 class="sa-boss-answer-title">{{ questionLabel }}</h3>
      </div>
      <button v-if="showDetailsButton" class="sa-boss-answer-link" @click="$emit('viewDetails')">查看详情</button>
    </div>

    <div class="sa-core-section">
      <div class="sa-section-label">一、核心结论</div>
      <div class="sa-core-body">
        <div v-if="isComparisonDigest" class="sa-comparison-digest">
          <div class="sa-comparison-verdict">{{ comparisonVerdict }}</div>
          <div class="sa-comparison-card-grid" :class="`is-count-${Math.min(visibleComparisonDigestRows.length, 4)}`">
            <article
              v-for="row in visibleComparisonDigestRows"
              :key="row.name"
              class="sa-comparison-card"
              :class="{ 'is-leader': row.name === comparisonLeader?.name }"
            >
              <div class="sa-comparison-card-head">
                <span>{{ row.name }}</span>
                <strong>{{ row.rateText || '-' }}</strong>
              </div>
              <div class="sa-comparison-metrics">
                <span>开单 {{ row.actualText || '-' }}</span>
                <span>任务 {{ row.taskText || '-' }}</span>
                <span>缺口 {{ row.remainText || '-' }}</span>
              </div>
            </article>
          </div>
          <div v-if="comparisonGapItems.length" class="sa-comparison-gap-list">
            <span v-for="item in comparisonGapItems" :key="item.label">{{ item.label }} {{ item.value }}</span>
          </div>
        </div>
        <p v-else class="sa-boss-answer-conclusion">{{ directAnswer }}</p>
      </div>
    </div>

    <div v-if="primaryKpiCards.length" class="sa-report-mini-section">
      <div class="sa-section-label">二、关键指标</div>
      <div class="sa-kpi-grid" :class="`is-count-${Math.min(primaryKpiCards.length, 4)}`">
        <article v-for="card in primaryKpiCards" :key="card.key" class="sa-kpi-card" :class="`is-${card.tone}`">
          <div class="sa-kpi-value">{{ card.value }}</div>
          <div class="sa-kpi-label">{{ card.label }}</div>
          <div v-if="card.hint" class="sa-kpi-hint">{{ card.hint }}</div>
        </article>
      </div>
    </div>

    <div v-if="insightCards.length" class="sa-report-mini-section">
      <div class="sa-section-label">三、结构看板</div>
      <div class="sa-insight-grid">
        <article v-for="item in insightCards" :key="item.label" class="sa-insight-card" :class="`is-${item.tone}`">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.desc }}</small>
        </article>
      </div>
    </div>

    <div v-if="secondaryDrillRows.length" class="sa-report-mini-section sa-drill-section">
      <div class="sa-section-title-line">
        <div class="sa-section-label">{{ drillSectionLabel }}</div>
        <span>{{ secondaryDrillSummary }}</span>
      </div>
      <div class="sa-drill-table" :class="{ 'is-person-ranking': isBusinessPersonRanking }" role="table" aria-label="二级经营拆解">
        <div class="sa-drill-row is-head" role="row">
          <span>节点</span>
          <span>任务 / 完成</span>
          <span>缺口</span>
          <span>达成率</span>
        </div>
        <template v-for="group in secondaryDrillGroups" :key="group.key">
          <div v-if="group.title" class="sa-drill-group-row" :class="`is-group-${(group.index % 4) + 1}`" role="row">
            <span>{{ group.title }}</span>
            <small>{{ group.rows.length }}个{{ secondaryLevelLabel }}</small>
          </div>
          <div v-for="(row, index) in group.rows" :key="`drill-${row.level}-${row.parent}-${row.name}-${index}`" class="sa-drill-row" role="row">
            <div class="sa-drill-node">
              <strong>{{ row.name }}</strong>
              <span>{{ drillNodeMeta(row) }}</span>
            </div>
            <div class="sa-drill-number">
              <strong>{{ row.taskText || '-' }}</strong>
              <span>完成 {{ row.actualText || '-' }}</span>
            </div>
            <div class="sa-drill-gap">{{ row.remainText || '-' }}</div>
            <div class="sa-drill-rate" :class="secondaryRateTone(row)">
              <div class="sa-drill-rate-head">
                <strong>{{ row.rateText || '-' }}</strong>
                <span>{{ secondaryRateHint(row) }}</span>
              </div>
              <div class="sa-drill-bar" aria-hidden="true">
                <i :style="{ width: secondaryBarWidth(row) }"></i>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div
      v-if="supportLines.length || actionItems.length"
      class="sa-report-mini-section sa-advice-section"
      :class="{ 'is-single': !supportLines.length || !actionItems.length }"
    >
      <div v-if="supportLines.length" class="sa-advice-block">
        <div class="sa-section-label">{{ supportSectionLabel }}</div>
        <ol class="sa-advice-list">
          <li v-for="(line, index) in supportLines.slice(0, 3)" :key="`support-${index}`">{{ line }}</li>
        </ol>
      </div>
      <div v-if="actionItems.length" class="sa-advice-block">
        <div class="sa-section-label">{{ actionSectionLabel }}</div>
        <ol class="sa-advice-list">
          <li v-for="(line, index) in actionItems" :key="`action-${index}`">{{ line }}</li>
        </ol>
      </div>
    </div>

    <div v-if="reportDebugItems.length" class="sa-report-debug-strip" aria-label="报告状态">
      <span v-for="item in reportDebugItems" :key="item.label" :class="`is-${item.tone || 'neutral'}`">
        {{ item.label }}：{{ item.value }}
      </span>
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
  showDetailsButton: {
    type: Boolean,
    default: true,
  },
  flowLabel: {
    type: String,
    default: '',
  },
  flowClass: {
    type: String,
    default: '',
  },
  flowHint: {
    type: String,
    default: '',
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
const sameOrgName = (left, right) => {
  const leftText = cleanText(left)
  const rightText = cleanText(right)
  if (!leftText || !rightText) return false
  return leftText === rightText || leftText.includes(rightText) || rightText.includes(leftText)
}

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

const amountText = (value) => {
  const numeric = toNumber(value)
  if (numeric === null) return ''
  const abs = Math.abs(numeric)
  if (abs >= 100000000) return `${(numeric / 100000000).toFixed(2).replace(/\.?0+$/, '')}亿`
  if (abs >= 10000) return `${(numeric / 10000).toFixed(1).replace(/\.?0+$/, '')}万`
  return numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

const questionText = computed(() => cleanText(props.question || props.title))
const chineseNumberMap = {
  一: 1,
  二: 2,
  两: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
  七: 7,
  八: 8,
  九: 9,
}
const parseRankNumber = (value) => {
  const text = cleanText(value)
  if (!text) return 0
  if (/^\d+$/.test(text)) return Number(text)
  if (text === '十') return 10
  if (text.includes('十')) {
    const [left, right] = text.split('十')
    return (chineseNumberMap[left] || (left ? 0 : 1)) * 10 + (chineseNumberMap[right] || 0)
  }
  return chineseNumberMap[text] || 0
}
const requestedRankLimit = computed(() => {
  const text = questionText.value
  const match = text.match(/(?:Top|TOP|top|前|后|倒数)\s*(\d+|[一二两三四五六七八九十]+)/)
  const count = parseRankNumber(match?.[1])
  if (count) return Math.max(1, Math.min(20, count))
  if (/排名|排行|前|后/.test(text)) return 3
  return 0
})
const isRankingQuestion = computed(() => Boolean(
  requestedRankLimit.value || /排名|排行|最高|最低|最好|最差|倒数|垫底/.test(questionText.value),
))
const rankDirection = computed(() => (
  /最低|最差|倒数|垫底|后/.test(questionText.value) ? 'asc' : 'desc'
))
const normalizeLevelHint = (value) => {
  const text = cleanText(value)
  if (!text || /^(对象|下一层级|明细层级|下级节点)$/.test(text)) return ''
  if (text.includes('业务代表') || text.includes('业务员')) return '业务代表'
  if (text.includes('代表处')) return '代表处'
  if (text.includes('城市公司') || text.includes('城市分公司')) return '城市公司'
  if (text.includes('分公司')) return '分公司'
  if (text.includes('业务部')) return '业务部'
  return ''
}
const explicitQuestionLevel = computed(() => {
  const text = questionText.value
  if (/业务代表|业务员/.test(text)) return '业务代表'
  if (/代表处/.test(text)) return '代表处'
  if (/城市公司|城市分公司/.test(text)) return '城市公司'
  if (/业务部/.test(text)) return '业务部'
  if (/分公司/.test(text)) return '分公司'
  return ''
})
const specScope = computed(() => props.dataset?.report_spec?.scope || datasetList.value.find(item => item?.report_spec?.scope)?.report_spec?.scope || {})
const specCompareLevel = computed(() => normalizeLevelHint(specScope.value?.compareLevelLabel))
const specDetailLevel = computed(() => normalizeLevelHint(specScope.value?.detailLevelLabel))
const digestCompareLevel = computed(() => explicitQuestionLevel.value || specCompareLevel.value)
const isPeerLevelQuestion = computed(() => Boolean(
  digestCompareLevel.value &&
  !specScope.value?.focusNode &&
  /各|全部|所有|每个|四个|多个|分别|对比|比较|排名|排行|业绩|情况|怎么样|完成|达成/.test(questionText.value),
))
const rowMatchesLevel = (row, level) => {
  const target = normalizeLevelHint(level)
  if (!target) return true
  const name = cleanText(row?.name)
  const nameLevel = normalizeLevelHint(name)
  if (nameLevel && nameLevel !== target) return false
  return row?.level === target || name.includes(target)
}

const specDigestRows = computed(() => {
  const accordions = Array.isArray(props.dataset?.report_spec?.accordions)
    ? props.dataset.report_spec.accordions
    : []
  const rows = accordions.map((item) => {
    const kpis = Array.isArray(item?.kpis) ? item.kpis : []
    const findKpi = (matcher) => kpis.find(kpi => matcher.test(kpi?.label || '')) || null
    const task = findKpi(/总任务|任务金额|任务|目标/i)
    const actual = findKpi(/年度开单|开单金额|开单|完成|实际|销售/i)
    const remain = findKpi(/剩余|缺口|差额|remain/i)
    const rate = findKpi(/达成率|percent|rate/i)
    const rateValue = toNumber(rate?.value)
    return {
      name: cleanText(item?.title || item?.name || ''),
      parent: cleanText(item?.parentName || ''),
      level: cleanText(item?.levelLabel || props.dataset?.report_spec?.scope?.compareLevelLabel || ''),
      rate: rateValue,
      rateText: rate?.value || (rateValue !== null ? `${rateValue.toFixed(2).replace(/\.?0+$/, '')}%` : ''),
      task: toNumber(task?.value),
      actual: toNumber(actual?.value),
      remain: toNumber(remain?.value),
      taskText: task?.value || '',
      actualText: actual?.value || '',
      remainText: remain?.value || '',
    }
  }).filter(item => item.name)
  const level = digestCompareLevel.value
  if (!level) return rows
  const scoped = rows.filter(item => rowMatchesLevel(item, level))
  return scoped.length >= 2 ? scoped : rows
})

const normalizedRows = computed(() => rows.value.map((row) => {
  const rowKeys = Object.keys(row || {})
  const nameKey = findColumn(row, [/节点名称/, /^name$/i, /名称/, /分公司|代表处|业务代表/])
  const parentKey = findColumn(row, [/上级名称/, /上级组织/, /父级名称/, /父级节点/, /parent/i, /上级/, /父级/])
  const pathKey = findColumn(row, [/组织路径/, /归属组织/, /组织归属/, /管理链路/, /路径/])
  const levelKey = findColumn(row, [/层级/, /^level$/i])
  const rateKey = findColumn(row, [/达成率/, /completion.*rate/i, /\brate\b/i])
  const taskKey = rowKeys.find(key => /总任务|任务金额|任务|目标/i.test(key) && !/剩余|缺口|差额|remain/i.test(key)) || ''
  const actualKey = rowKeys.find(key => /年度开单|开单金额|开单|完成|实际|销售/i.test(key) && !/达成率|完成率|率/i.test(key)) || ''
  const remainKey = rowKeys.find(key => /剩余任务|剩余|缺口|差额|remain/i.test(key)) || ''
  return {
    name: cleanText(nameKey ? row[nameKey] : ''),
    parent: cleanText(parentKey ? row[parentKey] : ''),
    path: cleanText(pathKey ? row[pathKey] : ''),
    level: cleanText(levelKey ? row[levelKey] : ''),
    rate: toNumber(rateKey ? row[rateKey] : null),
    rateText: rateText(row),
    task: toNumber(taskKey ? row[taskKey] : null),
    actual: toNumber(actualKey ? row[actualKey] : null),
    remain: toNumber(remainKey ? row[remainKey] : null),
    taskText: amountText(taskKey ? row[taskKey] : null),
    actualText: amountText(actualKey ? row[actualKey] : null),
    remainText: amountText(remainKey ? row[remainKey] : null),
    raw: row,
  }
}).filter(item => item.name))

const isComparisonQuestion = computed(() => resolvedMemberNames.value.length >= 2 || /对比|比较|差异|哪个|谁更|分别|各自|和.+比|跟.+比|与.+比|\bvs\b/i.test(questionText.value))
const asksLowest = computed(() => /最低|最差|不好|垫底|落后|风险/.test(questionText.value))
const asksRepresentative = computed(() => /代表处/.test(questionText.value))
const asksBusinessPerson = computed(() => /业务代表|业务员/.test(questionText.value))
const asksLowerNode = computed(() => asksRepresentative.value || asksBusinessPerson.value)
const lowerNodeLabel = computed(() => (asksBusinessPerson.value ? '业务代表' : '代表处'))
const reportConfig = computed(() => (
  props.dataset?.report_config
  || datasetList.value.find(item => item?.report_config)?.report_config
  || {}
))
const riskThreshold = computed(() => Number(reportConfig.value?.officeRiskThreshold || reportConfig.value?.riskThreshold || 10))
const reportDebug = computed(() => (
  props.dataset?.report_debug
  || props.dataset?.report_spec?.debug
  || datasetList.value.find(item => item?.report_debug)?.report_debug
  || {}
))

const reportDebugItems = computed(() => {
  const scene = reportDebug.value?.scene || reportDebug.value?.debug?.scene || {}
  const contract = reportDebug.value?.contract || reportDebug.value?.debug?.contract || {}
  const layout = reportDebug.value?.layoutTemplate || props.dataset?.report_spec?.layoutTemplate || ''
  const items = []
  if (scene?.label || scene?.key) {
    items.push({ label: '场景', value: scene.label || scene.key, tone: 'info' })
  }
  if (layout) {
    items.push({ label: '界面', value: layout, tone: 'neutral' })
  }
  if (reportDebug.value?.report_config_source) {
    items.push({
      label: '报告契约',
      value: reportDebug.value.report_config_source === 'dataset_config' ? '数据集配置' : '默认配置',
      tone: reportDebug.value.report_config_source === 'dataset_config' ? 'success' : 'warning',
    })
  }
  if (Number.isFinite(Number(contract?.score))) {
    items.push({
      label: '契约健康',
      value: `${contract.score}/100`,
      tone: contract.level === 'healthy' ? 'success' : contract.level === 'danger' ? 'danger' : 'warning',
    })
  }
  if (Array.isArray(contract?.missing) && contract.missing.length) {
    items.push({ label: '缺失', value: contract.missing.slice(0, 3).join('、'), tone: 'danger' })
  }
  return items
})

const reportSpec = computed(() => props.dataset?.report_spec || datasetList.value.find(item => item?.report_spec)?.report_spec || {})
const queryIntent = computed(() => {
  const intent = reportSpec.value?.debug?.query_intent
  return intent && typeof intent === 'object' ? intent : {}
})

const rankingMetricMeta = computed(() => {
  const key = cleanText(queryIntent.value?.sort_metric_key).toLowerCase()
  const column = cleanText(queryIntent.value?.sort_metric_column)
  const text = `${questionText.value} ${column}`
  if (key === 'actual' || /年度开单|开单金额|开单|完成金额|实际|销售/.test(text)) {
    return { key: 'actual', label: column || '年度开单金额' }
  }
  if (key === 'task' || /任务|目标/.test(text)) {
    return { key: 'task', label: column || '任务金额' }
  }
  if (key === 'remain' || /剩余|缺口|差额|待完成/.test(text)) {
    return { key: 'remain', label: column || '剩余任务金额' }
  }
  return { key: 'rate', label: column || '达成率' }
})

const rankingMetricValue = (row) => {
  if (!row) return null
  const key = rankingMetricMeta.value.key
  const value = key === 'actual' ? row.actual : key === 'task' ? row.task : key === 'remain' ? row.remain : row.rate
  return value === null || value === undefined || Number.isNaN(Number(value)) ? null : Number(value)
}

const rankingMetricText = (row) => {
  if (!row) return ''
  const key = rankingMetricMeta.value.key
  return key === 'actual' ? row.actualText : key === 'task' ? row.taskText : key === 'remain' ? row.remainText : row.rateText
}

const rankingMetricPhrase = (row) => {
  const value = rankingMetricText(row)
  return value ? `${rankingMetricMeta.value.label}${value}` : rankingMetricMeta.value.label
}

const metricTone = (label, value) => {
  const text = `${label || ''} ${value || ''}`
  const numeric = toNumber(value)
  if (/达成率|完成率|rate|percent/i.test(text)) {
    if (numeric === null) return 'neutral'
    if (numeric >= 15) return 'good'
    if (numeric >= riskThreshold.value) return 'warn'
    return 'danger'
  }
  if (/剩余|缺口|风险/.test(text)) return 'danger'
  return 'neutral'
}

const metricHint = (label) => {
  if (/总任务|任务金额|目标/i.test(label)) return '年度目标总量'
  if (/年度开单|开单金额|开单|完成|实际|销售/i.test(label)) return '当前已完成金额'
  if (/达成率|完成率|rate|percent/i.test(label)) return '整体推进进度'
  if (/剩余|缺口|差额|remain/i.test(label)) return '后续需推进缺口'
  return ''
}

const normalizeMetricCard = (item, index) => {
  const label = cleanText(item?.label || item?.name || item?.key || `指标${index + 1}`)
  const value = cleanText(item?.displayValue ?? item?.value ?? '')
  if (!label || !value) return null
  return {
    key: cleanText(item?.key || `${label}-${index}`),
    label,
    value,
    hint: cleanText(item?.hint || metricHint(label)),
    tone: item?.tone || metricTone(label, value),
  }
}

const resolveFocusRow = (items = []) => {
  const focusName = cleanText(reportSpec.value?.scope?.focusNode || '')
  if (focusName) {
    return items.find(item => item.name === focusName)
      || items.find(item => item.name && (item.name.includes(focusName) || focusName.includes(item.name)))
      || null
  }
  const question = questionLabel.value
  return items.find(item => item.name && question.includes(item.name) && !/业务代表|业务员/.test(item.level))
    || items.find(item => item.name && !item.parent)
    || null
}

const resolveFocusDrillRows = (items = []) => {
  const focusRow = resolveFocusRow(items)
  const focusName = cleanText(reportSpec.value?.scope?.focusNode || focusRow?.name || '')
  const withRate = (source) => source.filter(item => item.name !== focusName && item.rate !== null)
  if (!focusName) return withRate(items)
  const directChildren = withRate(items.filter(item => item.parent === focusName))
  if (directChildren.length) return directChildren
  const nextLevelRows = withRate(items.filter(item => item.level && item.level !== focusRow?.level))
  return nextLevelRows.length ? nextLevelRows : withRate(items)
}

const primaryKpiCards = computed(() => {
  const kpis = Array.isArray(reportSpec.value?.kpis) ? reportSpec.value.kpis : []
  const normalized = kpis.map(normalizeMetricCard).filter(Boolean)
  if (normalized.length) {
    if (isComparisonDigest.value && normalized.length > 4) {
      const rateCards = normalized.filter(item => /达成率|完成率|rate|percent/i.test(item.label))
      const summaryCards = normalized.filter(item => /^累计|整体|数量|最高|最低|首尾/.test(item.label))
      return [...summaryCards, ...rateCards].filter((item, index, list) => (
        list.findIndex(card => card.key === item.key) === index
      )).slice(0, 6)
    }
    return normalized.slice(0, isComparisonDigest.value ? 6 : 4)
  }

  const focusRow = resolveFocusRow(normalizedRows.value)
  const source = isComparisonDigest.value ? comparisonDigestRows.value : [focusRow || sortedByRateDesc.value[0]].filter(Boolean)
  const first = source[0]
  if (!first) return []
  return [
    first.taskText ? { key: 'task', label: '总任务金额', value: first.taskText, hint: '年度目标总量', tone: 'neutral' } : null,
    first.actualText ? { key: 'actual', label: '年度开单金额', value: first.actualText, hint: '当前已完成金额', tone: 'neutral' } : null,
    first.rateText ? { key: 'rate', label: '达成率', value: first.rateText, hint: '整体推进进度', tone: metricTone('达成率', first.rateText) } : null,
    first.remainText ? { key: 'remain', label: '剩余任务金额', value: first.remainText, hint: '后续需推进缺口', tone: 'danger' } : null,
  ].filter(Boolean)
})

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

const managementLayerRows = computed(() => {
  if (specDigestRows.value.length >= 2) return specDigestRows.value
  const focus = resolveFocusRow(normalizedRows.value)
  const focusName = cleanText(reportSpec.value?.scope?.focusNode || focus?.name || '')
  if (focusName) {
    const direct = normalizedRows.value.filter(item => item.parent === focusName && item.rate !== null)
    if (direct.length >= 2) return direct
  }
  if (digestCompareLevel.value) {
    const scoped = normalizedRows.value.filter(item => rowMatchesLevel(item, digestCompareLevel.value) && item.rate !== null)
    if (scoped.length >= 2) return scoped
  }
  const levelOrder = ['分公司', '业务部', '代表处', '城市公司']
  for (const level of levelOrder) {
    const byLevel = normalizedRows.value.filter(item => item.level === level && item.rate !== null)
    if (byLevel.length >= 2) return byLevel
  }
  const parentNames = new Set(normalizedRows.value.map(item => item.parent).filter(Boolean))
  const withChildren = normalizedRows.value.filter(item => parentNames.has(item.name) && item.rate !== null)
  return withChildren.length >= 2 ? withChildren : normalizedRows.value.filter(item => item.rate !== null)
})

const topManagementRows = computed(() => (
  [...managementLayerRows.value]
    .sort((a, b) => (b.rate ?? -Infinity) - (a.rate ?? -Infinity))
    .slice(0, requestedRankLimit.value || 3)
))

const bottomManagementRows = computed(() => (
  [...managementLayerRows.value]
    .sort((a, b) => (a.rate ?? Infinity) - (b.rate ?? Infinity))
    .slice(0, requestedRankLimit.value || 3)
))

const rateDistribution = computed(() => {
  const source = managementLayerRows.value.filter(item => item.rate !== null)
  const total = source.length || 0
  const buckets = [
    { label: '20%以下', min: -Infinity, max: 20, count: 0 },
    { label: '20%-40%', min: 20, max: 40, count: 0 },
    { label: '40%以上', min: 40, max: Infinity, count: 0 },
  ]
  source.forEach((item) => {
    const bucket = buckets.find(part => item.rate < part.max && item.rate >= part.min)
    if (bucket) bucket.count += 1
  })
  return buckets.map(item => ({
    ...item,
    pct: total ? `${Math.round(item.count / total * 100)}%` : '0%',
  }))
})

const formatRankRows = (items = []) => (
  items
    .filter(Boolean)
    .map(item => `${item.path || item.name}${item.rateText ? ` ${item.rateText}` : ''}${item.remainText ? `，缺口${item.remainText}` : ''}`)
    .join('；')
)

const sectionNoText = (value) => ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九'][value] || String(value)

const adviceStartIndex = computed(() => 4 + (secondaryDrillRows.value.length ? 1 : 0))
const supportSectionLabel = computed(() => `${sectionNoText(adviceStartIndex.value)}、重点发现`)
const actionSectionLabel = computed(() => {
  const index = adviceStartIndex.value + (supportLines.value.length ? 1 : 0)
  return `${sectionNoText(index)}、建议动作`
})

const rateGapText = computed(() => {
  const best = topManagementRows.value[0]
  const worst = bottomManagementRows.value[0]
  if (!best || !worst || best.rate === null || worst.rate === null || best.name === worst.name) return ''
  return `${Math.abs(best.rate - worst.rate).toFixed(2).replace(/\.?0+$/, '')}pct`
})

const progressDistributionText = computed(() => (
  rateDistribution.value.map(item => `${item.label}${item.count}个(${item.pct})`).join('、')
))

const levelSummary = computed(() => {
  const counts = new Map()
  normalizedRows.value.forEach((item) => {
    const key = item.level || '明细'
    counts.set(key, (counts.get(key) || 0) + 1)
  })
  return Array.from(counts.entries()).map(([level, count]) => `${level}${count}个`).join('、')
})

const riskRows = computed(() => {
  const scopedRows = digestCompareLevel.value
    ? normalizedRows.value.filter(item => rowMatchesLevel(item, digestCompareLevel.value))
    : normalizedRows.value
  return scopedRows.filter(item => item.rate !== null && item.rate < riskThreshold.value)
})

const bestRow = computed(() => {
  const source = isComparisonDigest.value
    ? comparisonDigestRows.value.filter(item => item.rate !== null)
    : resolveFocusDrillRows(normalizedRows.value)
  return [...source].sort((a, b) => b.rate - a.rate)[0] || null
})

const worstRow = computed(() => {
  const source = isComparisonDigest.value
    ? comparisonDigestRows.value.filter(item => item.rate !== null)
    : resolveFocusDrillRows(normalizedRows.value)
  return [...source].sort((a, b) => a.rate - b.rate)[0] || null
})

const insightCards = computed(() => {
  const cards = []
  const compareCount = comparisonDigestRows.value.length
  const totalRows = rowCount.value || normalizedRows.value.length
  if (compareCount >= 2) {
    cards.push({
      label: '对比对象',
      value: `${compareCount} 个${comparisonLevelLabel.value}`,
      desc: compareCount > 4 ? '首屏聚焦最高、最低和整体差异' : '已纳入本轮横向对比',
      tone: 'info',
    })
  } else if (totalRows) {
    cards.push({
      label: '数据覆盖',
      value: `${totalRows} 行`,
      desc: levelSummary.value || '已返回可分析数据',
      tone: 'info',
    })
  }
  if (bestRow.value) {
    cards.push({
      label: '当前标杆',
      value: bestRow.value.name,
      desc: bestRow.value.rateText ? `达成率 ${bestRow.value.rateText}` : '表现相对靠前',
      tone: 'good',
    })
  }
  if (worstRow.value) {
    cards.push({
      label: '重点压力',
      value: worstRow.value.name,
      desc: worstRow.value.rateText ? `达成率 ${worstRow.value.rateText}` : '建议优先复核',
      tone: 'danger',
    })
  }
  cards.push({
    label: '风险节点',
    value: `${riskRows.value.length} 个`,
    desc: riskRows.value.length ? `低于 ${riskThreshold.value}% 风险线` : `暂无低于 ${riskThreshold.value}% 的节点`,
    tone: riskRows.value.length ? 'warn' : 'good',
  })
  return cards.slice(0, 4)
})

const resolvedMemberNames = computed(() => {
  const payloads = [
    props.dataset?.resolved_entities,
    ...datasetList.value.map(item => item?.resolved_entities),
    props.route?.resolved_entities,
  ].filter(Boolean)
  const names = []
  payloads.forEach((payload) => {
    ;(payload?.all_members || []).forEach((name) => {
      const value = cleanText(name)
      if (value && !names.includes(value)) names.push(value)
    })
    ;(payload?.entities || []).forEach((entity) => {
      ;(entity?.members || []).forEach((name) => {
        const value = cleanText(name)
        if (value && !names.includes(value)) names.push(value)
      })
    })
  })
  return names
})

const comparisonRows = computed(() => {
  if (!isComparisonQuestion.value && !isPeerLevelQuestion.value) return []
  if (specDigestRows.value.length >= 2) return specDigestRows.value
  const resolvedSet = new Set(resolvedMemberNames.value)
  const targetLevel = resolvedMemberNames.value.length
    ? normalizedRows.value.find(item => resolvedSet.has(item.name))?.level
    : digestCompareLevel.value
  const officeRows = normalizedRows.value.filter((item) => {
    if (targetLevel) return item.level === targetLevel
    return /分公司|业务部|代表处/.test(item.level) || /分公司|业务部|代表处/.test(item.name)
  })
  if (!officeRows.length) return []
  if (resolvedMemberNames.value.length >= 2) {
    const resolved = officeRows
      .filter(item => resolvedMemberNames.value.includes(item.name))
      .sort((left, right) => resolvedMemberNames.value.indexOf(left.name) - resolvedMemberNames.value.indexOf(right.name))
    if (resolved.length >= 2) return resolved
  }
  const explicit = officeRows
    .filter(item => questionText.value.includes(item.name))
    .sort((left, right) => comparisonMentionIndex(left.name) - comparisonMentionIndex(right.name))
  if (explicit.length >= 2) return explicit
  return officeRows.length >= 2 ? officeRows.slice(0, 4) : []
})

const comparisonMentionIndex = (name) => {
  const resolvedIndex = resolvedMemberNames.value.indexOf(name)
  if (resolvedIndex >= 0) return resolvedIndex
  const exact = questionText.value.indexOf(name)
  if (exact >= 0) return exact
  return 9999
}

const comparisonMetricLine = (row) => {
  const parts = [
    row.actualText ? `开单${row.actualText}` : '',
    row.taskText ? `任务${row.taskText}` : '',
    row.rateText ? `达成率${row.rateText}` : '',
    row.remainText ? `剩余缺口${row.remainText}` : '',
  ].filter(Boolean)
  return `${row.name}：${parts.join(' / ') || '暂无关键指标'}`
}

const parseMetricText = (text, patterns) => {
  const source = String(text || '')
  for (const pattern of patterns) {
    const match = source.match(pattern)
    if (match?.[1]) return cleanText(match[1])
  }
  return ''
}

const parsedComparisonRows = computed(() => {
  const source = `${props.report || ''}\n${props.title || ''}`
  if (!source || !/开单|任务|达成率|剩余缺口|差异/.test(source)) return []
  const matches = [...source.matchAll(/([^；。\n:：]{2,24}分公司)[:：]([^；。\n]+)/g)]
  const rows = []
  matches.forEach((match) => {
    const name = cleanText(match[1])
    const body = cleanText(match[2])
    if (!name || rows.some(item => item.name === name)) return
    const actualText = parseMetricText(body, [/开单\s*([0-9.]+(?:万|亿)?)/])
    const taskText = parseMetricText(body, [/任务\s*([0-9.]+(?:万|亿)?)/])
    const rateTextValue = parseMetricText(body, [/达成率\s*([0-9.]+%?)/])
    const remainText = parseMetricText(body, [/剩余缺口\s*([0-9.]+(?:万|亿)?)/])
    if (!actualText && !taskText && !rateTextValue) return
    const normalizedRateText = rateTextValue && !rateTextValue.includes('%') ? `${rateTextValue}%` : rateTextValue
    rows.push({
      name,
      parent: '',
      level: '分公司',
      rate: toNumber(normalizedRateText),
      rateText: normalizedRateText,
      task: toNumber(taskText),
      actual: toNumber(actualText),
      remain: toNumber(remainText),
      taskText,
      actualText,
      remainText,
    })
  })
  return rows.slice(0, 4)
})

const comparisonDigestRows = computed(() => (
  comparisonRows.value.length >= 2 ? comparisonRows.value : parsedComparisonRows.value
))

const isComparisonDigest = computed(() => comparisonDigestRows.value.length >= 2)

const comparisonParentNames = computed(() => {
  const names = []
  ;[
    ...comparisonDigestRows.value.map(item => item.name),
    ...resolvedMemberNames.value,
  ].forEach((name) => {
    const value = cleanText(name)
    if (value && !names.some(item => sameOrgName(item, value))) names.push(value)
  })
  return names
})

const rawRowText = (row) => Object.values(row?.raw || {})
  .map(value => cleanText(value))
  .filter(Boolean)
  .join(' ')

const rowMatchedParentName = (row, parentNames = []) => parentNames.find((parent) => {
  if (sameOrgName(row?.parent, parent)) return true
  const rawText = rawRowText(row)
  return rawText ? rawText.includes(parent) : false
}) || ''

const comparisonLevelLabel = computed(() => {
  const level = comparisonDigestRows.value.find(item => item.level)?.level || ''
  if (level) return level
  const name = comparisonDigestRows.value.find(item => item.name)?.name || ''
  if (name.includes('业务部')) return '业务部'
  if (name.includes('分公司')) return '分公司'
  if (name.includes('代表处')) return '代表处'
  return '对象'
})

const visibleComparisonDigestRows = computed(() => {
  const rows = comparisonDigestRows.value
  if (rows.length <= 4) return rows
  const ranked = rows.filter(item => item.rate !== null).sort((a, b) => b.rate - a.rate)
  const leader = ranked[0] || rows[0]
  const laggard = ranked[ranked.length - 1] || rows[rows.length - 1]
  return [leader, laggard].filter((item, index, list) => item && list.findIndex(row => row.name === item.name) === index)
})

const comparisonLeader = computed(() => {
  const rows = comparisonDigestRows.value.filter(item => item.rate !== null)
  if (rows.length) return [...rows].sort((a, b) => b.rate - a.rate)[0]
  return comparisonDigestRows.value[0] || null
})

const comparisonGapItems = computed(() => {
  const rows = comparisonDigestRows.value
  const ranked = rows.filter(item => item.rate !== null).sort((a, b) => b.rate - a.rate)
  const left = rows.length > 2 ? ranked[0] : rows[0]
  const right = rows.length > 2 ? ranked[ranked.length - 1] : rows[1]
  if (!left || !right) return []
  const items = []
  if (left.rate !== null && right.rate !== null) {
    const diff = Math.abs(left.rate - right.rate).toFixed(2).replace(/\.?0+$/, '')
    const winner = left.rate >= right.rate ? left.name : right.name
    const loser = left.rate >= right.rate ? right.name : left.name
    items.push({ label: rows.length > 2 ? '首尾达成率差' : '达成率差', value: `${winner} 比 ${loser} 高 ${diff}pct` })
  }
  if (left.actual !== null && right.actual !== null) {
    const diff = Math.abs(left.actual - right.actual)
    const winner = left.actual >= right.actual ? left.name : right.name
    const loser = left.actual >= right.actual ? right.name : left.name
    items.push({ label: rows.length > 2 ? '首尾开单差' : '开单差', value: `${winner} 比 ${loser} 多 ${amountText(diff)}` })
  }
  return items
})

const comparisonVerdict = computed(() => {
  const rows = comparisonDigestRows.value
  const ranked = rows.filter(item => item.rate !== null).sort((a, b) => b.rate - a.rate)
  const left = rows.length > 2 ? ranked[0] : rows[0]
  const right = rows.length > 2 ? ranked[ranked.length - 1] : rows[1]
  if (!left || !right) return directAnswer.value
  const leader = comparisonLeader.value
  if (!leader) return `${left.name} 与 ${right.name} 已完成对比，建议结合下钻明细判断差距来源。`
  const follower = leader.name === left.name ? right : left
  const rateDiff = left.rate !== null && right.rate !== null
    ? Math.abs(left.rate - right.rate).toFixed(2).replace(/\.?0+$/, '')
    : ''
  if (rows.length > 2) {
    return rateDiff
      ? `本次对比 ${rows.length} 个${comparisonLevelLabel.value}：${leader.name}达成率最高，${follower.name}最低，首尾相差 ${rateDiff} 个百分点。`
      : `本次对比 ${rows.length} 个${comparisonLevelLabel.value}，建议继续看下钻明细定位差距。`
  }
  return rateDiff
    ? `${leader.name}当前领先${follower.name}，达成率高 ${rateDiff} 个百分点。`
    : `${leader.name}当前表现更优，建议继续看下钻明细定位差距。`
})

const comparisonGapLine = computed(() => {
  const [left, right] = comparisonRows.value
  if (!left || !right) return ''
  const lines = []
  if (left.rate !== null && right.rate !== null) {
    const diff = Math.abs(left.rate - right.rate).toFixed(2).replace(/\.?0+$/, '')
    const winner = left.rate >= right.rate ? left.name : right.name
    const loser = left.rate >= right.rate ? right.name : left.name
    lines.push(`${winner}达成率比${loser}高${diff}个百分点`)
  }
  if (left.actual !== null && right.actual !== null) {
    const diff = Math.abs(left.actual - right.actual)
    const winner = left.actual >= right.actual ? left.name : right.name
    const loser = left.actual >= right.actual ? right.name : left.name
    lines.push(`${winner}开单金额比${loser}高${amountText(diff)}`)
  }
  return lines.length ? `差异：${lines.join('，')}。` : ''
})

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

const getPrimaryKpiText = (matcher) => (
  primaryKpiCards.value.find(item => matcher.test(item.label || ''))?.value || ''
)

const singleFocusRow = computed(() => resolveFocusRow(normalizedRows.value))

const singleFocusName = computed(() => (
  cleanText(reportSpec.value?.scope?.focusNode || '')
  || singleFocusRow.value?.name
  || resolvedMemberNames.value[0]
  || ''
))

const singleRateText = computed(() => (
  getPrimaryKpiText(/达成率|完成率|rate|percent/i) || singleFocusRow.value?.rateText || ''
))

const singleRateTone = computed(() => metricTone('达成率', singleRateText.value))

const focusDrillRows = computed(() => {
  const rows = resolveFocusDrillRows(normalizedRows.value)
  if (singleFocusName.value) return rows
  return rows.filter(item => item.name !== singleFocusRow.value?.name)
})

const comparisonDrillRows = computed(() => {
  if (comparisonDigestRows.value.length < 2) return []
  const parentNames = comparisonParentNames.value
  if (!parentNames.length) return []
  const detailLevel = expectedDetailLevel.value
  return normalizedRows.value
    .map((item) => {
      const matchedParent = rowMatchedParentName(item, parentNames)
      return matchedParent ? { ...item, parent: matchedParent } : item
    })
    .filter(item => (
      item.rate !== null &&
      item.parent &&
      parentNames.some(parent => sameOrgName(item.parent, parent)) &&
      !parentNames.some(parent => sameOrgName(item.name, parent)) &&
      (!detailLevel || rowMatchesLevel(item, detailLevel))
    ))
})

const expectedDetailLevel = computed(() => {
  const parentNames = comparisonParentNames.value
  if (parentNames.length) {
    const counts = new Map()
    normalizedRows.value.forEach((item) => {
      if (!item?.level || item.rate === null) return
      if (!parentNames.some(parent => sameOrgName(item.parent, parent))) return
      if (parentNames.some(parent => sameOrgName(item.name, parent))) return
      counts.set(item.level, (counts.get(item.level) || 0) + 1)
    })
    const [level] = Array.from(counts.entries()).sort((a, b) => b[1] - a[1])[0] || []
    if (level) return level
  }
  if (specDetailLevel.value && specDetailLevel.value !== digestCompareLevel.value) return specDetailLevel.value
  if (digestCompareLevel.value === '分公司') {
    return normalizedRows.value.some(item => item.level === '代表处') ? '代表处' : '城市公司'
  }
  if (digestCompareLevel.value === '业务部' || digestCompareLevel.value === '代表处') return '业务代表'
  return ''
})

const secondaryDrillAllRows = computed(() => {
  const isComparisonScope = comparisonDigestRows.value.length >= 2
  if (isComparisonScope && !comparisonDrillRows.value.length) return []
  const source = isComparisonScope
    ? comparisonDrillRows.value
    : (focusDrillRows.value.length ? focusDrillRows.value : managementLayerRows.value)
  const detailLevel = isComparisonScope ? expectedDetailLevel.value : ''
  const unique = []
  const seen = new Set()
  source.forEach((item) => {
    const key = `${item?.level || ''}|${item?.parent || ''}|${item?.name || ''}`
    if (!item?.name || item.name === singleFocusName.value || seen.has(key)) return
    if (detailLevel && !rowMatchesLevel(item, detailLevel)) return
    seen.add(key)
    unique.push(item)
  })
  const ranked = unique
    .filter(item => item.rate !== null)
    .sort((left, right) => (right.rate ?? -Infinity) - (left.rate ?? -Infinity))
  const fallback = unique.filter(item => item.rate === null)
  const rows = [...ranked, ...fallback]
  return rows
})

const secondaryDrillRows = computed(() => {
  const rows = secondaryDrillAllRows.value
  if (!isRankingQuestion.value) return rows
  const limit = requestedRankLimit.value || 3
  return [...rows]
    .sort((left, right) => (
      rankDirection.value === 'asc'
        ? (rankingMetricValue(left) ?? Infinity) - (rankingMetricValue(right) ?? Infinity)
        : (rankingMetricValue(right) ?? -Infinity) - (rankingMetricValue(left) ?? -Infinity)
    ))
    .slice(0, limit)
})

const drillSectionLabel = computed(() => (
  isRankingQuestion.value ? '四、排名结果' : '四、二级拆解'
))

const secondaryDrillGroups = computed(() => {
  const rows = secondaryDrillRows.value
  const parents = [...new Set(rows.map(item => item.parent).filter(Boolean))]
  const shouldGroup = comparisonParentNames.value.length >= 2 && parents.length >= 1
  if (!shouldGroup) return [{ key: 'all', title: '', rows }]

  const parentOrder = comparisonParentNames.value
  const orderedParents = [
    ...parentOrder.filter(name => parents.some(parent => sameOrgName(parent, name))),
    ...parents.filter(name => !parentOrder.some(parent => sameOrgName(parent, name))),
  ]

  return orderedParents
    .map((parent, index) => ({
      key: `group-${parent}`,
      title: parent,
      index,
      rows: rows.filter(item => sameOrgName(item.parent, parent)),
    }))
    .filter(group => group.rows.length)
})

const secondaryLevelLabel = computed(() => {
  if (expectedDetailLevel.value) return expectedDetailLevel.value
  const counts = new Map()
  secondaryDrillRows.value.forEach((item) => {
    if (item.level) counts.set(item.level, (counts.get(item.level) || 0) + 1)
  })
  const [level] = Array.from(counts.entries()).sort((a, b) => b[1] - a[1])[0] || []
  return level || '下级节点'
})

const isBusinessPersonRanking = computed(() => (
  isRankingQuestion.value && secondaryLevelLabel.value === '业务代表'
))

const drillNodeMeta = (row) => {
  const path = cleanText(row?.path)
  if (path) return path
  const level = cleanText(row?.level || secondaryLevelLabel.value)
  const parent = cleanText(row?.parent)
  if (parent && level === '业务代表') return `${level} · 上级：${parent}`
  if (parent && isBusinessPersonRanking.value) return `上级：${parent}`
  return level
}

const secondaryDrillSummary = computed(() => {
  const rows = secondaryDrillAllRows.value
  if (!rows.length) return ''
  if (isRankingQuestion.value) {
    const shown = secondaryDrillRows.value
    const directionText = rankDirection.value === 'asc' ? '最低' : '最高'
    return `按${rankingMetricMeta.value.label}取${directionText}${shown.length}个${secondaryLevelLabel.value}，完整明细见下表`
  }
  const ranked = rows.filter(item => item.rate !== null).sort((a, b) => b.rate - a.rate)
  const best = ranked[0]
  const worst = ranked[ranked.length - 1]
  const riskCount = rows.filter(item => item.rate !== null && item.rate < riskThreshold.value).length
  const displayText = secondaryDrillRows.value.length < rows.length ? `，当前展示${secondaryDrillRows.value.length}个` : ''
  const parts = [`覆盖${rows.length}个${secondaryLevelLabel.value}${displayText}`]
  if (best) parts.push(`最高${best.name} ${best.rateText}`)
  if (worst && worst.name !== best?.name) parts.push(`最低${worst.name} ${worst.rateText}`)
  if (riskCount) parts.push(`${riskCount}个低于${riskThreshold.value}%预警线`)
  return parts.join('，')
})

const secondaryBarWidth = (row) => {
  const value = row?.rate
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '0%'
  return `${Math.max(0, Math.min(100, Number(value)))}%`
}

const secondaryRelativeTier = (row) => {
  const rows = secondaryDrillAllRows.value
    .filter(item => item?.rate !== null && item?.rate !== undefined)
    .sort((left, right) => (right.rate ?? -Infinity) - (left.rate ?? -Infinity))
  const index = rows.findIndex(item => (
    item.name === row?.name &&
    item.parent === row?.parent &&
    item.level === row?.level
  ))
  if (index < 0) return null
  if (rows.length === 1) return 'single'
  if (rows.length === 2) return index === 0 ? 'leader' : 'pressure'

  const topCount = Math.max(1, Math.ceil(rows.length / 3))
  const pressureCount = Math.max(1, Math.floor(rows.length / 3))
  const pressureStart = rows.length - pressureCount
  if (index < topCount) return 'leader'
  if (index >= pressureStart) return 'pressure'
  return 'steady'
}

const secondaryRateTone = (row) => {
  const value = row?.rate
  if (value === null || value === undefined) return 'is-neutral'
  const tier = secondaryRelativeTier(row)
  if (tier === 'leader') return 'is-success'
  if (tier === 'pressure') return 'is-danger'
  if (tier === 'steady') return 'is-warn'
  if (value < riskThreshold.value) return 'is-danger'
  return 'is-warn'
}

const secondaryRateHint = (row) => {
  const value = row?.rate
  if (value === null || value === undefined) return '缺少口径'
  const tier = secondaryRelativeTier(row)
  if (tier === 'leader') return '相对领先'
  if (tier === 'steady') return '稳定推进'
  if (tier === 'pressure') return value < riskThreshold.value ? '重点风险' : '相对承压'
  if (value < riskThreshold.value) return '预警'
  return '需推进'
}

const focusDrillRank = computed(() => {
  const ranked = [...focusDrillRows.value].sort((a, b) => b.rate - a.rate)
  return {
    best: ranked[0] || null,
    worst: ranked[ranked.length - 1] || null,
  }
})

const singleOrgConclusion = computed(() => {
  if (isComparisonDigest.value) return ''
  const subject = singleFocusName.value || '当前主体'
  const task = getPrimaryKpiText(/总任务|任务金额|目标/i) || singleFocusRow.value?.taskText || ''
  const actual = getPrimaryKpiText(/年度开单|开单|完成|实际|销售/i) || singleFocusRow.value?.actualText || ''
  const rate = singleRateText.value
  const remain = getPrimaryKpiText(/剩余|缺口|差额|remain/i) || singleFocusRow.value?.remainText || ''
  if (!task && !actual && !rate && !remain) return ''
  const toneText = {
    good: '整体进度相对靠前',
    warn: '整体进度需要重点跟进',
    danger: '整体进度明显承压',
    neutral: '已形成整体业绩判断',
  }[singleRateTone.value] || '已形成整体业绩判断'
  const metrics = [
    task ? `年度总任务 ${task}` : '',
    actual ? `当前开单 ${actual}` : '',
    rate ? `整体达成率 ${rate}` : '',
    remain ? `剩余缺口 ${remain}` : '',
  ].filter(Boolean)
  const { best, worst } = focusDrillRank.value
  const drillLevel = best?.level || worst?.level || '下级节点'
  const drillText = best && worst && best.name !== worst.name
    ? `下级${drillLevel}中，${best.name}表现最好${best.rateText ? `（${best.rateText}）` : ''}，${worst.name}压力最大${worst.rateText ? `（${worst.rateText}）` : ''}。`
    : ''
  return `${subject}${toneText}，${metrics.join('，')}。${drillText}`
})

const directAnswer = computed(() => {
  if (comparisonRows.value.length >= 2) {
    const rows = comparisonRows.value
    const metrics = rows.length <= 4
      ? rows.map(comparisonMetricLine).join('；')
      : visibleComparisonDigestRows.value.map(comparisonMetricLine).join('；')
    const suffix = rows.length > 4 ? `完整 ${rows.length} 个对象请看右侧对比表。` : ''
    return `${metrics}。${comparisonGapLine.value}${suffix}`
  }
  if (asksLowerNode.value && asksLowest.value && groupedWorstLines.value.length) {
    return `已按上级组织拆开看，不能把所有${lowerNodeLabel.value}直接混在一起比。`
  }
  if (isRankingQuestion.value && secondaryDrillRows.value.length) {
    const directionText = rankDirection.value === 'asc' ? '最低' : '最高'
    const leader = secondaryDrillRows.value[0]
    const topNames = secondaryDrillRows.value
      .slice(0, Math.min(3, secondaryDrillRows.value.length))
      .map(item => item.name)
      .filter(Boolean)
      .join('、')
    const leaderMetrics = [
      rankingMetricText(leader) ? `${rankingMetricMeta.value.label}${rankingMetricText(leader)}` : '',
      rankingMetricMeta.value.key !== 'rate' && leader?.rateText ? `达成率${leader.rateText}` : '',
      leader?.remainText ? `缺口${leader.remainText}` : '',
    ].filter(Boolean).join('，')
    const riskHint = leader?.rate !== null && leader?.rate !== undefined && Number(leader.rate) < 60
      ? '，但达成率仍低于60%红线，需要把“相对领先”和“绝对进度风险”分开管理'
      : ''
    return `本轮${secondaryLevelLabel.value}${rankingMetricMeta.value.label}${directionText}${secondaryDrillRows.value.length}名已生成，前三为${topNames || leader?.name || '见下方明细'}；榜首${leader?.name || '当前对象'}${leaderMetrics ? `，${leaderMetrics}` : ''}${riskHint}。完整名单见排名结果。`
  }
  if (singleOrgConclusion.value) return singleOrgConclusion.value
  if (managementLayerRows.value.length >= 2) {
    const best = topManagementRows.value[0]
    const worst = bottomManagementRows.value[0]
    const focus = resolveFocusRow(normalizedRows.value)
    const focusMetrics = focus
      ? [
          focus.taskText ? `任务${focus.taskText}` : '',
          focus.actualText ? `完成${focus.actualText}` : '',
          focus.rateText ? `达成率${focus.rateText}` : '',
          focus.remainText ? `缺口${focus.remainText}` : '',
        ].filter(Boolean).join('，')
      : ''
    const gap = rateGapText.value ? `，头尾差${rateGapText.value}` : ''
    return `${focus?.name || '当前口径'}${focusMetrics ? `：${focusMetrics}` : '已形成经营判断'}。下级${managementLayerRows.value[0]?.level || '节点'}中，${best?.name || '标杆节点'}领先，${worst?.name || '压力节点'}承压${gap}；风险信号集中在低达成和剩余缺口节点。`
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
  if (comparisonDigestRows.value.length >= 2) {
    const detailRows = normalizedRows.value.filter(item => item.parent && comparisonDigestRows.value.some(row => row.name === item.parent))
    const sortedDetails = [...detailRows].filter(item => item.rate !== null).sort((a, b) => b.rate - a.rate)
    const best = sortedDetails[0]
    const worst = sortedDetails[sortedDetails.length - 1]
    const detailFindings = [
      best ? `下钻亮点：${best.parent}下${best.name}达成率${best.rateText}` : '',
      worst ? `重点压力：${worst.parent}下${worst.name}达成率${worst.rateText}` : '',
    ].filter(Boolean)
    if (detailFindings.length) return detailFindings

    const ranked = comparisonDigestRows.value
      .filter(item => item.rate !== null)
      .sort((a, b) => b.rate - a.rate)
    const leader = ranked[0] || comparisonDigestRows.value[0]
    const pressure = ranked[ranked.length - 1] || comparisonDigestRows.value[1]
    const taskRows = comparisonDigestRows.value.filter(item => item.task !== null).sort((a, b) => b.task - a.task)
    const remainRows = comparisonDigestRows.value.filter(item => item.remain !== null).sort((a, b) => b.remain - a.remain)
    const lines = []
    if (leader && pressure && leader.name !== pressure.name && leader.rate !== null && pressure.rate !== null) {
      const diff = Math.abs(leader.rate - pressure.rate).toFixed(2).replace(/\.?0+$/, '')
      lines.push(`达成率差距：${leader.name}${leader.rateText || ''}，${pressure.name}${pressure.rateText || ''}，相差${diff}个百分点。`)
    }
    if (taskRows.length >= 2) {
      lines.push(`任务体量：${taskRows[0].name}任务${taskRows[0].taskText || amountText(taskRows[0].task)}，${taskRows[taskRows.length - 1].name}任务${taskRows[taskRows.length - 1].taskText || amountText(taskRows[taskRows.length - 1].task)}。`)
    }
    if (remainRows.length >= 2) {
      lines.push(`缺口压力：${remainRows[0].name}缺口${remainRows[0].remainText || amountText(remainRows[0].remain)}，${remainRows[remainRows.length - 1].name}缺口${remainRows[remainRows.length - 1].remainText || amountText(remainRows[remainRows.length - 1].remain)}。`)
    }
    return lines.filter(Boolean)
  }
  if (isRankingQuestion.value && secondaryDrillRows.value.length) {
    const shown = secondaryDrillRows.value
    const leader = shown[0]
    const tail = shown[shown.length - 1]
    const leaderValue = rankingMetricValue(leader)
    const tailValue = rankingMetricValue(tail)
    const metricGap = leader && tail && leader.name !== tail.name && leaderValue !== null && tailValue !== null
      ? Math.abs(leaderValue - tailValue)
      : null
    const gapText = metricGap !== null
      ? (rankingMetricMeta.value.key === 'rate' ? `${metricGap.toFixed(2).replace(/\.?0+$/, '')}个百分点` : amountText(metricGap))
      : ''
    const riskCount = shown.filter(item => item.rate !== null && item.rate < riskThreshold.value).length
    return [
      leader ? `榜首判断：${leader.name}${rankingMetricText(leader) ? `的${rankingMetricPhrase(leader)}` : ''}${leader.rateText && rankingMetricMeta.value.key !== 'rate' ? `，达成率${leader.rateText}` : ''}，可作为本轮复盘样本。` : '',
      tail && leader && tail.name !== leader.name && gapText
        ? `榜内分化：第1名与第${shown.length}名相差${gapText}，说明头部${secondaryLevelLabel.value}之间仍需分层管理。`
        : '',
      riskCount
        ? `风险提醒：Top${shown.length}中仍有${riskCount}个低于${riskThreshold.value}%风险线，不能只看排名，还要看缺口消化。`
        : `风险提醒：Top${shown.length}暂无低于${riskThreshold.value}%风险线的节点，重点沉淀领先动作。`,
    ].filter(Boolean)
  }
  if (groupedWorstLines.value.length) return groupedWorstLines.value
  const worst = sortedByRateAsc.value[0]
  const second = sortedByRateAsc.value[1]
  if (worst && asksLowest.value) {
    return [
      second ? `次低是 ${second.name}${second.rateText ? `，达成率 ${second.rateText}` : ''}` : '',
      '右侧可查看完整明细、SQL 和报告。',
    ].filter(Boolean)
  }
  if (singleOrgConclusion.value) {
    const { best, worst: pressure } = focusDrillRank.value
    const drillLabel = best?.level || pressure?.level || '下级节点'
    return [
      levelSummary.value ? `覆盖范围：${levelSummary.value}` : '',
      best && pressure && best.name !== pressure.name
        ? `${drillLabel}分化：${best.name}达成率${best.rateText || '-'}，${pressure.name}达成率${pressure.rateText || '-'}。`
        : '',
      riskRows.value.length
        ? `风险提醒：低于${riskThreshold.value}%风险线的节点 ${riskRows.value.length} 个，建议优先下钻定位缺口来源。`
        : `风险提醒：暂无低于${riskThreshold.value}%风险线的明显节点。`,
    ].filter(Boolean)
  }
  if (managementLayerRows.value.length >= 2) {
    const topText = formatRankRows(topManagementRows.value)
    const bottomText = formatRankRows(bottomManagementRows.value)
    return [
      topText ? `分公司/关键节点Top3：${topText}。` : '',
      bottomText ? `末位/压力节点：${bottomText}。` : '',
      progressDistributionText.value ? `达成率分布：${progressDistributionText.value}，用于识别预警节点。` : '',
    ].filter(Boolean)
  }
  if (normalizedRows.value.length) {
    return [
      levelSummary.value ? `覆盖层级：${levelSummary.value}` : '',
      riskRows.value.length ? `低于${riskThreshold.value}%风险线的节点 ${riskRows.value.length} 个，建议先看右侧下钻明细。` : `暂无低于${riskThreshold.value}%风险线的明显风险节点。`,
    ].filter(Boolean)
  }
  return usefulReportLines.value.slice(1, 3)
})

const actionItems = computed(() => {
  const actions = []
  if (comparisonDigestRows.value.length >= 2) {
    const leader = comparisonLeader.value
    const pressure = worstRow.value
    if (leader) actions.push(`先复盘${leader.name}的高达成路径，提炼目标拆解、客户跟进和项目推进节奏。`)
    if (pressure) actions.push(`优先下钻${pressure.name}，定位低达成节点的项目缺口和责任人推进状态。`)
    actions.push(`保持同层级横向比较，再向下一层级展开，避免用业务员明细直接替代管理层级判断。`)
    return actions.slice(0, 3)
  }
  if (riskRows.value.length) {
    const names = riskRows.value.slice(0, 3).map(item => item.name).join('、')
    actions.push(`优先跟进${names}等低达成节点，形成周度缺口推进清单。`)
  }
  if (bestRow.value) {
    actions.push(`复盘${bestRow.value.name}的有效动作，形成目标拆解、项目推进和客户转化清单，并在两周内同步给同层级低达成节点。`)
  }
  if (worstRow.value && worstRow.value !== bestRow.value) {
    actions.push(`对${worstRow.value.name}做下一层下钻，由业务负责人和经营分析共同确认是任务体量、项目阶段滞后还是客户转化不足。`)
  }
  if (managementLayerRows.value.length >= 2) {
    actions.push(`按${managementLayerRows.value[0]?.level || '下级节点'}建立红黄绿看板，低于20%的节点周度复盘，20%-40%的节点专项推进。`)
  }
  if (!actions.length && usefulReportLines.value.length > 1) {
    actions.push(usefulReportLines.value[1])
  }
  return actions.slice(0, 3)
})
</script>

<style scoped>
.sa-boss-answer {
  width: 100%;
  padding: 15px 17px 16px;
  border-radius: 16px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.055);
}

.sa-boss-answer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(29, 33, 41, 0.06);
}

.sa-boss-answer-title-block {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sa-boss-answer-kicker-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  min-height: 22px;
}

.sa-boss-answer-kicker,
.sa-section-label {
  color: #165dff;
  font-size: 12px;
  line-height: 1.35;
  font-weight: 800;
}

.sa-report-flow-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border: 1px solid rgba(22, 93, 255, 0.16);
  border-radius: 999px;
  background: #f4f8ff;
  color: #165dff;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}

.sa-report-flow-badge.is-advanced {
  border-color: rgba(0, 180, 42, 0.2);
  background: #f3fff7;
  color: #178a3b;
}

.sa-report-flow-hint {
  color: #86909c;
  font-size: 11px;
  line-height: 1.4;
}

.sa-boss-answer-title {
  margin: 0;
  color: #1d2129;
  font-size: 16px;
  line-height: 1.45;
  font-weight: 800;
  word-break: break-word;
}

.sa-core-section,
.sa-report-mini-section {
  margin-top: 13px;
}

.sa-core-body {
  margin-top: 8px;
  padding: 12px 13px;
  border-radius: 12px;
  border: 1px solid rgba(22, 93, 255, 0.1);
  background: #f8fbff;
}

.sa-boss-answer-conclusion {
  margin: 0;
  min-width: 0;
  font-size: 15px;
  line-height: 1.75;
  color: #1d2129;
  font-weight: 700;
}

.sa-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 9px;
}

.sa-kpi-grid.is-count-1 {
  grid-template-columns: minmax(0, 1fr);
}

.sa-kpi-grid.is-count-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.sa-kpi-grid.is-count-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.sa-kpi-card {
  min-width: 0;
  padding: 12px 10px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 5px 14px rgba(15, 23, 42, 0.035);
}

.sa-kpi-value {
  color: #165dff;
  font-size: 24px;
  line-height: 1.2;
  font-weight: 800;
}

.sa-kpi-label {
  margin-top: 5px;
  color: #1d2129;
  font-weight: 700;
  font-size: 12px;
  line-height: 1.35;
}

.sa-kpi-hint {
  margin-top: 2px;
  color: #86909c;
  font-size: 11px;
  line-height: 1.4;
}

.sa-kpi-card.is-good .sa-kpi-value {
  color: #00a870;
}

.sa-kpi-card.is-warn .sa-kpi-value {
  color: #ff7d00;
}

.sa-kpi-card.is-danger .sa-kpi-value {
  color: #f53f3f;
}

.sa-insight-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 9px;
  margin-top: 9px;
}

.sa-insight-card {
  min-width: 0;
  padding: 10px 10px;
  border-radius: 10px;
  border: 1px solid rgba(29, 33, 41, 0.07);
  background: #f7f9fc;
}

.sa-insight-card span,
.sa-insight-card small {
  display: block;
  color: #86909c;
  font-size: 11px;
  line-height: 1.35;
}

.sa-insight-card strong {
  display: block;
  margin: 4px 0 3px;
  color: #1d2129;
  font-size: 14px;
  line-height: 1.35;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.sa-insight-card.is-good {
  background: #f2fff7;
  border-color: rgba(0, 180, 42, 0.16);
}

.sa-insight-card.is-warn {
  background: #fffaf2;
  border-color: rgba(255, 125, 0, 0.18);
}

.sa-insight-card.is-danger {
  background: #fff7f7;
  border-color: rgba(245, 63, 63, 0.16);
}

.sa-insight-card.is-info {
  background: #f5f8ff;
  border-color: rgba(22, 93, 255, 0.12);
}

.sa-section-title-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 9px;
}

.sa-section-title-line > span {
  min-width: 0;
  color: #86909c;
  font-size: 12px;
  line-height: 1.4;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-drill-section {
  padding: 11px 12px 12px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  border-radius: 14px;
  background: #fbfdff;
}

.sa-drill-table {
  overflow: hidden;
  border: 1px solid rgba(29, 33, 41, 0.07);
  border-radius: 12px;
  background: #fff;
}

.sa-drill-row {
  display: grid;
  grid-template-columns: minmax(116px, 1.15fr) minmax(112px, 1fr) minmax(74px, 0.72fr) minmax(150px, 1.28fr);
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-top: 1px solid rgba(29, 33, 41, 0.06);
}

.sa-drill-table.is-person-ranking .sa-drill-row {
  grid-template-columns: minmax(220px, 1.55fr) minmax(120px, 0.9fr) minmax(90px, 0.62fr) minmax(170px, 1.15fr);
}

.sa-drill-row:first-child {
  border-top: 0;
}

.sa-drill-row.is-head {
  padding: 8px 12px;
  background: #f7f9fc;
  color: #86909c;
  font-size: 12px;
  font-weight: 700;
}

.sa-drill-group-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 12px;
  border-top: 1px solid rgba(22, 93, 255, 0.08);
  border-left: 3px solid #165dff;
  background: linear-gradient(90deg, rgba(22, 93, 255, 0.08), rgba(22, 93, 255, 0.02));
}

.sa-drill-group-row.is-group-2 {
  border-left-color: #ff7d00;
  background: linear-gradient(90deg, rgba(255, 125, 0, 0.1), rgba(255, 125, 0, 0.025));
}

.sa-drill-group-row.is-group-2 span {
  color: #d46b08;
}

.sa-drill-group-row.is-group-3 {
  border-left-color: #00a870;
  background: linear-gradient(90deg, rgba(0, 168, 112, 0.1), rgba(0, 168, 112, 0.025));
}

.sa-drill-group-row.is-group-3 span {
  color: #008f62;
}

.sa-drill-group-row.is-group-4 {
  border-left-color: #722ed1;
  background: linear-gradient(90deg, rgba(114, 46, 209, 0.1), rgba(114, 46, 209, 0.025));
}

.sa-drill-group-row.is-group-4 span {
  color: #6d3cc7;
}

.sa-drill-group-row span {
  min-width: 0;
  color: #165dff;
  font-size: 13px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-drill-group-row small {
  flex: 0 0 auto;
  color: #4e5969;
  font-size: 12px;
  font-weight: 700;
}

.sa-drill-node,
.sa-drill-number,
.sa-drill-rate {
  min-width: 0;
}

.sa-drill-node {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sa-drill-node strong,
.sa-drill-number strong,
.sa-drill-rate-head strong {
  min-width: 0;
  color: #1d2129;
  font-size: 13px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-drill-node span,
.sa-drill-number span,
.sa-drill-rate-head span {
  color: #86909c;
  font-size: 12px;
  line-height: 1.35;
}

.sa-drill-number {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sa-drill-gap {
  color: #4e5969;
  font-size: 13px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-drill-rate {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sa-drill-rate-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sa-drill-bar {
  position: relative;
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(29, 33, 41, 0.08);
}

.sa-drill-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #165dff;
}

.sa-drill-rate.is-success .sa-drill-bar i {
  background: #00b42a;
}

.sa-drill-rate.is-success .sa-drill-rate-head strong,
.sa-drill-rate.is-success .sa-drill-rate-head span {
  color: #00a321;
}

.sa-drill-rate.is-warn .sa-drill-bar i {
  background: #ff7d00;
}

.sa-drill-rate.is-warn .sa-drill-rate-head strong,
.sa-drill-rate.is-warn .sa-drill-rate-head span {
  color: #d46b08;
}

.sa-drill-rate.is-danger .sa-drill-bar i {
  background: #f53f3f;
}

.sa-drill-rate.is-danger .sa-drill-rate-head strong,
.sa-drill-rate.is-danger .sa-drill-rate-head span {
  color: #d92d20;
}

.sa-drill-rate.is-neutral .sa-drill-bar i {
  background: #86909c;
}

.sa-drill-rate.is-neutral .sa-drill-rate-head strong,
.sa-drill-rate.is-neutral .sa-drill-rate-head span {
  color: #6b7280;
}

.sa-advice-section {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.sa-advice-section.is-single {
  grid-template-columns: minmax(0, 1fr);
}

.sa-advice-block {
  min-width: 0;
  padding: 11px 12px;
  border-radius: 12px;
  border: 1px solid rgba(22, 93, 255, 0.1);
  background: #ffffff;
}

.sa-advice-list {
  margin: 8px 0 0;
  padding-left: 20px;
  color: #1d2129;
  font-size: 13px;
  line-height: 1.75;
}

.sa-advice-list li + li {
  margin-top: 4px;
}

.sa-comparison-digest {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 7px;
}

.sa-comparison-verdict {
  color: #1d2129;
  font-size: 14px;
  line-height: 1.55;
  font-weight: 800;
}

.sa-comparison-card-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.sa-comparison-card-grid.is-count-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.sa-comparison-card-grid.is-count-4 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.sa-comparison-card {
  min-width: 0;
  padding: 8px 9px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 8px;
  background: #fbfcff;
}

.sa-comparison-card.is-leader {
  border-color: rgba(22, 93, 255, 0.22);
  background: #f7faff;
}

.sa-comparison-card-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 7px;
  color: #1d2129;
  font-size: 13px;
  font-weight: 800;
}

.sa-comparison-card-head span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
  line-height: 1.35;
}

.sa-comparison-card-head strong {
  flex-shrink: 0;
  color: #165dff;
  font-size: 15px;
  line-height: 1.25;
}

.sa-comparison-metrics,
.sa-comparison-gap-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 8px;
}

.sa-comparison-metrics {
  margin-top: 6px;
  color: #4e5969;
  font-size: 11px;
  line-height: 1.45;
}

.sa-comparison-metrics span {
  white-space: nowrap;
}

.sa-comparison-gap-list span {
  padding: 4px 8px;
  border-radius: 7px;
  background: #f7f9ff;
  border: 1px solid rgba(22, 93, 255, 0.12);
  color: #2f5fd7;
  font-size: 11px;
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

.sa-boss-answer-points.is-drill {
  padding: 7px 9px;
  border-radius: 8px;
  background: #f7f9fc;
  border: 1px solid rgba(29, 33, 41, 0.06);
}

.sa-boss-answer-points span:not(:last-child)::after {
  content: '·';
  margin-left: 12px;
  color: #c9cdd4;
}

.sa-report-debug-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}

.sa-report-debug-strip span {
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: #f7f8fa;
  color: #4e5969;
  font-size: 11px;
  line-height: 1.4;
}

.sa-report-debug-strip .is-success {
  border-color: rgba(0, 180, 42, 0.2);
  background: #f3fff7;
  color: #178a3b;
}

.sa-report-debug-strip .is-warning {
  border-color: rgba(255, 125, 0, 0.22);
  background: #fff8f0;
  color: #b45f00;
}

.sa-report-debug-strip .is-danger {
  border-color: rgba(245, 63, 63, 0.22);
  background: #fff5f5;
  color: #c73737;
}

.sa-report-debug-strip .is-info {
  border-color: rgba(22, 93, 255, 0.18);
  background: #f4f8ff;
  color: #245bd6;
}

@media (max-width: 760px) {
  .sa-boss-answer-head {
    flex-direction: column;
    align-items: stretch;
  }

  .sa-kpi-grid,
  .sa-kpi-grid.is-count-2,
  .sa-kpi-grid.is-count-3,
  .sa-insight-grid,
  .sa-advice-section {
    grid-template-columns: minmax(0, 1fr);
  }

  .sa-kpi-value {
    font-size: 22px;
  }

  .sa-comparison-card-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .sa-comparison-card-grid.is-count-3,
  .sa-comparison-card-grid.is-count-4 {
    grid-template-columns: minmax(0, 1fr);
  }

  .sa-section-title-line {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .sa-section-title-line > span {
    max-width: 100%;
    text-align: left;
    white-space: normal;
  }

  .sa-drill-row,
  .sa-drill-row.is-head {
    grid-template-columns: minmax(0, 1fr);
  }

  .sa-drill-row.is-head {
    display: none;
  }

  .sa-drill-group-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }
}

@media (min-width: 761px) and (max-width: 900px) {
  .sa-kpi-grid,
  .sa-insight-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .sa-comparison-card-grid.is-count-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .sa-comparison-card {
    padding: 8px;
  }

  .sa-comparison-card-head {
    grid-template-columns: minmax(0, 1fr);
    gap: 2px;
  }
}
</style>
