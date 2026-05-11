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
          <span v-else class="sa-boss-answer-conclusion">{{ directAnswer }}</span>
        </div>
      </div>

      <button class="sa-boss-answer-link" @click="$emit('viewDetails')">查看详情</button>
    </div>

    <div v-if="supportLines.length" class="sa-boss-answer-points" :class="{ 'is-drill': isComparisonDigest }">
      <span v-for="(line, index) in supportLines.slice(0, 2)" :key="index">{{ line }}</span>
    </div>

    <div v-if="reportDebugItems.length" class="sa-report-debug-strip">
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

const amountText = (value) => {
  const numeric = toNumber(value)
  if (numeric === null) return ''
  const abs = Math.abs(numeric)
  if (abs >= 100000000) return `${(numeric / 100000000).toFixed(2).replace(/\.?0+$/, '')}亿`
  if (abs >= 10000) return `${(numeric / 10000).toFixed(1).replace(/\.?0+$/, '')}万`
  return numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

const specDigestRows = computed(() => {
  const accordions = Array.isArray(props.dataset?.report_spec?.accordions)
    ? props.dataset.report_spec.accordions
    : []
  return accordions.map((item) => {
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
})

const normalizedRows = computed(() => rows.value.map((row) => {
  const rowKeys = Object.keys(row || {})
  const nameKey = findColumn(row, [/节点名称/, /^name$/i, /名称/, /分公司|代表处|业务代表/])
  const parentKey = findColumn(row, [/上级名称/, /parent/i, /分公司/])
  const levelKey = findColumn(row, [/层级/, /^level$/i])
  const rateKey = findColumn(row, [/达成率/, /completion.*rate/i, /\brate\b/i])
  const taskKey = rowKeys.find(key => /总任务|任务金额|任务|目标/i.test(key) && !/剩余|缺口|差额|remain/i.test(key)) || ''
  const actualKey = rowKeys.find(key => /年度开单|开单金额|开单|完成|实际|销售/i.test(key) && !/达成率|完成率|率/i.test(key)) || ''
  const remainKey = rowKeys.find(key => /剩余任务|剩余|缺口|差额|remain/i.test(key)) || ''
  return {
    name: cleanText(nameKey ? row[nameKey] : ''),
    parent: cleanText(parentKey ? row[parentKey] : ''),
    level: cleanText(levelKey ? row[levelKey] : ''),
    rate: toNumber(rateKey ? row[rateKey] : null),
    rateText: rateText(row),
    task: toNumber(taskKey ? row[taskKey] : null),
    actual: toNumber(actualKey ? row[actualKey] : null),
    remain: toNumber(remainKey ? row[remainKey] : null),
    taskText: amountText(taskKey ? row[taskKey] : null),
    actualText: amountText(actualKey ? row[actualKey] : null),
    remainText: amountText(remainKey ? row[remainKey] : null),
  }
}).filter(item => item.name))

const questionText = computed(() => cleanText(props.question || props.title))
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

const riskRows = computed(() => normalizedRows.value.filter(item => item.rate !== null && item.rate < riskThreshold.value))

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
  if (!isComparisonQuestion.value) return []
  if (specDigestRows.value.length >= 2) return specDigestRows.value
  const resolvedSet = new Set(resolvedMemberNames.value)
  const targetLevel = resolvedMemberNames.value.length
    ? normalizedRows.value.find(item => resolvedSet.has(item.name))?.level
    : ''
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
    return [
      best ? `下钻亮点：${best.parent}下${best.name}达成率${best.rateText}` : '',
      worst ? `重点压力：${worst.parent}下${worst.name}达成率${worst.rateText}` : '',
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
  if (normalizedRows.value.length) {
    return [
      levelSummary.value ? `覆盖层级：${levelSummary.value}` : '',
      riskRows.value.length ? `低于${riskThreshold.value}%风险线的节点 ${riskRows.value.length} 个，建议先看右侧下钻明细。` : `暂无低于${riskThreshold.value}%风险线的明显风险节点。`,
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
  flex: 1;
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
  .sa-boss-answer-mainline {
    flex-direction: column;
  }

  .sa-comparison-card-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .sa-comparison-card-grid.is-count-3,
  .sa-comparison-card-grid.is-count-4 {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (min-width: 761px) and (max-width: 900px) {
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
