import { computed, reactive } from 'vue'
import { confirmByBoss, sendSmartChat } from '../api/index.js'

const STORAGE_KEY = 'smart-ask-session-v1'

const phaseTemplates = [
  {
    key: 'submit',
    title: '问题已提交',
    detail: '问题已经发送到 Four-Agent 问数链路。',
    status: 'success',
  },
  {
    key: 'agent1',
    title: 'Agent1 路由中',
    detail: '识别问题语义并匹配候选数据集。',
    status: 'running',
  },
  {
    key: 'agent2',
    title: 'Agent2 生成 SQL',
    detail: '结合数据集书架、DDL 和示例生成查询 SQL。',
    status: 'pending',
  },
  {
    key: 'agent3',
    title: 'Agent3 复核 SQL',
    detail: '检查口径、安全性和可执行性。',
    status: 'pending',
  },
  {
    key: 'execute',
    title: '系统执行 SQL',
    detail: '执行查询并整理结果集。',
    status: 'pending',
  },
  {
    key: 'agent4',
    title: 'Agent4 业务解读',
    detail: '输出管理视角的分析结论。',
    status: 'pending',
  },
]

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
    Object.assign(state, parsed)
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

const setLogStatus = (key, status, detail) => {
  const target = state.logs.find((item) => item.key === key)
  if (!target) return

  target.status = status
  target.time = nowText()
  if (detail) target.detail = detail
}

const appendLog = (entry) => {
  const index = state.logs.findIndex((item) => item.key === entry.key)
  const fullEntry = {
    time: nowText(),
    status: 'pending',
    ...entry,
  }

  if (index >= 0) state.logs[index] = fullEntry
  else state.logs.push(fullEntry)

  state.updatedAt = new Date().toISOString()
  persist()
}

const beginPhaseStreaming = () => {
  stopPhaseTimer()
  state.logs = []

  phaseTemplates.forEach((item, index) => {
    appendLog({
      ...item,
      status: index === 0 ? 'success' : index === 1 ? 'running' : 'pending',
    })
  })

  let currentIndex = 1
  phaseTimer = setInterval(() => {
    if (state.status !== 'running') {
      stopPhaseTimer()
      return
    }

    if (currentIndex >= phaseTemplates.length - 1) return

    setLogStatus(phaseTemplates[currentIndex].key, 'success')
    currentIndex += 1
    setLogStatus(phaseTemplates[currentIndex].key, 'running')
    persist()
  }, 2500)
}

const mergeBackendSteps = (steps) => {
  if (!Array.isArray(steps) || steps.length === 0) return

  state.logs = state.logs.filter((item) => !String(item.key).startsWith('backend-step-'))

  steps.forEach((step, index) => {
    appendLog({
      key: `backend-step-${index}`,
      title: step.title || `阶段 ${index + 1}`,
      detail: step.message || (step.duration ? `${step.duration} ms` : '后端已完成该阶段。'),
      status: step.status || 'success',
    })
  })
}

const finalizeFromResult = (data) => {
  stopPhaseTimer()

  const route = data?.route || {}
  const matchedIds = route.dataset_ids || []
  const matchedNames = (data?.dataset_results || []).map((item) => item.dataset_name).filter(Boolean)

  if (matchedIds.length > 0) {
    appendLog({
      key: 'matched-dataset',
      title: '命中数据集',
      detail: matchedNames.length > 0 ? matchedNames.join('、') : `数据集 ID: ${matchedIds.join(', ')}`,
      status: 'success',
    })
  }

  if (data?.requires_confirmation) {
    setLogStatus('agent1', 'success')
    appendLog({
      key: 'boss-confirm',
      title: '等待老板确认',
      detail: data.confirmation_question || '当前问题需要先确认统计口径。',
      status: 'warning',
    })
    state.status = 'waiting_confirmation'
  } else {
    phaseTemplates.forEach((item) => setLogStatus(item.key, 'success'))
    mergeBackendSteps(data?.steps)
    state.status = 'completed'
  }

  state.result = data
  state.error = data?.error || ''
  state.currentSessionId = data?.session_id || state.currentSessionId
  state.updatedAt = new Date().toISOString()
  persist()
}

const startAsk = async (question, selectedDatasetId) => {
  const normalizedQuestion = String(question || '').trim()
  if (!normalizedQuestion) return null

  state.question = normalizedQuestion
  state.selectedDatasetId = selectedDatasetId || null
  state.status = 'running'
  state.result = null
  state.error = ''
  state.startedAt = new Date().toISOString()
  state.updatedAt = state.startedAt
  state.currentSessionId = ''

  beginPhaseStreaming()
  persist()

  try {
    const selected = selectedDatasetId ? [selectedDatasetId] : undefined
    const data = await sendSmartChat(normalizedQuestion, undefined, selected)
    finalizeFromResult(data)
    return data
  } catch (error) {
    stopPhaseTimer()
    phaseTemplates.forEach((item) => {
      const target = state.logs.find((log) => log.key === item.key)
      if (target && target.status === 'running') {
        target.status = 'error'
        target.time = nowText()
      }
    })

    state.status = 'error'
    state.error = error?.response?.data?.error || '请求失败'
    appendLog({
      key: 'request-error',
      title: '问数失败',
      detail: state.error,
      status: 'error',
    })
    persist()
    throw error
  }
}

const submitBossConfirmation = async (selectedOption) => {
  if (!state.result?.session_id) return null

  state.status = 'running'
  appendLog({
    key: 'boss-confirm-submit',
    title: '已提交确认',
    detail: selectedOption,
    status: 'success',
  })
  appendLog({
    key: 'agent2',
    title: 'Agent2 生成 SQL',
    detail: '根据确认后的统计口径继续生成 SQL。',
    status: 'running',
  })
  persist()

  const data = await confirmByBoss({
    session_id: state.result.session_id,
    selected_option: selectedOption,
  })

  finalizeFromResult(data)
  return data
}

const resetSession = () => {
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
    submitBossConfirmation,
    resetSession,
  }
}
