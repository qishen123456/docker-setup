import { ref } from 'vue'

export const SMART_ASK_HISTORY_KEY = 'smartask_history_sessions_v1'

const historySessions = ref([])
const pendingRestoreId = ref('')
const activeHistoryId = ref('')
let loaded = false
let historyScope = 'anonymous'

const clone = (value) => JSON.parse(JSON.stringify(value))

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
    historySessions.value = raw ? JSON.parse(raw) : []
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

export const upsertSmartAskHistory = (payload) => {
  ensureLoaded()
  const nextItem = clone(payload)
  historySessions.value = [
    nextItem,
    ...historySessions.value.filter(item => item.id !== nextItem.id),
  ].slice(0, 50)
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
}

export const clearSmartAskHistory = () => {
  ensureLoaded()
  historySessions.value = []
  persistSmartAskHistory()
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
  upsertHistory: upsertSmartAskHistory,
  removeHistory: removeSmartAskHistory,
  clearHistory: clearSmartAskHistory,
  findHistoryById: findSmartAskHistoryById,
  requestRestore: requestSmartAskHistoryRestore,
  clearRestoreRequest: clearSmartAskHistoryRestoreRequest,
  setActiveHistory: setActiveSmartAskHistory,
})
