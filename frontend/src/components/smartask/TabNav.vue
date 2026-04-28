<template>
  <div class="sa-panel-tabs">
    <div 
      v-for="tab in tabs" 
      :key="tab" 
      class="sa-tab" 
      :class="{ active: activeTab === tab }" 
      @click="$emit('change', tab)"
    >
      {{ tab }}
    </div>
  </div>
</template>

<script setup>
defineProps({
  tabs: {
    type: Array,
    default: () => ['汇总报告', '数据预览', '执行详情']
  },
  activeTab: {
    type: String,
    default: '执行详情'
  }
})

defineEmits(['change'])
</script>

<style scoped>
.sa-panel-tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.sa-tab {
  flex: 1;
  text-align: center;
  padding: 10px 0;
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}

.sa-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

.sa-tab:hover:not(.active) {
  color: var(--text-body);
}
</style>
