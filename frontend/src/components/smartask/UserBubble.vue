<template>
  <div class="sa-user-message">
    <div class="sa-user-main">
      <div class="sa-user-bubble">{{ content }}</div>
      <div class="sa-user-actions" aria-label="问题操作">
        <el-tooltip content="复制" placement="bottom" :show-after="180">
          <button class="sa-user-action" type="button" aria-label="复制问题" @click="$emit('copy')">
            <el-icon><DocumentCopy /></el-icon>
          </button>
        </el-tooltip>
        <el-tooltip content="修改" placement="bottom" :show-after="180">
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
        <el-tooltip content="重新问" placement="bottom" :show-after="180">
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
    <div class="sa-user-avatar">{{ userName[0] }}</div>
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
  width: 26px;
  height: 26px;
  background: #86909c;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
}

.sa-user-bubble {
  padding: 11px 15px;
  background: #165dff;
  color: #ffffff;
  border-radius: 12px 12px 2px 12px;
  font-size: 13px;
  line-height: 1.58;
  word-break: break-word;
  box-shadow: 0 8px 18px rgba(22, 93, 255, 0.16);
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
  border: 1px solid rgba(22, 93, 255, 0.12);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.96);
  color: #4e5969;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
  transition: color 0.16s ease, border-color 0.16s ease, transform 0.16s ease, background 0.16s ease;
}

.sa-user-action:hover:not(:disabled) {
  color: #165dff;
  border-color: rgba(22, 93, 255, 0.32);
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
