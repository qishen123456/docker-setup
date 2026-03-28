// ─────────────────────────────────────────────────────────
// axios 统一封装
// 所有接口请求通过 /api 前缀，Vite 代理到 :5000 后端
// ─────────────────────────────────────────────────────────
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // 增加到120秒
  headers: { 'Content-Type': 'application/json' }
})

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  response => response.data,
  error => {
    const msg = error.response?.data?.error || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

// ─────────────────────────────────────────────────────────
// Dashboard API
// ─────────────────────────────────────────────────────────
export const getDashboard = () => api.get('/dashboard')

// ─────────────────────────────────────────────────────────
// 数据源 API
// ─────────────────────────────────────────────────────────
export const getDataSources = () => api.get('/datasources')
export const createDataSource = (data) => api.post('/datasources', data)
export const updateDataSource = (id, data) => api.put(`/datasources/${id}`, data)
export const deleteDataSource = (id) => api.delete(`/datasources/${id}`)
export const testDataSource = (id) => api.post(`/datasources/${id}/test`)

// ─────────────────────────────────────────────────────────
// AI 模型 API
// ─────────────────────────────────────────────────────────
export const getAIModels = () => api.get('/ai-models')
export const createAIModel = (data) => api.post('/ai-models', data)
export const updateAIModel = (id, data) => api.put(`/ai-models/${id}`, data)
export const deleteAIModel = (id) => api.delete(`/ai-models/${id}`)
export const testAIModel = (id) => api.post(`/ai-models/${id}/test`)
export const setDefaultAIModel = (id) => api.post(`/ai-models/${id}/set-default`)

// ─────────────────────────────────────────────────────────
// 训练数据 API
// ─────────────────────────────────────────────────────────
export const getTrainingData = () => api.get('/training')
export const addTrainingData = (data) => api.post('/training', data)
export const deleteTrainingData = (id) => api.delete(`/training/${id}`)
export const batchTrain = (data) => api.post('/training/train', data)

// ─────────────────────────────────────────────────────────
// 聊天 API
// ─────────────────────────────────────────────────────────
export const sendChat = (question, signal) => api.post('/chat', { question }, { signal })
export const generateSQLOnly = (question, signal) => api.post('/chat/generate-sql', { question }, { signal })
export const getChatHistory = (limit = 20) => api.get(`/chat/history?limit=${limit}`)
export const getVannaStatus = () => api.get('/chat/vanna-status')

// ─────────────────────────────────────────────────────────
// 飞书同步 API
// ─────────────────────────────────────────────────────────
export const getFeishuSyncConfigs = () => api.get('/feishu-sync')
export const createFeishuSyncConfig = (data) => api.post('/feishu-sync', data)
export const updateFeishuSyncConfig = (id, data) => api.put(`/feishu-sync/${id}`, data)
export const deleteFeishuSyncConfig = (id) => api.delete(`/feishu-sync/${id}`)
export const startFeishuSync = (id) => api.post(`/feishu-sync/${id}/start`)
export const pauseFeishuSync = (id) => api.post(`/feishu-sync/${id}/pause`)
export const resumeFeishuSync = (id) => api.post(`/feishu-sync/${id}/resume`)
export const testFeishuConnection = (data) => api.post('/feishu-sync/test-connection', data)
export const parseFeishuUrl = (url) => api.post('/feishu-sync/parse-url', { url })

// 日志相关API
export const getFeishuSyncLogs = (configId, limit = 100) => api.get(`/feishu-sync/logs/${configId}?limit=${limit}`)
export const getAllFeishuSyncLogs = (limit = 50) => api.get(`/feishu-sync/logs?limit=${limit}`)
export const getFeishuSyncLogStats = () => api.get('/feishu-sync/logs/stats')
export const clearFeishuSyncLogs = (configId) => api.post(`/feishu-sync/logs/${configId}/clear`)
export const clearAllFeishuSyncLogs = () => api.post('/feishu-sync/logs/clear')

// ─────────────────────────────────────────────────────────
// 数据分析 API
// ─────────────────────────────────────────────────────────
export const getAnalysisPrompts = () => api.get('/analysis-prompts')
export const createAnalysisPrompt = (data) => api.post('/analysis-prompts', data)
export const updateAnalysisPrompt = (id, data) => api.put(`/analysis-prompts/${id}`, data)
export const deleteAnalysisPrompt = (id) => api.delete(`/analysis-prompts/${id}`)
export const generateAnalysis = (data) => api.post('/analysis-prompts/generate', data)

// 流式生成分析报告
export const generateAnalysisStream = (data, onContent, onDone, onError) => {
  return new Promise((resolve, reject) => {
    const eventSource = new EventSource('/api/analysis-prompts/generate-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    })

    // 由于EventSource不支持POST，我们改用fetch流式接收
    fetch('/api/analysis-prompts/generate-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      function processText(text) {
        buffer += text
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // 保留最后一行（可能不完整）
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              switch (data.type) {
                case 'content':
                  if (onContent) onContent(data.content)
                  break
                case 'done':
                  if (onDone) onDone(data.analysis)
                  resolve(data)
                  break
                case 'error':
                  if (onError) onError(data.error)
                  reject(new Error(data.error))
                  break
              }
            } catch (e) {
              console.warn('解析SSE数据失败:', e)
            }
          }
        }
      }
      
      // 流式读取
      function read() {
        reader.read().then(({ done, value }) => {
          if (done) {
            if (buffer) processText('\n') // 处理剩余数据
            return
          }
          
          const text = decoder.decode(value, { stream: true })
          processText(text)
          read()
        }).catch(error => {
          console.error('流式读取错误:', error)
          if (onError) onError(error.message)
          reject(error)
        })
      }
      
      read()
    })
    .catch(error => {
      console.error('流式请求错误:', error)
      if (onError) onError(error.message)
      reject(error)
    })
  })
}

// ─────────────────────────────────────────────────────────
// 分析思路管理 API (Vanna训练)
// ─────────────────────────────────────────────────────────
export const getAnalysisThinking = () => api.get('/analysis-thinking')
export const addAnalysisThinking = (data) => api.post('/analysis-thinking', data)
export const trainDefaultThinking = () => api.post('/analysis-thinking/train-templates')

// ─────────────────────────────────────────────────────────
// 健康检查
// ─────────────────────────────────────────────────────────
export const healthCheck = () => api.get('/health')

export default api
