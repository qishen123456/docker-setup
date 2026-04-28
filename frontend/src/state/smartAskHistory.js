import { ref } from 'vue'

export const SMART_ASK_HISTORY_KEY = 'smartask_history_sessions_v1'

const historySessions = ref([])
const pendingRestoreId = ref('')
const activeHistoryId = ref('')
let loaded = false

const clone = (value) => JSON.parse(JSON.stringify(value))

export const loadSmartAskHistory = () => {
  if (typeof window === 'undefined') {
    historySessions.value = []
    return historySessions.value
  }

  try {
    const raw = localStorage.getItem(SMART_ASK_HISTORY_KEY)
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
  localStorage.setItem(SMART_ASK_HISTORY_KEY, JSON.stringify(historySessions.value))
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
  loadHistory: loadSmartAskHistory,
  upsertHistory: upsertSmartAskHistory,
  removeHistory: removeSmartAskHistory,
  clearHistory: clearSmartAskHistory,
  findHistoryById: findSmartAskHistoryById,
  requestRestore: requestSmartAskHistoryRestore,
  clearRestoreRequest: clearSmartAskHistoryRestoreRequest,
  setActiveHistory: setActiveSmartAskHistory,
})
