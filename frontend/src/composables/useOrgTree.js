/**
 * Build a report tree from SQL rows and dataset report_config.
 *
 * The tree is data-driven: SQL returns name / parent / level / metrics,
 * config only tells us which columns and level values are meaningful.
 */

import { computed, unref } from 'vue'

export const getDefaultConfig = () => ({
  nameColumn: '节点名称',
  parentColumn: '上级名称',
  trackColumn: '条线',
  levelColumn: '层级',
  metrics: [
    { key: 'task', label: '总任务金额', column: '总任务金额', format: 'amount' },
    { key: 'actual', label: '年度开单金额', column: '年度开单金额', format: 'amount' },
    { key: 'rate', label: '达成率', column: '达成率', format: 'percent' },
    { key: 'remain', label: '剩余任务金额', column: '剩余任务金额', format: 'amount' },
  ],
  levels: [
    { name: '机构层', values: ['代表处', '分公司', '业务部'] },
    { name: '个人层', values: ['业务代表', '业务员', '业务'] },
  ],
  riskThreshold: 80,
  signalRules: [
    { key: 'rate', op: '>=', value: 100, tone: 'good', label: '绿灯' },
    { key: 'rate', op: '>=', value: 80, tone: 'warn', label: '黄灯' },
    { key: 'rate', op: '<', value: 80, tone: 'danger', label: '红灯' },
  ],
  sections: ['core', 'group', 'risk', 'strategy'],
  reportTitle: '经营分析报告',
})

export const normalizeConfig = (config = {}) => ({
  ...getDefaultConfig(),
  ...(config || {}),
  metrics: Array.isArray(config?.metrics) && config.metrics.length ? config.metrics : getDefaultConfig().metrics,
  levels: Array.isArray(config?.levels) && config.levels.length ? config.levels : getDefaultConfig().levels,
  signalRules: Array.isArray(config?.signalRules) && config.signalRules.length ? config.signalRules : getDefaultConfig().signalRules,
})

export const getColumnNames = (config = {}) => {
  const cfg = normalizeConfig(config)
  const metric = (key, fallback) => cfg.metrics.find(item => item.key === key)?.column || fallback
  return {
    NAME_COL: cfg.nameColumn || '节点名称',
    PARENT_COL: cfg.parentColumn || '上级名称',
    TRACK_COL: cfg.trackColumn || '条线',
    LEVEL_COL: cfg.levelColumn || '层级',
    TASK_COL: metric('task', '总任务金额'),
    ACTUAL_COL: metric('actual', '年度开单金额'),
    RATE_COL: metric('rate', '达成率'),
    REMAIN_COL: metric('remain', '剩余任务金额'),
  }
}

export const toNumber = (value) => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  const cleaned = String(value ?? '').replace(/[^0-9.-]/g, '')
  if (!cleaned) return null
  const numeric = Number(cleaned)
  return Number.isFinite(numeric) ? numeric : null
}

const uniqueBy = (items, keyFn) => {
  const seen = new Set()
  return items.filter((item) => {
    const key = keyFn(item)
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const inferConfiguredLevel = (row, config, levelColumn) => {
  const levelValue = String(row?.[levelColumn] ?? '').trim()
  const matched = (config.levels || []).find(level => (level.values || []).includes(levelValue))
  return {
    levelName: matched?.name || levelValue || '未分层',
    levelValue,
  }
}

export const aggregateMetrics = (nodes = [], config = {}) => {
  const cfg = normalizeConfig(config)
  const metrics = {}
  const rows = nodes.flatMap(node => Array.isArray(node.rows) ? node.rows : [node.raw || node]).filter(Boolean)

  cfg.metrics.forEach((metric) => {
    const values = rows.map(row => toNumber(row?.[metric.column])).filter(value => value !== null)
    if (!values.length) {
      metrics[metric.key] = null
      return
    }
    if (metric.key === 'rate' || metric.format === 'percent') {
      const taskMetric = cfg.metrics.find(item => item.key === 'task')
      const actualMetric = cfg.metrics.find(item => item.key === 'actual')
      const task = taskMetric ? rows.reduce((sum, row) => sum + (toNumber(row?.[taskMetric.column]) || 0), 0) : 0
      const actual = actualMetric ? rows.reduce((sum, row) => sum + (toNumber(row?.[actualMetric.column]) || 0), 0) : 0
      metrics[metric.key] = task > 0 ? Number((actual / task * 100).toFixed(2)) : Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2))
      return
    }
    metrics[metric.key] = values.reduce((sum, value) => sum + value, 0)
  })

  return metrics
}

export const getRiskNodes = (nodes = [], config = {}) => {
  const cfg = normalizeConfig(config)
  const rateKey = cfg.metrics.find(item => item.key === 'rate')?.key || cfg.metrics.find(item => item.format === 'percent')?.key || 'rate'
  const threshold = Number(cfg.riskThreshold ?? 80)
  return nodes.filter(node => {
    const rate = toNumber(node?.metrics?.[rateKey])
    return rate !== null && rate < threshold
  }).sort((a, b) => (toNumber(a.metrics?.[rateKey]) || 0) - (toNumber(b.metrics?.[rateKey]) || 0))
}

export const getTopNodes = (nodes = [], config = {}, topN = 5) => {
  const cfg = normalizeConfig(config)
  const rateKey = cfg.metrics.find(item => item.key === 'rate')?.key || cfg.metrics.find(item => item.format === 'percent')?.key || 'rate'
  return [...nodes]
    .filter(node => toNumber(node?.metrics?.[rateKey]) !== null)
    .sort((a, b) => (toNumber(b.metrics?.[rateKey]) || 0) - (toNumber(a.metrics?.[rateKey]) || 0))
    .slice(0, topN)
}

export const getGroupBlocks = (levelSection = {}) => {
  const groups = new Map()
  ;(levelSection.nodes || []).forEach((node) => {
    const key = node.parentName || '未归属'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(node)
  })
  return Array.from(groups.entries()).map(([parentName, nodes]) => ({
    parentName,
    nodes,
    metrics: aggregateMetrics(nodes, levelSection.config || {}),
    riskNodes: getRiskNodes(nodes, levelSection.config || {}),
    topNodes: getTopNodes(nodes, levelSection.config || {}, 3),
  }))
}

export const buildOrgTree = (inputRows = [], inputConfig = {}) => {
  const rows = Array.isArray(inputRows) ? inputRows : []
  const config = normalizeConfig(inputConfig)
  const columns = getColumnNames(config)
  const nodeKey = (row) => [row?.[columns.NAME_COL], row?.[columns.LEVEL_COL], row?.[columns.PARENT_COL]].map(item => String(item ?? '').trim()).join('::')
  const uniqueRows = uniqueBy(rows, nodeKey)
  const rowByName = new Map()
  const nodes = uniqueRows.map((row) => {
    const { levelName, levelValue } = inferConfiguredLevel(row, config, columns.LEVEL_COL)
    const node = {
      id: nodeKey(row),
      name: String(row?.[columns.NAME_COL] ?? '').trim(),
      parentName: String(row?.[columns.PARENT_COL] ?? '').trim(),
      levelName,
      levelValue,
      trackName: String(row?.[columns.TRACK_COL] ?? '').trim(),
      depth: 0,
      children: [],
      metrics: {},
      raw: row,
      rows: [row],
    }
    config.metrics.forEach((metric) => {
      node.metrics[metric.key] = toNumber(row?.[metric.column])
    })
    if (node.name) rowByName.set(node.name, node)
    return node
  }).filter(node => node.name)

  nodes.forEach((node) => {
    const parent = rowByName.get(node.parentName)
    if (parent && parent !== node) parent.children.push(node)
  })

  const roots = nodes.filter(node => !node.parentName || !rowByName.has(node.parentName))
  const visited = new Set()
  const walk = (node, depth) => {
    if (visited.has(node.id)) return
    visited.add(node.id)
    node.depth = depth
    node.children.forEach(child => walk(child, depth + 1))
  }
  roots.forEach(root => walk(root, 0))
  nodes.filter(node => !visited.has(node.id)).forEach(node => walk(node, 0))

  const depthOrder = Array.from(new Set(nodes.map(node => node.depth))).sort((a, b) => a - b)
  const levelSections = depthOrder
    .map((depth, index) => {
      const sectionNodes = nodes.filter(node => node.depth === depth)
      if (!sectionNodes.length) return null
      const levelValues = Array.from(new Set(sectionNodes.map(node => node.levelValue).filter(Boolean)))
      const semanticNames = Array.from(new Set(sectionNodes.map(node => node.levelName).filter(Boolean)))
      const displayName = levelValues.join(' / ') || semanticNames.join(' / ') || `第 ${index + 1} 层`
      const section = {
        depth: index + 1,
        treeDepth: depth,
        levelName: displayName,
        semanticLevelNames: semanticNames,
        levelValues,
        trackNames: Array.from(new Set(sectionNodes.map(node => node.trackName).filter(Boolean))),
        nodes: sectionNodes,
        config,
      }
      section.groupBlocks = getGroupBlocks(section)
      section.metrics = aggregateMetrics(sectionNodes, config)
      section.riskNodes = getRiskNodes(sectionNodes, config)
      section.topNodes = getTopNodes(sectionNodes, config)
      return section
    })
    .filter(Boolean)

  return {
    tree: roots,
    flatNodes: nodes,
    levelSections,
    rootMetrics: aggregateMetrics(levelSections[0]?.nodes || nodes, config),
    columns,
    config,
  }
}

const evaluateRule = (value, rule) => {
  const num = toNumber(value)
  if (num === null) return false
  if (rule.op === '>=') return num >= rule.value
  if (rule.op === '<=') return num <= rule.value
  if (rule.op === '>') return num > rule.value
  if (rule.op === '<') return num < rule.value
  if (rule.op === '==') return num === rule.value
  return false
}

export function useOrgTree(rows, config) {
  const model = computed(() => buildOrgTree(unref(rows), unref(config)))
  const getSignal = (node) => {
    const cfg = normalizeConfig(unref(config))
    for (const rule of cfg.signalRules || []) {
      if (evaluateRule(node?.metrics?.[rule.key], rule)) return { tone: rule.tone, label: rule.label }
    }
    return { tone: 'neutral', label: '' }
  }

  return {
    tree: computed(() => model.value.tree),
    flatNodes: computed(() => model.value.flatNodes),
    levelSections: computed(() => model.value.levelSections),
    rootMetrics: computed(() => model.value.rootMetrics),
    getSignal,
    getColumnNames: () => getColumnNames(unref(config)),
    getGroupBlocks,
    getRiskNodes: (nodes, thresholdConfig) => getRiskNodes(nodes, thresholdConfig || unref(config)),
    getTopNodes: (nodes, topN) => getTopNodes(nodes, unref(config), topN),
    aggregateMetrics: (nodes) => aggregateMetrics(nodes, unref(config)),
  }
}
