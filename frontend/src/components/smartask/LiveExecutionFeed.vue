<template>
  <section v-if="displaySteps.length" class="sa-lite-flow">
    <div class="sa-lite-head">
      <span class="sa-lite-badge">{{ mode === 'completed' ? '执行完成' : '实时执行' }}</span>
      <span class="sa-lite-title">{{ mode === 'completed' ? '本轮流程已完成' : '正在按流程推进' }}</span>
      <span v-if="feedElapsedLabel" class="sa-lite-elapsed">{{ feedElapsedLabel }}</span>
    </div>

    <ol class="sa-lite-steps">
      <li
        v-for="(step, index) in displaySteps"
        :key="step.key"
        class="sa-lite-step"
        :class="{ latest: index === compactSteps.length - 1, running: step.status === 'running' }"
      >
        <span class="sa-lite-marker" :class="step.status">
          <span v-if="step.status === 'running'" class="sa-lite-spinner"></span>
          <span v-else-if="step.status === 'success' || step.status === 'completed'">✓</span>
          <span v-else>{{ index + 1 }}</span>
        </span>
        <span v-if="index !== displaySteps.length - 1" class="sa-lite-line"></span>

        <div class="sa-lite-copy">
          <div class="sa-lite-step-top">
            <span class="sa-lite-step-title">{{ step.title }}</span>
            <span class="sa-lite-step-state">{{ step.stateText }}</span>
          </div>
          <div class="sa-lite-step-desc">{{ step.description }}</div>

          <div v-if="step.showThought && activeThoughtLines.length" ref="thoughtRef" class="sa-lite-thought">
            <div class="sa-lite-thought-label">{{ activeThoughtLabel }}</div>
            <div class="sa-lite-print-lines">
              <div
                v-for="(line, lineIndex) in activeThoughtLines"
                :key="`${lineIndex}-${line}`"
                class="sa-lite-print-line"
                :class="{ latest: lineIndex === activeThoughtLines.length - 1 }"
              >
                <span class="sa-lite-print-dot"></span>
                <TypewriterLine
                  v-if="lineIndex === activeThoughtLines.length - 1"
                  :text="line"
                  :speed="28"
                />
                <span v-else>{{ line }}</span>
              </div>
            </div>
          </div>
        </div>
      </li>
    </ol>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import TypewriterLine from './TypewriterLine.vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => [],
  },
  maxItems: {
    type: Number,
    default: 6,
  },
  mode: {
    type: String,
    default: 'live',
  },
  elapsedLabel: {
    type: String,
    default: '',
  },
})

const clockNow = ref(Date.now())
const thoughtRef = ref(null)
const clockTimer = setInterval(() => {
  clockNow.value = Date.now()
}, 1000)
let thoughtScrollTimer = null

const formatDuration = (duration) => {
  const value = Number(duration)
  if (!Number.isFinite(value) || value <= 0) return ''
  const totalSeconds = Math.max(1, Math.round(value / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const remain = totalSeconds % 60
  if (minutes > 0) return `${minutes}m ${remain}s`
  return `${totalSeconds}s`
}

const feedElapsedLabel = computed(() => {
  const starts = (props.logs || [])
    .map(log => Number(log?.startedAtMs))
    .filter(value => Number.isFinite(value) && value > 0)
  if (starts.length > 0) return formatDuration(clockNow.value - Math.min(...starts))
  return props.elapsedLabel || ''
})

const stageMeta = {
  confirm: {
    order: 0,
    title: '确认口径',
    done: '已确认',
    running: '待确认',
    description: '已收到业务口径确认，继续推进后续查询。',
  },
  route: {
    order: 1,
    title: '理解问题',
    done: '已完成',
    running: '执行中',
    description: '识别问题意图，并选择可用数据范围。',
  },
  dataset: {
    order: 2,
    title: '准备数据',
    done: '已完成',
    running: '加载中',
    description: '读取字段字典、样例 SQL 和数据集上下文。',
  },
  sql: {
    order: 3,
    title: '生成 SQL',
    done: '已生成',
    running: '生成中',
    description: '按业务口径生成只读查询语句。',
  },
  review: {
    order: 4,
    title: '复核 SQL',
    done: '已通过',
    running: '复核中',
    description: '检查字段、过滤条件、统计口径和只读安全。',
  },
  execute: {
    order: 5,
    title: '执行查询',
    done: '已返回',
    running: '查询中',
    description: '提交 SQL 并等待数据源返回结果。',
  },
  report: {
    order: 6,
    title: '整理结果',
    done: '已完成',
    running: '整理中',
    description: '整理指标、图表和分析结论。',
  },
}

const classifyStage = (log = {}) => {
  const text = `${log?.key || ''} ${log?.title || ''} ${log?.summary || ''} ${log?.kind || ''} ${log?.toolType || ''}`
  if (/确认|confirmation|boss-confirm/i.test(text)) return 'confirm'
  if (/执行\s*SQL|SQL\s*执行|查询执行|execute/i.test(text)) return 'execute'
  if (/校验|复核|review|agent3/i.test(text)) return 'review'
  if (/生成\s*SQL|继续生成|模型生成|agent2/i.test(text)) return 'sql'
  if (/加载|数据集上下文|字段字典|Golden SQL|dataset/i.test(text)) return 'dataset'
  if (/报告|分析结论|指标|图表|fact|report|核对/i.test(text)) return 'report'
  if (/理解|路由|问题路径|route|agent1/i.test(text)) return 'route'
  return ''
}

const normalizeStatus = (status) => {
  if (status === 'completed') return 'success'
  if (['success', 'running', 'warning', 'error', 'pending'].includes(status)) return status
  return 'success'
}

const latestLog = computed(() => (props.logs || [])[props.logs.length - 1] || null)

const activeThoughtLines = computed(() => {
  const log = latestLog.value
  const liveLines = Array.isArray(log?.liveThoughtLines) ? log.liveThoughtLines.filter(Boolean) : []
  const sourceLines = liveLines.length ? liveLines : [log?.streamText || log?.pulseText || '']
  return uniquePreviewLines(sourceLines.map(line => toSafeProgressSnippet(line, log))).slice(-5)
})

const activeThoughtLabel = computed(() => {
  const source = latestLog.value?.liveThoughtSource
  if (source === 'llm-reasoning') return '实时推理进度'
  if (source === 'llm-stream') return '实时生成进度'
  return '执行摘要'
})

const toSafeProgressSnippet = (value, log = {}) => {
  const text = String(value || '').trim()
  if (!text) return ''
  if (/^SQL片段：/i.test(text)) {
    return text.replace(/\s+/g, ' ').slice(0, 120)
  }
  if (/<\/?think>|```|^\s*[{[]|"\s*sql\s*"|dataset_id|option_id|score_hint|WITH\s+|SELECT\s+|FROM\s+/i.test(text)) {
    if (/理解|路由|口径|agent1/i.test(`${log?.key || ''} ${log?.title || ''}`)) {
      return '正在识别问题意图，并比较候选数据范围。'
    }
    if (/agent3|复核|校验/i.test(`${log?.key || ''} ${log?.title || ''}`)) {
      return '模型正在复核 SQL 口径，完整 SQL 已放到右侧详情。'
    }
    if (/agent2|生成|SQL/i.test(`${log?.key || ''} ${log?.title || ''}`)) {
      return '模型正在生成 SQL，完整语句已放到右侧详情。'
    }
    return '正在接收模型返回内容，完整内容已放到右侧详情。'
  }
  return text
    .replace(/<\/?think>/gi, '')
    .replace(/\s+/g, ' ')
    .slice(0, 96)
}

const uniquePreviewLines = (lines = []) => Array.from(new Set(
  lines.map(line => String(line || '').trim()).filter(Boolean),
))

const compactSteps = computed(() => {
  const grouped = new Map()

  ;(props.logs || []).forEach((log) => {
    const stage = classifyStage(log)
    if (!stage || !stageMeta[stage]) return

    const meta = stageMeta[stage]
    const status = normalizeStatus(log?.status)
    const existing = grouped.get(stage)
    const description = status === 'running'
      ? (String(log?.summary || '').trim() || meta.description)
      : meta.description

    grouped.set(stage, {
      key: stage,
      order: meta.order,
      title: meta.title,
      description,
      status,
      stateText: status === 'running'
        ? meta.running
        : status === 'warning'
          ? '待确认'
          : status === 'error'
            ? '异常'
            : meta.done,
      showThought: false,
      latestAt: Number(log?.startedAtMs || 0) || Date.now(),
      originalLog: log,
      existed: Boolean(existing),
    })
  })

  const steps = Array.from(grouped.values())
    .sort((left, right) => left.order - right.order)
    .slice(0, Math.max(Number(props.maxItems) || 6, 1))

  const runningIndex = steps.findIndex(step => step.status === 'running')
  const thoughtIndex = runningIndex >= 0 ? runningIndex : (props.mode === 'live' ? steps.length - 1 : -1)
  if (thoughtIndex >= 0 && steps[thoughtIndex]) {
    steps[thoughtIndex] = { ...steps[thoughtIndex], showThought: props.mode === 'live' }
  }
  return steps
})

const displaySteps = computed(() => {
  if (compactSteps.value.length) return compactSteps.value
  if (props.mode !== 'live') return []
  return [
    {
      key: 'boot',
      title: '启动问数',
      description: '正在连接后端实时执行链路。',
      status: 'running',
      stateText: '执行中',
      showThought: true,
    },
  ]
})

const clearThoughtScrollTimer = () => {
  if (thoughtScrollTimer) {
    clearInterval(thoughtScrollTimer)
    thoughtScrollTimer = null
  }
}

const scrollThoughtToBottom = () => nextTick(() => {
  const el = Array.isArray(thoughtRef.value)
    ? thoughtRef.value[thoughtRef.value.length - 1]
    : thoughtRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
})

watch(
  () => [props.mode, activeThoughtLines.value.join('|')],
  () => {
    clearThoughtScrollTimer()
    if (props.mode !== 'live' || !activeThoughtLines.value.length) return
    scrollThoughtToBottom()
    thoughtScrollTimer = setInterval(scrollThoughtToBottom, 300)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  clearInterval(clockTimer)
  clearThoughtScrollTimer()
})
</script>

<style scoped>
.sa-lite-flow {
  width: 100%;
  padding: 6px 2px 2px;
  color: #1d2129;
}

.sa-lite-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.sa-lite-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  background: #eef4ff;
  color: #165dff;
  font-size: 11px;
  font-weight: 700;
}

.sa-lite-title {
  font-size: 12px;
  color: #4e5969;
}

.sa-lite-elapsed {
  font-size: 11px;
  color: #86909c;
}

.sa-lite-steps {
  list-style: none;
  margin: 0;
  padding: 0;
}

.sa-lite-step {
  position: relative;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  column-gap: 8px;
  min-height: 46px;
  padding-bottom: 8px;
}

.sa-lite-marker {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-top: 2px;
  border-radius: 50%;
  background: #f2f3f5;
  color: #86909c;
  font-size: 10px;
  font-weight: 800;
}

.sa-lite-marker.success,
.sa-lite-marker.completed {
  background: #e8ffea;
  color: #00a63e;
}

.sa-lite-marker.running {
  background: #e8f3ff;
  color: #165dff;
}

.sa-lite-marker.warning {
  background: #fff7e8;
  color: #ff7d00;
}

.sa-lite-marker.error {
  background: #fff1f0;
  color: #f53f3f;
}

.sa-lite-spinner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid rgba(22, 93, 255, 0.2);
  border-top-color: #165dff;
  animation: sa-lite-spin 0.9s linear infinite;
}

.sa-lite-line {
  position: absolute;
  left: 8px;
  top: 24px;
  bottom: 0;
  width: 1px;
  background: #e5e6eb;
}

.sa-lite-copy {
  min-width: 0;
  padding-bottom: 2px;
}

.sa-lite-step-top {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 20px;
}

.sa-lite-step-title {
  font-size: 13px;
  font-weight: 700;
  color: #1d2129;
}

.sa-lite-step-state {
  font-size: 11px;
  color: #86909c;
}

.sa-lite-step-desc {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.55;
  color: #667085;
}

.sa-lite-thought {
  margin-top: 6px;
  padding: 6px 8px;
  border-radius: 8px;
  background: linear-gradient(180deg, #fbfcff 0%, #f7f9fc 100%);
  border: 1px solid rgba(229, 233, 242, 0.78);
  color: #86909c;
  font-size: 10px;
  line-height: 1.55;
  white-space: normal;
  max-height: 88px;
  overflow: auto;
}

.sa-lite-thought-label {
  display: block;
  margin-bottom: 3px;
  color: #b0b8c4;
  font-size: 9px;
  font-weight: 600;
}

.sa-lite-print-lines {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sa-lite-print-line {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  color: #9aa3b2;
}

.sa-lite-print-line.latest {
  color: #7a8494;
}

.sa-lite-print-dot {
  width: 3px;
  height: 3px;
  margin-top: 6px;
  border-radius: 50%;
  background: #c7ced8;
  flex-shrink: 0;
}

.sa-lite-print-line.latest .sa-lite-print-dot {
  background: #8aa8ff;
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.05);
}

.sa-lite-step.latest .sa-lite-step-title {
  color: #165dff;
}

@keyframes sa-lite-spin {
  to { transform: rotate(360deg); }
}
</style>
