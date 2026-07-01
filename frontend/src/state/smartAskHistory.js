import { ref } from 'vue'
import {
  clearSmartAskReportHistory,
  deleteSmartAskReportHistory,
  getSmartAskReportHistory,
  saveSmartAskReportHistory,
} from '../api/index.js'

export const SMART_ASK_HISTORY_KEY = 'smartask_history_sessions_v2'

const historySessions = ref([])
const pendingRestoreId = ref('')
const activeHistoryId = ref('')
let loaded = false
let historyScope = 'anonymous'
let isClearing = false
let clearingPromise = null
let syncGeneration = 0
let lastClearGeneration = 0

const clone = (value) => JSON.parse(JSON.stringify(value))
const MAX_HISTORY_ITEMS = 50
const MAX_LOCAL_HISTORY_ITEMS = 20
const MAX_LOCAL_ROWS = 80
const MAX_LOCAL_MESSAGES = 8
const MAX_LOCAL_STRING_LENGTH = 12000

const normalizeScopePart = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9_\-@.]+/gi, '_')
  .replace(/^_+|_+$/g, '')

const getScopedHistoryKey = () => `${SMART_ASK_HISTORY_KEY}:${historyScope}`

export const buildSmartAskHistoryScope = (user = {}) => {
  const role = normalizeScopePart(user.role || 'user')
  const identity = normalizeScopePart(
    user.username
    || user.login_account
    || user.account
    || user.union_id
    || user.permission_identifier
    || user.name
    || 'anonymous'
  )
  return `${role}:${identity || 'anonymous'}`
}

export const setSmartAskHistoryScope = (scope) => {
  const nextScope = normalizeScopePart(scope) || 'anonymous'
  if (historyScope === nextScope && loaded) return
  historyScope = nextScope
  loaded = false
  historySessions.value = []
  activeHistoryId.value = ''
  pendingRestoreId.value = ''
  loadSmartAskHistory()
}

export const loadSmartAskHistory = () => {
  if (typeof window === 'undefined') {
    historySessions.value = []
    return historySessions.value
  }

  try {
    const raw = localStorage.getItem(getScopedHistoryKey())
    const parsed = raw ? JSON.parse(raw) : []
    historySessions.value = mergeHistoryItems([], Array.isArray(parsed) ? parsed : [])
  } catch {
    historySessions.value = []
  }

  loaded = true
  return historySessions.value
}

const ensureLoaded = () => {
  if (!loaded) loadSmartAskHistory()
}

const isQuotaExceededError = (error) => (
  error?.name === 'QuotaExceededError'
  || error?.name === 'NS_ERROR_DOM_QUOTA_REACHED'
  || error?.code === 22
  || error?.code === 1014
)

const compactString = (value, limit = MAX_LOCAL_STRING_LENGTH) => {
  const text = String(value || '')
  return text.length > limit ? `${text.slice(0, limit)}\n...` : text
}

const compactRows = (rows = []) => (
  Array.isArray(rows) ? rows.slice(0, MAX_LOCAL_ROWS) : rows
)

const compactDatasetResult = (dataset = {}) => {
  if (!dataset || typeof dataset !== 'object') return dataset
  const next = { ...dataset }
  if (Array.isArray(next.rows)) next.rows = compactRows(next.rows)
  if (Array.isArray(next.tableRows)) next.tableRows = compactRows(next.tableRows)
  if (Array.isArray(next.preview_rows)) next.preview_rows = compactRows(next.preview_rows)
  if (Array.isArray(next.sample_rows)) next.sample_rows = compactRows(next.sample_rows)
  if (typeof next.report === 'string') next.report = compactString(next.report)
  if (typeof next.markdown === 'string') next.markdown = compactString(next.markdown)
  if (next.report_spec && typeof next.report_spec === 'object') {
    next.report_spec = compactNestedValue(next.report_spec, 0)
  }
  return next
}

const compactNestedValue = (value, depth = 0, key = '') => {
  if (typeof value === 'string') return compactString(value, depth > 3 ? 4000 : MAX_LOCAL_STRING_LENGTH)
  if (!value || typeof value !== 'object') return value
  if (Array.isArray(value)) {
    const limit = /rows|table|samples|messages/i.test(key) ? MAX_LOCAL_ROWS : 120
    return value.slice(0, limit).map(item => compactNestedValue(item, depth + 1, key))
  }
  const next = {}
  Object.entries(value).forEach(([childKey, childValue]) => {
    if (/raw|debug|trace|prompt|token|reasoning/i.test(childKey) && typeof childValue === 'string') {
      next[childKey] = compactString(childValue, 2000)
      return
    }
    next[childKey] = compactNestedValue(childValue, depth + 1, childKey)
  })
  return next
}

const compactHistoryItemForLocal = (item = {}) => {
  const next = clone(item)
  const snapshot = next.reportSnapshot || {}
  const result = snapshot.result || {}
  if (Array.isArray(result.dataset_results)) {
    result.dataset_results = result.dataset_results.map(compactDatasetResult)
  }
  if (Array.isArray(result.logs)) {
    // 保留含 SQL 的关键日志，便于历史详情里查看 SQL；其余日志清空节省空间。
    result.logs = result.logs
      .filter(log => log && (log.sql || log.sqlTitle || String(log.key || '').includes('sql') || String(log.kind || '').includes('sql')))
      .slice(-10)
      .map((log) => {
        const next = { ...log }
        if (Array.isArray(next.detailLines)) {
          next.detailLines = next.detailLines.map(line => compactString(line, 2000))
        }
        if (next.summary) next.summary = compactString(next.summary, 2000)
        return next
      })
  }
  if (typeof result.report === 'string') result.report = compactString(result.report)
  if (typeof result.answer === 'string') result.answer = compactString(result.answer)
  if (Array.isArray(snapshot.messages)) {
    snapshot.messages = snapshot.messages
      .slice(-MAX_LOCAL_MESSAGES)
      .map((message) => {
        const normalized = {
          id: message?.id,
          role: message?.role,
          content: compactString(message?.content || '', 3000),
          loading: false,
        }
        if (message?.data && typeof message.data === 'object') {
          normalized.data = compactNestedValue(clone(message.data), 0, 'data')
        }
        return normalized
      })
  }
  next.reportSnapshot = {
    ...snapshot,
    result,
    localCompacted: true,
  }
  return next
}

const persistLocalItems = (items) => {
  localStorage.setItem(getScopedHistoryKey(), JSON.stringify(items))
}

const persistSmartAskHistory = () => {
  if (typeof window === 'undefined') return
  let items = historySessions.value.slice(0, MAX_LOCAL_HISTORY_ITEMS).map(compactHistoryItemForLocal)

  // 即使 items 为空（例如清空历史），也必须写入 localStorage，
  // 否则旧数据会原封不动地保留在 localStorage 中。
  if (items.length === 0) {
    try {
      persistLocalItems(items)
    } catch (error) {
      console.warn('[smartAskHistory] failed to persist empty history', error)
    }
    return
  }

  while (items.length > 0) {
    try {
      persistLocalItems(items)
      return
    } catch (error) {
      if (!isQuotaExceededError(error)) {
        console.warn('[smartAskHistory] failed to persist local history', error)
        return
      }
      items = items.slice(0, Math.max(1, items.length - 1))
      if (items.length === 1) {
        items = items.map((item) => ({
          ...item,
          reportSnapshot: {
            ...item.reportSnapshot,
            messages: [],
            result: {
              ...(item.reportSnapshot?.result || {}),
              dataset_results: [],
              localCompacted: true,
            },
          },
        }))
        try {
          persistLocalItems(items)
        } catch {
          try { localStorage.removeItem(getScopedHistoryKey()) } catch {}
        }
        return
      }
    }
  }
}

const itemTime = (item) => {
  const raw = item?.reportSnapshot?.updatedAt || item?.serverUpdatedAt || item?.updatedAt || ''
  const parsed = Date.parse(raw)
  return Number.isFinite(parsed) ? parsed : 0
}

const normalizeReportSnapshot = (item = {}) => {
  const snapshot = item.reportSnapshot && typeof item.reportSnapshot === 'object'
    ? clone(item.reportSnapshot)
    : null
  if (snapshot?.result) return snapshot

  const legacyResult = item?.sessionState?.result
  if (legacyResult && typeof legacyResult === 'object') {
    return {
      version: 2,
      question: legacyResult.question || item.question || item.title || '',
      updatedAt: item.updatedAt || item.serverUpdatedAt || new Date().toISOString(),
      datasetId: item.datasetId || legacyResult.dataset_id || legacyResult.datasetId || null,
      datasetName: item.datasetName || legacyResult.dataset_name || legacyResult.datasetName || '',
      result: clone(legacyResult),
    }
  }
  return null
}

const normalizeHistoryItem = (item = {}) => {
  if (!item?.id) return null
  const reportSnapshot = normalizeReportSnapshot(item)
  if (!reportSnapshot?.result) return null
  const result = reportSnapshot.result || {}
  const dataset = Array.isArray(result.dataset_results) ? result.dataset_results[0] : null
  const question = String(
    item.question ||
    reportSnapshot.question ||
    result.question ||
    item.title ||
    '未命名问题'
  ).trim()
  const updatedAt = item.updatedAt || reportSnapshot.updatedAt || item.serverUpdatedAt || new Date().toLocaleString()
  return {
    id: String(item.id),
    title: String(item.title || question || '未命名问题').slice(0, 24),
    question,
    datasetId: item.datasetId || reportSnapshot.datasetId || result.dataset_id || dataset?.dataset_id || null,
    datasetName: item.datasetName || reportSnapshot.datasetName || result.dataset_name || dataset?.dataset_name || '自动路由数据集',
    updatedAt,
    serverUpdatedAt: item.serverUpdatedAt || '',
    reportSnapshot: {
      ...reportSnapshot,
      version: reportSnapshot.version || 2,
      question,
      updatedAt,
    },
  }
}

const mergeHistoryItems = (localItems = [], remoteItems = []) => {
  const byId = new Map()
  // 服务端完整版优先写入；本地 compact 版只有时间严格更晚时才覆盖，
  // 避免同时间戳下本地裁剪数据覆盖服务端完整数据。
  remoteItems.forEach((item) => {
    const normalized = normalizeHistoryItem(item)
    if (!normalized?.id) return
    byId.set(normalized.id, normalized)
  })
  localItems.forEach((item) => {
    const normalized = normalizeHistoryItem(item)
    if (!normalized?.id) return
    const existing = byId.get(normalized.id)
    if (!existing || itemTime(normalized) > itemTime(existing)) {
      byId.set(normalized.id, normalized)
    }
  })
  return Array.from(byId.values())
    .sort((a, b) => itemTime(b) - itemTime(a))
    .slice(0, MAX_HISTORY_ITEMS)
}

const pushHistoryToServer = async (item) => {
  if (!item?.id || typeof window === 'undefined') return
  try {
    await saveSmartAskReportHistory(item)
  } catch {
    // Local history remains available if the backend is offline.
  }
}

export const syncSmartAskHistoryFromServer = async () => {
  ensureLoaded()
  if (typeof window === 'undefined') return historySessions.value
  if (isClearing) {
    console.warn('[smartAskHistory] sync skipped: clearing')
    return historySessions.value
  }

  const startGeneration = ++syncGeneration
  const startClearGeneration = lastClearGeneration
  console.warn('[smartAskHistory] sync start', { startGeneration, startClearGeneration, len: historySessions.value.length })
  let response = null
  try {
    response = await getSmartAskReportHistory(50)
  } catch (error) {
    console.warn('[smartAskHistory] sync fetch failed', error)
    return historySessions.value
  }

  // 请求飞行期间如果发生过清空，或已经有更新的 sync 请求发出，
  // 丢弃本次结果，避免用旧快照覆盖清空后的状态。
  if (startClearGeneration !== lastClearGeneration) {
    console.warn('[smartAskHistory] sync aborted: clear happened during fetch')
    return historySessions.value
  }
  if (startGeneration !== syncGeneration) {
    console.warn('[smartAskHistory] sync aborted: newer sync started')
    return historySessions.value
  }

  const localItems = clone(historySessions.value)
  const remoteItems = Array.isArray(response?.history) ? response.history : []
  console.warn('[smartAskHistory] sync merge', { localLen: localItems.length, remoteLen: remoteItems.length })
  historySessions.value = mergeHistoryItems(localItems, remoteItems)
  persistSmartAskHistory()

  // 清空后不应再把旧记录推回服务端；通过 startClearGeneration 保证。
  const remoteIds = new Set(remoteItems.map(item => item?.id).filter(Boolean))
  localItems
    .filter(item => item?.id && !remoteIds.has(item.id))
    .forEach(item => { pushHistoryToServer(item) })
  console.warn('[smartAskHistory] sync done', { len: historySessions.value.length })
  return historySessions.value
}

export const upsertSmartAskHistory = (payload) => {
  ensureLoaded()
  if (isClearing) return ''
  const nextItem = normalizeHistoryItem(payload)
  if (!nextItem) return ''
  pushHistoryToServer(nextItem)
  historySessions.value = [
    nextItem,
    ...historySessions.value.filter(item => item.id !== nextItem.id),
  ].slice(0, MAX_HISTORY_ITEMS)
  persistSmartAskHistory()
  return nextItem.id
}

export const removeSmartAskHistory = (id) => {
  ensureLoaded()
  historySessions.value = historySessions.value.filter(item => item.id !== id)
  if (activeHistoryId.value === id) {
    activeHistoryId.value = ''
  }
  persistSmartAskHistory()
  if (id) {
    deleteSmartAskReportHistory(id).catch(() => {})
  }
}

export const clearSmartAskHistory = async () => {
  ensureLoaded()
  if (isClearing) {
    console.warn('[smartAskHistory] clear already in progress')
    if (clearingPromise) await clearingPromise
    return
  }

  const rollbackSnapshot = clone(historySessions.value)
  console.warn('[smartAskHistory] clear start', { rollbackLen: rollbackSnapshot.length })
  historySessions.value = []
  activeHistoryId.value = ''
  pendingRestoreId.value = ''
  persistSmartAskHistory()

  lastClearGeneration += 1
  isClearing = true
  clearingPromise = clearSmartAskReportHistory()
  try {
    await clearingPromise
    console.warn('[smartAskHistory] clear server ok')
  } catch (error) {
    // 后端清空失败时回滚本地状态，避免给用户“已清空”的假象
    console.warn('[smartAskHistory] clear server failed, rollback', error)
    historySessions.value = rollbackSnapshot
    persistSmartAskHistory()
    throw error
  } finally {
    isClearing = false
    clearingPromise = null
  }
}

export const findSmartAskHistoryById = (id) => {
  ensureLoaded()
  return historySessions.value.find(item => item.id === id) || null
}

export const requestSmartAskHistoryRestore = (id) => {
  pendingRestoreId.value = id || ''
}

export const clearSmartAskHistoryRestoreRequest = () => {
  pendingRestoreId.value = ''
}

export const setActiveSmartAskHistory = (id) => {
  activeHistoryId.value = id || ''
}

export const useSmartAskHistory = () => ({
  historySessions,
  pendingRestoreId,
  activeHistoryId,
  buildHistoryScope: buildSmartAskHistoryScope,
  setHistoryScope: setSmartAskHistoryScope,
  loadHistory: loadSmartAskHistory,
  syncHistory: syncSmartAskHistoryFromServer,
  upsertHistory: upsertSmartAskHistory,
  removeHistory: removeSmartAskHistory,
  clearHistory: clearSmartAskHistory,
  findHistoryById: findSmartAskHistoryById,
  requestRestore: requestSmartAskHistoryRestore,
  clearRestoreRequest: clearSmartAskHistoryRestoreRequest,
  setActiveHistory: setActiveSmartAskHistory,
})
