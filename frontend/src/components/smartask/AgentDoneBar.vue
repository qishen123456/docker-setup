<template>
  <div class="sa-agent-done">
    <div class="sa-agent-copy">
      <div class="sa-agent-avatar">DA</div>
      <div class="sa-agent-text">
        <div class="sa-agent-kicker">经营分析顾问已完成执行任务</div>
        <div class="sa-agent-title">{{ title }}</div>
        <div class="sa-agent-subtitle">执行明细、结果数据和分析报告已经整理完成，可继续查看下一步结果。</div>
      </div>
    </div>

    <div class="sa-agent-actions">
      <button class="sa-secondary-btn" @click="$emit('viewDetails')">查看详情</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '本月公司经营表现分析'
  }
})

defineEmits(['viewDetails'])
</script>

<style scoped>
.sa-agent-done {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 11px 13px;
  border: 1px solid rgba(29, 33, 41, 0.06);
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%);
  box-shadow: 0 7px 16px rgba(15, 23, 42, 0.035);
}

.sa-agent-copy {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.sa-agent-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(180deg, #2a6cff 0%, #165dff 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.sa-agent-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sa-agent-kicker {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #4e5969;
}

.sa-agent-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
}

.sa-agent-subtitle {
  font-size: 11px;
  color: #86909c;
  line-height: 1.5;
}

.sa-agent-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.sa-secondary-btn {
  height: 28px;
  padding: 0 10px;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.sa-secondary-btn {
  border: 1px solid rgba(29, 33, 41, 0.12);
  background: #fff;
  color: #1d2129;
}

.sa-secondary-btn:hover {
  border-color: #165dff;
  color: #165dff;
}

@media (max-width: 900px) {
  .sa-agent-done {
    flex-direction: column;
    align-items: stretch;
  }

  .sa-agent-actions {
    justify-content: flex-end;
  }
}
</style>
