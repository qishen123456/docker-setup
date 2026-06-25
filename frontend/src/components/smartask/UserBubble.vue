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
      <span class="sa-user-avatar-mark">U</span>
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
  margin: 14px 0;
}

.sa-user-main {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  max-width: 72%;
}

.sa-user-avatar {
  width: 30px;
  height: 30px;
  position: relative;
  overflow: hidden;
  background: rgba(26, 24, 22, 0.94);
  color: #FFFFFF;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: none;
  box-shadow:
    0 6px 14px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.sa-user-avatar-mark {
  position: relative;
  z-index: 1;
  font-size: 12px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: 0;
}

.sa-user-bubble {
  padding: 12px 16px;
  background: linear-gradient(180deg, #ffffff 0%, #FDFBF9 100%);
  color: #111827;
  border: 1px solid rgba(26, 24, 22, 0.08);
  border-radius: 18px 18px 6px 18px;
  font-size: 13px;
  line-height: 1.62;
  word-break: break-word;
  box-shadow:
    0 10px 24px rgba(0, 0, 0, 0.04),
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
