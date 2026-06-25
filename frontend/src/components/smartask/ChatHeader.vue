<template>
  <div class="sa-header">
    <div class="sa-header-left">
      <div class="sa-header-copy">
        <div class="sa-title-row">
          <div class="sa-title">当前会话</div>
          <span class="sa-workspace-badge">经营助手</span>
        </div>
      </div>
    </div>

    <div class="sa-header-right">
      <button v-if="allowNewChat" class="sa-solid-btn" type="button" @click="$emit('newChat')">新会话</button>
      <button v-if="allowTogglePanel" class="sa-text-btn" type="button" @click="$emit('togglePanel')">
        {{ showPanel ? '隐藏详情' : '显示详情' }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  showPanel: {
    type: Boolean,
    default: true
  },
  allowTogglePanel: {
    type: Boolean,
    default: true
  },
  allowNewChat: {
    type: Boolean,
    default: true
  }
})

defineEmits(['togglePanel', 'newChat', 'showHistory'])
</script>

<style scoped>
.sa-header {
  min-height: 46px;
  padding: 6px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  container-type: inline-size;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.92);
  flex-shrink: 0;
}

.sa-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1 1 320px;
}

.sa-header-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.sa-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.sa-title {
  font-size: 11px;
  line-height: 1.2;
  font-weight: 700;
  color: #111827;
}

.sa-workspace-badge {
  display: inline-flex;
  align-items: center;
  height: 17px;
  padding: 0 6px;
  border-radius: 8px;
  background: #F3F4F6;
  color: #1A1A1A;
  font-size: 9px;
  font-weight: 700;
}

.sa-header-right {
  display: flex;
  align-items: center;
  gap: 7px;
  flex: 0 1 auto;
  justify-content: flex-end;
  margin-left: auto;
  min-width: 0;
}

.sa-solid-btn,
.sa-text-btn {
  height: 26px;
  padding: 0 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-text-btn {
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(248, 249, 251, 0.92);
  color: #6B7280;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.sa-text-btn:hover {
  color: #1A1A1A;
  border-color: rgba(26, 26, 26, 0.16);
  background: #F8F9FA;
  transform: translateY(-1px);
}

.sa-solid-btn {
  border: 1px solid rgba(26, 26, 26, 0.12);
  background: linear-gradient(180deg, #F8F9FA 0%, #E5E7EB 100%);
  color: #1A1A1A;
  box-shadow:
    0 8px 18px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.sa-solid-btn:hover {
  border-color: rgba(26, 26, 26, 0.22);
  background: linear-gradient(180deg, #ffffff 0%, #F8F9FA 100%);
  color: #000000;
  transform: translateY(-1px);
}

.sa-solid-btn:active,
.sa-text-btn:active {
  transform: scale(0.96);
}

@container (max-width: 760px) {
  .sa-header {
    padding: 7px 12px;
  }
}

@container (max-width: 620px) {
  .sa-workspace-badge {
    display: none;
  }

  .sa-header-right {
    width: 100%;
    justify-content: flex-start;
    margin-left: 0;
  }

  .sa-solid-btn,
  .sa-text-btn {
    height: 24px;
    padding: 0 9px;
    font-size: 10px;
  }
}

@media (max-width: 900px) {
  .sa-header {
    align-items: flex-start;
  }

  .sa-header-right {
    width: 100%;
    justify-content: flex-start;
    margin-left: 0;
  }
}
</style>
