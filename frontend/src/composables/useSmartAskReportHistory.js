import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'

const clone = (value) => JSON.parse(JSON.stringify(value))
const MAX_SNAPSHOT_MESSAGES = 30

export const useSmartAskReportHistory = ({
  session,
  messages,
  datasetId,
  datasets,
  isRunning,
  isDatasetVisible,
  loadHistory,
  upsertHistory,
  setActiveHistory,
  detailReportResult,
  showPanel,
  thinkingOpen,
  logOpen,
  timelineVersion,
  scrollChat,
  scrollPanel,
  createMessageId,
}) => {
  const lastSavedHistorySignature = ref('')

  const buildHistoryTitle = () => {
    const firstUser = messages.find(m => m.role === 'user')
    const q = firstUser?.content || session.state.question || '未命名对话'
    return String(q).slice(0, 24)
  }

  const createHistoryId = () => {
    // 每条历史记录必须独立，不能复用会话 ID，否则同一会话下多次问数会互相覆盖。
    if (typeof window !== 'undefined' && window.crypto?.randomUUID) {
      return `history-report-${window.crypto.randomUUID()}`
    }
    return `history-report-${Date.now()}-${Math.random().toString(16).slice(2)}`
  }

  const normalizeSnapshotMessages = (items = []) => (
    items
      .slice(-MAX_SNAPSHOT_MESSAGES)
      .map((item) => {
        const normalized = {
          id: item?.id,
          role: item?.role,
          content: item?.content || '',
          loading: false,
        }
        if (item?.data && typeof item.data === 'object') {
          normalized.data = clone(item.data)
        }
        return normalized
      })
      .filter(item => item.role === 'user' || item.role === 'ai')
  )

  const buildReportHistorySnapshot = (result = session.state.result) => {
    if (!result || result?.error || result?.requires_confirmation) return null
    const clonedResult = clone(result)
    const firstDataset = Array.isArray(clonedResult.dataset_results) ? clonedResult.dataset_results[0] : null
    const selectedId = datasetId.value || session.state.selectedDatasetId || clonedResult.dataset_id || firstDataset?.dataset_id || null
    const selectedDataset = datasets.value.find(item => Number(item.id) === Number(selectedId))
    const question = clonedResult.question || session.state.question || buildHistoryTitle()
    const updatedAt = new Date().toLocaleString()
    return {
      version: 2,
      question,
      updatedAt,
      datasetId: selectedId,
      datasetName: selectedDataset?.dataset_name || clonedResult.dataset_name || firstDataset?.dataset_name || '自动路由数据集',
      result: clonedResult,
      conversationSessionId: session.state.conversationSessionId || '',
      messages: normalizeSnapshotMessages(messages),
    }
  }

  const saveCurrentToHistory = (result = session.state.result) => {
    const reportSnapshot = buildReportHistorySnapshot(result)
    if (!reportSnapshot?.result) return ''

    const signature = JSON.stringify({
      question: reportSnapshot.question,
      updatedAt: session.state.updatedAt,
      datasetId: reportSnapshot.datasetId,
      messageCount: reportSnapshot.messages?.length || 0,
    })
    if (signature === lastSavedHistorySignature.value) return ''

    loadHistory()
    lastSavedHistorySignature.value = signature
    const payload = {
      id: createHistoryId(),
      title: String(reportSnapshot.question || buildHistoryTitle()).slice(0, 24),
      question: reportSnapshot.question,
      datasetId: reportSnapshot.datasetId,
      datasetName: reportSnapshot.datasetName,
      updatedAt: reportSnapshot.updatedAt,
      reportSnapshot,
    }
    return upsertHistory(payload)
  }

  const filterResultDatasets = (result) => {
    if (Array.isArray(result?.dataset_results)) {
      result.dataset_results = result.dataset_results.filter(dataset => isDatasetVisible(dataset?.dataset_id))
    }
    return result
  }

  const restoreSnapshotMessages = (snapshotMessages = [], fallbackQuestion, fallbackResult) => {
    const restoredMessages = Array.isArray(snapshotMessages)
      ? snapshotMessages
          .map((item) => {
            if (item?.role === 'user') {
              return {
                id: createMessageId(),
                role: 'user',
                content: String(item.content || ''),
              }
            }
            if (item?.role === 'ai') {
              let data = item.data && typeof item.data === 'object'
                ? filterResultDatasets(clone(item.data))
                : null
              // 兜底：本地 compact 或旧数据导致 AI 消息 data 缺失时，
              // 用报告快照的完整 result 重建，保证回答卡片能正常渲染。
              if (!data && fallbackResult && typeof fallbackResult === 'object') {
                data = filterResultDatasets(clone(fallbackResult))
              }
              return {
                id: createMessageId(),
                role: 'ai',
                loading: false,
                data,
              }
            }
            return null
          })
          .filter(Boolean)
      : []

    if (restoredMessages.length) return restoredMessages
    return [
      { id: createMessageId(), role: 'user', content: fallbackQuestion },
      { id: createMessageId(), role: 'ai', loading: false, data: fallbackResult },
    ]
  }

  const restoreHistory = (item) => {
    if (!item) return false
    if (isRunning.value) {
      ElMessage.warning('正在执行中，无法恢复历史对话')
      return false
    }

    setActiveHistory(item.id)
    const reportSnapshot = item.reportSnapshot || {}
    const result = reportSnapshot.result || item.sessionState?.result || null
    if (!result) {
      ElMessage.warning('该历史记录缺少报告快照，无法恢复完整报告。')
      return false
    }

    const restoredResult = filterResultDatasets(clone(result))
    const question = item.question || reportSnapshot.question || restoredResult.question || item.title || ''
    messages.splice(0, messages.length, ...restoreSnapshotMessages(reportSnapshot.messages, question, restoredResult))

    session.state.question = question
    const restoredSelectedDatasetId = reportSnapshot.datasetId || item.datasetId || restoredResult.selectedDatasetId || restoredResult.dataset_id || null
    session.state.selectedDatasetId = restoredSelectedDatasetId && isDatasetVisible(restoredSelectedDatasetId)
      ? restoredSelectedDatasetId
      : null
    session.state.status = 'completed'
    session.state.result = restoredResult
    detailReportResult.value = null
    session.state.error = ''
    session.state.logs = []
    session.state.startedAt = ''
    session.state.updatedAt = reportSnapshot.updatedAt || item.updatedAt || ''
    session.state.currentSessionId = ''
    session.state.conversationSessionId = reportSnapshot.conversationSessionId || session.state.conversationSessionId

    datasetId.value = item.datasetId && isDatasetVisible(item.datasetId) ? item.datasetId : null
    if ((item.datasetId || restoredSelectedDatasetId) && !datasetId.value && !session.state.selectedDatasetId) {
      ElMessage.warning('该历史会话包含当前账号无权访问的数据集，已隐藏相关结果。')
    }
    showPanel.value = true

    Object.keys(thinkingOpen).forEach(k => delete thinkingOpen[k])
    Object.keys(logOpen).forEach(k => delete logOpen[k])
    lastSavedHistorySignature.value = JSON.stringify({
      question,
      updatedAt: session.state.updatedAt,
      datasetId: reportSnapshot.datasetId || item.datasetId || restoredSelectedDatasetId,
    })
    timelineVersion.value += 1

    nextTick(() => {
      scrollChat('auto')
      scrollPanel('auto')
    })
    return true
  }

  return {
    buildReportHistorySnapshot,
    saveCurrentToHistory,
    restoreHistory,
  }
}
