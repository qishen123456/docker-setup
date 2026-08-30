<template>
  <div class="sa-user-message">
    <div class="sa-user-main">
      <div class="sa-user-bubble">
        <template v-if="segments">
          <template v-for="(seg, i) in segments" :key="i">
            <span
              v-if="seg.slot"
              class="sa-user-span"
              :title="`${seg.slot === 'node' ? '对象' : '指标'}：${seg.resolved}`"
            >{{ seg.text }}</span>
            <template v-else>{{ seg.text }}</template>
          </template>
        </template>
        <template v-else>{{ content }}</template>
      </div>
      <div v-if="allowCopy || allowEdit || allowRerun" class="sa-user-actions" aria-label="问题操作">
        <el-tooltip v-if="allowCopy" content="复制" placement="bottom" :show-after="180">
          <button class="sa-user-action" type="button" aria-label="复制问题" @click="$emit('copy')">
            <el-icon><DocumentCopy /></el-icon>
          </button>
        </el-tooltip>
        <el-tooltip v-if="allowEdit" content="修改" placement="bottom" :show-after="180">
          <button
            class="sa-user-action"
            type="button"
            aria-label="修改问题"
            :disabled="disabled"
            @click="$emit('edit')"
          >
            <el-icon><Edit /></el-icon>
          </button>
        </el-tooltip>
        <el-tooltip v-if="allowRerun" content="重新问" placement="bottom" :show-after="180">
          <button
            class="sa-user-action"
            type="button"
            aria-label="重新问"
            :disabled="disabled"
            @click="$emit('rerun')"
          >
            <el-icon><RefreshRight /></el-icon>
          </button>
        </el-tooltip>
      </div>
    </div>
    <div class="sa-user-avatar" aria-label="用户头像">
      <svg class="sa-user-avatar-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="userAuraChat" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#475569" />
            <stop offset="100%" stop-color="#CBD5E1" />
          </linearGradient>
          <linearGradient id="innerBgChatUser" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#FFFFFF" />
            <stop offset="100%" stop-color="#F8FAFC" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="45" stroke="url(#userAuraChat)" stroke-width="2.5" />
        <circle cx="50" cy="50" r="40" fill="url(#innerBgChatUser)" />
        <circle cx="50" cy="50" r="32" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="2 2" />
        <circle cx="50" cy="38" r="10" fill="#475569" />
        <path d="M50 54 L25 76 L75 76 Z" fill="#64748B" opacity="0.85"/>
        <path d="M50 54 L36 76 L64 76 Z" fill="#475569"/>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { DocumentCopy, Edit, RefreshRight } from '@element-plus/icons-vue'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  userName: {
    type: String,
    default: '用户'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  allowCopy: {
    type: Boolean,
    default: true
  },
  allowEdit: {
    type: Boolean,
    default: true
  },
  allowRerun: {
    type: Boolean,
    default: true
  },
  // 解析条 span 框出（parse-bar-design.md v1）：[{start, end, slot, resolved_value}]
  spans: {
    type: Array,
    default: null
  }
})

defineEmits(['copy', 'edit', 'rerun'])

// 按 spans 的 start/end 把问句切成 普通文本/高亮片段 段；区间无效或重叠时回退纯文本
const segments = computed(() => {
  const spans = (props.spans || [])
    .filter(s => Number.isInteger(s.start) && Number.isInteger(s.end) && s.end > s.start)
    .sort((a, b) => a.start - b.start)
  if (!spans.length || !props.content) return null
  const segs = []
  let cursor = 0
  for (const s of spans) {
    if (s.start < cursor || s.end > props.content.length) return null // 重叠/越界 → 回退纯文本
    if (s.start > cursor) segs.push({ text: props.content.slice(cursor, s.start) })
    segs.push({ text: props.content.slice(s.start, s.end), slot: s.slot, resolved: s.resolved_value })
    cursor = s.end
  }
  if (cursor < props.content.length) segs.push({ text: props.content.slice(cursor) })
  return segs
})
</script>

<style scoped>
.sa-user-message {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  justify-content: flex-end;
  margin: 10px 0;
}

.sa-user-main {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  max-width: 70%;
}

.sa-user-avatar {
  width: 40px;
  height: 40px;
  position: relative;
  overflow: visible;
  background: transparent;
  color: #475569;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 0;
  box-shadow: none;
}

.sa-user-avatar::before {
  content: none;
}

.sa-user-avatar::after {
  content: '';
  position: absolute;
  right: 1px;
  bottom: 1px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #DC2626;
  box-shadow:
    0 0 0 3px #FFFFFF,
    0 4px 9px rgba(185, 28, 28, 0.15);
}

.sa-user-avatar-svg {
  width: 40px;
  height: 40px;
  display: block;
}

.sa-user-bubble {
  padding: 12px 18px;
  background: linear-gradient(135deg, #DC2626 0%, #B91C1C 100%);
  color: #ffffff;
  border: none;
  border-radius: 20px 20px 6px 20px;
  font-size: 15px;
  line-height: 1.7;
  word-break: break-word;
  box-shadow:
    0 6px 16px rgba(185, 28, 28, 0.15),
    0 2px 5px rgba(185, 28, 28, 0.08);
}

/* 解析片段框出（解析条 v1）：红底气泡上的白边半透框 */
.sa-user-span {
  display: inline-block;
  padding: 0 4px;
  margin: 0 1px;
  border: 1px solid rgba(255, 255, 255, 0.85);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.16);
  cursor: default;
}

.sa-user-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
  margin-top: 6px;
  padding: 2px;
  opacity: 0;
  pointer-events: none;
  transform: translateY(-3px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.sa-user-message:hover .sa-user-actions,
.sa-user-actions:focus-within {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.sa-user-action {
  width: 28px;
  height: 28px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.98);
  color: #64748B;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
}

.sa-user-action:hover:not(:disabled) {
  color: #B91C1C;
  border-color: rgba(185, 28, 28, 0.18);
  background: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(185, 28, 28, 0.1);
}

.sa-user-action:disabled {
  cursor: not-allowed;
  opacity: 0.42;
  box-shadow: none;
}

.sa-user-action :deep(.el-icon) {
  font-size: 14px;
}

@media (max-width: 720px) {
  .sa-user-main {
    max-width: 82%;
  }
}
</style>
