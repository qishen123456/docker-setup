import { computed, reactive } from 'vue'
import { confirmByBoss, sendSmartChatStream } from '../api/index.js'

const STORAGE_KEY = 'smart-ask-session-v1'

const phaseTemplates = [
  {
    key: 'submit',
    title: '开始执行任务',
    summary: '已接收问题，准备启动本轮问数链路。',
    detailLines: ['已记录当前问题内容。', '任务上下文初始化完成。'],
    status: 'success',
    kind: 'system',
    toolType: 'default',
  },
  {
    key: 'intent',
    title: '理解问题口径',
    summary: '正在识别业务指标、时间范围和分析对象。',
    detailLines: ['解析业务关键词与统计范围。', '识别核心指标与分析维度。'],
    status: 'running',
    kind: 'system',
    toolType: 'default',
  },
  {
    key: 'context',
    title: '补充上下文信息',
    summary: '检索历史上下文与已知业务约束。',
    detailLines: ['读取历史对话上下文。', '补充已知业务约束与分析背景。'],
    status: 'pending',
    kind: 'system',
    toolType: 'default',
  },
  {
    key: 'schema',
    title: '选择数据表',
    summary: '正在匹配最合适的数据集和字段范围。',
    detailLines: ['匹配候选数据集。', '锁定字段与表范围。'],
    status: 'pending',
    kind: 'tool',
    toolType: 'dataset',
  },
  {
    key: 'plan',
    title: '生成执行计划',
    summary: '整理拆解步骤，准备进入查询执行。',
    detailLines: ['输出本轮执行计划。', '确认后续查询顺序。'],
    status: 'pending',
    kind: 'system',
    toolType: 'default',
  },
  {
    key: 'sql_gen',
    title: '生成 SQL',
    summary: '正在编写查询语句与聚合逻辑。',
    detailLines: ['生成查询语句草稿。', '补充聚合与筛选条件。'],
    status: 'pending',
    kind: 'tool',
    toolType: 'sql',
  },
  {
    key: 'sql_check',
    title: '校验 SQL',
    summary: '检查查询语义、性能与可执行性。',
    detailLines: ['检查查询语义。', '验证可执行性与性能风险。'],
    status: 'pending',
    kind: 'tool',
    toolType: 'sql',
  },
  {
    key: 'execute',
    title: '执行 SQL',
    summary: '查询任务已提交到数据仓库执行。',
    detailLines: ['提交 SQL 到数据仓库。', '等待查询执行返回结果。'],
    status: 'pending',
    kind: 'tool',
    toolType: 'sql',
  },
  {
    key: 'data_fetch',
    title: '整理结果数据',
    summary: '正在回传结果并生成预览内容。',
    detailLines: ['整理结果字段与行数据。', '生成表格或图表预览。'],
    status: 'pending',
    kind: 'tool',
    toolType: 'dataset',
  },
  {
    key: 'analyze',
    title: '等待报告生成',
    summary: '正在输出经营分析摘要与最终报告，请稍候。',
    detailLines: ['正在生成经营分析摘要。', '正在整理完整报告内容。'],
    status: 'pending',
    kind: 'report-stage',
    toolType: 'report',
  },
]

const normalizeStatus = (status) => {
  const value = String(status || '').toLowerCase()
  if (['success', 'completed', 'done'].includes(value)) return 'success'
  if (['running', 'processing', 'in_progress'].includes(value)) return 'running'
  if (['warning', 'waiting', 'wait', 'waiting_confirmation'].includes(value)) return 'warning'
  if (['error', 'failed', 'failure'].includes(value)) return 'error'
  return 'pending'
}

const uniqueLines = (lines) => Array.from(new Set((lines || []).map(item => String(item || '').trim()).filter(Boolean)))

const inferToolType = (entry) => {
  if (entry?.toolType) return entry.toolType
  const text = `${entry?.kind || ''} ${entry?.key || ''} ${entry?.title || ''}`
  if (/sql|查询|复核|校验/i.test(text)) return 'sql'
  if (/python|pandas/i.test(text)) return 'python'
  if (/确认|口径/i.test(text)) return 'confirm'
  if (/事实|计划/i.test(text)) return 'fact'
  if (/报告|分析|总结/i.test(text)) return 'report'
  if (/数据集|数据表|schema/i.test(text)) return 'dataset'
  return 'default'
}

const buildDetailLines = (entry) => {
  if (Array.isArray(entry?.detailLines) && entry.detailLines.length > 0) {
    return uniqueLines(entry.detailLines)
  }

  const lines = []
  if (entry?.summary) lines.push(entry.summary)
  if (entry?.thought) {
    lines.push(
      ...String(entry.thought)
        .split(/\n+/)
        .map(item => item.trim())
        .filter(Boolean)
    )
  }
  if (entry?.detail && entry.detail !== entry.summary) lines.push(entry.detail)

  const text = `${entry?.kind || ''} ${entry?.key || ''} ${entry?.title || ''}`
  if (/确认统计口径|boss-confirm/i.test(text)) {
    lines.push('当前任务需要先确认统计口径。')
  } else if (/执行异常|request-error/i.test(text)) {
    lines.push('当前节点发生异常，请检查错误信息。')
  } else if (/任务已停止|request-aborted/i.test(text)) {
    lines.push('当前任务已手动停止。')
  }

  return uniqueLines(lines)
}

const buildThoughtLines = (entry) => {
  const text = String(entry?.thought || entry?.summary || '').trim()
  if (!text) return []
  return text
    .split(/\n+/)
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 3)
}

const createTimelineEvent = (entry = {}) => {
  const codeBlocks = Array.isArray(entry.codeBlocks) ? entry.codeBlocks.filter(Boolean) : []
  const tables = Array.isArray(entry.tables) ? entry.tables.filter(Boolean) : []
  const charts = Array.isArray(entry.charts) ? entry.charts.filter(Boolean) : []
  const firstSqlBlock = codeBlocks.find(item => /sql/i.test(`${item?.language || ''} ${item?.title || ''}`))
  const firstTable = tables[0]
  const firstChart = charts[0]
  const summary = entry.summary || entry.detail || ''

  const normalized = {
    time: entry.time || nowText(),
    key: entry.key || `log-${Date.now()}`,
    title: entry.title || '执行节点',
    kind: entry.kind || 'tool',
    toolType: inferToolType(entry),
    status: normalizeStatus(entry.status),
    summary,
    thought: entry.thought || '',
    detail: entry.detail || summary,
    markdown: entry.markdown || '',
    codeBlocks,
    tables,
    charts,
    duration: entry.duration,
    timeLabel: entry.time || '',
    durationLabel: formatDuration(entry.duration),
    thoughtLines: buildThoughtLines(entry),
    detailLines: buildDetailLines({ ...entry, summary }),
    sqlTitle: entry.sqlTitle || firstSqlBlock?.title || '',
    sql: entry.sql || firstSqlBlock?.code || '',
    tableTitle: entry.tableTitle || firstTable?.title || '',
    tableColumns: entry.tableColumns || firstTable?.columns || [],
    tableRows: entry.tableRows || firstTable?.rows || [],
    chartTitle: entry.chartTitle || firstChart?.title || '',
    chartData: entry.chartData || firstChart || null,
  }

  return normalized
}

const state = reactive({
  question: '',
  selectedDatasetId: null,
  status: 'idle',
  result: null,
  error: '',
  logs: [],
  startedAt: '',
  updatedAt: '',
  currentSessionId: '',
})

let phaseTimer = null
let activeAbortController = null

const snapshot = () => ({
  question: state.question,
  selectedDatasetId: state.selectedDatasetId,
  status: state.status,
  result: state.result,
  error: state.error,
  logs: state.logs,
  startedAt: state.startedAt,
  updatedAt: state.updatedAt,
  currentSessionId: state.currentSessionId,
})

const persist = () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot()))
}

const hydrate = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    // Only restore the question for convenience; never restore old results/logs
    // to avoid the illusion of "cached instant answers"
    if (parsed.question) state.question = parsed.question
  } catch {
    // ignore broken cache
  }
}

const nowText = () => new Date().toLocaleTimeString('zh-CN', { hour12: false })

const stopPhaseTimer = () => {
  if (phaseTimer) {
    clearInterval(phaseTimer)
    phaseTimer = null
  }
}

const replaceLogs = (entries) => {
  state.logs = (entries || []).map(createTimelineEvent)
  state.updatedAt = new Date().toISOString()
  persist()
}

const setLogStatus = (key, status, detail, meta = {}) => {
  const index = state.logs.findIndex((item) => item.key === key)
  if (index < 0) return

  state.logs[index] = createTimelineEvent({
    ...state.logs[index],
    status,
    detail: detail || state.logs[index].detail,
    ...meta,
    time: nowText(),
  })
}

const appendLog = (entry) => {
  const index = state.logs.findIndex((item) => item.key === entry.key)
  const fullEntry = createTimelineEvent({
    time: nowText(),
    status: 'pending',
    ...entry,
  })

  if (index >= 0) state.logs[index] = fullEntry
  else state.logs.push(fullEntry)

  state.updatedAt = new Date().toISOString()
  persist()
}

const beginPhaseStreaming = () => {
  stopPhaseTimer()
  replaceLogs([
    {
      ...phaseTemplates[0],
      status: 'success',
      duration: 260,
    },
    {
      ...phaseTemplates[1],
      status: 'running',
    },
  ])

  let currentIndex = 1
  let phaseStartedAt = Date.now()
  phaseTimer = setInterval(() => {
    if (state.status !== 'running') {
      stopPhaseTimer()
      return
    }

    const currentPhase = phaseTemplates[currentIndex]
    if (!currentPhase) return

    setLogStatus(currentPhase.key, 'success', '', {
      duration: Date.now() - phaseStartedAt,
    })
    currentIndex += 1
    phaseStartedAt = Date.now()

    const nextPhase = phaseTemplates[currentIndex]
    if (!nextPhase) {
      stopPhaseTimer()
      persist()
      return
    }

    appendLog({
      ...nextPhase,
      status: 'running',
    })
    persist()

    if (nextPhase.key === 'analyze') {
      stopPhaseTimer()
    }
  }, 1200)
}

const beginRealtimeStreaming = (question) => {
  stopPhaseTimer()
  replaceLogs([
    {
      key: 'stream-connect',
      title: '连接真实执行流',
      kind: 'system',
      toolType: 'default',
      status: 'running',
      summary: '正在连接后端实时执行链路。',
      detailLines: [
        `开始执行任务：${question}`,
        '正在与后端建立实时执行事件通道。',
      ],
    },
  ])
}

const normalizeTraceStageKey = (stage) => {
  const text = String(stage || '')
  if (text === 'request.received') return 'trace-submit'
  if (text.startsWith('agent1.') || text === 'route.override') return 'trace-route'
  if (text.startsWith('confirmation.')) return 'trace-confirmation'
  if (text === 'pipeline.dataset_context') return 'trace-context'
  if (text.startsWith('agent2.') || text === 'pipeline.agent2_result') return 'trace-agent2'
  if (text.startsWith('agent3.') || text === 'pipeline.agent3_result') return 'trace-agent3'
  if (text.startsWith('datasource.execute_sql') || text === 'pipeline.execute_sql') return 'trace-execute'
  if (text.startsWith('agent4.') || text === 'pipeline.agent4_result') return 'trace-agent4'
  if (text.startsWith('request.')) return 'trace-request'
  return `trace-${text.replace(/[^a-z0-9_-]+/gi, '-') || 'event'}`
}

const getTraceStageMeta = (stage) => {
  const text = String(stage || '')
  if (text === 'request.received') {
    return { title: '开始执行任务', kind: 'system', toolType: 'default' }
  }
  if (text.startsWith('agent1.') || text === 'route.override') {
    return { title: '理解问题口径', kind: 'system', toolType: 'default' }
  }
  if (text.startsWith('confirmation.')) {
    return { title: '确认统计口径', kind: 'confirmation', toolType: 'confirm' }
  }
  if (text === 'pipeline.dataset_context') {
    return { title: '加载数据集上下文', kind: 'tool', toolType: 'dataset' }
  }
  if (text.startsWith('agent2.') || text === 'pipeline.agent2_result') {
    return { title: '生成 SQL', kind: 'tool', toolType: 'sql' }
  }
  if (text.startsWith('agent3.') || text === 'pipeline.agent3_result') {
    return { title: '校验 SQL', kind: 'tool', toolType: 'sql' }
  }
  if (text.startsWith('datasource.execute_sql') || text === 'pipeline.execute_sql') {
    return { title: '执行 SQL', kind: 'tool', toolType: 'sql' }
  }
  if (text.startsWith('agent4.') || text === 'pipeline.agent4_result') {
    return { title: '生成经营分析结论', kind: 'report-stage', toolType: 'report' }
  }
  if (text === 'request.error') {
    return { title: '执行异常', kind: 'system', toolType: 'default' }
  }
  return { title: '执行节点', kind: 'tool', toolType: 'default' }
}

const normalizeTraceStatus = (status, stage) => {
  const value = String(status || '').toLowerCase()
  if (value === 'error') return 'error'
  if (value === 'fallback') return 'warning'
  if (stage === 'request.received') return 'success'
  if (['request', 'processing'].includes(value)) return 'running'
  if (['response', 'parsed', 'info'].includes(value)) return 'success'
  return normalizeStatus(value)
}

const buildTraceDetailLines = (stage, status, payload = {}) => {
  const lines = []
  const text = String(stage || '')

  if (text === 'request.received') {
    lines.push(`开始执行任务：${payload.question || state.question || '当前业务问题'}`)
    if (Array.isArray(payload.preferred_dataset_ids) && payload.preferred_dataset_ids.length > 0) {
      lines.push(`已指定数据集 ID：${payload.preferred_dataset_ids.join('、')}`)
    }
  }

  if (text === 'agent1.route_result' && payload.route) {
    const route = payload.route || {}
    if (route.refined_query) lines.push(`识别问题口径：${route.refined_query}`)
    if (Array.isArray(route.dataset_ids) && route.dataset_ids.length > 0) {
      lines.push(`候选数据集 ID：${route.dataset_ids.join('、')}`)
    }
    if (route.decision) lines.push(`当前执行决策：${route.decision}`)
  }

  if (text === 'route.override' && Array.isArray(payload.dataset_ids)) {
    lines.push(`已按手动选择覆盖自动路由：${payload.dataset_ids.join('、')}`)
  }

  if (text === 'pipeline.dataset_context') {
    if (payload.dataset_name) lines.push(`当前数据集：${payload.dataset_name}`)
    if (Number.isFinite(Number(payload.golden_sql_count))) lines.push(`Golden SQL 样本：${payload.golden_sql_count} 条`)
    if (Number.isFinite(Number(payload.dictionary_count))) lines.push(`数据字典条目：${payload.dictionary_count} 条`)
  }

  if (text.startsWith('agent2.') || text === 'pipeline.agent2_result') {
    if (status === 'request') lines.push('正在结合书架上下文和业务口径生成 SQL。')
    if (payload.notes) lines.push(`生成说明：${payload.notes}`)
    if (payload.sample_id) lines.push(`已回退到样例 SQL：${payload.sample_id}`)
  }

  if (text.startsWith('agent3.') || text === 'pipeline.agent3_result') {
    if (status === 'request') lines.push('正在复核 SQL 语义、统计口径与安全性。')
    if (payload.review_summary) lines.push(`复核结论：${payload.review_summary}`)
    if (Array.isArray(payload.risks) && payload.risks.length > 0) {
      lines.push(`识别风险：${payload.risks.join('；')}`)
    }
  }

  if (text.startsWith('datasource.execute_sql') || text === 'pipeline.execute_sql') {
    if (status === 'response') {
      const rowCount = Number(payload.row_count)
      if (Number.isFinite(rowCount)) lines.push(`SQL 返回 ${rowCount} 行结果。`)
      if (Array.isArray(payload.columns) && payload.columns.length > 0) {
        lines.push(`返回字段：${payload.columns.join('、')}`)
      }
    } else if (status === 'error' && payload.error) {
      lines.push(`执行失败：${payload.error}`)
    } else {
      lines.push('已提交 SQL，正在等待数据仓库执行结果。')
    }
  }

  if (text.startsWith('agent4.') || text === 'pipeline.agent4_result') {
    if (status === 'request') lines.push('正在生成经营分析摘要与最终报告。')
    if (payload.analysis_preview) lines.push('已生成分析摘要预览。')
  }

  if (text.startsWith('confirmation.')) {
    if (payload.confirmation_question) lines.push(payload.confirmation_question)
    if (payload.selected_option) lines.push(`确认内容：${payload.selected_option}`)
  }

  if (text === 'request.error' && payload.error) {
    lines.push(`执行失败：${payload.error}`)
  }

  if (payload.error && !lines.some(line => line.includes(payload.error))) {
    lines.push(payload.error)
  }

  if (payload.duration_seconds) {
    lines.push(`节点耗时 ${formatDuration(Number(payload.duration_seconds) * 1000)}。`)
  }

  return uniqueLines(lines)
}

const buildTraceThought = (stage, status, payload = {}) => {
  const text = String(stage || '')
  if (payload.response_text) return String(payload.response_text).trim()
  if (payload.analysis_preview) return String(payload.analysis_preview).trim()
  if (payload.review_summary) return String(payload.review_summary).trim()
  if (status === 'request' && text.startsWith('agent2.')) return '模型正在根据业务问题、书架上下文和样例 SQL 组织查询语句。'
  if (status === 'request' && text.startsWith('agent3.')) return '正在从统计口径、字段匹配和只读安全三个方向复核当前 SQL。'
  if (status === 'request' && text.startsWith('agent4.')) return '正在基于结果数据生成经营分析摘要和建议动作。'
  return ''
}

const applyTraceEvent = (payload = {}) => {
  const event = payload?.event || {}
  const stage = String(event.stage || '')
  if (!stage) return

  if (state.logs.some(item => item.key === 'stream-connect')) {
    setLogStatus('stream-connect', 'success', '', {
      summary: '后端实时执行链路已建立。',
      detailLines: [
        `开始执行任务：${state.question || '当前业务问题'}`,
        '已连接后端实时事件通道，后续节点将按真实执行顺序推进。',
      ],
      time: nowText(),
    })
  }

  const meta = getTraceStageMeta(stage)
  const key = normalizeTraceStageKey(stage)
  const normalizedStatus = normalizeTraceStatus(event.status, stage)
  const detailLines = buildTraceDetailLines(stage, event.status, event)
  const thought = buildTraceThought(stage, event.status, event)
  const summary = detailLines[0] || `${meta.title}处理中`
  const existing = state.logs.find(item => item.key === key)

  appendLog({
    key,
    title: meta.title,
    kind: meta.kind,
    toolType: meta.toolType,
    status: normalizedStatus,
    summary,
    thought,
    detailLines,
    time: event.time || nowText(),
    duration: event.duration_seconds ? Number(event.duration_seconds) * 1000 : existing?.duration,
  })
}

const formatDuration = (duration) => {
  const value = Number(duration)
  if (!Number.isFinite(value) || value <= 0) return ''
  const seconds = value / 1000
  if (seconds >= 60) {
    const minutes = Math.floor(seconds / 60)
    const remain = seconds - minutes * 60
    const remainLabel = remain.toFixed(remain >= 10 ? 0 : 1).replace(/\.0$/, '')
    return `${minutes}m ${remainLabel}s`
  }
  const label = seconds.toFixed(seconds >= 10 ? 1 : 2).replace(/\.0$/, '').replace(/(\.\d*[1-9])0+$/, '$1')
  return `${label}s`
}

const normalizeSelectedDatasetIds = (selectedDatasetInput) => {
  if (Array.isArray(selectedDatasetInput)) {
    return selectedDatasetInput
      .map(item => Number(item))
      .filter(item => Number.isFinite(item) && item > 0)
  }
  const value = Number(selectedDatasetInput)
  return Number.isFinite(value) && value > 0 ? [value] : []
}

const splitDatasetSteps = (steps = []) => {
  const routeSteps = []
  const confirmSteps = []
  const datasetGroups = []
  let currentGroup = []

  steps.forEach((step) => {
    const title = String(step?.title || '')
    if (/老板确认/i.test(title)) {
      confirmSteps.push(step)
      return
    }
    if (/Agent1/i.test(title)) {
      routeSteps.push(step)
      return
    }

    currentGroup.push(step)
    if (/Agent4/i.test(title)) {
      datasetGroups.push(currentGroup)
      currentGroup = []
    }
  })

  if (currentGroup.length > 0) datasetGroups.push(currentGroup)
  return { routeSteps, confirmSteps, datasetGroups }
}

const buildChartPreview = (dataset) => {
  const columns = Array.isArray(dataset?.columns) ? dataset.columns : []
  const rows = Array.isArray(dataset?.rows) ? dataset.rows : []
  if (rows.length < 2 || columns.length < 2) return null

  const firstRow = rows[0] || {}
  const categoryColumn =
    columns.find(col => /日期|时间|城市|分公司|名称|类型|水平/i.test(col)) ||
    columns.find(col => typeof firstRow[col] === 'string') ||
    columns[0]

  const numericColumns = columns.filter(col => typeof firstRow[col] === 'number')
  if (!categoryColumn || numericColumns.length === 0) return null

  const chartType = rows.length > 6 ? 'trend' : 'pie'
  const previewColumns = chartType === 'trend'
    ? [categoryColumn, ...numericColumns.slice(0, 2)]
    : [categoryColumn, numericColumns[0]]

  return {
    title: chartType === 'trend' ? '图表预览' : '分布预览',
    chartType,
    columns: previewColumns,
    rows,
  }
}

const inferQueryTitle = (dataset) => {
  const sqlText = String(dataset?.sql || '')
  const reviewFallback = String(dataset?.agent3_review?.fallback_reason || '')
  if (/fallback|纠错|修正/i.test(reviewFallback)) return 'SQL纠错并重新执行'
  if (/group\s+by|count\s*\(|sum\s*\(|avg\s*\(|distinct/i.test(sqlText)) return '复杂查询 pandas 代码到 SQL 转换'
  return '选择数据表并执行SQL语句查询数据'
}

const inferDetailedQueryTitle = (dataset) => {
  const sqlText = String(dataset?.sql || '')
  const reviewFallback = String(dataset?.agent3_review?.fallback_reason || '')
  if (/fallback|纠错|修正/i.test(reviewFallback)) return '复杂查询pandas代码到SQL转换'
  if (/group\s+by|count\s*\(|sum\s*\(|avg\s*\(|distinct|rank\s*\(|over\s*\(/i.test(sqlText)) return '复杂查询pandas代码到SQL转换'
  return '选择数据表并执行SQL语句查询数据'
}

const inferSqlGenerationTitle = (dataset) => {
  const sqlText = String(dataset?.sql || '')
  const reviewFallback = String(dataset?.agent3_review?.fallback_reason || '')
  if (/fallback|纠错|修正|绾犻敊|淇/i.test(reviewFallback)) return 'SQL纠错并重新生成'
  if (/rank\s*\(|over\s*\(/i.test(sqlText)) return '生成复杂分析 SQL'
  if (/group\s+by|count\s*\(|sum\s*\(|avg\s*\(|distinct/i.test(sqlText)) return '生成聚合分析 SQL'
  return '生成 SQL'
}

const inferSqlReviewTitle = (dataset) => {
  const reviewFallback = String(dataset?.agent3_review?.fallback_reason || '')
  return /fallback|纠错|修正|绾犻敊|淇/i.test(reviewFallback) ? 'SQL纠错并重新生成' : '校验 SQL'
}

const hasExplicitPythonSignal = (stepGroup = [], dataset = {}) => {
  const stepText = stepGroup
    .map(step => [step?.title, step?.detail, step?.summary].filter(Boolean).join(' '))
    .join(' ')
  const datasetText = [
    dataset?.analysis,
    dataset?.processing_mode,
    dataset?.pipeline,
  ].filter(Boolean).join(' ')

  return /python|pandas/i.test(`${stepText} ${datasetText}`)
}

const inferProcessingTitle = (stepGroup = [], chartPreview, dataset = {}) => {
  if (hasExplicitPythonSignal(stepGroup, dataset)) {
    return '使用python语言进行数据处理和运算'
  }
  if (chartPreview) {
    return '整理查询结果并生成图表预览'
  }
  return '整理查询结果'
}

const buildRouteEvent = (question, route, datasetResults, routeSteps) => {
  const matchedNames = datasetResults.map(item => item.dataset_name).filter(Boolean)
  const matchedIds = Array.isArray(route?.dataset_ids) ? route.dataset_ids : []
  const routeStep = routeSteps[0]
  const details = [
    `开始执行任务：${route?.refined_query || question || '围绕当前业务问题生成数据分析结论。'}`,
    route?.intent ? `已识别任务类型：${route.intent}` : '',
    matchedNames.length > 0
      ? `已命中数据集：${matchedNames.join('、')}`
      : matchedIds.length > 0
        ? `已命中数据集 ID：${matchedIds.join('、')}`
        : '',
    route?.decision === 'direct_execute'
      ? '当前问题命中高匹配执行路径，可直接进入查询。'
      : '当前问题无需进一步拆解，可直接进入查询执行。',
    routeStep?.duration ? `语义路由耗时 ${formatDuration(routeStep.duration)}` : '',
  ]

  return {
    key: 'route-event',
    title: '选择数据表并确认分析口径',
    kind: 'tool',
    toolType: 'dataset',
    status: 'success',
    summary: `已完成问题理解与数据集匹配。`,
    thought: route?.matched_reason || '',
    detailLines: details,
  }
}

const buildConfirmationEvent = (question, data) => ({
  key: 'boss-confirm',
  title: '确认统计口径',
  kind: 'confirmation',
  toolType: 'confirm',
  status: 'warning',
  summary: '当前任务暂停，等待确认统计口径后继续执行。',
  thought: question || '',
  detailLines: [
    `开始执行任务：${question || '当前业务问题需要先确认统计口径。'}`,
    '当前问题需要先确认统计口径。',
    data?.confirmation_question || '请先确认统计口径后继续执行。',
  ],
})

const buildDatasetExecutionEvents = (question, route, dataset, stepGroup = [], index = 0) => {
  const datasetName = dataset?.dataset_name || `数据集 ${index + 1}`
  const agent2Step = stepGroup.find(step => /Agent2/i.test(step?.title || ''))
  const agent3Step = stepGroup.find(step => /Agent3/i.test(step?.title || ''))
  const executeStep = stepGroup.find(step => /执行 SQL/i.test(step?.title || ''))
  const chartPreview = buildChartPreview(dataset)
  const reviewFallback = String(dataset?.agent3_review?.fallback_reason || '').trim()
  const reviewSummary = String(dataset?.agent3_review?.review_summary || '').trim()
  const sqlTitle = inferSqlGenerationTitle(dataset)
  const reviewTitle = inferSqlReviewTitle(dataset)
  const processingTitle = inferProcessingTitle(stepGroup, chartPreview, dataset)
  const showPythonSignal = hasExplicitPythonSignal(stepGroup, dataset)
  const shouldShowProcessingEvent = showPythonSignal || Boolean(chartPreview) || Boolean(dataset?.rows?.length)
  const refinedQuestion = route?.refined_query || question || `围绕 ${datasetName} 进行数据查询。`
  const events = []

  events.push({
    key: `dataset-query-open-${dataset?.dataset_id || index}`,
    title: '选择数据表并执行SQL语句查询数据',
    kind: 'tool',
    toolType: 'sql',
    status: 'success',
    summary: `开始围绕 ${datasetName} 组织查询任务。`,
    thought: route?.matched_reason || '',
    detailLines: [
      `开始执行任务：${refinedQuestion}`,
      `已锁定数据集：${datasetName}`,
      `此查询问题无需拆解：${refinedQuestion}`,
    ],
  })

  if (agent2Step || dataset?.sql) {
    events.push({
      key: `dataset-query-sql-${dataset?.dataset_id || index}`,
      title: sqlTitle,
      kind: 'tool',
      toolType: 'sql',
      status: 'success',
      summary: dataset?.sql ? '模型生成SQL成功' : '调用模型生成SQL中...',
      thought: reviewFallback
        ? '检测到复杂查询或复核风险，已切换到更稳妥的 SQL 重写链路。'
        : '正在结合筛选、分组、聚合和排序规则生成查询语句。',
      detailLines: [
        '调用模型生成SQL中...',
        dataset?.sql ? '模型生成SQL成功。' : '',
        agent2Step?.duration ? `SQL 生成耗时 ${formatDuration(agent2Step.duration)}。` : '',
      ],
      codeBlocks: dataset?.sql ? [{ language: 'sql', title: '模型生成SQL成功', code: dataset.sql }] : [],
    })
  }

  if (agent3Step || reviewFallback || reviewSummary) {
    events.push({
      key: `dataset-query-review-${dataset?.dataset_id || index}`,
      title: reviewTitle,
      kind: 'tool',
      toolType: 'sql',
      status: 'success',
      summary: reviewFallback ? 'SQL纠错 / SQL重新生成完成' : 'SQL 复核完成',
      thought: reviewSummary || '',
      detailLines: [
        reviewFallback ? `SQL纠错：${reviewFallback}` : '已完成 SQL 语义、口径和只读安全复核。',
        agent3Step?.duration ? `SQL 复核耗时 ${formatDuration(agent3Step.duration)}。` : '',
        reviewSummary ? `复核结论：${reviewSummary}` : '',
      ],
      codeBlocks: reviewFallback && dataset?.sql
        ? [{ language: 'sql', title: 'SQL重新生成', code: dataset.sql }]
        : [],
    })
  }

  if (executeStep) {
    events.push({
      key: `dataset-query-execute-${dataset?.dataset_id || index}`,
      title: '开始执行 SQL',
      kind: 'tool',
      toolType: 'sql',
      status: 'success',
      summary: '开始执行SQL...',
      detailLines: [
        '开始执行SQL...',
        '正在等待数据仓库返回查询结果。',
      ],
    })
  }

  events.push({
    key: `dataset-query-result-${dataset?.dataset_id || index}`,
    title: 'SQL 执行结束',
    kind: 'tool',
    toolType: 'sql',
    status: 'success',
    summary: 'SQL执行结束',
    thought: dataset?.row_count !== undefined
      ? `查询结果共 ${dataset.row_count} 行，已同步为结果预览。`
      : '',
    detailLines: [
      executeStep?.duration ? `SQL执行结束，执行耗时为 ${formatDuration(executeStep.duration)}。` : '',
      dataset?.row_count !== undefined ? `查询结果共 ${dataset.row_count} 行。` : '',
      dataset?.rows?.length ? `已生成 ${datasetName} 结果表预览。` : '',
    ],
    tables: dataset?.rows?.length
      ? [{
          title: `${datasetName} 结果预览`,
          columns: dataset.columns || [],
          rows: dataset.rows || [],
        }]
      : [],
  })

  if (shouldShowProcessingEvent) {
    events.push({
      key: `dataset-python-${dataset?.dataset_id || index}`,
      title: processingTitle,
      kind: 'tool',
      toolType: showPythonSignal ? 'python' : 'dataset',
      status: 'success',
      summary: '已对查询结果进行数据处理、指标整理与结果封装。',
      thought: chartPreview
        ? '当前结果已转换为图表和表格可直接渲染的结构。'
        : '当前结果已完成表格清洗和指标整理，可继续进入经营分析阶段。',
      detailLines: [
        `已基于 ${datasetName} 的原始查询结果进行数据处理和运算。`,
        chartPreview ? '已生成图表预览结构。' : '当前结果无需额外图表转换。',
        dataset?.rows?.length ? `处理后的结果表共 ${dataset.rows.length} 行。` : '',
      ],
      tables: dataset?.rows?.length
        ? [{
            title: `${datasetName} 数据处理结果`,
            columns: dataset.columns || [],
            rows: dataset.rows || [],
          }]
        : [],
      charts: chartPreview ? [chartPreview] : [],
    })
  }

  return events.filter(Boolean)
}

const buildDatasetInsightEvent = (dataset, stepGroup = [], index = 0) => {
  const datasetName = dataset?.dataset_name || `数据集 ${index + 1}`
  const agent4Step = stepGroup.find(step => /Agent4/i.test(step?.title || ''))
  const summaryLines = String(dataset?.analysis || '')
    .replace(/^#+\s*/gm, '')
    .replace(/\*\*/g, '')
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 5)

  return {
    key: `dataset-insight-${dataset?.dataset_id || index}`,
    title: '生成经营分析结论',
    kind: 'report-stage',
    toolType: 'report',
    status: 'success',
    summary: `已基于 ${datasetName} 生成经营分析摘要。`,
    thought: datasetName ? `当前结论围绕 ${datasetName} 的查询结果进行归纳。` : '',
    detailLines: [
      `开始整理 ${datasetName} 的结果结论。`,
      agent4Step?.duration ? `结果解读耗时 ${formatDuration(agent4Step.duration)}。` : '',
      summaryLines[0] || '已完成经营分析结论整理。',
    ],
    markdown: summaryLines.map(line => `- ${line}`).join('\n'),
  }
}

const buildFactMarkdown = (question, route, datasetResults) => {
  const sections = []
  sections.push('### 当前事实')
  sections.push(`- 当前问题：${question || '未提供问题内容'}`)
  if (route?.intent) sections.push(`- 任务类型：${route.intent}`)
  if (datasetResults.length > 0) {
    sections.push(`- 已命中数据集数量：${datasetResults.length}`)
    datasetResults.forEach((item) => {
      sections.push(`- ${item.dataset_name || `数据集 ${item.dataset_id}`}：已返回 ${item.row_count || 0} 行数据`)
    })
  }
  sections.push('')
  sections.push('### 执行计划更新')
  sections.push('- 已完成数据检索、结果预览与基础解读。')
  sections.push('- 可继续查看右侧执行详情、左侧结果摘要与最终报告。')
  return sections.join('\n')
}

const buildFactEvent = (question, route, datasetResults) => ({
  key: 'fact-update',
  title: '更新事实&计划',
  kind: 'fact-update',
  toolType: 'fact',
  status: 'success',
  summary: '已根据查询结果更新当前事实与后续处理计划。',
  detailLines: [
    '执行任务：更新事实&计划',
    `已整理 ${datasetResults.length} 个数据结果节点。`,
    '已同步更新后续分析与展示内容。',
  ],
  markdown: buildFactMarkdown(question, route, datasetResults),
})

const combineReportMarkdown = (datasetResults) => {
  const sections = (datasetResults || [])
    .map((dataset, index) => {
      const analysis = String(dataset?.analysis || '').trim()
      if (!analysis) return ''
      const datasetName = dataset?.dataset_name || `数据集 ${dataset?.dataset_id || index + 1}`
      return `## ${datasetName}\n\n${analysis}`
    })
    .filter(Boolean)

  return sections.join('\n\n---\n\n')
}

const buildReportEvents = (datasetResults) => {
  const primary = datasetResults[0]
  const report = combineReportMarkdown(datasetResults)
  return [
    {
      key: 'report-draft',
      title: '生成初版报告',
      kind: 'report-stage',
      toolType: 'report',
      status: 'success',
      summary: '已整合当前结果，生成初版报告结构。',
      detailLines: ['开始整合所有分析结果。', '已完成初版报告草稿整理。'],
    },
    {
      key: 'report-polish',
      title: '报告智能润色',
      kind: 'report-stage',
      toolType: 'report',
      status: 'success',
      summary: '已对初版报告进行润色和表达整理。',
      detailLines: ['已完成内容校正。', '报告表达与结构已优化。'],
    },
    createTimelineEvent({
      key: 'report-final',
      title: '生成最终报告',
      kind: 'report-stage',
      toolType: 'report',
      status: 'success',
      summary: '已完成经营分析摘要与最终报告整理。',
      thought: primary?.dataset_name ? `报告内容基于 ${primary.dataset_name} 当前返回结果生成。` : '',
      detailLines: ['开始生成经营分析报告。', '报告智能润色完成。', '生成最终报告。'],
      markdown: report,
    }),
  ]
}

const buildTimelineFromResult = (data) => {
  const route = data?.route || {}
  const datasetResults = Array.isArray(data?.dataset_results) ? data.dataset_results : []
  const { routeSteps, datasetGroups } = splitDatasetSteps(Array.isArray(data?.steps) ? data.steps : [])
  const events = []

  events.push(buildRouteEvent(data?.question || state.question, route, datasetResults, routeSteps))

  if (data?.requires_confirmation) {
    events.push(buildConfirmationEvent(data?.question || state.question, data))
    return events
  }

  datasetResults.forEach((dataset, index) => {
    events.push(...buildDatasetExecutionEvents(data?.question || state.question, route, dataset, datasetGroups[index] || [], index))
    if (dataset?.analysis) {
      events.push(buildDatasetInsightEvent(dataset, datasetGroups[index] || [], index))
    }
  })

  if (datasetResults.length > 0) {
    events.push(buildFactEvent(data?.question || state.question, route, datasetResults))
  }

  if (datasetResults.some(item => item?.analysis)) {
    events.push(...buildReportEvents(datasetResults))
  }

  return events.filter(Boolean)
}

const finalizeFromResult = (data) => {
  stopPhaseTimer()

  state.result = data
  state.currentSessionId = data?.session_id || state.currentSessionId
  state.updatedAt = new Date().toISOString()

  if (data?.error) {
    state.status = 'error'
    state.error = data.error
    appendLog({
      key: 'request-error',
      title: '执行异常',
      kind: 'system',
      toolType: 'default',
      detail: data.error,
      summary: '当前任务执行失败。',
      detailLines: ['当前任务执行失败。', data.error],
      status: 'error',
    })
    persist()
    return
  }

  const timeline = buildTimelineFromResult(data)
  replaceLogs(timeline)
  state.status = data?.requires_confirmation ? 'waiting_confirmation' : 'completed'
  state.error = ''
  persist()
}

const startAsk = async (question, selectedDatasetInput) => {
  const normalizedQuestion = String(question || '').trim()
  if (!normalizedQuestion) return null
  const selectedIds = normalizeSelectedDatasetIds(selectedDatasetInput)

  if (activeAbortController) {
    activeAbortController.abort()
  }
  activeAbortController = new AbortController()

  state.question = normalizedQuestion
  state.selectedDatasetId = selectedIds.length === 1 ? selectedIds[0] : null
  state.status = 'running'
  state.result = null
  state.error = ''
  state.startedAt = new Date().toISOString()
  state.updatedAt = state.startedAt
  state.currentSessionId = ''

  beginRealtimeStreaming(normalizedQuestion)
  persist()

  try {
    const selected = selectedIds.length > 0 ? selectedIds : undefined
    let finalPayload = null
    await sendSmartChatStream(
      normalizedQuestion,
      activeAbortController.signal,
      selected,
      (eventName, payload) => {
        if (eventName === 'trace') {
          applyTraceEvent(payload)
          return
        }
        if (eventName === 'result') {
          finalPayload = payload
        }
      },
    )
    if (!finalPayload) {
      throw new Error('后端实时执行流已结束，但没有返回最终结果。')
    }
    const data = finalPayload
    finalizeFromResult(data)
    activeAbortController = null
    return data
  } catch (error) {
    stopPhaseTimer()
    const aborted = error?.name === 'CanceledError' || error?.code === 'ERR_CANCELED'

    if (aborted) {
      state.status = 'idle'
      state.error = ''
      appendLog({
        key: 'request-aborted',
        title: '任务已停止',
        kind: 'system',
        toolType: 'default',
        summary: '当前问数任务已由你手动停止。',
        detailLines: ['已收到停止指令。', '当前任务不会继续后续执行。'],
        status: 'warning',
      })
      state.logs = state.logs.filter((item) => item.key !== 'request-error')
      persist()
      activeAbortController = null
      return null
    }

    state.logs = state.logs.map((log) => (
      log.status === 'running'
        ? createTimelineEvent({ ...log, status: 'error', time: nowText() })
        : log
    ))

    state.status = 'error'
    state.error = error?.response?.data?.error || '请求失败'
    appendLog({
      key: 'request-error',
      title: '执行异常',
      kind: 'system',
      toolType: 'default',
      detail: state.error,
      summary: '当前任务执行失败。',
      detailLines: ['当前任务执行失败。', state.error],
      status: 'error',
    })
    persist()
    activeAbortController = null
    throw error
  }
}

const submitBossConfirmation = async (selectedOption, context = {}) => {
  const optionLabel = typeof selectedOption === 'string'
    ? selectedOption.trim()
    : String(selectedOption?.label || selectedOption?.name || '').trim()
  const optionId = typeof selectedOption === 'string' ? '' : (selectedOption?.id || '')
  const selectedDatasetIds = typeof selectedOption === 'string'
    ? []
    : normalizeSelectedDatasetIds(selectedOption?.dataset_ids)
  const fallbackCandidateIds = normalizeSelectedDatasetIds(context?.candidateDatasetIds)
  const fallbackQuestion = [
    String(context?.originalQuestion || state.question || '').trim(),
    optionLabel ? `补充确认口径：${optionLabel}` : '',
  ].filter(Boolean).join('\n')

  if (!state.result?.session_id) {
    return startAsk(fallbackQuestion, selectedDatasetIds.length > 0 ? selectedDatasetIds : fallbackCandidateIds)
  }

  state.status = 'running'
  setLogStatus('boss-confirm', 'success', optionLabel, {
    summary: '已提交确认选项，任务继续进入执行流程。',
    thought: '',
    detailLines: [
      '已提交确认选项。',
      `确认内容：${optionLabel || '继续沿当前口径执行'}`,
      '确认完成后，系统将继续生成 SQL 与后续分析结果。',
    ],
    time: nowText(),
  })
  appendLog({
    key: 'agent2-resume',
    title: '继续生成 SQL',
    kind: 'tool',
    toolType: 'sql',
    summary: '根据确认后的统计口径继续生成 SQL。',
    detailLines: ['已收到确认结果。', '根据最新口径继续生成 SQL。'],
    status: 'running',
  })
  persist()

  try {
    const data = await confirmByBoss({
      session_id: state.result.session_id,
      selected_option: optionLabel,
      option_id: optionId || undefined,
      selected_dataset_ids: selectedDatasetIds.length > 0 ? selectedDatasetIds : undefined,
    })

    finalizeFromResult(data)
    return data
  } catch (error) {
    const errorMessage = String(error?.response?.data?.error || error?.message || '').trim()
    if (/Confirmation session not found or expired/i.test(errorMessage)) {
      appendLog({
        key: 'boss-confirm-restart',
        title: '确认会话已失效，重新发起问数',
        kind: 'confirmation',
        toolType: 'confirm',
        summary: '原确认会话已失效，已按最新补充口径重新发起任务。',
        detailLines: [
          '原确认会话已失效。',
          optionLabel ? `已自动带上补充口径：${optionLabel}` : '将沿当前补充口径重新发起任务。',
        ],
        status: 'warning',
      })
      return startAsk(
        fallbackQuestion,
        selectedDatasetIds.length > 0 ? selectedDatasetIds : fallbackCandidateIds,
      )
    }
    throw error
  }
}

const resetSession = () => {
  if (activeAbortController) {
    activeAbortController.abort()
    activeAbortController = null
  }
  stopPhaseTimer()
  state.question = ''
  state.selectedDatasetId = null
  state.status = 'idle'
  state.result = null
  state.error = ''
  state.logs = []
  state.startedAt = ''
  state.updatedAt = ''
  state.currentSessionId = ''
  localStorage.removeItem(STORAGE_KEY)
}

const stopAsk = () => {
  if (activeAbortController) {
    activeAbortController.abort()
  } else {
    resetSession()
  }
}

const clearRecoveredSessionResult = () => {
  stopPhaseTimer()
  state.question = ''
  state.status = 'idle'
  state.result = null
  state.error = ''
  state.logs = []
  state.startedAt = ''
  state.updatedAt = ''
  state.currentSessionId = ''
  persist()
}

hydrate()

export const smartAskSession = state

export const useSmartAskSession = () => {
  const latestLog = computed(() => state.logs[state.logs.length - 1] || null)
  const activeDatasetIds = computed(() => state.result?.route?.dataset_ids || [])

  return {
    state,
    latestLog,
    activeDatasetIds,
    startAsk,
    stopAsk,
    submitBossConfirmation,
    clearRecoveredSessionResult,
    resetSession,
  }
}
