<template>
  <div class="sa-user-message">
    <div class="sa-user-main">
      <div class="sa-user-bubble">{{ content }}</div>
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
import { DocumentCopy, Edit, RefreshRight } from '@element-plus/icons-vue'

defineProps({
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
  }
})

defineEmits(['copy', 'edit', 'rerun'])
</script>

<style scoped>
.sa-user-message {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  justify-content: flex-end;
  margin: 18px 0;
}

.sa-user-main {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  max-width: 72%;
}

.sa-user-avatar {
  width: 44px;
  height: 44px;
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
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #E61F24;
  box-shadow:
    0 0 0 3px #FFFFFF,
    0 4px 9px rgba(230, 31, 36, 0.18);
}

.sa-user-avatar-svg {
  width: 44px;
  height: 44px;
  display: block;
}

.sa-user-bubble {
  padding: 14px 18px;
  background: linear-gradient(180deg, #ffffff 0%, #FAFBFC 100%);
  color: #111827;
  border: 1px solid rgba(17, 24, 39, 0.07);
  border-radius: 20px 20px 8px 20px;
  font-size: 14px;
  line-height: 1.68;
  word-break: break-word;
  box-shadow:
    0 16px 28px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.sa-user-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
  margin-top: 4px;
  padding: 2px;
  opacity: 0;
  pointer-events: none;
  transform: translateY(-3px);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.sa-user-message:hover .sa-user-actions,
.sa-user-actions:focus-within {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.sa-user-action {
  width: 26px;
  height: 26px;
  border: 1px solid rgba(26, 24, 22, 0.12);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.96);
  color: #6B7280;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: color 0.16s ease, border-color 0.16s ease, transform 0.16s ease, background 0.16s ease;
}

.sa-user-action:hover:not(:disabled) {
  color: #1A1816;
  border-color: rgba(26, 24, 22, 0.32);
  background: #ffffff;
  transform: translateY(-1px);
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
