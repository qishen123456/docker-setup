<template>
  <div class="sa-timeline">
    <div v-if="logs.length === 0" class="sa-empty">
      <div class="sa-empty-icon" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
      <p>执行事件会在这里持续更新</p>
    </div>

    <div v-for="(log, i) in logs" :key="getNodeKey(log, i)" class="sa-log-node" :class="log.status">
      <span class="sa-node-marker" :class="log.status"></span>

      <div class="sa-node-main">
        <div class="sa-node-header" @click="$emit('toggle', i)">
          <span class="sa-node-arrow" :class="{ open: openState[i] }">▶</span>
          <span class="sa-node-icon" :class="iconClass(log)" aria-hidden="true"></span>
          <span class="sa-node-title">{{ log.title }}</span>
          <span v-if="log.status === 'running'" class="sa-spin">◌</span>
          <span class="sa-node-status" :class="log.status">{{ nodeStatusText(log) }}</span>
        </div>

        <transition name="sa-collapse">
          <div v-if="openState[i]" class="sa-node-body">
            <div class="sa-node-body-head">
              <span class="sa-node-body-label">{{ sectionLabel(log) }}</span>
            </div>

            <div v-if="log.summary && !isDurationLine(log.summary)" class="sa-node-summary">{{ log.summary }}</div>

            <div v-if="compactThought(log) && !latestLiveThought(log) && isThoughtVisible(log, i)" class="sa-node-thought">
              <span class="sa-node-thought-label">执行摘要</span>
              <p>{{ compactThought(log) }}</p>
            </div>

            <div v-if="latestLiveThought(log)" class="sa-node-live-thought">
              <div class="sa-node-live-head">
                <span class="sa-live-pulse-dot"></span>
                <span>{{ liveThoughtLabel(log) }}</span>
              </div>
              <div ref="liveLineRef" class="sa-node-live-line">
                <div
                  v-for="(line, lineIndex) in compactLiveThoughtLines(log)"
                  :key="`${lineIndex}-${line}`"
                  class="sa-node-live-check"
                  :class="{ latest: lineIndex === compactLiveThoughtLines(log).length - 1 }"
                >
                  <span class="sa-node-live-check-dot"></span>
                  <span>{{ line }}</span>
                </div>
              </div>
            </div>

            <div class="sa-log-steps">
              <div
                v-for="(line, lineIndex) in visibleDetailLines(log, i)"
                :key="`${getNodeKey(log, i)}-${lineIndex}`"
                class="sa-log-step"
              >
                <span class="sa-log-step-dot"></span>
                <span class="sa-log-step-text">{{ line }}</span>
              </div>

              <div v-if="hasPendingLines(log, i)" class="sa-log-step sa-log-step-printing">
                <span class="sa-log-step-dot"></span>
                <span class="sa-log-step-text">
                  正在整理更多细节
                  <span class="sa-print-cursor"></span>
                </span>
              </div>
            </div>

            <div v-if="isContentVisible(log, i)" class="sa-node-rich">
              <slot name="content" :log="log" :index="i"></slot>
            </div>

          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  openState: {
    type: Object,
    default: () => ({})
  }
})

defineEmits(['toggle'])

const revealState = reactive({})
const revealTimers = new Map()
const clockNow = ref(Date.now())
const liveLineRef = ref(null)
const clockTimer = setInterval(() => {
  clockNow.value = Date.now()
}, 1000)
let liveLineScrollTimer = null

const statusLabel = (status) => ({
  success: '已完成',
  running: '执行中',
  pending: '待执行',
  error: '异常',
  warning: '待确认'
}[status] || status)

const isCanceledLog = (log = {}) => /取消|停止|request-aborted|aborted|canceled|cancelled/i.test(
  `${log?.key || ''} ${log?.title || ''} ${log?.summary || ''}`,
)

const getNodeKey = (log, index) => log?.key || `${log?.title || 'node'}-${index}`

const detailLines = (log) => {
  const summaryKey = normalizeDisplayLine(log?.summary)
  const withoutSummaryDuplicate = (lines) => lines.filter(line => normalizeDisplayLine(line) !== summaryKey)
  if (Array.isArray(log?.detailLines) && log.detailLines.length > 0) {
    return uniqueDisplayLines(withoutSummaryDuplicate(log.detailLines)
      .map(item => String(item || '').trim())
      .filter(Boolean)
      .filter(line => !isDurationLine(line) && !isRedundantRealtimePrintLine(line)))
  }

  const lines = [`开始执行任务：${log?.title || '执行节点'}`]

  if (log?.detail) {
    lines.push(
      ...String(log.detail)
        .split(/\n+/)
        .map(item => item.trim())
        .filter(Boolean)
    )
  }

  if (log?.status === 'success') lines.push('当前节点执行完成。')
  if (log?.status === 'running') lines.push('当前节点仍在执行中。')
  if (log?.status === 'warning') lines.push('当前节点等待进一步确认。')
  if (log?.status === 'error') lines.push('当前节点执行失败，请查看错误信息。')

  return uniqueDisplayLines(lines.filter(line => !isDurationLine(line) && !isRedundantRealtimePrintLine(line)))
}

const isDurationLine = (line) => {
  const text = String(line || '')
    .trim()
    .replace(/^[•·\-\s]+/, '')
    .replace(/[。；;,.，、\s]+$/g, '')
  return /节点耗时|当前节点耗时|当前节点已运行|^已运行\s*[\dm.\s]+s?$|^耗时\s*[\dm.\s]+s?$/i.test(text)
}

const isRedundantRealtimePrintLine = (line) => {
  const text = normalizeDisplayLine(line)
  return text.includes('模型正在实时返回真实内容') && text.includes('逐段打印')
}

const normalizeDisplayLine = (line) => String(line || '')
  .trim()
  .replace(/\s+/g, ' ')
  .replace(/[。；;,.，、\s]+$/g, '')

const uniqueDisplayLines = (lines = []) => {
  const seen = new Set()
  return lines.filter((line) => {
    const key = normalizeDisplayLine(line)
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const iconClass = (log) => {
  const toolType = log?.toolType || ''
  if (toolType === 'sql') return 'sql'
  if (toolType === 'dataset') return 'dataset'
  if (toolType === 'report' || toolType === 'fact') return 'report'
  if (toolType === 'confirm') return 'confirm'
  if (toolType === 'python') return 'python'
  const text = `${log?.key || ''} ${log?.title || ''}`
  if (/sql|查询/i.test(text)) return 'sql'
  if (/数据表|数据集|schema/i.test(text)) return 'dataset'
  if (/结果|报告|分析|事实|计划/i.test(text)) return 'report'
  if (/确认|口径/i.test(text)) return 'confirm'
  if (/python|pandas/i.test(text)) return 'python'
  return 'default'
}

const sectionLabel = (log) => {
  if (log?.kind === 'report-stage') return '报告节点'
  if (log?.kind === 'fact-update') return '事实更新'
  if (log?.kind === 'confirmation') return '确认节点'
  return '执行记录'
}

const formatDuration = (duration) => {
  const value = Number(duration)
  if (!Number.isFinite(value) || value <= 0) return ''
  const totalSeconds = Math.max(1, Math.round(value / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const remain = totalSeconds % 60
  if (minutes > 0) return `${minutes}m ${remain}s`
  return `${totalSeconds}s`
}

const nodeDurationLabel = (log) => {
  const startedAtMs = Number(log?.startedAtMs)
  if (log?.status === 'running' && Number.isFinite(startedAtMs)) {
    return formatDuration(clockNow.value - startedAtMs)
  }
  return log?.durationLabel || log?.elapsedLabel || ''
}

const nodeStatusText = (log) => {
  const base = isCanceledLog(log) ? '已取消' : statusLabel(log?.status)
  const duration = nodeDurationLabel(log)
  if (!duration || log?.status === 'pending') return base
  return `${base} ${duration}`
}

const latestLiveThought = (log) => {
  if (log?.status !== 'running') return ''
  if (Array.isArray(log?.liveThoughtLines) && log.liveThoughtLines.length > 0) {
    return log.liveThoughtLines[log.liveThoughtLines.length - 1]
  }
  if (Array.isArray(log?.thoughtLines) && log.thoughtLines.length > 0 && log?.status === 'running') {
    return log.thoughtLines[log.thoughtLines.length - 1]
  }
  return ''
}

const isReportNode = (log = {}) => /报告|分析结论|经营分析|agent4/i.test(`${log?.key || ''} ${log?.title || ''}`)

const isJsonLike = (value) => {
  const text = String(value || '').trim()
  return text.startsWith('{') || text.startsWith('[') || /^```json/i.test(text)
}

const parseJsonPreview = (value) => {
  const text = String(value || '')
    .trim()
    .replace(/^```json\s*/i, '')
    .replace(/```$/i, '')
    .trim()
  try {
    return JSON.parse(text)
  } catch (error) {
    return null
  }
}

const structuredProgressPreview = (value, log = {}) => {
  const raw = String(value || '').trim()
  const scope = `${log?.key || ''} ${log?.title || ''} ${log?.summary || ''}`
  if (/^SQL片段：/i.test(raw)) {
    return raw.replace(/\s+/g, ' ').slice(0, 150)
  }
  if (/<\/?think>|dataset_id|option_id|score_hint|confirm_question|need_confirm/i.test(raw)) {
    if (/理解|路由|口径|agent1/i.test(scope)) return '正在识别问题意图，并比较候选数据范围。'
    if (/确认|confirm/i.test(scope)) return '正在整理需要确认的统计口径。'
    return '正在接收后端实时执行进度。'
  }
  if (/WITH\s+|SELECT\s+|FROM\s+/i.test(raw) || /生成.*SQL|SQL/i.test(scope)) {
    return /复核|校验|review|agent3/i.test(scope)
      ? '模型正在复核 SQL 口径，完整语句已放到下方详情。'
      : '模型正在生成 SQL，完整语句已放到下方详情。'
  }
  if (!isJsonLike(raw)) return ''

  const data = parseJsonPreview(raw)
  if (data?.need_confirm || data?.confirm_question || Array.isArray(data?.options)) {
    return '模型正在判断是否需要口径确认，确认项会整理成可读卡片。'
  }
  if (data?.sql) return '模型正在生成 SQL，完整语句已放到下方详情。'
  if (data?.analysis || data?.report || data?.conclusion) return '模型正在生成分析摘要，完整报告会在下方展示。'
  return '模型正在返回结构化结果，系统会整理成可读内容。'
}

const cleanupMarkdownPreview = (value) => String(value || '')
  .replace(/```[\s\S]*?```/g, ' ')
  .replace(/`([^`]+)`/g, '$1')
  .replace(/^#{1,6}\s*/gm, '')
  .replace(/\*\*([^*]+)\*\*/g, '$1')
  .replace(/^\s*[•*-]\s*/gm, '')
  .replace(/\s*->\s*/g, '：')
  .replace(/\s+/g, ' ')
  .trim()

const pickReportConclusion = (text) => {
  const cleaned = cleanupMarkdownPreview(text)
  const match = cleaned.match(/核心结论[:：]?\s*([^。！？\n]{8,120}[。！？]?)/)
  if (match?.[1]) return `报告摘要：${match[1].trim()}`
  const firstSentence = cleaned.split(/[。！？]/).find(item => item.trim().length >= 8)
  return firstSentence ? `报告摘要：${firstSentence.trim()}。` : cleaned
}

const compactPreview = (value, log = {}, limit = 120) => {
  const raw = String(value || '').trim()
  if (!raw) return ''
  const structured = structuredProgressPreview(raw, log)
  if (structured) return structured
  const text = isReportNode(log) ? pickReportConclusion(raw) : cleanupMarkdownPreview(raw)
  if (text.length <= limit) return text
  return `${text.slice(0, limit).replace(/[，、；：,.:\s]+$/, '')}...`
}

const compactThought = (log) => {
  if (log?.markdown && log?.status !== 'running') return ''
  return compactPreview(log?.thought, log, 112)
}

const compactLiveThoughtLines = (log) => {
  const lines = Array.isArray(log?.liveThoughtLines) && log.liveThoughtLines.length > 0
    ? log.liveThoughtLines
    : [latestLiveThought(log)]
  return Array.from(new Set(
    lines
      .map(line => compactPreview(line, log, 128))
      .filter(Boolean)
      .filter(line => line !== '模型正在实时返回真实内容，已切换为逐段打印。')
  )).slice(-4)
}

const liveThoughtLabel = (log) => {
  if (log?.liveThoughtSource === 'llm-reasoning') return '实时推理进度'
  if (log?.liveThoughtSource === 'llm-stream') return '实时生成进度'
  return '执行摘要'
}

const buildRevealSignature = (log) => {
  const lines = detailLines(log)
  return [
    log?.status || '',
    lines.length,
    log?.sql ? 'has-sql' : '',
    log?.markdown ? 'has-markdown' : '',
    log?.chartData ? 'has-chart' : '',
    Array.isArray(log?.tableRows) ? log.tableRows.length : 0,
    Array.isArray(log?.charts) ? log.charts.length : 0
  ].join('::')
}

const ensureRevealState = (key) => {
  if (!revealState[key]) {
    revealState[key] = {
      signature: '',
      thoughtVisible: false,
      visibleSteps: 0,
      contentVisible: false,
      initialized: false
    }
  }
  return revealState[key]
}

const clearNodeTimers = (key) => {
  const handles = revealTimers.get(key) || []
  handles.forEach((handle) => {
    clearTimeout(handle)
    clearInterval(handle)
  })
  revealTimers.delete(key)
}

const pushTimer = (key, handle) => {
  const current = revealTimers.get(key) || []
  current.push(handle)
  revealTimers.set(key, current)
}

const hasRichContent = (log) => {
  if (log?.sql) return true
  if (log?.markdown) return true
  if (Array.isArray(log?.tableRows) && log.tableRows.length > 0) return true
  if (Array.isArray(log?.charts) && log.charts.length > 0) return true
  if (Array.isArray(log?.tables) && log.tables.length > 0) return true
  if (Array.isArray(log?.codeBlocks) && log.codeBlocks.length > 0) return true
  if (log?.chartData) return true
  return false
}

const startReveal = (log, index) => {
  const key = getNodeKey(log, index)
  const state = ensureRevealState(key)
  const lines = detailLines(log)
  const rich = hasRichContent(log)

  clearNodeTimers(key)
  state.signature = buildRevealSignature(log)
  state.initialized = true
  state.thoughtVisible = !log?.thought
  state.visibleSteps = 0
  state.contentVisible = false

  if (log?.thought) {
    pushTimer(key, setTimeout(() => {
      state.thoughtVisible = true
    }, 120))
  }

  if (lines.length === 0) {
    pushTimer(key, setTimeout(() => {
      state.contentVisible = true
    }, log?.thought ? 240 : 120))
    return
  }

  let cursor = 0
  const revealNext = () => {
    cursor = Math.min(cursor + 1, lines.length)
    state.visibleSteps = cursor

    if (cursor >= lines.length) {
      clearNodeTimers(key)
      if (rich) {
        pushTimer(key, setTimeout(() => {
          state.contentVisible = true
        }, 140))
      } else {
        state.contentVisible = true
      }
    }
  }

  const starter = setTimeout(() => {
    revealNext()
    const interval = setInterval(() => {
      revealNext()
      if (cursor >= lines.length) {
        clearInterval(interval)
      }
    }, 180)
    pushTimer(key, interval)
  }, log?.thought ? 190 : 80)

  pushTimer(key, starter)
}

const syncRevealState = () => {
  const activeKeys = new Set()

  props.logs.forEach((log, index) => {
    const key = getNodeKey(log, index)
    activeKeys.add(key)
    const state = ensureRevealState(key)
    const signature = buildRevealSignature(log)

    if (props.openState[index]) {
      if (!state.initialized || state.signature !== signature) {
        startReveal(log, index)
      }
    } else {
      clearNodeTimers(key)
      state.signature = signature
      state.initialized = false
      state.thoughtVisible = true
      state.visibleSteps = detailLines(log).length
      state.contentVisible = true
    }
  })

  Object.keys(revealState).forEach((key) => {
    if (!activeKeys.has(key)) {
      clearNodeTimers(key)
      delete revealState[key]
    }
  })
}

const visibleDetailLines = (log, index) => {
  const key = getNodeKey(log, index)
  const state = ensureRevealState(key)
  return detailLines(log).slice(0, state.visibleSteps)
}

const hasPendingLines = (log, index) => {
  const key = getNodeKey(log, index)
  const state = ensureRevealState(key)
  return state.visibleSteps < detailLines(log).length
}

const isThoughtVisible = (log, index) => {
  const key = getNodeKey(log, index)
  return ensureRevealState(key).thoughtVisible
}

const isContentVisible = (log, index) => {
  const key = getNodeKey(log, index)
  return ensureRevealState(key).contentVisible
}

watch(
  () => props.logs.map((log, index) => ({
    key: getNodeKey(log, index),
    open: Boolean(props.openState[index]),
    signature: buildRevealSignature(log)
  })),
  syncRevealState,
  { deep: true, immediate: true }
)

const clearLiveLineScrollTimer = () => {
  if (liveLineScrollTimer) {
    clearInterval(liveLineScrollTimer)
    liveLineScrollTimer = null
  }
}

const scrollLiveLineToBottom = () => nextTick(() => {
  const el = Array.isArray(liveLineRef.value)
    ? liveLineRef.value[liveLineRef.value.length - 1]
    : liveLineRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
})

watch(
  () => props.logs.map(log => `${log?.status || ''}:${Array.isArray(log?.liveThoughtLines) ? log.liveThoughtLines.join('|') : ''}:${log?.pulseText || ''}:${log?.streamText || ''}`).join('||'),
  () => {
    clearLiveLineScrollTimer()
    scrollLiveLineToBottom()
    liveLineScrollTimer = setInterval(scrollLiveLineToBottom, 300)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  clearInterval(clockTimer)
  clearLiveLineScrollTimer()
  Array.from(revealTimers.keys()).forEach(clearNodeTimers)
})
</script>

<style scoped>
.sa-timeline {
  padding: 12px 13px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sa-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 46px 16px;
  color: var(--text-muted);
  text-align: center;
}

.sa-empty-icon {
  width: 40px;
  height: 40px;
  border-radius: 11px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: linear-gradient(180deg, #f5f9ff 0%, #ffffff 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  padding: 0 12px;
  margin-bottom: 9px;
}

.sa-empty-icon span {
  height: 2px;
  border-radius: 999px;
  background: rgba(22, 93, 255, 0.4);
}

.sa-empty-icon span:nth-child(1) { width: 70%; }
.sa-empty-icon span:nth-child(2) { width: 100%; }
.sa-empty-icon span:nth-child(3) { width: 55%; }

.sa-log-node {
  position: relative;
  display: flex;
  gap: 8px;
  padding-bottom: 1px;
}

.sa-log-node:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 7px;
  top: 16px;
  bottom: -16px;
  width: 1px;
  background: #e5e6eb;
}

.sa-node-marker {
  position: relative;
  z-index: 1;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  margin-top: 11px;
  flex-shrink: 0;
  background: #d9dde4;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #e5e6eb;
}

.sa-node-marker.success {
  background: #00b42a;
  box-shadow: 0 0 0 1px rgba(0, 180, 42, 0.16);
}

.sa-node-marker.running {
  background: #165dff;
  box-shadow: 0 0 0 1px rgba(22, 93, 255, 0.16);
}

.sa-node-marker.error {
  background: #f53f3f;
  box-shadow: 0 0 0 1px rgba(245, 63, 63, 0.16);
}

.sa-node-marker.warning {
  background: #ff7d00;
  box-shadow: 0 0 0 1px rgba(255, 125, 0, 0.16);
}

.sa-node-main {
  flex: 1;
  min-width: 0;
  padding-right: 1px;
}

.sa-node-header {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 0;
  cursor: pointer;
  background: transparent;
  transition: background 0.1s;
}

.sa-node-arrow {
  font-size: 12px;
  color: #86909c;
  transition: transform 0.2s;
  flex-shrink: 0;
}

.sa-node-arrow.open {
  transform: rotate(90deg);
}

.sa-node-icon {
  width: 15px;
  height: 15px;
  border-radius: 4px;
  background: linear-gradient(180deg, #eef4ff 0%, #dfe9ff 100%);
  border: 1px solid rgba(22, 93, 255, 0.14);
  position: relative;
  flex-shrink: 0;
}

.sa-node-icon::before,
.sa-node-icon::after {
  content: '';
  position: absolute;
  left: 3px;
  right: 3px;
  height: 1px;
  background: rgba(22, 93, 255, 0.46);
}

.sa-node-icon::before { top: 5px; }
.sa-node-icon::after { top: 9px; }

.sa-node-icon.dataset {
  background: linear-gradient(180deg, #ecfdf3 0%, #d9f7e7 100%);
  border-color: rgba(0, 180, 42, 0.16);
}

.sa-node-icon.dataset::before,
.sa-node-icon.dataset::after {
  background: rgba(0, 180, 42, 0.4);
}

.sa-node-icon.report {
  background: linear-gradient(180deg, #fff6e8 0%, #ffe9c7 100%);
  border-color: rgba(255, 125, 0, 0.18);
}

.sa-node-icon.report::before,
.sa-node-icon.report::after {
  background: rgba(255, 125, 0, 0.45);
}

.sa-node-icon.confirm {
  background: linear-gradient(180deg, #fff4f0 0%, #ffe0d6 100%);
  border-color: rgba(245, 63, 63, 0.16);
}

.sa-node-icon.confirm::before,
.sa-node-icon.confirm::after {
  background: rgba(245, 63, 63, 0.4);
}

.sa-node-icon.python {
  background: linear-gradient(180deg, #f4f1ff 0%, #e4dcff 100%);
  border-color: rgba(114, 46, 209, 0.16);
}

.sa-node-icon.python::before,
.sa-node-icon.python::after {
  background: rgba(114, 46, 209, 0.4);
}

.sa-node-title {
  flex: 1;
  font-size: 11px;
  font-weight: 500;
  color: #1d2129;
  line-height: 1.4;
}

.sa-node-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  justify-content: flex-end;
  min-width: 58px;
  padding: 0 1px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: 0.01em;
  font-variant-numeric: tabular-nums;
}

.sa-node-status::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.9;
}

.sa-node-status.success { color: #22a35a; }
.sa-node-status.running { color: #165dff; }
.sa-node-status.error { color: #f53f3f; }
.sa-node-status.pending { color: #86909c; }
.sa-node-status.warning { color: #ff7d00; }

.sa-spin {
  color: #165dff;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.sa-node-body {
  margin: 2px 0 0;
  padding: 9px 11px;
  background: #ffffff;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  box-shadow: 0 3px 12px rgba(15, 23, 42, 0.035);
}

.sa-node-body-head {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  margin-bottom: 7px;
}

.sa-node-body-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #86909c;
}

.sa-log-steps {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 7px;
}

.sa-node-summary {
  margin-bottom: 7px;
  font-size: 10px;
  line-height: 1.6;
  color: #1d2129;
}

.sa-node-thought {
  margin-bottom: 7px;
  padding: 7px 9px;
  border-radius: 8px;
  background: #fafbfc;
  border: 1px solid rgba(229, 230, 235, 0.9);
}

.sa-node-thought-label {
  display: inline-flex;
  margin-bottom: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #a0a7b2;
}

.sa-node-thought p {
  margin: 0;
  font-size: 10px;
  line-height: 1.55;
  color: #667085;
}

.sa-node-live-thought {
  margin: 0 0 8px;
  padding: 6px 8px;
  height: 92px;
  box-sizing: border-box;
  border-radius: 8px;
  border: 1px solid rgba(229, 233, 242, 0.74);
  background: linear-gradient(180deg, #fbfcff 0%, #f7f9fc 100%);
  overflow: hidden;
}

.sa-node-live-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #b0b8c4;
}

.sa-live-pulse-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #8aa8ff;
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.05);
  animation: saLivePulse 1.3s ease-in-out infinite;
}

.sa-node-live-line {
  height: 60px;
  overflow-y: auto;
  padding-right: 3px;
  white-space: normal;
  font-size: 10px;
  line-height: 1.55;
  color: #7a8494;
}

.sa-node-live-line::-webkit-scrollbar {
  width: 3px;
}

.sa-node-live-line::-webkit-scrollbar-thumb {
  background: #d8dee8;
  border-radius: 999px;
}

.sa-node-live-check {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-height: 18px;
  color: #86909c;
}

.sa-node-live-check.latest {
  color: #4e5969;
}

.sa-node-live-check-dot {
  width: 4px;
  height: 4px;
  margin-top: 6px;
  border-radius: 50%;
  background: #b8c2d0;
  flex-shrink: 0;
}

.sa-node-live-check.latest .sa-node-live-check-dot {
  background: #165dff;
  box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.06);
}

.sa-log-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.sa-log-step-dot {
  width: 6px;
  height: 6px;
  margin-top: 7px;
  border-radius: 50%;
  background: #165dff;
  flex-shrink: 0;
}

.sa-log-step-text {
  font-size: 10px;
  color: #4e5969;
  line-height: 1.6;
}

.sa-log-step-printing .sa-log-step-text {
  color: #86909c;
}

.sa-print-cursor {
  display: inline-flex;
  width: 7px;
  height: 12px;
  margin-left: 5px;
  border-right: 2px solid #165dff;
  animation: blink 0.9s steps(1, end) infinite;
  vertical-align: -2px;
}

@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

@keyframes saLivePulse {
  0%, 100% {
    transform: scale(0.9);
    opacity: 0.62;
  }
  50% {
    transform: scale(1.12);
    opacity: 1;
  }
}

.sa-node-rich {
  animation: none;
}

@keyframes revealContent {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.sa-log-time {
  font-size: 10px;
  color: #86909c;
  margin-top: 4px;
}

.sa-collapse-enter-active,
.sa-collapse-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.sa-collapse-enter-from,
.sa-collapse-leave-to {
  opacity: 0;
  max-height: 0;
}

.sa-collapse-enter-to,
.sa-collapse-leave-from {
  opacity: 1;
  max-height: 1200px;
}
</style>
