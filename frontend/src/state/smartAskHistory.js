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

const clone = (value) => JSON.parse(JSON.stringify(value))
const MAX_HISTORY_ITEMS = 50

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

const persistSmartAskHistory = () => {
  if (typeof window === 'undefined') return
  localStorage.setItem(getScopedHistoryKey(), JSON.stringify(historySessions.value))
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
  ;[...remoteItems, ...localItems].forEach((item) => {
    const normalized = normalizeHistoryItem(item)
    if (!normalized?.id) return
    const existing = byId.get(normalized.id)
    if (!existing || itemTime(normalized) >= itemTime(existing)) {
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
  try {
    const localItems = clone(historySessions.value)
    const response = await getSmartAskReportHistory(50)
    const remoteItems = Array.isArray(response?.history) ? response.history : []
    historySessions.value = mergeHistoryItems(localItems, remoteItems)
    persistSmartAskHistory()

    const remoteIds = new Set(remoteItems.map(item => item?.id).filter(Boolean))
    localItems
      .filter(item => item?.id && !remoteIds.has(item.id))
      .forEach(item => { pushHistoryToServer(item) })
  } catch {
    // Keep localStorage as the fallback cache.
  }
  return historySessions.value
}

export const upsertSmartAskHistory = (payload) => {
  ensureLoaded()
  const nextItem = normalizeHistoryItem(payload)
  if (!nextItem) return ''
  historySessions.value = [
    nextItem,
    ...historySessions.value.filter(item => item.id !== nextItem.id),
  ].slice(0, MAX_HISTORY_ITEMS)
  persistSmartAskHistory()
  pushHistoryToServer(nextItem)
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

export const clearSmartAskHistory = () => {
  ensureLoaded()
  historySessions.value = []
  activeHistoryId.value = ''
  pendingRestoreId.value = ''
  persistSmartAskHistory()
  clearSmartAskReportHistory().catch(() => {})
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
