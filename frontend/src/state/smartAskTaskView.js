import { ref, computed } from 'vue'

const runningSessionId = ref(null)
const viewingTaskId = ref('default')
const readonlySnapshot = ref(null)
const runningTaskStatus = ref('idle') // idle / running / pending_confirmation / completed / failed
const completedTaskId = ref(null)
const pendingTaskId = ref(null)

export const isViewingReadonly = computed(() => {
  return viewingTaskId.value !== 'default' && 
         viewingTaskId.value !== runningSessionId.value && 
         viewingTaskId.value !== pendingTaskId.value &&
         readonlySnapshot.value
})

export const switchViewToDefault = () => {
  viewingTaskId.value = 'default'
  readonlySnapshot.value = null
}

export const setViewingTask = (id) => {
  viewingTaskId.value = id || 'default'
}

export const setRunningSessionId = (id) => {
  runningSessionId.value = id || null
  completedTaskId.value = null
  pendingTaskId.value = null
  runningTaskStatus.value = id ? 'running' : 'idle'
  if (id) {
    viewingTaskId.value = id
    readonlySnapshot.value = null
  }
}

export const markRunningTaskPending = (id) => {
  if (runningSessionId.value === id) {
    runningTaskStatus.value = 'pending_confirmation'
    pendingTaskId.value = id
  }
}

export const markRunningTaskCompleted = (id) => {
  if (runningSessionId.value === id) {
    runningTaskStatus.value = 'completed'
    completedTaskId.value = id
    pendingTaskId.value = null
  }
}

export const markRunningTaskFailed = (id) => {
  if (runningSessionId.value === id) {
    runningTaskStatus.value = 'failed'
    completedTaskId.value = id
    pendingTaskId.value = null
  }
}

export const clearRunningSessionId = () => {
  if (runningSessionId.value && (viewingTaskId.value === runningSessionId.value || viewingTaskId.value === pendingTaskId.value)) {
    viewingTaskId.value = 'default'
    readonlySnapshot.value = null
  }
  runningSessionId.value = null
  runningTaskStatus.value = 'idle'
  completedTaskId.value = null
  pendingTaskId.value = null
}

export const switchViewToRunning = () => {
  if (runningSessionId.value && runningTaskStatus.value === 'running') {
    viewingTaskId.value = runningSessionId.value
    readonlySnapshot.value = null
  } else if (pendingTaskId.value && runningTaskStatus.value === 'pending_confirmation') {
    viewingTaskId.value = pendingTaskId.value
    readonlySnapshot.value = null
  } else if (completedTaskId.value) {
    viewingTaskId.value = completedTaskId.value
    readonlySnapshot.value = null
    runningSessionId.value = null
    runningTaskStatus.value = 'idle'
    completedTaskId.value = null
    pendingTaskId.value = null
  } else {
    viewingTaskId.value = 'default'
    readonlySnapshot.value = null
  }
}

export const setReadonlySnapshot = (snapshot) => {
  readonlySnapshot.value = snapshot
}

export const clearReadonlySnapshot = () => {
  readonlySnapshot.value = null
}

export const useSmartAskTaskView = () => ({
  runningSessionId,
  viewingTaskId,
  isViewingReadonly,
  readonlySnapshot,
  runningTaskStatus,
  completedTaskId,
  pendingTaskId,
  switchViewToDefault,
  setViewingTask,
  setRunningSessionId,
  markRunningTaskPending,
  markRunningTaskCompleted,
  markRunningTaskFailed,
  clearRunningSessionId,
  switchViewToRunning,
  setReadonlySnapshot,
  clearReadonlySnapshot,
})
