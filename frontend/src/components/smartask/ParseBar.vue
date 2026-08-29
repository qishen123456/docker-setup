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
          :class="{ 'sa-parse-token-editable': editable, 'sa-parse-token-corrected': s.corrected }"
          :title="editable ? '数据集（点击修正）' : '数据集'"
          @click.stop="openPicker('dataset', s, $event)"
        >{{ s.resolved_value }}</span>
        里
      </template>
      <template v-if="nodeSlots.length">
        查
        <template v-for="(s, i) in nodeSlots" :key="`nd-${i}`">
          <span
            class="sa-parse-token sa-parse-token-node"
            :class="{
              'sa-parse-token-inherited': s.inherited,
              'sa-parse-token-editable': editable && !s.inherited,
              'sa-parse-token-corrected': s.corrected,
              'sa-parse-token-learned': s.learned
            }"
            :title="nodeTitle(s)"
            @click.stop="openPicker('node', s, $event)"
          >{{ s.resolved_value }}<span v-if="s.learned" class="sa-parse-learned">↺</span></span>{{ i < nodeSlots.length - 1 ? '、' : '' }}
        </template>
      </template>
      <template v-if="metricSlot">
        的
        <span
          class="sa-parse-token sa-parse-token-metric"
          :class="{ 'sa-parse-token-editable': editable, 'sa-parse-token-corrected': metricSlot.corrected, 'sa-parse-token-learned': metricSlot.learned }"
          :title="(editable ? metricTitle + '（点击修正）' : metricTitle) + learnedTip(metricSlot)"
          @click.stop="openPicker('metric', metricSlot, $event)"
        >{{ metricSlot.resolved_value }}<span v-if="metricSlot.learned" class="sa-parse-learned">↺</span></span>
      </template>
      <template v-if="!nodeSlots.length && !metricSlot && datasetSlots.length">查询</template>
    </span>
    <span v-if="bar.inherited_note" class="sa-parse-inherited">{{ bar.inherited_note }}</span>

    <!-- 原位候选下拉（点击 token 弹出，点外关闭） -->
    <div v-if="picker.open" class="sa-parse-picker" :style="pickerStyle" @click.stop>
      <div class="sa-parse-picker-head">{{ pickerTitle }}</div>
      <div v-if="picker.loading" class="sa-parse-picker-empty">加载候选中…</div>
      <div v-else-if="!picker.candidates.length" class="sa-parse-picker-empty">暂无候选</div>
      <button
        v-for="c in picker.candidates"
        :key="String(c.value)"
        class="sa-parse-picker-item"
        :disabled="rerunning"
        @click.stop="pickCandidate(c)"
      >{{ c.label }}</button>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, onBeforeUnmount } from 'vue'
import { getParseBarCandidates } from '../../api'

const props = defineProps({
  bar: {
    type: Object,
    default: null
  },
  // 当前数据集 id（node 槽候选按此查兄弟节点）；多数据集取第一个
  datasetId: {
    type: Number,
    default: null
  },
  editable: {
    type: Boolean,
    default: false
  },
  rerunning: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['correct'])

const slots = computed(() => (props.bar && Array.isArray(props.bar.slots) ? props.bar.slots : []))
const datasetSlots = computed(() => slots.value.filter(s => s.slot === 'dataset'))
const nodeSlots = computed(() => slots.value.filter(s => s.slot === 'node'))
const metricSlot = computed(() => slots.value.find(s => s.slot === 'metric') || null)

const learnedTip = (s) => {
  if (!s || !s.learned || !s.learned.suggestion) return ''
  const at = s.learned.at ? String(s.learned.at).slice(0, 10) : ''
  return `；已学习：你上次修正为「${s.learned.suggestion}」${at ? `（${at}）` : ''}`
}
const nodeTitle = (s) => {
  if (s.inherited) return '对象（继承自上文，请直接重问修正）'
  const base = s.span_text ? `对象：原句「${s.span_text}」解析为「${s.resolved_value}」` : `对象：${s.resolved_value}`
  return (props.editable ? base + '（点击修正）' : base) + learnedTip(s)
}
const metricTitle = computed(() => {
  const s = metricSlot.value
  if (!s) return ''
  return s.span_text ? `指标：原句「${s.span_text}」解析为「${s.resolved_value}」` : `指标：${s.resolved_value}`
})

const picker = reactive({
  open: false,
  slot: '',
  candidates: [],
  loading: false,
  left: 0,
  top: 0
})

const pickerTitle = computed(() => {
  if (picker.slot === 'dataset') return '换个数据集'
  if (picker.slot === 'node') return '换个对象'
  return '换个指标'
})

const pickerStyle = computed(() => ({ left: picker.left + 'px', top: picker.top + 'px' }))

const closePicker = () => { picker.open = false }
if (typeof window !== 'undefined') {
  window.addEventListener('click', closePicker)
}
onBeforeUnmount(() => {
  if (typeof window !== 'undefined') window.removeEventListener('click', closePicker)
})

const openPicker = async (slot, slotObj, event) => {
  if (!props.editable || props.rerunning) return
  if (slot === 'node' && slotObj.inherited) return // 继承槽位无原句定位，禁编辑
  const rect = event.currentTarget.getBoundingClientRect()
  const host = event.currentTarget.closest('.sa-parse-bar').getBoundingClientRect()
  picker.slot = slot
  picker.left = Math.max(0, rect.left - host.left)
  picker.top = rect.bottom - host.top + 4
  picker.open = true
  picker.loading = true
  picker.candidates = []
  try {
    const { data } = await getParseBarCandidates({
      slot,
      current_value: slotObj.resolved_value,
      dataset_id: props.datasetId
    })
    picker.candidates = (data && data.candidates) || []
  } catch (e) {
    picker.candidates = [] // fail-open：候选拉不到不阻断
  } finally {
    picker.loading = false
  }
}

const pickCandidate = (c) => {
  if (props.rerunning) return
  picker.open = false
  emit('correct', {
    slot: picker.slot,
    new_value: c.value,
    dataset_id: picker.slot === 'dataset' ? c.value : props.datasetId
  })
}
</script>

<style scoped>
.sa-parse-bar {
  position: relative;
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

.sa-parse-token-editable {
  cursor: pointer;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.sa-parse-token-editable:hover {
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.12);
  transform: translateY(-1px);
}

.sa-parse-token-corrected {
  box-shadow: inset 0 -2px 0 currentColor;
}

.sa-parse-token-learned {
  border-style: dashed;
}

.sa-parse-learned {
  margin-left: 3px;
  font-size: 11px;
  opacity: 0.75;
}

.sa-parse-inherited {
  margin-left: auto;
  font-size: 12px;
  color: #94A3B8;
}

.sa-parse-picker {
  position: absolute;
  z-index: 30;
  min-width: 180px;
  max-width: 280px;
  max-height: 240px;
  overflow-y: auto;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
  padding: 6px;
}

.sa-parse-picker-head {
  padding: 4px 8px;
  font-size: 12px;
  color: #94A3B8;
}

.sa-parse-picker-empty {
  padding: 10px 8px;
  font-size: 13px;
  color: #94A3B8;
}

.sa-parse-picker-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 7px 10px;
  border: none;
  background: transparent;
  border-radius: 7px;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
}

.sa-parse-picker-item:hover:not(:disabled) {
  background: #F1F5F9;
  color: #B91C1C;
}

.sa-parse-picker-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
