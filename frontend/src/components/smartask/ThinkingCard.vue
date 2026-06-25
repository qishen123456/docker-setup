<template>
  <div class="sa-thinking-card">
    <div class="sa-thinking-header" @click="$emit('toggle')">
      <span class="sa-arrow" :class="{ open: isOpen }">▶</span>
      <span class="sa-title">{{ loading ? '思考中' : '思考完成' }}</span>
      <span class="sa-header-count">{{ normalizedSteps.length }} 个节点</span>
      <span class="sa-check" :class="{ loading }">{{ loading ? '...' : '✓' }}</span>
    </div>
    <transition name="sa-collapse">
      <div v-if="isOpen" class="sa-thinking-body">
        <div v-for="(step, idx) in normalizedSteps" :key="idx" class="sa-thinking-step">
          <span class="sa-dot" :class="step.status"></span>
          <div class="sa-step-copy">
            <span class="sa-step-text">{{ step.text }}</span>
            <span v-if="step.detail" class="sa-step-detail">{{ step.detail }}</span>
          </div>
          <span class="sa-step-status" :class="step.status">{{ step.statusText }}</span>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  steps: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle'])

const statusMap = {
  success: 'completed',
  completed: 'completed',
  running: 'running',
  pending: 'pending',
  warning: 'warning',
  error: 'error',
}

const statusTextMap = {
  completed: '已完成',
  running: '执行中',
  pending: '等待中',
  warning: '待确认',
  error: '异常',
}

const normalizedSteps = computed(() => {
  return (props.steps || []).map((step) => {
    const status = statusMap[step?.status] || 'completed'
    return {
      text: step?.text || step?.title || step?.detail || '执行步骤',
      detail: step?.detail && step?.detail !== step?.text && step?.detail !== step?.title ? step.detail : '',
      status,
      statusText: step?.statusText || statusTextMap[status],
    }
  })
})
</script>

<style scoped>
.sa-thinking-card {
  width: 100%;
  background: linear-gradient(180deg, #FFFFFF 0%, #ffffff 100%);
  border: 1px solid rgba(230, 31, 36, 0.12);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 7px 18px rgba(0, 0, 0, 0.035);
}

.sa-thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.sa-thinking-header:hover {
  background: #F8F9FA;
}

.sa-arrow {
  font-size: 12px;
  color: #9CA3AF;
  transition: transform 200ms;
}

.sa-arrow.open {
  transform: rotate(90deg);
}

.sa-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.sa-header-count {
  font-size: 11px;
  color: #9CA3AF;
}

.sa-check {
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #10B981;
  background: #ECFDF5;
}

.sa-check.loading {
  color: #E61F24;
  background: #FEF2F2;
}

.sa-thinking-body {
  background: #F8F9FA;
  border-top: 1px solid rgba(230, 31, 36, 0.08);
  padding: 11px 13px 13px;
}

.sa-thinking-step {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 7px 0;
}

.sa-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 6px;
}

.sa-dot.running {
  background: #E61F24;
  animation: pulse 1.2s ease-in-out infinite;
}

.sa-dot.completed {
  background: #10B981;
}

.sa-dot.pending {
  background: #9CA3AF;
}

.sa-dot.warning {
  background: #F59E0B;
}

.sa-dot.error {
  background: #E61F24;
}

.sa-step-copy {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.sa-step-text {
  font-size: 12px;
  color: #111827;
  line-height: 1.55;
}

.sa-step-detail {
  font-size: 11px;
  color: #9CA3AF;
  line-height: 1.52;
}

.sa-step-status {
  padding: 2px 7px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.sa-step-status.completed {
  background: #ECFDF5;
  color: #10B981;
}

.sa-step-status.running {
  background: #FEF2F2;
  color: #E61F24;
}

.sa-step-status.pending {
  background: #F3F4F6;
  color: #9CA3AF;
}

.sa-step-status.warning {
  background: #FFFBEB;
  color: #F59E0B;
}

.sa-step-status.error {
  background: #FEF2F2;
  color: #E61F24;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.4;
  }
  50% {
    opacity: 1;
  }
}

.sa-collapse-enter-active,
.sa-collapse-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.sa-collapse-enter-to,
.sa-collapse-leave-from {
  opacity: 1;
  max-height: 500px;
}

.sa-collapse-enter-from,
.sa-collapse-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
