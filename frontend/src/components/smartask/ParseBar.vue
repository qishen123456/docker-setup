<template>
  <div v-if="bar" class="sa-parse-bar">
    <span class="sa-parse-icon" aria-hidden="true">≡</span>
    <span class="sa-parse-label">我理解为：</span>
    <span class="sa-parse-body">
      <template v-if="datasetSlots.length">
        在
        <span
          v-for="(s, i) in datasetSlots"
          :key="`ds-${i}`"
          class="sa-parse-token sa-parse-token-dataset"
          title="数据集"
        >{{ s.resolved_value }}</span>
        里
      </template>
      <template v-if="nodeSlots.length">
        查
        <template v-for="(s, i) in nodeSlots" :key="`nd-${i}`">
          <span
            class="sa-parse-token sa-parse-token-node"
            :class="{ 'sa-parse-token-inherited': s.inherited }"
            :title="nodeTitle(s)"
          >{{ s.resolved_value }}</span>{{ i < nodeSlots.length - 1 ? '、' : '' }}
        </template>
      </template>
      <template v-if="metricSlot">
        的
        <span
          class="sa-parse-token sa-parse-token-metric"
          :title="metricTitle"
        >{{ metricSlot.resolved_value }}</span>
      </template>
      <template v-if="!nodeSlots.length && !metricSlot && datasetSlots.length">查询</template>
    </span>
    <span v-if="bar.inherited_note" class="sa-parse-inherited">{{ bar.inherited_note }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  bar: {
    type: Object,
    default: null
  }
})

const slots = computed(() => (props.bar && Array.isArray(props.bar.slots) ? props.bar.slots : []))
const datasetSlots = computed(() => slots.value.filter(s => s.slot === 'dataset'))
const nodeSlots = computed(() => slots.value.filter(s => s.slot === 'node'))
const metricSlot = computed(() => slots.value.find(s => s.slot === 'metric') || null)

const nodeTitle = (s) => {
  if (s.inherited) return '对象（继承自上文）'
  return s.span_text ? `对象：原句「${s.span_text}」解析为「${s.resolved_value}」` : `对象：${s.resolved_value}`
}
const metricTitle = computed(() => {
  const s = metricSlot.value
  if (!s) return ''
  return s.span_text ? `指标：原句「${s.span_text}」解析为「${s.resolved_value}」` : `指标：${s.resolved_value}`
})
</script>

<style scoped>
.sa-parse-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin: 8px 0 4px;
  padding: 6px 12px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.8;
  color: #64748B;
}

.sa-parse-icon {
  color: #94A3B8;
  font-weight: 600;
}

.sa-parse-label {
  color: #64748B;
  flex-shrink: 0;
}

.sa-parse-body {
  color: #475569;
}

.sa-parse-token {
  display: inline-block;
  padding: 0 7px;
  margin: 0 2px;
  border-radius: 6px;
  font-weight: 500;
  cursor: default;
}

.sa-parse-token-dataset {
  background: #EFF6FF;
  color: #1D4ED8;
  border: 1px solid #BFDBFE;
}

.sa-parse-token-node {
  background: #FEF2F2;
  color: #B91C1C;
  border: 1px solid #FECACA;
}

.sa-parse-token-inherited {
  border-style: dashed;
  opacity: 0.85;
}

.sa-parse-token-metric {
  background: #F0FDF4;
  color: #15803D;
  border: 1px solid #BBF7D0;
}

.sa-parse-inherited {
  margin-left: auto;
  font-size: 12px;
  color: #94A3B8;
}
</style>
