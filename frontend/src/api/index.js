import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 600000,
  headers: {
    'Content-Type': 'application/json'
  }
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

export const getDataSources = () => api.get('/datasources')
export const createDataSource = (data) => api.post('/datasources', data)
export const updateDataSource = (id, data) => api.put(`/datasources/${id}`, data)
export const deleteDataSource = (id) => api.delete(`/datasources/${id}`)
export const testDataSource = (id) => api.post(`/datasources/${id}/test`)

export const getAIModels = () => api.get('/ai-models')
export const createAIModel = (data) => api.post('/ai-models', data)
export const updateAIModel = (id, data) => api.put(`/ai-models/${id}`, data)
export const deleteAIModel = (id) => api.delete(`/ai-models/${id}`)
export const testAIModel = (id) => api.post(`/ai-models/${id}/test`)
export const setDefaultAIModel = (id) => api.post(`/ai-models/${id}/set-default`)

export const getFeishuSyncConfigs = () => api.get('/feishu-sync')
export const createFeishuSyncConfig = (data) => api.post('/feishu-sync', data)
export const updateFeishuSyncConfig = (id, data) => api.put(`/feishu-sync/${id}`, data)
export const deleteFeishuSyncConfig = (id) => api.delete(`/feishu-sync/${id}`)
export const startFeishuSync = (id) => api.post(`/feishu-sync/${id}/start`)
export const pauseFeishuSync = (id) => api.post(`/feishu-sync/${id}/pause`)
export const resumeFeishuSync = (id) => api.post(`/feishu-sync/${id}/resume`)
export const testFeishuConnection = (data) => api.post('/feishu-sync/test-connection', data)
export const parseFeishuUrl = (url) => api.post('/feishu-sync/parse-url', { url })
export const getFeishuSyncLogs = (configId, limit = 100) => api.get(`/feishu-sync/logs/${configId}?limit=${limit}`)
export const getAllFeishuSyncLogs = (limit = 50) => api.get(`/feishu-sync/logs?limit=${limit}`)
export const getFeishuSyncLogStats = () => api.get('/feishu-sync/logs/stats')
export const clearFeishuSyncLogs = (configId) => api.post(`/feishu-sync/logs/${configId}/clear`)
export const clearAllFeishuSyncLogs = () => api.post('/feishu-sync/logs/clear')

export const getBookshelfHealth = () => api.get('/bookshelves/health')
export const getBookshelfDatasets = () => api.get('/bookshelves/datasets')
export const createBookshelfDataset = (data) => api.post('/bookshelves/datasets', data)
export const updateBookshelfDataset = (id, data) => api.put(`/bookshelves/datasets/${id}`, data)
export const deleteBookshelfDataset = (id) => api.delete(`/bookshelves/datasets/${id}`)
export const getBookshelfDatasetFull = (id) => api.get(`/bookshelves/datasets/${id}/full`)
export const saveBookshelfDatasetFull = (id, data) => api.put(`/bookshelves/datasets/${id}/full`, data)
export const getSourceTables = (sourceId) => api.get(`/bookshelves/source-tables?source_id=${sourceId}`)
export const getCommonQuestions = (datasetId) =>
  datasetId ? api.get(`/bookshelves/common-questions?dataset_id=${datasetId}`) : api.get('/bookshelves/common-questions')

export const getAgents = () => api.get('/agents')
export const getAgent = (agentNo) => api.get(`/agents/${agentNo}`)
export const updateAgent = (agentNo, data) => api.put(`/agents/${agentNo}`, data)

export const sendSmartChat = (question, signal, selectedDatasetIds) =>
  api.post('/smart-chat', { question, selected_dataset_ids: selectedDatasetIds || undefined }, { signal })
export const confirmByBoss = (payload) => api.post('/smart-chat/confirm-by-boss', payload)
export const getVannaStatus = () => api.get('/bookshelves/health')

export default api
