<template>
  <div class="sa-composer">
    <div class="sa-composer-inner">
      <div v-if="allowDatasetSelect || allowModelSelect" class="sa-composer-top">
        <div class="sa-composer-selectors">
          <div v-if="allowDatasetSelect" class="sa-composer-dataset-bar">
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
              popper-class="sa-ds-popper"
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

          <div v-if="allowModelSelect" class="sa-composer-model-bar">
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
              popper-class="sa-ds-popper"
            >
              <template #prefix>
                <span class="sa-model-icon" aria-hidden="true">⚡</span>
              </template>
              <el-option
                label="Auto"
                value=""
              >
                <div class="sa-ds-option sa-ds-option-auto">
                  <div class="sa-ds-option-main">
                    <div class="sa-ds-option-title">Auto</div>
                    <div class="sa-ds-option-meta">自动选择默认模型，失败时切换备用</div>
                  </div>
                </div>
              </el-option>
              <el-option
                v-for="m in aiModels"
                :key="m.id"
                :label="m.name"
                :value="m.id"
              >
                <div class="sa-ds-option">
                  <div class="sa-ds-option-main">
                    <div class="sa-ds-option-title">{{ m.name }}</div>
                    <div class="sa-ds-option-meta">
                      {{ m.model }}
                      <span v-if="m.is_default" class="sa-model-default-badge">默认</span>
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
            @keydown.enter.exact.prevent="allowSend && !isRunning && $emit('send')"
          ></textarea>
          <div class="sa-composer-hint">Enter 发送，Shift + Enter 换行</div>
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

defineEmits(['send', 'stop', 'datasetChange'])

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
  box-shadow:
    0 10px 26px rgba(15, 23, 42, 0.04),
    0 1px 2px rgba(15, 23, 42, 0.03);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-composer-inner {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sa-composer-top {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 11px;
  border-bottom: 1px solid rgba(229, 230, 235, 0.76);
}

.sa-composer-selectors {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.sa-composer-dataset-bar {
  display: grid;
  grid-template-columns: minmax(0, 140px) minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.sa-composer-model-bar {
  display: grid;
  grid-template-columns: minmax(0, 120px) minmax(0, 1fr);
  gap: 12px;
  align-items: center;
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
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8b93a6;
}

.sa-ds-mode-chip {
  height: 18px;
  padding: 0 8px;
  border-radius: 999px;
  background: #f2f3f5;
  color: #7f8796;
  font-size: 10px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  cursor: default;
  transition: all 0.2s ease;
}

.sa-ds-mode-chip:hover {
  background: #eaecf0;
}

.sa-ds-mode-chip.active {
  background: #edf4ff;
  color: #165dff;
}

.sa-ds-mode-chip.active:hover {
  background: #dde9ff;
}

.sa-composer-caption {
  font-size: 11px;
  line-height: 1.5;
  color: #a0a8b8;
}

.sa-ds-select {
  width: 100%;
}

.sa-ds-select :deep(.el-select__wrapper) {
  min-height: 38px;
  padding-left: 30px;
  padding-right: 10px;
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(250, 252, 255, 0.98) 0%, rgba(243, 247, 255, 0.94) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 1px 2px rgba(15, 23, 42, 0.03);
}

.sa-ds-select :deep(.el-select__wrapper.is-focused) {
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 3px rgba(22, 93, 255, 0.1);
}

.sa-ds-select :deep(.el-select__selected-item) {
  font-size: 12px;
  font-weight: 600;
  color: #324055;
}

.sa-ds-select :deep(.el-select__placeholder) {
  font-size: 12px;
  color: #9aa3b2;
}

.sa-ds-select :deep(.el-select__caret) {
  color: #7b8798;
}

.sa-ds-icon {
  position: absolute;
  left: 11px;
  top: 50%;
  width: 14px;
  height: 14px;
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
  border: 1px solid rgba(84, 100, 126, 0.34);
  background:
    linear-gradient(180deg, rgba(240, 244, 255, 0.9) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.sa-ds-icon::after {
  top: 3px;
  left: 4px;
  width: 6px;
  height: 1.5px;
  background: rgba(84, 100, 126, 0.45);
  box-shadow: 0 3px 0 rgba(84, 100, 126, 0.28), 0 6px 0 rgba(84, 100, 126, 0.2);
}

.sa-ds-option {
  display: flex;
  align-items: center;
  min-width: 0;
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
  width: 40px;
  height: 40px;
  min-width: 40px;
  min-height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(29, 33, 41, 0.08);
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.sa-send-icon,
.sa-stop-icon {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}

.sa-send-icon {
  width: 12px;
  height: 12px;
}

.sa-send-icon::before,
.sa-send-icon::after {
  content: '';
  position: absolute;
  box-sizing: border-box;
}

.sa-send-icon::before {
  left: 5px;
  top: 4px;
  width: 2px;
  height: 7px;
  background: currentColor;
  border-radius: 999px;
}

.sa-send-icon::after {
  left: 2px;
  top: 1px;
  width: 8px;
  height: 8px;
  background: transparent;
  border-top: 2px solid currentColor;
  border-left: 2px solid currentColor;
  border-radius: 0;
  transform: rotate(45deg);
}

.sa-send-btn {
  background: linear-gradient(180deg, #7a7e84 0%, #666a70 100%);
  color: #fff;
  box-shadow:
    0 8px 18px rgba(95, 99, 104, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.14);
}

.sa-send-btn:hover {
  transform: translateY(-1px) scale(1.01);
  box-shadow:
    0 10px 20px rgba(95, 99, 104, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.sa-send-btn:active {
  transform: scale(0.9);
}

.sa-stop-btn {
  background: linear-gradient(180deg, #d8dadd 0%, #c7cacf 100%);
  color: #1f2329;
  border: 1px solid rgba(29, 33, 41, 0.06);
  box-shadow:
    0 6px 14px rgba(15, 23, 42, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.28);
}

.sa-stop-btn:hover {
  background: linear-gradient(180deg, #dee0e3 0%, #cfd2d7 100%);
  transform: translateY(-1px);
}

.sa-stop-icon {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: currentColor;
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
  min-height: 38px;
  padding-left: 30px;
  padding-right: 10px;
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(250, 252, 255, 0.98) 0%, rgba(243, 247, 255, 0.94) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 1px 2px rgba(15, 23, 42, 0.03);
}

.sa-model-select :deep(.el-select__wrapper.is-focused) {
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 3px rgba(22, 93, 255, 0.1);
}

.sa-model-select :deep(.el-select__selected-item) {
  font-size: 12px;
  font-weight: 600;
  color: #324055;
}

.sa-model-select :deep(.el-select__placeholder) {
  font-size: 12px;
  color: #9aa3b2;
}

.sa-model-select :deep(.el-select__caret) {
  color: #7b8798;
}

.sa-model-icon {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  pointer-events: none;
}

.sa-model-mode-chip {
  height: 18px;
  padding: 0 8px;
  border-radius: 999px;
  background: #f2f3f5;
  color: #7f8796;
  font-size: 10px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
  transition: all 0.2s ease;
}

.sa-model-mode-chip:hover {
  background: #eaecf0;
}

.sa-model-mode-chip.active {
  background: #e8f3ff;
  color: #165dff;
}

.sa-model-mode-chip.active:hover {
  background: #dae5ff;
}

.sa-model-default-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 0 5px;
  height: 14px;
  line-height: 14px;
  border-radius: 4px;
  background: #e8f3ff;
  color: #165dff;
  font-size: 9px;
  font-weight: 700;
}
</style>
