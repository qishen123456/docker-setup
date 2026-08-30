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
          :class="{ 'sa-parse-token-editable': editable, 'sa-parse-token-corrected': s.corrected, 'sa-parse-token-pending': isPending(s) }"
          :title="tokenTitle('数据集', s)"
          @click.stop="openPicker('dataset', s, $event)"
        >{{ displayLabel(s) }}</span>
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
              'sa-parse-token-learned': s.learned,
              'sa-parse-token-pending': isPending(s)
            }"
            :title="nodeTitle(s)"
            @click.stop="openPicker('node', s, $event)"
          >{{ displayLabel(s) }}<span v-if="s.learned" class="sa-parse-learned">↺</span></span>{{ i < nodeSlots.length - 1 ? '、' : '' }}
        </template>
      </template>
      <template v-if="metricSlot">
        的
        <span
          class="sa-parse-token sa-parse-token-metric"
          :class="{ 'sa-parse-token-editable': editable, 'sa-parse-token-corrected': metricSlot.corrected, 'sa-parse-token-learned': metricSlot.learned, 'sa-parse-token-pending': isPending(metricSlot) }"
          :title="tokenTitle(metricTitle, metricSlot) + learnedTip(metricSlot)"
          @click.stop="openPicker('metric', metricSlot, $event)"
        >{{ displayLabel(metricSlot) }}<span v-if="metricSlot.learned" class="sa-parse-learned">↺</span></span>
      </template>
      <template v-if="!nodeSlots.length && !metricSlot && datasetSlots.length">查询</template>
    </span>
    <span v-if="bar.inherited_note" class="sa-parse-inherited">{{ bar.inherited_note }}</span>

    <!-- 原位候选下拉（点击 token 弹出，点外关闭）。点选 = 本地暂存，不立即重跑 -->
    <div v-if="picker.open" class="sa-parse-picker" :style="pickerStyle" @click.stop>
      <div class="sa-parse-picker-head">{{ pickerTitle }}</div>
      <!-- 当前值（或已暂存值）置顶带对勾，点击仅关闭 -->
      <button
        v-if="pickerCurrentLabel"
        class="sa-parse-picker-item sa-parse-picker-current"
        @click.stop="closePicker()"
      ><span class="sa-parse-picker-check">✓</span>{{ pickerCurrentLabel }}</button>
      <!-- 已暂存时提供"恢复原解析"入口 -->
      <button
        v-if="pickerStaged"
        class="sa-parse-picker-item sa-parse-picker-restore"
        @click.stop="unstage(picker.key)"
      ><span class="sa-parse-picker-check sa-parse-picker-check-empty"></span>恢复原解析「{{ pickerOriginalLabel }}」</button>
      <div v-if="picker.loading" class="sa-parse-picker-empty">加载候选中…</div>
      <template v-else>
        <button
          v-for="c in picker.candidates"
          :key="String(c.value)"
          class="sa-parse-picker-item"
          @click.stop="pickCandidate(c)"
        ><span class="sa-parse-picker-check sa-parse-picker-check-empty"></span>{{ c.label }}</button>
        <div v-if="!picker.candidates.length" class="sa-parse-picker-empty">暂无其他候选</div>
      </template>
      <div v-if="pickerStaged" class="sa-parse-picker-foot">已暂存，点下方「按新理解重新提问」生效</div>
    </div>

    <!-- 暂存确认条：可连改多个槽位，确认后作为新提问发进当前会话 -->
    <div v-if="hasPending" class="sa-parse-confirm" @click.stop>
      <span class="sa-parse-confirm-text">已修改：{{ pendingSummary }}</span>
      <button class="sa-parse-confirm-btn" @click.stop="confirmAsk">按新理解重新提问</button>
      <button class="sa-parse-undo" @click.stop="undoAll">撤销</button>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, watch, onBeforeUnmount } from 'vue'
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
  }
})

const emit = defineEmits(['ask'])

const slots = computed(() => (props.bar && Array.isArray(props.bar.slots) ? props.bar.slots : []))
const datasetSlots = computed(() => slots.value.filter(s => s.slot === 'dataset'))
const nodeSlots = computed(() => slots.value.filter(s => s.slot === 'node'))
const metricSlot = computed(() => slots.value.find(s => s.slot === 'metric') || null)

// ---- 暂存态（编辑不立即重跑，确认后由父组件编译新问句发进当前会话）----
// key：node 槽用 span 位置区分多次出现；metric/dataset 单槽直接用 slot 名
const pending = reactive({})
const slotKey = (s) => (s.slot === 'node' ? `node:${s.start ?? s.resolved_value}` : s.slot)
const isPending = (s) => Boolean(pending[slotKey(s)])
const displayLabel = (s) => pending[slotKey(s)]?.new_label || s.resolved_value

const SLOT_NAME = { node: '对象', metric: '指标', dataset: '数据集' }
const hasPending = computed(() => Object.keys(pending).length > 0)
const pendingSummary = computed(() => Object.values(pending)
  .map(p => `${SLOT_NAME[p.slot] || p.slot} ${p.original}→${p.new_label}`)
  .join('；'))

const resetPending = () => {
  for (const k of Object.keys(pending)) delete pending[k]
}
// bar 被替换（历史恢复等）时丢弃暂存，避免把旧句的 offset 套到新句上
watch(() => props.bar, resetPending)

const learnedTip = (s) => {
  if (!s || !s.learned || !s.learned.suggestion) return ''
  const at = s.learned.at ? String(s.learned.at).slice(0, 10) : ''
  return `；已学习：你上次修正为「${s.learned.suggestion}」${at ? `（${at}）` : ''}`
}
const tokenTitle = (base, s) => {
  const p = pending[slotKey(s)]
  const staged = p ? `；暂存为「${p.new_label}」，确认后生效` : ''
  return (props.editable ? base + '（点击修正）' : base) + staged
}
const nodeTitle = (s) => {
  if (s.abbrev) return `对象：缩写映射为「${s.resolved_value}」（如不对请重问修正）`
  if (s.inherited) return '对象（继承自上文，请直接重问修正）'
  const base = s.span_text ? `对象：原句「${s.span_text}」解析为「${s.resolved_value}」` : `对象：${s.resolved_value}`
  return tokenTitle(base, s) + learnedTip(s)
}
const metricTitle = computed(() => {
  const s = metricSlot.value
  if (!s) return ''
  return s.span_text ? `指标：原句「${s.span_text}」解析为「${s.resolved_value}」` : `指标：${s.resolved_value}`
})

const picker = reactive({
  open: false,
  slot: '',
  key: '',
  candidates: [],
  loading: false,
  left: 0,
  top: 0,
  originalLabel: '',
  originalValue: null
})

const pickerTitle = computed(() => {
  if (picker.slot === 'dataset') return '换个数据集'
  if (picker.slot === 'node') return '换个对象'
  return '换个指标'
})
const pickerStyle = computed(() => ({ left: picker.left + 'px', top: picker.top + 'px' }))
const pickerStaged = computed(() => Boolean(picker.key && pending[picker.key]))
const pickerCurrentLabel = computed(() => pending[picker.key]?.new_label || picker.originalLabel)
const pickerOriginalLabel = computed(() => picker.originalLabel)

const closePicker = () => { picker.open = false }
if (typeof window !== 'undefined') {
  window.addEventListener('click', closePicker)
}
onBeforeUnmount(() => {
  if (typeof window !== 'undefined') window.removeEventListener('click', closePicker)
})

const openPicker = async (slot, slotObj, event) => {
  if (!props.editable) return
  if (slot === 'node' && slotObj.inherited) return // 继承槽位无原句定位，禁编辑
  const rect = event.currentTarget.getBoundingClientRect()
  const host = event.currentTarget.closest('.sa-parse-bar').getBoundingClientRect()
  picker.slot = slot
  picker.key = slotKey(slotObj)
  picker.left = Math.max(0, rect.left - host.left)
  picker.top = rect.bottom - host.top + 4
  picker.open = true
  picker.loading = true
  picker.candidates = []
  picker.originalLabel = slotObj.resolved_value || ''
  picker.originalValue = slot === 'dataset' ? props.datasetId : slotObj.resolved_value
  picker.slotObj = slotObj
  try {
    const resp = await getParseBarCandidates({
      slot,
      current_value: slotObj.resolved_value,
      dataset_id: props.datasetId
    })
    picker.candidates = (resp && resp.candidates) || [] // 拦截器已返回响应体，直接取 candidates
  } catch (e) {
    picker.candidates = [] // fail-open：候选拉不到不阻断
  } finally {
    picker.loading = false
  }
}

const pickCandidate = (c) => {
  const s = picker.slotObj
  if (!s) { closePicker(); return }
  const isSame = picker.slot === 'dataset'
    ? Number(c.value) === Number(picker.originalValue)
    : String(c.label) === String(picker.originalLabel)
  if (isSame) {
    delete pending[picker.key] // 选回原值 = 撤销该槽暂存
  } else {
    pending[picker.key] = {
      slot: picker.slot,
      start: Number.isInteger(s.start) ? s.start : null,
      end: Number.isInteger(s.end) ? s.end : null,
      span_text: s.span_text || '',
      original: s.resolved_value || '',
      new_value: c.value,
      new_label: c.label,
      dataset_id: picker.slot === 'dataset' ? c.value : props.datasetId
    }
  }
  closePicker()
}

const unstage = (key) => {
  delete pending[key]
  closePicker()
}

const undoAll = () => resetPending()

const confirmAsk = () => {
  const overrides = Object.values(pending)
  if (!overrides.length) return
  const dsOverride = overrides.find(o => o.slot === 'dataset')
  emit('ask', {
    overrides,
    dataset_id: dsOverride?.dataset_id ?? props.datasetId
  })
  resetPending()
  closePicker()
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

/* 暂存态：新值 + 虚线下划线，等确认后生效 */
.sa-parse-token-pending {
  border-style: dashed;
  box-shadow: inset 0 -2px 0 currentColor;
  font-weight: 600;
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
  max-height: 260px;
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

.sa-parse-picker-item:hover {
  background: #F1F5F9;
  color: #B91C1C;
}

.sa-parse-picker-current {
  font-weight: 600;
  color: #0F172A;
  background: #F8FAFC;
}

.sa-parse-picker-restore {
  color: #64748B;
}

.sa-parse-picker-check {
  display: inline-block;
  width: 16px;
  margin-right: 4px;
  color: #15803D;
  font-weight: 700;
}

.sa-parse-picker-check-empty {
  visibility: hidden;
}

.sa-parse-picker-foot {
  padding: 6px 8px 4px;
  font-size: 12px;
  color: #B45309;
  border-top: 1px dashed #E2E8F0;
  margin-top: 4px;
}

/* 暂存确认条：整行铺在解析条底部 */
.sa-parse-confirm {
  flex-basis: 100%;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px dashed #E2E8F0;
}

.sa-parse-confirm-text {
  font-size: 12px;
  color: #B45309;
}

.sa-parse-confirm-btn {
  padding: 4px 12px;
  border: none;
  border-radius: 7px;
  background: #B91C1C;
  color: #FFFFFF;
  font-size: 12px;
  cursor: pointer;
}

.sa-parse-confirm-btn:hover {
  background: #991B1B;
}

.sa-parse-undo {
  padding: 4px 10px;
  border: 1px solid #E2E8F0;
  border-radius: 7px;
  background: #FFFFFF;
  color: #64748B;
  font-size: 12px;
  cursor: pointer;
}

.sa-parse-undo:hover {
  color: #334155;
  border-color: #CBD5E1;
}
</style>
