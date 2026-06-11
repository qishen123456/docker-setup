<template>
  <div class="sa-composer" :class="{ 'is-running': isRunning }">
    <div class="sa-composer-inner">
      <div v-if="allowDatasetSelect || allowModelSelect" class="sa-composer-top">
        <div class="sa-composer-selectors">
          <div
            v-if="allowDatasetSelect"
            class="sa-composer-dataset-bar"
            :class="{ active: !!selectedDatasetMeta }"
          >
            <div class="sa-composer-label-block">
              <div class="sa-composer-label-row">
                <div class="sa-composer-label">选择数据集</div>
                <el-tooltip content="不预选时会按问题自动匹配最合适的数据集" placement="top" :show-after="300">
                  <span class="sa-ds-mode-chip" :class="{ active: !!selectedDatasetMeta }">
                    {{ selectedDatasetMeta ? '已选择' : '自动路由' }}
                  </span>
                </el-tooltip>
              </div>
              <div class="sa-composer-caption">
                {{ selectedDatasetMeta ? selectedDatasetMeta.dataset_name : '按问题自动匹配' }}
              </div>
            </div>
            <el-select
              v-model="datasetSelectValue"
              placeholder="自动路由数据集"
              size="small"
              class="sa-ds-select"
              popper-class="sa-ds-popper sa-dataset-popper"
              placement="top-start"
              :fallback-placements="['top-start']"
              @change="$emit('datasetChange', $event || null)"
            >
              <template #prefix>
                <span class="sa-ds-icon" aria-hidden="true"></span>
              </template>
              <el-option
                label="自动路由数据集"
                value=""
              >
                <div class="sa-ds-option sa-ds-option-auto">
                  <div class="sa-ds-option-main">
                    <div class="sa-ds-option-title">自动路由数据集</div>
                    <div class="sa-ds-option-meta">根据问题内容自动匹配业务口径</div>
                  </div>
                </div>
              </el-option>
              <el-option
                v-for="d in datasets"
                :key="d.id"
                :label="d.dataset_name"
                :value="d.id"
              >
                <div class="sa-ds-option">
                  <div class="sa-ds-option-main">
                    <div class="sa-ds-option-title">{{ d.dataset_name }}</div>
                    <div class="sa-ds-option-meta">
                      {{ d.business_domain || '未设置业务域' }}
                      <span v-if="d.dataset_code" class="sa-ds-option-sep">·</span>
                      <span v-if="d.dataset_code">{{ d.dataset_code }}</span>
                    </div>
                  </div>
                </div>
              </el-option>
            </el-select>
          </div>

          <div
            v-if="allowModelSelect"
            class="sa-composer-model-bar"
            :class="{ active: !!selectedModelMeta }"
          >
            <div class="sa-composer-label-block">
              <div class="sa-composer-label-row">
                <div class="sa-composer-label">AI 模型</div>
                <el-tooltip content="自动选择默认模型，失败时自动切换备用" placement="top" :show-after="300">
                  <span class="sa-model-mode-chip" :class="{ active: !!selectedModelMeta }">
                    {{ selectedModelMeta ? selectedModelMeta.name : 'AUTO' }}
                  </span>
                </el-tooltip>
              </div>
              <div class="sa-composer-caption">
                {{ selectedModelMeta ? selectedModelMeta.model : '默认模型 · 自动切换' }}
              </div>
            </div>
            <el-select
              v-model="modelSelectValue"
              placeholder="Auto"
              size="small"
              class="sa-model-select"
              popper-class="sa-ds-popper sa-model-popper"
              placement="top-start"
              :fallback-placements="['top-start']"
            >
              <template #prefix>
                <span class="sa-model-icon" aria-hidden="true">⚡</span>
              </template>
              <el-option
                label="Auto"
                value=""
              >
                <div class="sa-ds-option sa-model-option sa-ds-option-auto">
                  <div class="sa-ds-option-main">
                    <div class="sa-ds-option-title">Auto</div>
                  </div>
                </div>
              </el-option>
              <el-option
                v-for="m in aiModels"
                :key="m.id"
                :label="m.name"
                :value="m.id"
              >
                <div
                  class="sa-ds-option sa-model-option"
                  :class="{ 'is-default-model': m.is_default }"
                >
                  <div class="sa-ds-option-main">
                    <div class="sa-ds-option-title sa-model-option-title">
                      <span>{{ m.name }}</span>
                      <span v-if="m.is_default" class="sa-model-default-badge">默认模型</span>
                    </div>
                  </div>
                </div>
              </el-option>
            </el-select>
          </div>
        </div>
      </div>

      <div class="sa-composer-input-row">
        <div class="sa-textarea-wrap">
          <span class="sa-textarea-leading" aria-hidden="true"></span>
          <textarea
            ref="inputRef"
            v-model="modelQuery"
            class="sa-textarea"
            placeholder="请输入您的业务问题..."
            rows="1"
            :disabled="isRunning"
            @input="autoGrow"
            @keydown="handleKeydown"
          ></textarea>
          <div class="sa-composer-hint">Enter / Alt + Enter 发送，Shift + Enter 换行</div>
        </div>

        <button
          v-if="!isRunning && allowSend"
          class="sa-send-btn"
          aria-label="发送问题"
          @click="$emit('send')"
        >
          <span class="sa-send-icon" aria-hidden="true"></span>
        </button>

        <button
          v-else-if="isRunning && allowStop"
          class="sa-stop-btn"
          aria-label="停止执行"
          @click="$emit('stop')"
        >
          <span class="sa-stop-icon" aria-hidden="true"></span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'

const modelQuery = defineModel('query', { type: String, default: '' })
const modelDatasetId = defineModel('datasetId', { default: null })
const modelModelId = defineModel('modelId', { default: null })

const props = defineProps({
  datasets: {
    type: Array,
    default: () => []
  },
  aiModels: {
    type: Array,
    default: () => []
  },
  isRunning: {
    type: Boolean,
    default: false
  },
  allowSend: {
    type: Boolean,
    default: true
  },
  allowStop: {
    type: Boolean,
    default: true
  },
  allowDatasetSelect: {
    type: Boolean,
    default: true
  },
  allowModelSelect: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['send', 'stop', 'datasetChange'])

const inputRef = ref(null)
const datasetSelectValue = computed({
  get: () => modelDatasetId.value ?? '',
  set: value => { modelDatasetId.value = value === '' ? null : value },
})
const modelSelectValue = computed({
  get: () => modelModelId.value ?? '',
  set: value => { modelModelId.value = value === '' ? null : value },
})
const selectedDatasetMeta = computed(() => (
  (props.datasets || []).find(item => Number(item?.id) === Number(modelDatasetId.value)) || null
))
const selectedModelMeta = computed(() => (
  (props.aiModels || []).find(item => Number(item?.id) === Number(modelModelId.value)) || null
))

const resizeTextarea = () => {
  const textarea = inputRef.value
  if (!textarea) return
  textarea.style.height = 'auto'
  textarea.style.height = `${Math.min(textarea.scrollHeight, 132)}px`
}

const autoGrow = () => {
  resizeTextarea()
}

const handleKeydown = (event) => {
  if (event.key !== 'Enter') return
  if (event.shiftKey) return
  if (!props.allowSend || props.isRunning) return
  event.preventDefault()
  emit('send')
}

watch(modelQuery, () => nextTick(resizeTextarea))

onMounted(() => {
  nextTick(() => {
    resizeTextarea()
    inputRef.value?.focus()
  })
})
</script>

<style scoped>
.sa-composer {
  margin: 16px 22px 22px;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid rgba(29, 33, 41, 0.07);
  border-radius: 22px;
  padding: 14px 15px 15px;
  position: relative;
  overflow: hidden;
  box-shadow:
    0 10px 26px rgba(15, 23, 42, 0.04),
    0 1px 2px rgba(15, 23, 42, 0.03);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-composer.is-running {
  border-color: transparent;
  background:
    radial-gradient(circle at 12% 0%, rgba(20, 184, 166, 0.1), transparent 28%),
    radial-gradient(circle at 88% 100%, rgba(22, 93, 255, 0.1), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.99) 0%, rgba(247, 250, 255, 0.97) 100%);
  box-shadow:
    0 16px 38px rgba(22, 93, 255, 0.12),
    0 0 0 5px rgba(22, 93, 255, 0.06);
}

.sa-composer.is-running::before {
  content: '';
  position: absolute;
  inset: 0;
  padding: 3px;
  border-radius: inherit;
  background:
    conic-gradient(
      from var(--sa-composer-angle),
      rgba(22, 93, 255, 0.18),
      rgba(20, 184, 166, 0.95),
      rgba(255, 181, 71, 0.88),
      rgba(124, 58, 237, 0.86),
      rgba(22, 93, 255, 0.18)
    );
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  mask-composite: exclude;
  opacity: 0.98;
  pointer-events: none;
  animation: sa-composer-marquee 1.9s linear infinite;
}

.sa-composer-inner {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
  z-index: 1;
}

.sa-composer-top {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px 0 12px;
  border-bottom: 1px solid rgba(229, 230, 235, 0.76);
}

.sa-composer-selectors {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.sa-composer-dataset-bar {
  display: grid;
  grid-template-columns: minmax(0, 156px) minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  position: relative;
  min-width: 0;
  padding: 10px 12px 10px 14px;
  border-radius: 16px;
  border: 1px solid rgba(30, 41, 59, 0.1);
  background:
    linear-gradient(90deg, rgba(30, 41, 59, 0.035), transparent 34%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.035),
    inset 3px 0 0 rgba(37, 99, 235, 0.5);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.sa-composer-model-bar {
  display: grid;
  grid-template-columns: minmax(0, 136px) minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  position: relative;
  min-width: 0;
  padding: 10px 12px 10px 14px;
  border-radius: 16px;
  border: 1px solid rgba(30, 41, 59, 0.1);
  background:
    linear-gradient(90deg, rgba(30, 41, 59, 0.035), transparent 34%),
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.035),
    inset 3px 0 0 rgba(15, 118, 110, 0.5);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.sa-composer-dataset-bar:hover,
.sa-composer-model-bar:hover,
.sa-composer-dataset-bar.active,
.sa-composer-model-bar.active {
  transform: translateY(-1px);
}

.sa-composer-dataset-bar:hover,
.sa-composer-dataset-bar.active {
  border-color: rgba(37, 99, 235, 0.22);
  background:
    linear-gradient(90deg, rgba(37, 99, 235, 0.075), transparent 42%),
    linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
  box-shadow:
    0 0 0 1px rgba(37, 99, 235, 0.08),
    0 12px 24px rgba(15, 23, 42, 0.055),
    inset 3px 0 0 #2563eb;
}

.sa-composer-dataset-bar.active .sa-ds-select :deep(.el-select__wrapper) {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(239, 246, 255, 0.98) 100%);
  box-shadow:
    inset 0 0 0 1px rgba(37, 99, 235, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 3px rgba(37, 99, 235, 0.08),
    0 12px 24px rgba(37, 99, 235, 0.055);
}

.sa-composer-model-bar:hover,
.sa-composer-model-bar.active {
  border-color: rgba(15, 118, 110, 0.24);
  box-shadow:
    0 12px 24px rgba(15, 23, 42, 0.055),
    inset 3px 0 0 #0f766e;
}

.sa-composer-label-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.sa-composer-label-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sa-composer-label {
  font-size: 11px;
  font-weight: 760;
  letter-spacing: 0;
  text-transform: uppercase;
  color: #5b667a;
}

.sa-ds-mode-chip {
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(30, 41, 59, 0.06);
  color: #475569;
  font-size: 10px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  cursor: default;
  transition: all 0.2s ease;
}

.sa-ds-mode-chip:hover {
  background: #eaecf0;
}

.sa-ds-mode-chip.active {
  background: #1e293b;
  color: #ffffff;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12);
}

.sa-model-mode-chip {
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(30, 41, 59, 0.06);
  color: #475569;
  font-size: 10px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  max-width: 92px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
  transition: all 0.2s ease;
}

.sa-model-mode-chip:hover {
  background: rgba(30, 41, 59, 0.09);
}

.sa-model-mode-chip.active {
  background: #1e293b;
  color: #ffffff;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12);
}

.sa-ds-mode-chip.active:hover {
  background: #1e293b;
  color: #ffffff;
}

.sa-composer-caption {
  font-size: 11px;
  line-height: 1.5;
  color: #778397;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sa-ds-select {
  width: 100%;
}

.sa-ds-select :deep(.el-select__wrapper) {
  min-height: 42px;
  padding-left: 34px;
  padding-right: 12px;
  border-radius: 13px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  box-shadow:
    inset 0 0 0 1px rgba(30, 41, 59, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 8px 18px rgba(15, 23, 42, 0.035);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.sa-ds-select :deep(.el-select__wrapper.is-focused) {
  box-shadow:
    inset 0 0 0 1px rgba(37, 99, 235, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 3px rgba(37, 99, 235, 0.08),
    0 12px 24px rgba(15, 23, 42, 0.055);
}

.sa-ds-select :deep(.el-select__selected-item) {
  font-size: 12px;
  font-weight: 760;
  color: #1e293b;
}

.sa-ds-select :deep(.el-select__placeholder) {
  font-size: 12px;
  color: #9aa3b2;
}

.sa-ds-select :deep(.el-select__caret) {
  color: #64748b;
}

.sa-ds-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transform: translateY(-50%);
  pointer-events: none;
}

.sa-ds-icon::before,
.sa-ds-icon::after {
  content: '';
  position: absolute;
  border-radius: 4px;
}

.sa-ds-icon::before {
  inset: 1px;
  border: 1px solid rgba(30, 41, 59, 0.16);
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.sa-ds-icon::after {
  top: 4px;
  left: 5px;
  width: 6px;
  height: 1.5px;
  background: rgba(71, 85, 105, 0.58);
  box-shadow: 0 3px 0 rgba(71, 85, 105, 0.38), 0 6px 0 rgba(71, 85, 105, 0.24);
}

.sa-ds-option {
  display: flex;
  align-items: center;
  min-width: 0;
  position: relative;
  padding-left: 11px;
}

.sa-ds-option::before {
  content: '';
  position: absolute;
  left: 0;
  top: 5px;
  bottom: 5px;
  width: 3px;
  border-radius: 999px;
  background: #2563eb;
  opacity: 0.7;
}

.sa-model-option::before {
  background: #0f766e;
}

.sa-model-option.is-default-model {
  margin: -2px 0;
  padding: 8px 10px 8px 13px;
  border-radius: 10px;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.09), rgba(51, 65, 85, 0.035));
  box-shadow:
    inset 0 0 0 1px rgba(15, 118, 110, 0.14),
    inset 3px 0 0 rgba(15, 118, 110, 0.78);
}

.sa-model-option.is-default-model::before {
  display: none;
}

.sa-ds-option-auto::before {
  opacity: 1;
}

.sa-ds-option-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sa-ds-option-title {
  font-size: 12px;
  font-weight: 700;
  color: #243041;
  line-height: 1.4;
}

.sa-model-option-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.sa-model-option-title > span:first-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-ds-option-meta {
  font-size: 10px;
  line-height: 1.45;
  color: #8a94a6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sa-ds-option-sep {
  margin: 0 4px;
}

.sa-ds-option-auto .sa-ds-option-title {
  color: #165dff;
}

:deep(.sa-ds-popper.el-popper) {
  border-radius: 16px;
  border: 1px solid rgba(29, 33, 41, 0.08);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  padding: 6px;
}

:deep(.sa-ds-popper .el-select-dropdown) {
  max-height: min(320px, 42vh);
}

:deep(.sa-ds-popper .el-select-dropdown__wrap) {
  max-height: min(308px, calc(42vh - 12px));
  overflow-y: auto;
}

:deep(.sa-ds-popper .el-select-dropdown__wrap::-webkit-scrollbar) {
  width: 8px;
}

:deep(.sa-ds-popper .el-select-dropdown__wrap::-webkit-scrollbar-thumb) {
  border: 2px solid transparent;
  border-radius: 999px;
  background: rgba(100, 116, 139, 0.36);
  background-clip: padding-box;
}

:deep(.sa-ds-popper .el-select-dropdown__wrap::-webkit-scrollbar-track) {
  background: transparent;
}

:deep(.sa-ds-popper .el-select-dropdown__list) {
  padding: 0;
}

:deep(.sa-ds-popper .el-select-dropdown__item) {
  min-height: 46px;
  border-radius: 10px;
  padding-top: 6px;
  padding-bottom: 6px;
  color: #3d4756;
}

:deep(.sa-ds-popper .el-select-dropdown__item.is-hovering),
:deep(.sa-ds-popper .el-select-dropdown__item:hover) {
  background: #f5f8ff;
}

:deep(.sa-ds-popper .el-select-dropdown__item.is-selected) {
  background: #edf4ff;
}

:deep(.sa-dataset-popper .el-select-dropdown__item.is-hovering),
:deep(.sa-dataset-popper .el-select-dropdown__item:hover) {
  background: rgba(37, 99, 235, 0.07);
}

:deep(.sa-dataset-popper .el-select-dropdown__item.is-selected) {
  background:
    linear-gradient(90deg, rgba(37, 99, 235, 0.14), rgba(37, 99, 235, 0.055));
  box-shadow:
    inset 0 0 0 1px rgba(37, 99, 235, 0.14),
    inset 3px 0 0 #2563eb;
}

:deep(.sa-dataset-popper .el-select-dropdown__item.is-selected .sa-ds-option) {
  padding-right: 28px;
}

:deep(.sa-dataset-popper .el-select-dropdown__item.is-selected .sa-ds-option::before) {
  opacity: 0;
}

:deep(.sa-dataset-popper .el-select-dropdown__item.is-selected .sa-ds-option::after) {
  content: '';
  position: absolute;
  right: 8px;
  top: 50%;
  width: 12px;
  height: 7px;
  border-left: 2px solid #2563eb;
  border-bottom: 2px solid #2563eb;
  transform: translateY(-65%) rotate(-45deg);
}

:deep(.sa-dataset-popper .el-select-dropdown__item.is-selected .sa-ds-option-title) {
  color: #174ea6;
}

:deep(.sa-model-popper .el-select-dropdown__item.is-hovering),
:deep(.sa-model-popper .el-select-dropdown__item:hover) {
  background: rgba(15, 118, 110, 0.07);
}

:deep(.sa-model-popper .el-select-dropdown__item.is-selected) {
  background: rgba(15, 118, 110, 0.11);
}

:deep(.sa-model-popper .el-select-dropdown__item) {
  height: auto;
}

.sa-composer-input-row {
  display: flex;
  gap: 12px;
  align-items: stretch;
}

.sa-textarea-wrap {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px 0 0 22px;
}

.sa-textarea-leading {
  position: absolute;
  left: 0;
  top: 6px;
  width: 14px;
  height: 14px;
  pointer-events: none;
  transition: color 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-textarea-leading::before,
.sa-textarea-leading::after {
  content: '';
  position: absolute;
  border-radius: 999px;
  background: rgba(201, 205, 212, 0.8);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-textarea-leading::before {
  inset: 4px;
}

.sa-textarea-leading::after {
  inset: 0;
  opacity: 0.34;
}

.sa-textarea {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  min-height: 24px;
  max-height: 132px;
  resize: none;
  line-height: 1.7;
  color: #1d2129;
  background: transparent;
}

.sa-textarea::placeholder {
  color: #c9cdd4;
  font-size: 12px;
}

.sa-textarea:focus + .sa-composer-hint,
.sa-textarea-wrap:focus-within .sa-composer-hint {
  color: #6b7280;
}

.sa-textarea-wrap:focus-within .sa-textarea-leading {
  color: #165dff;
}

.sa-textarea-wrap:focus-within .sa-textarea-leading::before {
  background: rgba(22, 93, 255, 0.88);
}

.sa-textarea-wrap:focus-within .sa-textarea-leading::after {
  background: rgba(22, 93, 255, 0.2);
}

.sa-composer.is-running .sa-textarea-leading::before {
  background: rgba(20, 184, 166, 0.95);
}

.sa-composer.is-running .sa-textarea-leading::after {
  background: rgba(20, 184, 166, 0.24);
  animation: sa-leading-pulse 1.4s ease-in-out infinite;
}

.sa-composer:focus-within {
  border-color: #165dff;
  box-shadow:
    0 10px 26px rgba(15, 23, 42, 0.04),
    0 0 0 3px rgba(22, 93, 255, 0.1);
}

.sa-composer-hint {
  font-size: 11px;
  color: #97a0b3;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-send-btn,
.sa-stop-btn {
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  border-radius: 50%;
  border: 1px solid rgba(15, 23, 42, 0.08);
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(180deg, #334155 0%, #1e293b 100%);
  color: #ffffff;
  box-shadow:
    0 10px 20px rgba(15, 23, 42, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.14);
}

.sa-send-icon,
.sa-stop-icon {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}

.sa-send-icon {
  width: 18px;
  height: 18px;
  z-index: 1;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.sa-send-icon::before,
.sa-send-icon::after {
  content: '';
  position: absolute;
  box-sizing: border-box;
}

.sa-send-icon::before {
  inset: 2px 1px 2px 2px;
  background: currentColor;
  border-radius: 2px;
  clip-path: polygon(0 7%, 100% 50%, 0 93%, 24% 57%, 56% 50%, 24% 43%);
}

.sa-send-icon::after {
  left: 5px;
  top: 8px;
  width: 7px;
  height: 1.5px;
  background: rgba(30, 41, 59, 0.42);
  border-radius: 999px;
  transform: rotate(-8deg);
}

.sa-send-btn {
  color: #ffffff;
}

.sa-send-btn::before,
.sa-stop-btn::before {
  content: '';
  position: absolute;
  inset: 5px;
  border-radius: inherit;
  border: 1px solid rgba(255, 255, 255, 0.14);
  pointer-events: none;
}

.sa-send-btn:hover,
.sa-stop-btn:hover {
  transform: translateY(-1px);
  background:
    linear-gradient(180deg, #3b4a5f 0%, #233044 100%);
  box-shadow:
    0 12px 22px rgba(15, 23, 42, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.16);
}

.sa-send-btn:hover .sa-send-icon {
  transform: translate(1px, -1px);
}

.sa-send-btn:active,
.sa-stop-btn:active {
  transform: translateY(0) scale(0.96);
}

.sa-stop-btn {
  color: #ffffff;
}

.sa-stop-icon {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: currentColor;
}

@property --sa-composer-angle {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}

@keyframes sa-composer-marquee {
  to { --sa-composer-angle: 360deg; }
}

@keyframes sa-leading-pulse {
  0%, 100% { transform: scale(0.88); opacity: 0.55; }
  50% { transform: scale(1.18); opacity: 0.9; }
}

@media (max-width: 900px) {
  .sa-composer {
    margin: 14px 16px 16px;
  }

  .sa-composer-selectors {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .sa-composer-dataset-bar,
  .sa-composer-model-bar {
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
  }
}

.sa-model-select {
  width: 100%;
}

.sa-model-select :deep(.el-select__wrapper) {
  min-height: 42px;
  padding-left: 34px;
  padding-right: 12px;
  border-radius: 13px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  box-shadow:
    inset 0 0 0 1px rgba(30, 41, 59, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 8px 18px rgba(15, 23, 42, 0.035);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.sa-model-select :deep(.el-select__wrapper.is-focused) {
  box-shadow:
    inset 0 0 0 1px rgba(15, 118, 110, 0.32),
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 3px rgba(15, 118, 110, 0.08),
    0 12px 24px rgba(15, 23, 42, 0.055);
}

.sa-model-select :deep(.el-select__selected-item) {
  font-size: 12px;
  font-weight: 760;
  color: #1e293b;
}

.sa-model-select :deep(.el-select__placeholder) {
  font-size: 12px;
  color: #9aa3b2;
}

.sa-model-select :deep(.el-select__caret) {
  color: #64748b;
}

.sa-model-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background:
    linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  color: #ffffff;
  font-size: 11px;
  line-height: 1;
  border: 1px solid rgba(15, 118, 110, 0.22);
  color: #0f766e;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.045);
  pointer-events: none;
}

.sa-model-mode-chip {
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
  font-size: 10px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  max-width: 92px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
  transition: all 0.2s ease;
}

.sa-model-mode-chip:hover {
  background: rgba(245, 158, 11, 0.18);
}

.sa-model-mode-chip.active {
  background: linear-gradient(135deg, #f59e0b 0%, #7c3aed 100%);
  color: #ffffff;
  box-shadow: 0 6px 14px rgba(124, 58, 237, 0.18);
}

.sa-model-mode-chip.active:hover {
  background: linear-gradient(135deg, #e58f08 0%, #6d28d9 100%);
}

.sa-model-default-badge {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  height: 18px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0;
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.18);
}
</style>
