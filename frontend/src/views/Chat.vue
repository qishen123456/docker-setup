<template>
  <div class="chat-page">
    <el-row :gutter="20" style="height:100%">
      <!-- 聊天区 -->
      <el-col :span="16" style="height:100%">
        <el-card style="height:100%;display:flex;flex-direction:column">
          <template #header>
            <div class="card-header">
              <span>💬 智能问数</span>
              <el-tag :type="vannaReady ? 'success' : 'warning'" size="small">
                {{ vannaReady ? '✅ Vanna 已就绪' : '⚠️ Vanna 初始化中...' }}
              </el-tag>
            </div>
          </template>

          <!-- 消息列表 -->
          <div class="message-list" ref="msgListRef">
            <div v-if="messages.length === 0" class="empty-state">
              <el-icon size="60" color="#ddd"><ChatLineRound /></el-icon>
              <p style="color:#aaa;margin-top:12px">输入问题，AI 将自动生成 SQL 并返回结果</p>
              <div class="example-questions">
                <p style="color:#8c8c8c;font-size:13px;margin-bottom:8px">试试这些问题：</p>
                <el-tag v-for="q in exampleQuestions" :key="q" @click="fillExample(q)" style="cursor:pointer;margin:4px">{{ q }}</el-tag>
              </div>
            </div>

            <div v-for="msg in messages" :key="msg.id" :class="['msg-item', msg.role]">
              <!-- 用户提问 -->
              <div v-if="msg.role === 'user'" class="user-bubble">
                <div class="bubble user-text-wrapper" 
                     @mouseenter="showUserActions(msg.id)" 
                     @mouseleave="hideUserActionsWithDelay(msg.id)">
                  <div class="bubble user-text">{{ msg.content }}</div>
                  <!-- 悬浮操作按钮 -->
                  <div class="bubble-actions" 
                       v-show="hoveredMsgId === msg.id"
                       @mouseenter="cancelHideDelay"
                       @mouseleave="hideUserActionsWithDelay(msg.id)">
                    <el-tooltip content="复制" placement="top">
                      <el-button link size="small" @click="copyUserMessage(msg.content)">
                        <el-icon><DocumentCopy /></el-icon>
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="编辑" placement="top">
                      <el-button link size="small" @click="editUserMessage(msg)">
                        <el-icon><Edit /></el-icon>
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="重新提问" placement="top">
                      <el-button link size="small" @click="reaskQuestion(msg.content)">
                        <el-icon><RefreshRight /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </div>
                </div>
                <el-avatar :size="32" style="background:#409EFF">我</el-avatar>
              </div>

              <!-- AI 回复 -->
              <div v-else class="ai-bubble">
                <el-avatar :size="32" style="background:linear-gradient(135deg,#667eea,#764ba2)">AI</el-avatar>
                <div class="ai-content">
                  <!-- 专业横向标签式思考过程 -->
                  <div v-if="msg.steps && msg.steps.length > 0" class="thinking-process">
                    <div class="process-header">
                      <div class="process-title">
                        <el-icon class="process-icon"><Timer /></el-icon>
                        <span>思考过程</span>
                        <el-tag v-if="msg.total_duration" size="small" type="info">{{ formatDuration(msg.total_duration) }}</el-tag>
                      </div>
                      <el-button 
                        link 
                        type="primary" 
                        size="small" 
                        @click="toggleThinkingDetail(msg)"
                        class="detail-toggle"
                      >
                        {{ msg.showThinkingDetail ? '收起详情' : '查看详情' }}
                        <el-icon class="toggle-icon">
                          <ArrowDown v-if="!msg.showThinkingDetail" />
                          <ArrowUp v-else />
                        </el-icon>
                      </el-button>
                    </div>
                    
                    <!-- 思考过程说明 -->
                    <div class="thinking-process-info">
                      <el-icon class="thinking-icon"><DataAnalysis /></el-icon>
                      <span class="thinking-text">AI正在分析您的问题，通过多个步骤生成最准确的答案</span>
                    </div>
                    
                    <!-- 横向步骤标签 - 文字紧凑显示 -->
                    <div class="process-steps-text">
                      <div 
                        v-for="(step, idx) in msg.steps" 
                        :key="step.key"
                        :class="['process-step-text', `step-${step.status}`, { 'step-active': msg.currentStep === idx && step.status === 'running' }]"
                        :title="`${step.name}: ${step.status === 'success' ? '完成' : step.status === 'skipped' ? '跳过' : step.status === 'error' ? '失败' : '进行中'}${step.duration ? ' (' + formatDuration(step.duration) + ')' : ''}`"
                      >
                        <span class="step-name-text">{{ step.name }}</span>
                        <span v-if="step.duration" class="step-duration-text">{{ formatDuration(step.duration) }}</span>
                        <span v-if="step.status === 'skipped'" class="step-skipped-text">跳过</span>
                        <span v-if="idx < msg.steps.length - 1" class="step-separator">></span>
                      </div>
                    </div>
                    
                    <!-- 详细信息展开区域 -->
                    <el-collapse-transition>
                      <div v-show="msg.showThinkingDetail" class="process-details">
                        <div class="details-content">
                          <!-- 使用原来的完整步骤显示 -->
                          <div class="process-steps">
                            <div 
                              v-for="(step, idx) in msg.steps" 
                              :key="step.key"
                              :class="['process-step', `step-${step.status}`, { 'step-active': msg.currentStep === idx && step.status === 'running' }]"
                            >
                              <div class="step-indicator">
                                <el-icon v-if="step.status === 'waiting'" class="icon-waiting"><Clock /></el-icon>
                                <el-icon v-else-if="step.status === 'running'" class="icon-running is-loading"><Loading /></el-icon>
                                <el-icon v-else-if="step.status === 'success'" class="icon-success"><CircleCheck /></el-icon>
                                <el-icon v-else-if="step.status === 'error'" class="icon-error"><CircleClose /></el-icon>
                                <el-icon v-else-if="step.status === 'skipped'" class="icon-skipped"><ArrowRight /></el-icon>
                              </div>
                              <div class="step-info">
                                <div class="step-name">{{ step.name }}</div>
                                <div v-if="step.duration" class="step-time">{{ formatDuration(step.duration) }}</div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </el-collapse-transition>
                  </div>

                  <!-- 加载中 -->
                  <div v-if="msg.loading" class="bubble ai-loading">
                    <el-icon class="is-loading"><Loading /></el-icon> 正在为您分析数据...
                  </div>

                  <!-- 取消状态 -->
                  <div v-else-if="msg.cancelled" class="ai-cancelled-body">
                    <el-alert 
                      type="success" 
                      effect="light"
                      title="请求已取消" 
                      description="用户主动取消了本次请求" 
                      :closable="false" 
                      show-icon 
                    />
                  </div>

                  <!-- 错误 -->
                  <div v-else-if="msg.error && msg.error !== ''" class="ai-error-body">
                    <el-alert type="error" :description="msg.error" :closable="false" show-icon />
                    
                    <!-- SQL 展示（即使错误也显示） -->
                    <div v-if="msg.sql" class="sql-block">
                      <el-collapse v-model="activeSteps">
                        <el-collapse-item name="sql">
                          <template #title>
                            <span class="sql-label">生成的 SQL 语句</span>
                          </template>
                          <div class="sql-content">
                            <div class="sql-actions">
                              <el-button link type="primary" size="small" @click="copySQL(msg.sql)">复制</el-button>
                            </div>
                            <pre class="sql-code">{{ msg.sql }}</pre>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>
                  </div>

                  <!-- 正常结果 -->
                  <div v-else class="ai-result-body">
                    <!-- 结果统计 -->
                    <div v-if="msg.row_count !== undefined" class="result-summary-compact">
                      <el-icon><Memo /></el-icon> 
                      查询结果：<strong>{{ msg.row_count }}</strong> 条
                    </div>

                    <!-- SQL 展示 - 紧凑版本，默认收起 -->
                    <div v-if="msg.sql" class="sql-block-compact">
                      <el-collapse v-model="activeSteps">
                        <el-collapse-item name="sql">
                          <template #title>
                            <span class="sql-label-compact">SQL</span>
                          </template>
                          <div class="sql-content-compact">
                            <div class="sql-actions-compact">
                              <el-button link type="primary" size="small" @click="copySQL(msg.sql)">复制</el-button>
                            </div>
                            <pre class="sql-code-compact">{{ msg.sql }}</pre>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>

                    <!-- 结果表格 - 紧凑版本，默认收起 -->
                    <div v-if="msg.row_count > 0" class="data-block-compact">
                      <el-collapse v-model="activeSteps">
                        <el-collapse-item name="data">
                          <template #title>
                            <span class="data-label-compact">数据 ({{ msg.row_count }}条)</span>
                          </template>
                          <div class="data-content-compact">
                            <div class="data-actions-compact">
                              <el-button link type="primary" size="small" @click="copyData(msg)">复制</el-button>
                            </div>
                            <el-table :data="msg.rows" border stripe size="small" max-height="200">
                              <el-table-column 
                                v-for="column in msg.columns" 
                                :key="column"
                                :prop="column"
                                :label="column"
                                show-overflow-tooltip
                                min-width="80"
                              />
                            </el-table>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>

                    <!-- 无数据提示 -->
                    <div v-else-if="msg.row_count === 0" class="no-data">
                      查询成功，但没有找到匹配数据
                    </div>

                    <!-- 分析报告 -->
                    <div v-if="msg.analysis" class="analysis-report">
                      <el-divider content-position="left">
                        <el-icon><DataAnalysis /></el-icon>
                        <span style="margin-left: 8px">数据分析报告</span>
                      </el-divider>
                      <div class="analysis-content" v-html="formatMarkdown(msg.analysis)"></div>
                    </div>
                  </div>

                  <!-- 反馈按钮 (固定在 AI 回复底部) -->
                  <div class="ai-footer" v-if="!msg.loading">
                    <el-button 
                      size="small" 
                      link 
                      type="info" 
                      @click="copyFeedback(msg)"
                      title="复制此条回复的详细调试信息，方便发给助手排查"
                    >
                      <el-icon><ChatDotRound /></el-icon> 复制反馈信息
                    </el-button>
                    <el-button 
                      v-if="msg.rows && msg.rows.length > 0 && !msg.analysis"
                      size="small" 
                      link 
                      type="primary" 
                      @click="generateAnalysisReport(msg)"
                      :loading="msg.analyzing"
                      title="基于当前数据生成分析报告"
                    >
                      <el-icon><DataAnalysis /></el-icon> 生成分析报告
                    </el-button>
                    
                    <!-- 暂停按钮 (生成中显示) -->
                    <el-button 
                      v-if="msg.analyzing"
                      size="small" 
                      link 
                      type="danger" 
                      @click="cancelAnalysisReport(msg)"
                      title="暂停分析报告生成"
                    >
                      <el-icon><Close /></el-icon> 暂停生成
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 输入区 -->
          <div class="input-area">
            <div style="display: flex; gap: 8px;">
              <el-input
                v-model="inputText"
                :placeholder="vannaReady ? '输入问题，例如：查询最近10条客户记录' : 'Vanna 初始化中，请稍候...'"
                :disabled="!vannaReady && !isSending"
                @keydown.enter.prevent="sendMessage"
                size="large"
                style="flex: 1;"
              />
              <el-button 
                type="primary" 
                :loading="false" 
                :disabled="!vannaReady && !isSending" 
                @click="handleButtonClick"
                size="large"
                :class="{ 'cancel-mode': isSending }"
                style="min-width: 100px;"
              >
                <el-icon v-if="!isSending"><Position /></el-icon>
                <el-icon v-else class="rotating-icon"><Close /></el-icon>
                {{ isSending ? '取消请求' : '发送' }}
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 历史记录 -->
      <el-col :span="8" style="height:100%">
        <el-card style="height:100%">
          <template #header>
            <div class="card-header">
              <span>📜 历史记录</span>
              <el-button link size="small" @click="clearMessages">清空对话</el-button>
            </div>
          </template>
          <div class="history-list">
            <div v-if="history.length === 0" style="text-align:center;padding:30px;color:#aaa">暂无历史</div>
            <div v-for="h in history" :key="h.id" class="history-item" @click="fillExample(h.question)">
              <el-icon :color="h.status === 'success' ? '#67c23a' : '#f56c6c'">
                <component :is="h.status === 'success' ? 'CircleCheck' : 'CircleClose'" />
              </el-icon>
              <div class="history-content">
                <div class="history-q">{{ h.question }}</div>
                <div class="history-time">{{ h.created_at }}</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentCopy, Edit, RefreshRight, Close, DataAnalysis, ChatDotRound, Timer, Clock, Loading, CircleCheck, CircleClose, Memo, ArrowDown, ArrowUp, ArrowRight } from '@element-plus/icons-vue'
import { sendChat, getVannaStatus, getChatHistory, generateAnalysis, generateAnalysisStream } from '../api/index.js'

// 步骤定义 - 与后端步骤对应
const STEPS = [
  { key: 'init', name: '初始化', icon: 'Search', description: '初始化AI引擎' },
  { key: 'parse', name: '解析问题', icon: 'Document', description: '解析用户问题' },
  { key: 'match', name: '匹配训练', icon: 'Link', description: '匹配训练问答对' },
  { key: 'generate', name: '生成SQL', icon: 'Edit', description: '大模型生成SQL' },
  { key: 'sql_complete', name: 'SQL完成', icon: 'Check', description: 'SQL生成完成' },
  { key: 'execute', name: '执行查询', icon: 'CaretRight', description: '执行SQL查询' }
]

// 步骤状态枚举
const STEP_STATUS = {
  WAITING: 'waiting',    // 等待中
  RUNNING: 'running',    // 进行中
  SUCCESS: 'success',    // 成功
  ERROR: 'error',        // 失败
  SKIPPED: 'skipped'      // 跳过
}

const messages = ref([])
const inputText = ref('')
const isSending = ref(false)
const vannaReady = ref(false)
const msgListRef = ref()
const history = ref([])
const hoveredMsgId = ref(null)
const activeSteps = ref([]) // 默认全部收起
let hideDelayTimer = null
let currentAbortController = null

// 格式化时间显示
const formatDuration = (ms) => {
  if (!ms) return '0s'
  
  if (ms >= 60000) {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.floor((ms % 60000) / 1000)
    return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`
  } else if (ms >= 1000) {
    const seconds = Math.floor(ms / 1000)
    return `${seconds}s`
  } else {
    return `${ms}ms`
  }
}

// 切换思考过程详情显示
const toggleThinkingDetail = (msg) => {
  msg.showThinkingDetail = !msg.showThinkingDetail
  saveLocalMessages()
}

// 初始化消息步骤
const initializeMessageSteps = (msg) => {
  msg.steps = STEPS.map(step => ({
    ...step,
    status: STEP_STATUS.WAITING,
    content: null,
    duration: null,
    startTime: null
  }))
  msg.currentStep = 0
  msg.showThinkingDetail = false // 默认收起详情
}

// 更新步骤状态
const updateStepStatus = (msg, stepKey, status, content = null) => {
  const step = msg.steps?.find(s => s.key === stepKey)
  if (step) {
    const prevStatus = step.status
    step.status = status
    
    if (status === STEP_STATUS.RUNNING && !step.startTime) {
      step.startTime = Date.now()
    } else if (prevStatus === STEP_STATUS.RUNNING && step.startTime) {
      step.duration = Date.now() - step.startTime
    }
    
    if (content) {
      step.content = content
    }
    
    // 更新当前步骤
    if (status === STEP_STATUS.RUNNING) {
      msg.currentStep = msg.steps.findIndex(s => s.key === stepKey)
    }
    
    saveLocalMessages()
  }
}

// 简单的Markdown格式化函数
const formatMarkdown = (text) => {
  if (!text) return ''
  
  try {
    let html = text
    
    // 1. 先处理表格 - 将Markdown表格转换为HTML表格
    // 修复正则表达式，更准确地匹配表格
    html = html.replace(/(\|.+?\|\s*\n\|[\s\-\|\:]+\|\s*\n(?:\|.+?\|\s*\n?)*)/g, (match) => {
      const lines = match.trim().split('\n')
      if (lines.length < 3) return match
      
      // 处理表头
      const headerCells = lines[0].split('|').map(cell => cell.trim()).filter(cell => cell)
      const headerHtml = headerCells.map(cell => `<th>${cell}</th>`).join('')
      
      // 处理表体 - 收集所有数据行
      const bodyRows = []
      for (let i = 2; i < lines.length; i++) {
        const line = lines[i].trim()
        if (line && line.includes('|')) {
          const rowCells = line.split('|').map(cell => cell.trim()).filter(cell => cell)
          if (rowCells.length > 0) {
            bodyRows.push(`<tr>${rowCells.map(cell => `<td>${cell}</td>`).join('')}</tr>`)
          }
        }
      }
      
      return `<table class="markdown-table"><thead><tr>${headerHtml}</tr></thead><tbody>${bodyRows.join('')}</tbody></table>`
    })
    
    // 2. 处理标题
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>')
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>')
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>')
    
    // 3. 处理粗体
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    
    // 4. 处理斜体
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')
    
    // 5. 处理引用
    html = html.replace(/^> (.*)$/gim, '<blockquote>$1</blockquote>')
    
    // 6. 处理无序列表
    html = html.replace(/^- (.*)$/gim, '<ul><li>$1</li></ul>')
    html = html.replace(/(<\/ul>\s*<ul>)/g, '') // 合并连续的ul标签
    
    // 7. 处理有序列表
    html = html.replace(/^\d+\. (.*)$/gim, '<ol><li>$1</li></ol>')
    html = html.replace(/(<\/ol>\s*<ol>)/g, '') // 合并连续的ol标签
    
    // 8. 处理代码块
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="markdown-code"><code>$2</code></pre>')
    
    // 9. 处理内联代码
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
    
    // 10. 处理换行
    html = html.replace(/\n\n/g, '<br><br>')
    html = html.replace(/\n/g, '<br>')
    
    return html
    
  } catch (error) {
    console.error('Markdown解析失败:', error)
    // 降级处理：简单替换
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>')
  }
}
let msgIdCounter = 0

// 持久化存储键
const CHAT_STORAGE_KEY = 'vanna_chat_messages'
const CHAT_HISTORY_KEY = 'vanna_chat_history'

// 加载本地存储的聊天记录
const loadLocalMessages = () => {
  try {
    const stored = localStorage.getItem(CHAT_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      messages.value = parsed.messages || []
      msgIdCounter = Math.max(...messages.value.map(m => m.id), 0)
      console.log('加载本地聊天记录:', messages.value.length, '条')
    }
  } catch (e) {
    console.warn('加载本地聊天记录失败:', e)
  }
}

// 保存聊天记录到本地存储
const saveLocalMessages = () => {
  try {
    const data = {
      messages: messages.value,
      timestamp: new Date().toISOString()
    }
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(data))
  } catch (e) {
    console.warn('保存本地聊天记录失败:', e)
  }
}

// 加载本地历史记录
const loadLocalHistory = () => {
  try {
    const stored = localStorage.getItem(CHAT_HISTORY_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      history.value = parsed.history || []
      console.log('加载本地历史记录:', history.value.length, '条')
    }
  } catch (e) {
    console.warn('加载本地历史记录失败:', e)
  }
}

// 保存历史记录到本地存储
const saveLocalHistory = () => {
  try {
    const data = {
      history: history.value,
      timestamp: new Date().toISOString()
    }
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(data))
  } catch (e) {
    console.warn('保存本地历史记录失败:', e)
  }
}

const exampleQuestions = [
  '查询前10条数据',
  '统计数据总量',
  '查询今天的记录'
]

const fillExample = (q) => { inputText.value = q }

// 用户消息操作功能
const showUserActions = (msgId) => {
  // 清除任何现有的隐藏定时器
  if (hideDelayTimer) {
    clearTimeout(hideDelayTimer)
    hideDelayTimer = null
  }
  hoveredMsgId.value = msgId
}

const hideUserActionsWithDelay = (msgId) => {
  // 如果鼠标移到按钮上，取消隐藏
  if (hoveredMsgId.value === msgId) {
    hideDelayTimer = setTimeout(() => {
      hoveredMsgId.value = null
      hideDelayTimer = null
    }, 200) // 200ms延迟
  }
}

const cancelHideDelay = () => {
  // 鼠标进入按钮区域，取消隐藏定时器
  if (hideDelayTimer) {
    clearTimeout(hideDelayTimer)
    hideDelayTimer = null
  }
}

const hideUserActions = () => {
  // 立即隐藏（兼容旧逻辑）
  hoveredMsgId.value = null
  if (hideDelayTimer) {
    clearTimeout(hideDelayTimer)
    hideDelayTimer = null
  }
}

const copyUserMessage = (content) => {
  navigator.clipboard.writeText(content)
  ElMessage.success('已复制到剪贴板')
}

const editUserMessage = (msg) => {
  inputText.value = msg.content
  // 删除该消息及其后续的AI回复
  const msgIndex = messages.value.findIndex(m => m.id === msg.id)
  if (msgIndex !== -1) {
    // 删除用户消息和可能的AI回复
    messages.value.splice(msgIndex, 2)
    saveLocalMessages()
  }
  // 聚焦到输入框
  nextTick(() => {
    const inputElement = document.querySelector('.el-input__inner')
    if (inputElement) {
      inputElement.focus()
    }
  })
}

const reaskQuestion = (content) => {
  inputText.value = content
  // 直接发送重新提问
  sendMessage()
}

const scrollToBottom = async () => {
  await nextTick()
  if (msgListRef.value) {
    msgListRef.value.scrollTop = msgListRef.value.scrollHeight
  }
}

const checkVannaStatus = async () => {
  try {
    await getVannaStatus()
    vannaReady.value = true
  } catch {
    vannaReady.value = false
  }
}

const loadHistory = async () => {
  try {
    // 先加载本地历史记录
    loadLocalHistory()
    
    // 然后从服务器获取最新历史记录
    const data = await getChatHistory(50)
    if (data.history && data.history.length > 0) {
      history.value = data.history
      saveLocalHistory()
      console.log('从服务器加载历史记录:', data.history.length, '条')
    }
  } catch (e) {
    console.warn('从服务器加载历史记录失败:', e)
    // 如果服务器失败，使用本地记录
    loadLocalHistory()
  }
}

const clearMessages = () => { 
  messages.value = []
  saveLocalMessages()
}

const copySQL = (text) => {
  navigator.clipboard.writeText(text)
  ElMessage.success('SQL 已复制到剪贴板')
}

const copyData = (msg) => {
  if (!msg.rows || msg.rows.length === 0) {
    ElMessage.warning('没有数据可复制')
    return
  }
  
  // 转换为制表符分隔的文本
  const headers = msg.columns.join('\t')
  const rows = msg.rows.map(row => 
    msg.columns.map(col => row[col] || '').join('\t')
  ).join('\n')
  
  const text = `${headers}\n${rows}`
  navigator.clipboard.writeText(text)
  ElMessage.success('数据已复制到剪贴板')
}

const copyFeedback = (msg) => {
  // 查找对应的用户问题 (前一个 id)
  const userMsg = messages.value.find(m => m.id === msg.id - 1)
  const question = userMsg ? userMsg.content : '未知问题'
  
  let feedbackText = `### 智能问数反馈\n`
  feedbackText += `**问题**: ${question}\n`
  feedbackText += `**生成的 SQL**: \n\`\`\`sql\n${msg.sql || '未生成'}\n\`\`\`\n`
  if (msg.error) {
    feedbackText += `**执行错误**: ${msg.error}\n`
  }
  if (msg.steps && msg.steps.length > 0) {
    feedbackText += `**处理步骤**:\n`
    msg.steps.forEach(s => {
      const status = s.status === 'success' ? '✅' : s.status === 'error' ? '❌' : '⏳'
      const duration = s.duration ? `${s.duration}ms` : 'nullms'
      const name = s.name || 'undefined'
      const content = s.content || ''
      feedbackText += `- ${name}: ${status} (${duration})${content ? ' - ' + content : ''}\n`
    })
  }
  feedbackText += `\n*反馈来源: 前端可视化调试面板*`
  
  navigator.clipboard.writeText(feedbackText)
  ElMessage.success('调试信息已复制，请粘贴发送给助手')
}

// 暂停分析报告生成
const cancelAnalysisReport = (msg) => {
  // 简单的UI状态停止（API不支持真正的取消）
  msg.analyzing = false
  ElMessage.success('分析报告生成已取消')
  saveLocalMessages()
}

// 生成分析报告
const generateAnalysisReport = async (msg) => {
  try {
    // 添加分析状态
    msg.analyzing = true
    msg.analysis = "" // 初始化空的分析内容
    
    // 查找对应的用户问题
    const userMsg = messages.value.find(m => m.id === msg.id - 1)
    const question = userMsg ? userMsg.content : '未知问题'
    
    const analysisData = {
      query_data: {
        question: question,
        sql: msg.sql,
        rows: msg.rows,
        columns: msg.columns
      },
      prompt: null // 使用默认提示词
    }
    
    // 使用流式API
    await generateAnalysisStream(
      analysisData,
      // onContent - 接收到内容时调用
      (content) => {
        msg.analysis += content
        // 滚动到底部
        nextTick(() => {
          if (msgListRef.value) {
            msgListRef.value.scrollTop = msgListRef.value.scrollHeight
          }
        })
      },
      // onDone - 完成时调用
      (fullAnalysis) => {
        msg.analyzing = false
        msg.analysis = fullAnalysis
        msg.analysis_summary = {
          question: question,
          row_count: msg.rows?.length || 0,
          columns: msg.columns || [],
          data_preview: msg.rows?.slice(0, 5) || []
        }
        
        ElMessage.success('分析报告生成成功')
        saveLocalMessages()
      },
      // onError - 错误时调用
      (error) => {
        msg.analyzing = false
        console.error('流式生成分析报告失败:', error)
        ElMessage.error('生成分析报告失败: ' + error)
      }
    )
    
  } catch (error) {
    console.error('生成分析报告失败:', error)
    msg.analyzing = false
    ElMessage.error('生成分析报告失败')
  }
}

// 格式化分析报告（支持Markdown）
const formatAnalysis = (analysis) => {
  if (!analysis) return ''
  
  let formatted = analysis
  
  // 先处理代码块，避免被其他规则干扰
  formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre class="code-block"><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`
  })
  
  // 处理内联代码
  formatted = formatted.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  
  // 处理表格 - 更精确的匹配
  const tableRegex = /(\|[^\n]+\|\n)+/g
  formatted = formatted.replace(tableRegex, (match) => {
    const lines = match.trim().split('\n')
    let tableHtml = '<table class="analysis-table">'
    
    lines.forEach((line, index) => {
      const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell)
      if (cells.length > 0) {
        // 检查是否是分隔符行
        if (cells.every(cell => /^[-\s]+$/.test(cell))) {
          return // 跳过分隔符行
        }
        const tag = index === 0 ? 'th' : 'td'
        const cellsHtml = cells.map(cell => `<${tag}>${cell}</${tag}>`).join('')
        tableHtml += `<tr>${cellsHtml}</tr>`
      }
    })
    
    tableHtml += '</table>'
    return tableHtml
  })
  
  // 处理标题
  formatted = formatted
    .replace(/^#### (.*$)/gm, '<h4>$1</h4>')
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
  
  // 处理粗体和斜体
  formatted = formatted
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
  
  // 处理引用
  formatted = formatted.replace(/^> (.*)$/gm, '<blockquote>$1</blockquote>')
  
  // 处理列表
  formatted = formatted
    .replace(/^[\*\-\+] (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
  
  // 将连续的li包装在ul中
  formatted = formatted.replace(/(<li>.*?<\/li>(\s*<li>.*?<\/li>)*)/g, '<ul>$1</ul>')
  
  // 处理换行 - 将多个连续换行转换为段落分隔
  formatted = formatted.replace(/\n{3,}/g, '\n\n')
  
  // 将双换行转换为段落结束和开始
  formatted = formatted.replace(/\n\n/g, '</p><p>')
  
  // 处理单个换行
  formatted = formatted.replace(/\n/g, '<br>')
  
  // 包装在段落中，但跳过已经是块级元素的内容
  if (!formatted.startsWith('<') && !formatted.startsWith('<h') && !formatted.startsWith('<table') && !formatted.startsWith('<pre')) {
    formatted = `<p>${formatted}</p>`
  }
  
  // 清理多余的标签
  formatted = formatted.replace(/<p><\/p>/g, '')
  formatted = formatted.replace(/<p>(<h[1-6]>)/g, '$1')
  formatted = formatted.replace(/(<\/h[1-6]>)<\/p>/g, '$1')
  formatted = formatted.replace(/<p>(<table)/g, '$1')
  formatted = formatted.replace(/(<\/table>)<\/p>/g, '$1')
  formatted = formatted.replace(/<p>(<pre)/g, '$1')
  formatted = formatted.replace(/(<\/pre>)<\/p>/g, '$1')
  formatted = formatted.replace(/<p>(<blockquote)/g, '$1')
  formatted = formatted.replace(/(<\/blockquote>)<\/p>/g, '$1')
  formatted = formatted.replace(/<p>(<ul>)/g, '$1')
  formatted = formatted.replace(/(<\/ul>)<\/p>/g, '$1')
  
  return formatted
}

// 按钮点击处理函数（支持取消请求）
const handleButtonClick = () => {
  console.log('按钮被点击')
  console.log('isSending.value:', isSending.value)
  
  if (isSending.value) {
    // 取消当前请求
    cancelRequest()
  } else {
    console.log('调用sendMessage')
    sendMessage()
  }
}

// 取消请求功能
const cancelRequest = () => {
  console.log('cancelRequest called, isSending:', isSending.value)
  console.log('currentAbortController:', currentAbortController)
  
  if (currentAbortController) {
    console.log('正在取消请求...')
    currentAbortController.abort()
    currentAbortController = null
    
    // 更新最后一条AI消息的状态
    const lastAIMessage = messages.value.filter(m => m.role === 'ai').pop()
    if (lastAIMessage && lastAIMessage.loading) {
      lastAIMessage.loading = false
      lastAIMessage.cancelled = true  // 添加取消状态
      lastAIMessage.error = null  // 清除错误状态
      saveLocalMessages()
    }
    
    isSending.value = false
    ElMessage.info('请求已取消')
  } else {
    console.log('没有正在进行的请求')
  }
}

const sendMessage = async () => {
  const q = inputText.value.trim()
  if (!q) return

  inputText.value = ''

  // 添加用户消息
  const userMsg = { id: ++msgIdCounter, role: 'user', content: q, timestamp: new Date().toISOString() }
  messages.value.push(userMsg)

  // 添加 AI 加载占位，并初始化步骤
  const aiMsg = { 
    id: ++msgIdCounter, 
    role: 'ai', 
    loading: true, 
    timestamp: new Date().toISOString()
  }
  initializeMessageSteps(aiMsg)
  messages.value.push(aiMsg)
  saveLocalMessages()
  await scrollToBottom()

  // 创建 AbortController 用于取消请求
  currentAbortController = new AbortController()
  isSending.value = true
  
  try {
    // 开始第一步：初始化
    updateStepStatus(aiMsg, 'init', STEP_STATUS.RUNNING)
    
    const result = await sendChat(q, currentAbortController.signal)
    
    // 根据后端返回的步骤信息更新状态
    if (result.steps && result.steps.length > 0) {
      result.steps.forEach((backendStep, index) => {
        // 根据后端步骤标题映射到前端步骤key
        let stepKey = 'execute' // 默认
        if (backendStep.title.includes('初始化')) {
          stepKey = 'init'
        } else if (backendStep.title.includes('解析问题')) {
          stepKey = 'parse'
        } else if (backendStep.title.includes('匹配训练')) {
          stepKey = 'match'
        } else if (backendStep.title.includes('大模型生成SQL')) {
          stepKey = 'generate'
        } else if (backendStep.title.includes('SQL生成完成')) {
          stepKey = 'sql_complete'
        } else if (backendStep.title.includes('执行')) {
          stepKey = 'execute'
        }
        
        const status = backendStep.status === 'success' ? STEP_STATUS.SUCCESS : 
                     backendStep.status === 'error' ? STEP_STATUS.ERROR : 
                     backendStep.status === 'running' ? STEP_STATUS.RUNNING : 
                     backendStep.status === 'skipped' ? STEP_STATUS.SKIPPED : STEP_STATUS.WAITING
        
        updateStepStatus(aiMsg, stepKey, status, backendStep.message || backendStep.title)
        
        // 设置步骤耗时
        const step = aiMsg.steps?.find(s => s.key === stepKey)
        if (step && backendStep.duration) {
          step.duration = backendStep.duration
        }
      })
    }
    
    // 更新消息内容
    const idx = messages.value.findIndex(m => m.id === aiMsg.id)
    if (idx !== -1) {
      messages.value[idx] = {
        ...aiMsg,
        loading: false,
        sql: result.sql,
        columns: result.columns || [],
        rows: result.rows || [],
        row_count: result.row_count,
        error: result.error,
        total_duration: result.total_duration
      }
    }
    
    saveLocalMessages()
    loadHistory()
  } catch (err) {
    // 检查是否是取消操作
    if (err.name === 'AbortError') {
      console.log('请求被用户取消')
      return // 已经在cancelRequest中处理了
    }
    
    const idx = messages.value.findIndex(m => m.id === aiMsg.id)
    if (idx !== -1) {
      messages.value[idx].loading = false
      messages.value[idx].error = err.message || '请求失败'
      
      // 标记当前步骤为错误
      if (messages.value[idx].steps && messages.value[idx].currentStep >= 0) {
        const currentStep = messages.value[idx].steps[messages.value[idx].currentStep]
        if (currentStep) {
          currentStep.status = STEP_STATUS.ERROR
        }
      }
      
      saveLocalMessages()
    }
    ElMessage.error('请求失败: ' + (err.message || '未知错误'))
  } finally {
    isSending.value = false
    currentAbortController = null
  }
}

// 监听消息变化，自动保存到本地存储
watch(messages, saveLocalMessages, { deep: true })
watch(history, saveLocalHistory, { deep: true })

onMounted(() => {
  // 加载本地存储的数据
  loadLocalMessages()
  loadLocalHistory()
  
  // 检查状态和获取最新数据
  checkVannaStatus()
  loadHistory()
  
  // 定期同步服务器数据
  setInterval(() => {
    loadHistory()
  }, 30000) // 每30秒同步一次
})
</script>

<style scoped>
.chat-page { height: calc(100vh - 112px); }
.card-header { display:flex; justify-content:space-between; align-items:center; }

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
  max-height: calc(100vh - 280px);
}

.empty-state { text-align: center; padding: 60px 20px; }
.example-questions { margin-top: 16px; }

.user-bubble { display:flex; gap:10px; align-items:flex-start; justify-content:flex-end; }
.ai-bubble { display:flex; gap:10px; align-items:flex-start; }
.ai-content { flex: 1; max-width: 90%; }

.bubble { padding: 12px 16px; border-radius: 12px; max-width: 100%; word-break: break-all; font-size: 14px; }
.user-text-wrapper {
  position: relative;
  display: inline-block;
}

.user-text { 
  background: #409EFF; 
  color: #fff; 
  border-radius: 12px 2px 12px 12px; 
  box-shadow: 0 2px 8px rgba(64,158,255,0.2); 
  position: relative;
  transition: all 0.2s ease;
  padding: 12px 16px;
}

.user-text:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64,158,255,0.3);
}

.bubble-actions {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: rgba(0,0,0,0.8);
  border-radius: 8px;
  padding: 4px;
  display: flex;
  gap: 4px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(8px);
  transition: all 0.2s ease;
  z-index: 10;
  min-width: 120px;
  justify-content: center;
}

.user-text-wrapper:hover .bubble-actions {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.bubble-actions .el-button {
  color: #fff;
  padding: 6px 8px;
  min-height: auto;
  border: none;
  background: transparent;
  font-size: 14px;
  transition: all 0.2s ease;
}

.bubble-actions .el-button:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #409EFF;
  transform: scale(1.05);
}
.ai-loading { background: #f0f2f5; color: #909399; display: inline-flex; align-items: center; gap: 8px; }

.ai-footer { margin-top: 8px; padding-left: 42px; display: flex; gap: 12px; }

/* 步骤展示 */
.steps-container { margin-bottom: 12px; border-radius: 8px; overflow: hidden; border: 1px solid #ebeef5; }
.steps-summary { color: #606266; font-size: 13px; display: flex; align-items: center; gap: 6px; }
:deep(.el-collapse-item__header) { height: 40px; padding: 0 12px; background: #fafafa; }
:deep(.el-collapse-item__content) { padding: 12px 20px 0; }
.step-title { font-size: 13px; }
.step-title.success { color: #67c23a; }
.step-title.error { color: #f56c6c; }

.ai-result-body { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); }

.sql-block { 
  background: #282c34; 
  border-radius: 8px; 
  padding: 12px; 
  margin-bottom: 12px; 
}

.data-block {
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 12px;
  border: 1px solid #e9ecef;
}

.data-content {
  padding: 12px;
}

.data-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.data-label {
  color: #abb2bf; 
  font-size: 12px; 
  font-weight: 600; 
  text-transform: uppercase; 
  letter-spacing: 0.5px; 
}
.sql-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.sql-label { color: #abb2bf; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.ai-error-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 专业产品级UI设计 */
.thinking-process {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 16px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.process-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.process-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.process-icon {
  color: #6366f1;
  font-size: 16px;
}

.process-title span {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
}

.detail-toggle {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.detail-toggle:hover {
  background: #f1f5f9;
}

.toggle-icon {
  margin-left: 4px;
  transition: transform 0.2s ease;
}

/* 横向步骤标签 - 文字紧凑版本 */
.process-steps-text {
  display: flex;
  padding: 8px 16px;
  gap: 4px;
  background: #fff;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: #e2e8f0 transparent;
  border-bottom: 1px solid #e2e8f0;
  align-items: center;
  flex-wrap: nowrap;
}

.process-steps-text::-webkit-scrollbar {
  height: 3px;
}

.process-steps-text::-webkit-scrollbar-track {
  background: transparent;
}

.process-steps-text::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 2px;
}

.process-step-text {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
  transition: all 0.2s ease;
  cursor: pointer;
}

.process-step-text.step-waiting {
  background: #f8fafc;
  border-color: #e2e8f0;
  color: #94a3b8;
}

.process-step-text.step-running {
  background: #dbeafe;
  border-color: #3b82f6;
  color: #1d4ed8;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.process-step-text.step-success {
  background: #f0fdf4;
  border-color: #22c55e;
  color: #16a34a;
}

.process-step-text.step-error {
  background: #fef2f2;
  border-color: #ef4444;
  color: #dc2626;
}

.process-step-text.step-skipped {
  background: #fefce8;
  border-color: #f59e0b;
  color: #d97706;
  opacity: 0.8;
}

.step-name-text {
  font-weight: 500;
  font-size: 11px;
}

.step-duration-text {
  font-weight: 400;
  font-size: 10px;
  opacity: 0.8;
}

.step-skipped-text {
  font-weight: 400;
  font-size: 10px;
  opacity: 0.8;
}

.step-separator {
  color: #94a3b8;
  font-size: 12px;
  margin: 0 2px;
  opacity: 0.6;
}

/* 横向步骤标签 - 紧凑版本（保留） */
.process-steps-compact {
  display: flex;
  padding: 8px 16px;
  gap: 4px;
  background: #fff;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: #e2e8f0 transparent;
  border-bottom: 1px solid #e2e8f0;
}

.process-steps-compact::-webkit-scrollbar {
  height: 3px;
}

.process-steps-compact::-webkit-scrollbar-track {
  background: transparent;
}

.process-steps-compact::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 2px;
}

.process-step-compact {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 50%;
  min-width: 20px;
  flex-shrink: 0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.process-step-compact.step-waiting {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.process-step-compact.step-running {
  background: #dbeafe;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.process-step-compact.step-success {
  background: #f0fdf4;
  border-color: #22c55e;
}

.process-step-compact.step-error {
  background: #fef2f2;
  border-color: #ef4444;
}

.process-step-compact.step-skipped {
  background: #fefce8;
  border-color: #f59e0b;
  opacity: 0.8;
}

.step-indicator-compact {
  width: 12px;
  height: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-indicator-compact .el-icon {
  font-size: 10px;
}

/* 思考过程说明 */
.thinking-process-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  margin-bottom: 8px;
  color: #0369a1;
  font-size: 12px;
}

.thinking-icon {
  color: #0284c7;
  font-size: 14px;
}

.thinking-text {
  font-size: 12px;
  color: #0369a1;
  line-height: 1.4;
}

/* 紧凑版本样式 */
.result-summary-compact {
  padding: 6px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  color: #64748b;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.sql-block-compact {
  background: #1e293b;
  border-radius: 6px;
  margin-bottom: 8px;
  border: 1px solid #334155;
}

.sql-header-compact {
  padding: 6px 12px;
  background: #334155;
  border-radius: 6px 6px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #475569;
}

.sql-label-compact {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 500;
}

.sql-content-compact {
  max-height: 120px;
  overflow-y: auto;
}

.sql-code-compact {
  margin: 0;
  padding: 8px 12px;
  background: transparent;
  color: #e2e8f0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 11px;
  line-height: 1.3;
  white-space: pre-wrap;
  word-break: break-all;
}

.data-block-compact {
  background: #f8fafc;
  border-radius: 6px;
  margin-bottom: 8px;
  border: 1px solid #e2e8f0;
}

.data-header-compact {
  padding: 6px 12px;
  background: #f1f5f9;
  border-radius: 6px 6px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
}

.data-label-compact {
  color: #64748b;
  font-size: 11px;
  font-weight: 500;
}

.data-content-compact {
  padding: 8px;
}

.data-content-compact :deep(.el-table) {
  font-size: 11px;
}

.data-content-compact :deep(.el-table th) {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  font-size: 11px;
  padding: 4px 6px;
}

.data-content-compact :deep(.el-table td) {
  padding: 4px 6px;
  font-size: 11px;
  line-height: 1.2;
}

.data-content-compact :deep(.el-table .cell) {
  padding: 0 6px;
  line-height: 1.2;
}

.sql-actions-compact {
  text-align: right;
  padding: 4px 12px;
  background: #334155;
  border-bottom: 1px solid #475569;
}

.data-actions-compact {
  text-align: right;
  padding: 4px 12px;
  background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
}

/* 原版本样式（保留用于错误状态） */
.process-steps {
  display: flex;
  padding: 16px 20px;
  gap: 8px;
  background: #fff;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: #e2e8f0 transparent;
}

.process-steps::-webkit-scrollbar {
  height: 4px;
}

.process-steps::-webkit-scrollbar-track {
  background: transparent;
}

.process-steps::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 2px;
}

.process-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  min-width: 0;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.process-step.step-waiting {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.process-step.step-running {
  background: #dbeafe;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.process-step.step-success {
  background: #f0fdf4;
  border-color: #22c55e;
}

.process-step.step-error {
  background: #fef2f2;
  border-color: #ef4444;
}

.process-step.step-skipped {
  background: #fefce8;
  border-color: #f59e0b;
  opacity: 0.8;
}

.step-indicator {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-waiting {
  color: #94a3b8;
  font-size: 14px;
}

.icon-running {
  color: #3b82f6;
  font-size: 14px;
}

.icon-success {
  color: #22c55e;
  font-size: 14px;
}

.icon-error {
  color: #ef4444;
  font-size: 14px;
}

.icon-skipped {
  color: #f59e0b;
  font-size: 14px;
}

.step-info {
  min-width: 0;
  flex: 1;
}

.step-name {
  font-weight: 500;
  color: #1e293b;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.step-time {
  color: #64748b;
  font-size: 10px;
  margin-top: 2px;
}

/* 详细信息展开区域 */
.process-details {
  background: #fff;
  border-top: 1px solid #e2e8f0;
}

.details-content {
  padding: 16px 20px;
}

.detail-item {
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.detail-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.detail-item:first-child {
  padding-top: 0;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.detail-status {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.status-success {
  color: #22c55e;
  font-size: 16px;
}

.status-error {
  color: #ef4444;
  font-size: 16px;
}

.status-waiting {
  color: #94a3b8;
  font-size: 16px;
}

.detail-title {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 13px;
}

.detail-desc {
  color: #64748b;
  font-size: 12px;
}

.detail-duration {
  color: #94a3b8;
  font-size: 11px;
  align-self: flex-start;
}

.detail-content {
  margin-top: 8px;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 6px;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
  border-left: 3px solid #6366f1;
}

/* 专业的结果展示 */
.result-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  color: #1e40af;
  font-size: 13px;
  margin-bottom: 16px;
  font-weight: 500;
}

.result-summary strong {
  color: #1e40af;
  font-weight: 700;
}

/* 专业的SQL和数据展示 */
.sql-block, .data-block {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 16px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.sql-content, .data-content {
  padding: 20px;
}

.sql-actions, .data-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.sql-label, .data-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sql-code {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 6px;
  font-family: 'SFMono-Regular', 'Consolas', 'Liberation Mono', 'Menlo', monospace;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  margin: 0;
  border: none;
}

.no-data {
  padding: 24px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

/* 专业的AI气泡设计 */
.ai-bubble {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.ai-content {
  flex: 1;
  max-width: 85%;
}

.ai-result-body {
  background: #fff;
  border-radius: 12px;
  padding: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

/* Element Plus 样式优化 */
:deep(.el-collapse) {
  border: none;
}

:deep(.el-collapse-item__header) {
  height: 48px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
  color: #1e293b;
  font-weight: 500;
}

:deep(.el-collapse-item__content) {
  padding: 0;
}

:deep(.el-table) {
  font-size: 12px;
  border-radius: 6px;
  overflow: hidden;
}

:deep(.el-table th) {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
}

:deep(.el-table td) {
  border-bottom: 1px solid #f1f5f9;
}

:deep(.el-button--small) {
  font-size: 12px;
  border-radius: 6px;
}

:deep(.el-tag--small) {
  font-size: 10px;
  border-radius: 4px;
  padding: 2px 6px;
}

:deep(.el-alert) {
  border-radius: 6px;
  border: none;
}

.ai-cancelled-body {
  padding: 12px 16px;
}

/* 确保取消提示显示为绿色 */
.ai-cancelled-body .el-alert--success {
  background-color: #f0f9ff;
  border-color: #67c23a;
}

.ai-cancelled-body .el-alert--success .el-alert__icon {
  color: #67c23a;
}

.ai-cancelled-body .el-alert--success .el-alert__title {
  color: #67c23a;
}

.ai-cancelled-body .el-alert--success .el-alert__description {
  color: #606266;
}

.sql-block {
  margin-bottom: 12px;
}

.sql-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sql-actions {
  display: flex;
  justify-content: flex-end;
  padding: 0 8px;
}

.sql-label {
  font-weight: 500;
  color: #606266;
  font-size: 13px;
}

.sql-code {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #333;
  overflow-x: auto;
}

.result-summary { color: #67c23a; margin-bottom: 10px; font-size: 14px; display: flex; align-items: center; gap: 6px; border-bottom: 1px solid #f0f2f5; padding-bottom: 10px; }
.result-table { max-height: 350px; overflow: auto; border-radius: 4px; border: 1px solid #f0f2f5; }
.no-data { color: #909399; font-size: 14px; padding: 20px; text-align: center; background: #fafafa; border-radius: 8px; }

.analysis-report {
  margin-top: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e9ecef;
}

.analysis-content {
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  background: white;
  padding: 16px;
  border-radius: 6px;
  border-left: 4px solid #409EFF;
}

.analysis-content strong {
  color: #1890ff;
  font-weight: 600;
}

.analysis-content h1, .analysis-content h2, .analysis-content h3 {
  color: #333;
  margin: 16px 0 8px 0;
}

.analysis-content h1 {
  font-size: 20px;
  border-bottom: 2px solid #409EFF;
  padding-bottom: 8px;
}

.analysis-content h2 {
  font-size: 18px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 4px;
}

.analysis-content h3 {
  font-size: 16px;
}

.analysis-content p {
  margin: 8px 0;
}

.analysis-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  background: white;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.analysis-table td {
  padding: 12px 16px;
  border: 1px solid #e0e0e0;
  text-align: left;
  vertical-align: top;
}

.analysis-table tr:nth-child(even) {
  background: #f8f9fa;
}

.analysis-table tr:hover {
  background: #f0f7ff;
}

/* 代码块样式 */
.code-block {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 16px;
  margin: 16px 0;
  overflow-x: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.4;
}

.code-block code {
  background: none;
  padding: 0;
  border: none;
  color: #333;
}

.inline-code {
  background: #f1f3f4;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: #d73a49;
}

/* 引用样式 */
blockquote {
  border-left: 4px solid #409EFF;
  margin: 16px 0;
  padding: 8px 16px;
  background: #f8f9fa;
  color: #666;
  font-style: italic;
}

/* 列表样式 */
.analysis-content ul {
  margin: 8px 0;
  padding-left: 20px;
}

.analysis-content li {
  margin: 4px 0;
  line-height: 1.5;
}

/* 标题样式优化 */
.analysis-content h1, .analysis-content h2, .analysis-content h3, .analysis-content h4 {
  margin: 20px 0 12px 0;
  line-height: 1.3;
}

.analysis-content h1 {
  font-size: 22px;
  border-bottom: 2px solid #409EFF;
  padding-bottom: 8px;
  color: #1a1a1a;
}

.analysis-content h2 {
  font-size: 20px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 6px;
  color: #333;
}

.analysis-content h3 {
  font-size: 18px;
  color: #444;
}

.analysis-content h4 {
  font-size: 16px;
  color: #555;
}

.analysis-content br {
  margin-bottom: 8px;
}

/* 基础Markdown样式 */
.markdown-table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
}

.markdown-table th,
.markdown-table td {
  border: 1px solid #ddd;
  padding: 8px 12px;
  text-align: left;
}

.markdown-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.markdown-table tr:nth-child(even) {
  background: #f9f9f9;
}

.markdown-table tr:hover {
  background: #f0f0f0;
}

.markdown-code {
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 12px;
  margin: 16px 0;
  overflow-x: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.4;
  color: #333;
}

.markdown-code code {
  background: none;
  padding: 0;
  border: none;
  color: inherit;
}

.markdown-quote {
  border-left: 4px solid #ddd;
  margin: 16px 0;
  padding: 0 12px;
  color: #666;
  background: #f9f9f9;
}

.markdown-quote p {
  margin: 8px 0;
}

/* 标题样式 */
.analysis-content h1,
.analysis-content h2,
.analysis-content h3,
.analysis-content h4,
.analysis-content h5,
.analysis-content h6 {
  margin: 20px 0 12px 0;
  font-weight: 600;
  color: #333;
}

.analysis-content h1 { font-size: 24px; }
.analysis-content h2 { font-size: 20px; }
.analysis-content h3 { font-size: 18px; }
.analysis-content h4 { font-size: 16px; }
.analysis-content h5 { font-size: 14px; }
.analysis-content h6 { font-size: 12px; }

/* 列表样式 */
.analysis-content ul,
.analysis-content ol {
  margin: 12px 0;
  padding-left: 24px;
}

.analysis-content li {
  margin: 4px 0;
  line-height: 1.5;
}

/* 内联代码样式 */
.analysis-content :not(pre) > code {
  background: #f5f5f5;
  color: #d73a49;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
}

/* 链接样式 */
.analysis-content a {
  color: #0366d6;
  text-decoration: none;
}

.analysis-content a:hover {
  text-decoration: underline;
}

.input-area { padding-top: 16px; border-top: 1px solid #f0f0f0; }

.history-list { display:flex; flex-direction:column; gap:8px; overflow-y:auto; max-height: calc(100vh - 220px); }
.history-item { display:flex; gap:8px; padding:8px; border-radius:6px; cursor:pointer; transition:background 0.2s; align-items:flex-start; }
.history-item:hover { background: #f5f7ff; }
.history-content { flex:1; min-width:0; }
.history-q { font-size:13px; color:#262626; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.history-time { font-size:11px; color:#aaa; margin-top:2px; }

/* 取消按钮样式 */
.cancel-mode {
  background-color: #f56c6c !important;
  border-color: #f56c6c !important;
  animation: pulse 1.5s infinite;
}

.cancel-mode:hover {
  background-color: #e64242 !important;
  border-color: #e64242 !important;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(245, 108, 108, 0); }
  100% { box-shadow: 0 0 0 0 rgba(245, 108, 108, 0); }
}

.rotating-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
