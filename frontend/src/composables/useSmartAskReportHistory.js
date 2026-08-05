import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { setReadonlySnapshot } from '@/state/smartAskTaskView'

const clone = (value) => JSON.parse(JSON.stringify(value))
const MAX_SNAPSHOT_MESSAGES = 30

export const useSmartAskReportHistory = ({
  session,
  messages,
  datasetId,
  datasets,
  isRunning,
  isDatasetVisible,
  ensureDatasetsReady,
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
    const rawLogs = Array.isArray(session.state.logs) ? session.state.logs : []
    // 日志最小裁剪：只保留步骤卡渲染必要字段，超长 SQL/字符串截断，最多 50 步
    const logs = rawLogs
      .slice(0, 50)
      .map((log) => {
        if (!log || typeof log !== 'object') return log
        const next = {
          key: log.key,
          title: log.title,
          summary: log.summary,
          status: log.status,
          durationMs: log.durationMs,
          kind: log.kind,
          toolType: log.toolType,
          sqlTitle: log.sqlTitle,
        }
        if (typeof log.sql === 'string') next.sql = log.sql.length > 4000 ? `${log.sql.slice(0, 4000)}\n...` : log.sql
        if (Array.isArray(log.detailLines)) {
          next.detailLines = log.detailLines.slice(0, 5).map(line => String(line || '').slice(0, 500))
        }
        return next
      })
    return {
      version: 2,
      question,
      updatedAt,
      datasetId: selectedId,
      datasetName: selectedDataset?.dataset_name || clonedResult.dataset_name || firstDataset?.dataset_name || '自动路由数据集',
      result: clonedResult,
      conversationSessionId: session.state.conversationSessionId || '',
      messages: normalizeSnapshotMessages(messages),
      logs,
    }
  }

  const computeResultFingerprint = (result) => {
    // 修复：确认前后（或不同层级）的结果 signature 必然不同，避免去重跳过正确结果
    if (!result || !Array.isArray(result.dataset_results)) return 'empty-result'
    const parts = result.dataset_results
      .slice(0, 10)
      .map((ds, i) => {
        const dsid = String(ds?.dataset_id ?? i)
        const rc = String(Array.isArray(ds?.rows) ? ds.rows.length : 0)
        const firstRow = Array.isArray(ds?.rows) && ds.rows[0]
          ? Object.keys(ds.rows[0]).slice(0, 5).map(k => String(ds.rows[0][k]).slice(0, 16)).join('|')
          : 'no-rows'
        const mode = String(ds?.report_spec?.answerMode ?? ds?.answerMode ?? '')
        const tl = String(ds?.report_spec?.compareLevelLabel ?? ds?.query_intent?.target_level ?? '')
        const tn = String(ds?.query_intent?.top_n ?? '')
        return `${dsid}:${rc}:${mode}:${tl}:${tn}:${firstRow}`
      })
    return parts.join('||')
  }

  const saveCurrentToHistory = (result = session.state.result, options = {}) => {
    const { preferId = '' } = options
    // 修 5（双写一致）：如果入参 result 是完整正确结果，但 messages 最后一条 ai.data 和它不一样，
    // 强制把 messages 最后一条 ai.data 更新为入参 result，防止保存时 messages 里是旧的错误层级
    if (result && !result.error && !result.requires_confirmation && Array.isArray(messages) && messages.length) {
      let lastAi = null
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i]?.role === 'ai') {
          lastAi = messages[i]
          break
        }
      }
      if (lastAi) {
        const fpIn = computeResultFingerprint(result)
        const fpMsg = computeResultFingerprint(lastAi.data)
        if (fpIn !== fpMsg && fpIn !== 'empty-result') {
          lastAi.data = clone(result)
        }
      }
    }

    const reportSnapshot = buildReportHistorySnapshot(result)
    if (!reportSnapshot?.result) return ''

    // 修 1（signature 加固）：除 question/updatedAt/datasetId/messageCount 外，再拼 resultFingerprint
    // 确保同一问题确认前（requires_confirmation 已在上游过滤，但若有层级变化）和确认后不会被当成同一条
    const signature = JSON.stringify({
      question: reportSnapshot.question,
      updatedAt: session.state.updatedAt,
      datasetId: reportSnapshot.datasetId,
      messageCount: reportSnapshot.messages?.length || 0,
      resultFingerprint: computeResultFingerprint(reportSnapshot.result),
    })
    if (signature === lastSavedHistorySignature.value) return ''

    // 注意：不能在这里调用 loadHistory()——它会用 localStorage 压缩版整体替换内存中的
    // 服务端完整历史列表；upsertHistory 内部已有 ensureLoaded 兜底。
    lastSavedHistorySignature.value = signature
    const payload = {
      id: preferId || createHistoryId(),
      title: String(reportSnapshot.question || buildHistoryTitle()).slice(0, 24),
      question: reportSnapshot.question,
      datasetId: reportSnapshot.datasetId,
      datasetName: reportSnapshot.datasetName,
      updatedAt: reportSnapshot.updatedAt,
      status: 'completed',
      reportSnapshot,
    }
    return upsertHistory(payload)
  }

  const restoreSnapshotMessages = (snapshotMessages = [], fallbackQuestion, fallbackResult) => {
    const sourceMessages = Array.isArray(snapshotMessages) ? snapshotMessages : []
    const lastAiIndex = sourceMessages.map(item => item?.role).lastIndexOf('ai')
    const restoredMessages = sourceMessages.length
      ? sourceMessages
          .map((item, index) => {
            if (item?.role === 'user') {
              return {
                id: createMessageId(),
                role: 'user',
                content: String(item.content || ''),
              }
            }
            if (item?.role === 'ai') {
              // 历史记录的权威结果是 reportSnapshot.result；messages[].data 可能来自
              // 本地旧缓存/压缩快照。最后一条 AI 消息必须用完整结果重建，避免恢复后显示旧口径。
              const shouldUseFallback = index === lastAiIndex && fallbackResult && typeof fallbackResult === 'object'
              const data = shouldUseFallback
                ? clone(fallbackResult)
                : (
                    item.data && typeof item.data === 'object'
                      ? clone(item.data)
                      : (fallbackResult && typeof fallbackResult === 'object' ? clone(fallbackResult) : null)
                  )
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

  const restoreHistory = async (item, options = {}) => {
    const { readonly = false } = options
    if (!item) return false

    if (isRunning.value && !readonly) {
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

    // 权限过滤前必须等数据集就绪：登录后 getBookshelfDatasets 为异步，
    // 首次点历史时 datasets 仍为空会被 isDatasetVisible 全部误判为无权限。
    // ensureDatasetsReady 带超时兜底，后端 GET 已做权限过滤，此处仅为二次校验。
    if (typeof ensureDatasetsReady === 'function') {
      try { await ensureDatasetsReady() } catch (_) { /* ignore */ }
    }

    const restoredResult = clone(result)
    // A-05 前端最小权限校验：用已有的 isDatasetVisible 工具过滤无权限数据集结果
    if (Array.isArray(restoredResult.dataset_results) && restoredResult.dataset_results.length > 0 && typeof isDatasetVisible === 'function') {
      const totalCount = restoredResult.dataset_results.length
      const visible = restoredResult.dataset_results.filter(ds => isDatasetVisible(ds?.dataset_id))
      if (visible.length === 0) {
        ElMessage.warning('当前账号没有访问该历史记录数据集的权限，已隐藏报告数据。')
        restoredResult.dataset_results = []
        restoredResult.error = '权限不足，历史报告数据已隔离。'
      } else if (visible.length < totalCount) {
        ElMessage.info(`${totalCount - visible.length} 个无权限数据集已从历史报告中过滤。`)
        restoredResult.dataset_results = visible
      }
    }

    const question = item.question || reportSnapshot.question || restoredResult.question || item.title || ''
    const restoredMessages = restoreSnapshotMessages(reportSnapshot.messages, question, restoredResult)
    // 修 3（恢复双写一致）：messages 替换后，再强制把最后一条 AI 的 data 等于 restoredResult。
    // 彻底防止 snapshot.messages 中旧的错误层级 data 覆盖正确结果，保证任何渲染分支（msg.data / session.state.result）同一份。
    {
      let lastAi = null
      for (let i = restoredMessages.length - 1; i >= 0; i--) {
        if (restoredMessages[i]?.role === 'ai') {
          lastAi = restoredMessages[i]
          break
        }
      }
      if (lastAi && restoredResult && typeof restoredResult === 'object') {
        lastAi.data = clone(restoredResult)
      }
    }

    const restoredLogs = Array.isArray(reportSnapshot.logs) ? clone(reportSnapshot.logs) : []
    const restoredSelectedDatasetId = reportSnapshot.datasetId || item.datasetId || restoredResult.selectedDatasetId || restoredResult.dataset_id || null

    if (readonly) {
      setReadonlySnapshot({
        messages: restoredMessages,
        result: restoredResult,
        question,
        logs: restoredLogs,
        datasetId: item.datasetId && (!isDatasetVisible || isDatasetVisible(item.datasetId)) ? item.datasetId : null,
        updatedAt: reportSnapshot.updatedAt || item.updatedAt || '',
      })
      return true
    }

    messages.splice(0, messages.length, ...restoredMessages)
    session.state.question = question
    session.state.selectedDatasetId = restoredSelectedDatasetId
    session.state.status = 'completed'
    session.state.result = restoredResult
    detailReportResult.value = null
    session.state.error = restoredResult.error || ''
    // S2 logs 对称还原：优先从 reportSnapshot.logs 还原，缺失时保持空数组（旧快照 v2 兼容）
    session.state.logs = restoredLogs
    // S1 历史快照信号：用于渲染层区分"真实执行中/当前会话" vs "历史快照恢复"
    session.state.isHistoricalSnapshot = true
    session.state.startedAt = ''
    session.state.updatedAt = reportSnapshot.updatedAt || item.updatedAt || ''
    session.state.currentSessionId = ''
    session.state.conversationSessionId = reportSnapshot.conversationSessionId || session.state.conversationSessionId

    // 选中的数据集若无权限则清空，防止后续依赖 datasetId.value 的分支拿脏值
    if (typeof isDatasetVisible === 'function' && item.datasetId && !isDatasetVisible(item.datasetId)) {
      datasetId.value = null
    } else {
      datasetId.value = item.datasetId || null
    }
    showPanel.value = true

    Object.keys(thinkingOpen).forEach(k => delete thinkingOpen[k])
    Object.keys(logOpen).forEach(k => delete logOpen[k])
    // 防重签名必须与 saveCurrentToHistory 的 signature 字段结构完全一致，
    // 否则"恢复历史 → 新建对话"时 resetForNewChat 的保存 guard 失效，产生重复历史条目。
    lastSavedHistorySignature.value = JSON.stringify({
      question: restoredResult.question || question,
      updatedAt: session.state.updatedAt,
      datasetId: restoredSelectedDatasetId,
      messageCount: messages.length,
      resultFingerprint: computeResultFingerprint(restoredResult),
    })
    timelineVersion.value += 1

    // 修 2（恢复持久化）：把会话状态写入 localStorage，防止刷新 / 定时器同步 / Vue 生命周期
    // 触发 localStorage 恢复时，把旧的错误层级 result 重新写回内存覆盖了正确的恢复结果。
    if (typeof session?.persist === 'function') {
      try { session.persist() } catch (_) { /* ignore persist errors */ }
    }

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
