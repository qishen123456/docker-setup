import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 600000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const authHeaders = () => {
  const token = getAuthToken()
  return token ? { 'X-Auth-Token': token } : {}
}

export const AUTH_TOKEN_KEY = 'auth_token'

export const getAuthToken = () => localStorage.getItem(AUTH_TOKEN_KEY) || ''
export const setAuthToken = (token) => {
  if (token) localStorage.setItem(AUTH_TOKEN_KEY, token)
}
export const clearAuthToken = () => localStorage.removeItem(AUTH_TOKEN_KEY)

api.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers['X-Auth-Token'] = token
  }
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.error || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export const healthCheck = () => api.get('/health')
export const getDashboard = () => api.get('/dashboard')

export const getCurrentUser = () => api.get('/auth/me')
export const logout = () => api.post('/auth/logout').finally(() => clearAuthToken())
export const passwordLogin = (data) => api.post('/auth/login', data)
export const adminLogin = (data) => api.post('/auth/admin/login', data)
export const changePassword = (data) => api.post('/auth/change-password', data)
export const getEmployeePermissions = () => api.get('/auth/employee-permissions')
export const saveEmployeePermissions = (employees) => api.put('/auth/employee-permissions', { employees })
export const getFeishuLoginUrl = () => api.get('/auth/feishu/login-url')
export const feishuInAppAuth = (authCode) => api.post('/feishu/auth', { auth_code: authCode })

export const getFeatureFlags = () => api.get('/feature-flags')
export const getAdminFeatureFlags = () => api.get('/admin/feature-flags')
export const saveAdminFeatureFlags = (features) => api.put('/admin/feature-flags', { features })
export const resetAdminFeatureFlags = () => api.post('/admin/feature-flags/reset')
export const getDataPermissions = () => api.get('/admin/data-permissions')
export const saveDataPermissions = (rules) => api.put('/admin/data-permissions', { rules })
export const getRbacOverview = () => api.get('/admin/rbac/overview')
export const createRbacRole = (data) => api.post('/admin/rbac/roles', data)
export const updateRbacRole = (id, data) => api.put(`/admin/rbac/roles/${id}`, data)
export const deleteRbacRole = (id) => api.delete(`/admin/rbac/roles/${id}`)
export const createRbacGroup = (data) => api.post('/admin/rbac/groups', data)
export const updateRbacGroup = (id, data) => api.put(`/admin/rbac/groups/${id}`, data)
export const deleteRbacGroup = (id) => api.delete(`/admin/rbac/groups/${id}`)
export const createRbacUser = (data) => api.post('/admin/rbac/users', data)
export const updateRbacUser = (id, data) => api.put(`/admin/rbac/users/${id}`, data)
export const resetRbacUserPassword = (id, data = {}) => api.post(`/admin/rbac/users/${id}/reset-password`, data)
export const bulkUpdateRbacUsers = (data) => api.post('/admin/rbac/users/bulk', data)
export const getRbacUserPermissions = (id) => api.get(`/admin/rbac/users/${id}/permissions`)
export const getRbacDatasetAccess = (id) => api.get(`/admin/rbac/datasets/${id}/access`)
export const getOrganizationTrees = () => api.get('/admin/organization-trees')
export const previewOrganizationTreeImport = (data) => api.post('/admin/organization-trees/import/preview', data)
export const applyOrganizationTreeImport = (data) => api.post('/admin/organization-trees/import/apply', data)
export const createOrganizationTreeType = (data) => api.post('/admin/organization-trees/types', data)
export const updateOrganizationTreeType = (id, data) => api.put(`/admin/organization-trees/types/${id}`, data)
export const deleteOrganizationTreeType = (id) => api.delete(`/admin/organization-trees/types/${id}`)
export const createOrganizationTreeNode = (data) => api.post('/admin/organization-trees/nodes', data)
export const updateOrganizationTreeNode = (id, data) => api.put(`/admin/organization-trees/nodes/${id}`, data)
export const deleteOrganizationTreeNode = (id) => api.delete(`/admin/organization-trees/nodes/${id}`)
export const getSystemLogs = (params = {}) => api.get('/admin/system-logs', { params })
export const getSystemLogStats = () => api.get('/admin/system-logs/stats')
export const getSystemLogDetail = (id) => api.get(`/admin/system-logs/${id}`)
export const clearSystemLogs = (data) => api.post('/admin/system-logs/clear', data)

export const getRuntimeMigrationSummary = () => api.get('/runtime-migration/summary')
export const exportRuntimeMigrationBundle = () => api.get('/runtime-migration/export', { responseType: 'blob' })
export const previewRuntimeMigrationImport = (bundle, options = {}) =>
  api.post('/runtime-migration/preview', { bundle, ...options })
export const importRuntimeMigrationBundle = (bundle, options = {}) =>
  api.post('/runtime-migration/import', { bundle, ...options })
export const createRuntimeMigrationBackup = () => api.post('/runtime-migration/backup')
export const getRuntimeMigrationBackups = () => api.get('/runtime-migration/backups')

export const getDataSources = () => api.get('/datasources')
export const createDataSource = (data) => api.post('/datasources', data)
export const updateDataSource = (id, data) => api.put(`/datasources/${id}`, data)
export const deleteDataSource = (id) => api.delete(`/datasources/${id}`)
export const testDataSource = (id) => api.post(`/datasources/${id}/test`)

export const getAIModels = () => api.get('/ai-models')
export const getActiveAIModels = () => api.get('/ai-models/active')
export const createAIModel = (data) => api.post('/ai-models', data)
export const updateAIModel = (id, data) => api.put(`/ai-models/${id}`, data)
export const deleteAIModel = (id) => api.delete(`/ai-models/${id}`)
export const testAIModel = (id) => api.post(`/ai-models/${id}/test`)
export const setDefaultAIModel = (id) => api.post(`/ai-models/${id}/set-default`)

// Report Config
export const getReportConfig = (datasetId) => api.get(`/datasets/${datasetId}/report-config`)
export const upsertReportConfig = (datasetId, config) => api.put(`/datasets/${datasetId}/report-config`, { config })
export const deleteReportConfig = (datasetId) => api.delete(`/datasets/${datasetId}/report-config`)
export const getDefaultReportConfig = () => api.get('/report-config/default')

export const getFeishuSyncConfigs = () => api.get('/feishu-sync')
export const createFeishuSyncConfig = (data) => api.post('/feishu-sync', data)
export const updateFeishuSyncConfig = (id, data) => api.put(`/feishu-sync/${id}`, data)
export const deleteFeishuSyncConfig = (id) => api.delete(`/feishu-sync/${id}`)
export const startFeishuSync = (id) => api.post(`/feishu-sync/${id}/start`)
export const pauseFeishuSync = (id) => api.post(`/feishu-sync/${id}/pause`)
export const resumeFeishuSync = (id) => api.post(`/feishu-sync/${id}/resume`)
export const testFeishuConnection = (data) => api.post('/feishu-sync/test-connection', data)
export const parseFeishuUrl = (url) => api.post('/feishu-sync/parse-url', { url })
export const previewFeishuSchema = (data) => api.post('/feishu-sync/schema-preview', data)
export const getFeishuSyncLogs = (configId, limit = 100) => api.get(`/feishu-sync/logs/${configId}?limit=${limit}`)
export const getAllFeishuSyncLogs = (limit = 50) => api.get(`/feishu-sync/logs?limit=${limit}`)
export const getFeishuSyncLogStats = () => api.get('/feishu-sync/logs/stats')
export const clearFeishuSyncLogs = (configId) => api.post(`/feishu-sync/logs/${configId}/clear`)
export const clearAllFeishuSyncLogs = () => api.post('/feishu-sync/logs/clear')

export const getBookshelfHealth = () => api.get('/bookshelves/health')
export const getBookshelfDatasets = (params = {}) => api.get('/bookshelves/datasets', { params })
export const createBookshelfDataset = async (data) => {
  try {
    return await api.post('/bookshelves/datasets', data)
  } catch (error) {
    if (error?.response?.status === 404) {
      const response = await axios.post('/api/bookshelves/datasets', data, {
        timeout: 600000,
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
      })
      return response.data
    }
    throw error
  }
}
export const generateBookshelfDatasetFromPrompt = (data, config = {}) => api.post('/bookshelves/datasets/generate-from-prompt', data, config)
export const updateBookshelfDataset = (id, data) => api.put(`/bookshelves/datasets/${id}`, data)
export const deleteBookshelfDataset = (id) => api.delete(`/bookshelves/datasets/${id}`)
export const getBookshelfDatasetFull = (id) => api.get(`/bookshelves/datasets/${id}/full`)
export const saveBookshelfDatasetFull = (id, data) => api.put(`/bookshelves/datasets/${id}/full`, data)
export const previewBookshelfDatasetSql = (id, data) => api.post(`/bookshelves/datasets/${id}/sql-preview`, data)
export const getSourceTables = (sourceId) => api.get(`/bookshelves/source-tables?source_id=${sourceId}`)
export const getCommonQuestions = (datasetId, params = {}) =>
  api.get('/bookshelves/common-questions', {
    params: {
      ...(datasetId ? { dataset_id: datasetId } : {}),
      ...params,
    },
  })

export const getAgents = () => api.get('/agents')
export const getAgent = (agentNo) => api.get(`/agents/${agentNo}`)
export const updateAgent = (agentNo, data) => api.put(`/agents/${agentNo}`, data)

export const sendSmartChat = (question, signal, selectedDatasetIds, modelId, sessionId, conversationHistory) =>
  api.post('/smart-chat', {
    question,
    selected_dataset_ids: selectedDatasetIds || undefined,
    model_id: modelId || undefined,
    session_id: sessionId || undefined,
    conversation_history: conversationHistory || undefined,
  }, { signal })

const sendSseRequest = async (url, body, signal, onEvent) => {
  const token = getAuthToken()
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { 'X-Auth-Token': token } : {}),
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    try {
      const payload = await response.json()
      message = payload?.error || message
    } catch {
      // ignore parse error
    }
    ElMessage.error(message)
    const error = new Error(message)
    error.response = { data: { error: message }, status: response.status }
    throw error
  }

  if (!response.body) {
    const error = new Error('浏览器当前无法建立实时执行流。')
    ElMessage.error(error.message)
    throw error
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const emitBufferedFrames = () => {
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''

    frames.forEach((frame) => {
      const lines = frame
        .split('\n')
        .map(line => line.replace(/\r$/, ''))
        .filter(Boolean)
      if (!lines.length) return

      let eventName = 'message'
      const dataLines = []
      lines.forEach((line) => {
        if (line.startsWith('event:')) {
          eventName = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim())
        }
      })

      if (!dataLines.length) return
      try {
        const payload = JSON.parse(dataLines.join('\n'))
        onEvent?.(eventName, payload)
      } catch {
        // ignore malformed stream payload
      }
    })
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    emitBufferedFrames()
  }

  buffer += decoder.decode()
  emitBufferedFrames()
}

export const sendSmartChatStream = (question, signal, selectedDatasetIds, onEvent, modelId, sessionId, conversationHistory) =>
  sendSseRequest('/api/smart-chat/stream', {
    question,
    selected_dataset_ids: selectedDatasetIds || undefined,
    model_id: modelId || undefined,
    session_id: sessionId || undefined,
    conversation_history: conversationHistory || undefined,
  }, signal, onEvent)

export const confirmByBoss = (payload) => api.post('/smart-chat/confirm-by-boss', payload)
export const confirmByBossStream = (payload, signal, onEvent) =>
  sendSseRequest('/api/smart-chat/confirm-by-boss/stream', payload, signal, onEvent)
export const getVannaStatus = () => api.get('/bookshelves/health')

export default api
