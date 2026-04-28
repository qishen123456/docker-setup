<template>
  <div class="sa-header">
    <div class="sa-header-left">
      <div class="sa-header-copy">
        <div class="sa-title-row">
          <div class="sa-title">当前会话</div>
          <span class="sa-workspace-badge">经营助手</span>
        </div>

        <div class="sa-subtitle-row">
          <span class="sa-subtitle-label">当前数据集</span>
          <div class="sa-dataset-badge">
            <span class="sa-dataset-dot"></span>
            <span class="sa-dataset-name">{{ datasetName }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="sa-header-right">
      <button class="sa-solid-btn" type="button" @click="$emit('newChat')">新会话</button>
      <button class="sa-text-btn" type="button" @click="$emit('togglePanel')">
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
  datasetName: {
    type: String,
    default: '自动路由数据集'
  }
})

defineEmits(['togglePanel', 'newChat', 'showHistory'])
</script>

<style scoped>
.sa-header {
  min-height: 54px;
  padding: 8px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  container-type: inline-size;
  border-bottom: 1px solid rgba(29, 33, 41, 0.08);
  background: rgba(255, 255, 255, 0.94);
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
  gap: 4px;
  min-width: 0;
}

.sa-title-row {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}

.sa-title {
  font-size: 12px;
  line-height: 1.2;
  font-weight: 700;
  color: #111827;
}

.sa-workspace-badge {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 7px;
  border-radius: 999px;
  background: #e8f3ff;
  color: #165dff;
  font-size: 10px;
  font-weight: 700;
}

.sa-subtitle-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex-wrap: wrap;
}

.sa-subtitle-label {
  font-size: 10px;
  color: #86909c;
}

.sa-subtitle-sep {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #c9cdd4;
  flex-shrink: 0;
}

.sa-dataset-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 320px;
  min-width: 0;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: #f7f8fa;
  color: #4e5969;
  font-size: 10px;
  font-weight: 600;
}

.sa-dataset-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #165dff;
  flex-shrink: 0;
}

.sa-dataset-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 1 auto;
  flex-wrap: wrap;
  justify-content: flex-end;
  margin-left: auto;
  min-width: 0;
}

.sa-solid-btn,
.sa-text-btn {
  height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-text-btn {
  border: 1px solid rgba(29, 33, 41, 0.06);
  background: rgba(248, 249, 251, 0.92);
  color: #4e5969;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.sa-text-btn:hover {
  color: #165dff;
  border-color: rgba(22, 93, 255, 0.16);
  background: #f5f8ff;
  transform: translateY(-1px);
}

.sa-solid-btn {
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
  color: #165dff;
  box-shadow:
    0 8px 18px rgba(22, 93, 255, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.sa-solid-btn:hover {
  border-color: rgba(22, 93, 255, 0.22);
  background: linear-gradient(180deg, #ffffff 0%, #f2f6ff 100%);
  color: #114fd6;
  transform: translateY(-1px);
}

.sa-solid-btn:active,
.sa-text-btn:active {
  transform: scale(0.96);
}

@container (max-width: 760px) {
  .sa-header {
    padding: 9px 12px;
  }

  .sa-header-copy {
    gap: 3px;
  }

  .sa-dataset-badge {
    max-width: 100%;
  }
}

@container (max-width: 620px) {
  .sa-workspace-badge {
    display: none;
  }

  .sa-subtitle-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
    align-items: start;
  }

  .sa-subtitle-sep {
    display: none;
  }

  .sa-subtitle-label {
    font-size: 9px;
  }

  .sa-dataset-badge {
    width: fit-content;
    max-width: 100%;
  }

  .sa-header-right {
    width: 100%;
    justify-content: flex-start;
    margin-left: 0;
  }

  .sa-solid-btn,
  .sa-text-btn {
    height: 26px;
    padding: 0 10px;
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
