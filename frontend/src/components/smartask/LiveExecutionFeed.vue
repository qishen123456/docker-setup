<template>
  <div v-if="normalizedLogs.length" class="sa-live-feed">
    <div class="sa-live-feed-head">
      <div class="sa-live-feed-badge">{{ mode === 'completed' ? '执行回放' : '实时执行' }}</div>
      <div class="sa-live-feed-title">
        {{ mode === 'completed' ? '本轮执行轨迹已收束完成' : '正在持续输出最新执行内容' }}
      </div>
      <div v-if="elapsedLabel" class="sa-live-feed-elapsed">已处理 {{ elapsedLabel }}</div>
      <div class="sa-live-feed-count">已记录 {{ totalCount }} 个执行节点</div>
    </div>

    <div v-if="latestLog" class="sa-live-current">
      <span class="sa-live-current-label">{{ mode === 'completed' ? '最终节点' : '最新进展' }}</span>
      <span class="sa-live-current-text">{{ latestLog.title }}</span>
    </div>

    <div v-if="isReportPending" class="sa-live-report-pending">
      <div class="sa-live-report-pending-badge">报告生成中</div>
      <div class="sa-live-report-pending-copy">
        <div class="sa-live-report-pending-title">正在整理结果摘要、分析结论和最终报告</div>
        <div class="sa-live-report-pending-desc">
          当前不是停住了，而是在等待模型完成最后一段结果归纳与报告输出。
        </div>
      </div>
      <div v-if="elapsedLabel" class="sa-live-report-pending-elapsed">已等待 {{ elapsedLabel }}</div>
    </div>

    <div class="sa-live-stream">
      <div
        v-for="(log, index) in normalizedLogs"
        :key="log.key || index"
        class="sa-live-item"
        :class="{
          latest: index === normalizedLogs.length - 1,
          running: log.status === 'running',
          archived: index < normalizedLogs.length - 2
        }"
      >
        <div class="sa-live-rail">
          <span class="sa-live-dot" :class="log.status"></span>
          <span v-if="index !== normalizedLogs.length - 1" class="sa-live-line"></span>
        </div>

        <div class="sa-live-copy">
          <div class="sa-live-top">
            <span class="sa-live-item-title">{{ log.title }}</span>
            <div class="sa-live-meta">
              <span v-if="log.timeLabel" class="sa-live-time">{{ log.timeLabel }}</span>
              <span v-if="log.durationLabel" class="sa-live-duration">{{ log.durationLabel }}</span>
              <span class="sa-live-status" :class="log.status">{{ log.statusText }}</span>
            </div>
          </div>
          <div v-if="log.summaryLine" class="sa-live-summary">{{ log.summaryLine }}</div>
          <div v-if="log.showThought && log.thoughtLines?.length" class="sa-live-thought">
            <div class="sa-live-thought-label">思考过程</div>
            <div v-for="(line, thoughtIndex) in log.thoughtLines" :key="thoughtIndex" class="sa-live-thought-line">
              {{ line }}
            </div>
          </div>
          <div v-for="(line, lineIndex) in log.conciseDetailLines" :key="lineIndex" class="sa-live-line-text">
            {{ line }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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

const statusTextMap = {
  success: '已完成',
  completed: '已完成',
  running: '执行中',
  pending: '等待中',
  warning: '待确认',
  error: '异常',
}

const totalCount = computed(() => (props.logs || []).length)

const normalizedLogs = computed(() => {
  const source = (props.logs || []).slice(-props.maxItems)
  return source.map((log, index) => {
    const status = log?.status || 'pending'
    const isLatest = index === source.length - 1
    const thoughtLines = Array.isArray(log?.thoughtLines)
      ? log.thoughtLines.filter(Boolean).slice(0, 3)
      : String(log?.thought || log?.summary || '')
          .split(/\n+/)
          .map(item => item.trim())
          .filter(Boolean)
          .slice(0, 2)
    const detailLines = Array.isArray(log?.detailLines)
      ? log.detailLines.filter(Boolean).slice(0, status === 'running' ? 4 : status === 'success' ? 2 : 3)
      : []
    const summaryLine = String(log?.summary || detailLines[0] || '').trim()
    const conciseDetailLines = (isLatest ? detailLines : detailLines.slice(0, 1))
      .filter(Boolean)
      .filter(line => line !== summaryLine)
      .slice(0, isLatest ? 2 : 1)

    return {
      key: log?.key,
      title: log?.title || log?.summary || '执行节点',
      summaryLine,
      thoughtLines,
      conciseDetailLines,
      showThought: isLatest && status !== 'success',
      kind: log?.kind || '',
      toolType: log?.toolType || '',
      timeLabel: log?.timeLabel || log?.time || '',
      durationLabel: log?.durationLabel || (log?.duration ? `${log.duration} ms` : ''),
      status,
      statusText:
        status === 'running' && /report/i.test(`${log?.toolType || ''} ${log?.kind || ''}`)
          ? '报告生成中'
          : (statusTextMap[status] || '已完成'),
    }
  })
})

const latestLog = computed(() => normalizedLogs.value[normalizedLogs.value.length - 1] || null)
const isReportPending = computed(() => {
  const log = latestLog.value
  if (!log || props.mode === 'completed') return false
  return log.status === 'running' && /报告|report/i.test(`${log.title || ''} ${log.toolType || ''} ${log.kind || ''}`)
})
</script>

<style scoped>
.sa-live-feed {
  width: 100%;
  padding: 2px 0 4px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sa-live-feed-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.sa-live-feed-badge {
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: #edf4ff;
  color: #165dff;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.sa-live-feed-title {
  font-size: 12px;
  color: #4e5969;
  line-height: 1.55;
}

.sa-live-feed-count {
  font-size: 10px;
  color: #86909c;
}

.sa-live-feed-elapsed {
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f7f8fa;
  color: #4e5969;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}

.sa-live-current {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 11px;
  background: linear-gradient(180deg, #f8fbff 0%, #f1f7ff 100%);
  border: 1px solid rgba(22, 93, 255, 0.1);
}

.sa-live-current-label {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  color: #165dff;
}

.sa-live-current-text {
  font-size: 12px;
  color: #1d2129;
  line-height: 1.55;
}

.sa-live-report-pending {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(22, 93, 255, 0.16);
  background: linear-gradient(135deg, rgba(237, 244, 255, 0.98) 0%, rgba(247, 250, 255, 0.98) 52%, rgba(255, 255, 255, 0.98) 100%);
  box-shadow: 0 12px 28px rgba(22, 93, 255, 0.08);
}

.sa-live-report-pending-badge {
  flex-shrink: 0;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #165dff;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  box-shadow: 0 8px 18px rgba(22, 93, 255, 0.2);
}

.sa-live-report-pending-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sa-live-report-pending-title {
  font-size: 13px;
  font-weight: 700;
  color: #1d2129;
  line-height: 1.5;
}

.sa-live-report-pending-desc {
  font-size: 12px;
  color: #4e5969;
  line-height: 1.65;
}

.sa-live-report-pending-elapsed {
  flex-shrink: 0;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: #165dff;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.sa-live-stream {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sa-live-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  animation: sa-live-enter 0.24s ease;
}

.sa-live-item.archived {
  opacity: 0.7;
}

.sa-live-rail {
  width: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.sa-live-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #c9cdd4;
  margin-top: 6px;
}

.sa-live-dot.success,
.sa-live-dot.completed {
  background: #00b42a;
}

.sa-live-dot.running {
  background: #165dff;
  box-shadow: 0 0 0 6px rgba(22, 93, 255, 0.1);
  animation: sa-live-pulse 1.2s ease-in-out infinite;
}

.sa-live-dot.warning {
  background: #ff7d00;
}

.sa-live-dot.error {
  background: #f53f3f;
}

.sa-live-line {
  width: 1px;
  flex: 1;
  min-height: 34px;
  margin-top: 6px;
  background: linear-gradient(180deg, rgba(22, 93, 255, 0.18), rgba(22, 93, 255, 0.04));
}

.sa-live-copy {
  flex: 1;
  min-width: 0;
  padding: 11px 13px;
  border-radius: 13px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
  box-shadow: 0 7px 18px rgba(15, 23, 42, 0.035);
}

.sa-live-item.latest .sa-live-copy {
  border-color: rgba(22, 93, 255, 0.16);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 10px 22px rgba(22, 93, 255, 0.07);
}

.sa-live-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.sa-live-item-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1.55;
}

.sa-live-meta {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.sa-live-time,
.sa-live-duration {
  font-size: 10px;
  color: #86909c;
  line-height: 1;
  white-space: nowrap;
}

.sa-live-status {
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: #f2f3f5;
  color: #86909c;
  font-size: 10px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.sa-live-status.success,
.sa-live-status.completed {
  background: #e8ffea;
  color: #00b42a;
}

.sa-live-status.running {
  background: #e8f3ff;
  color: #165dff;
}

.sa-live-status.warning {
  background: #fff7e8;
  color: #ff7d00;
}

.sa-live-status.error {
  background: #fff1f0;
  color: #f53f3f;
}

.sa-live-summary {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.6;
  color: #1d2129;
}

.sa-live-thought {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f7f8fa;
  border: 1px solid rgba(229, 230, 235, 0.9);
}

.sa-live-thought-label {
  margin-bottom: 4px;
  font-size: 10px;
  font-weight: 700;
  color: #86909c;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.sa-live-thought-line {
  font-size: 11px;
  line-height: 1.6;
  color: #4e5969;
}

.sa-live-line-text {
  margin-top: 4px;
  font-size: 10px;
  line-height: 1.6;
  color: #86909c;
}

@keyframes sa-live-enter {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes sa-live-pulse {
  0%, 100% {
    box-shadow: 0 0 0 4px rgba(22, 93, 255, 0.08);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(22, 93, 255, 0.14);
  }
}

@media (max-width: 760px) {
  .sa-live-report-pending {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
