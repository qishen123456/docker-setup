<template>
  <div class="sa-composer" :class="{ 'is-running': isRunning }">
    <div class="sa-composer-inner">
      <div class="sa-composer-body">
        <div
          v-if="allowDatasetSelect"
          class="sa-side-dataset-card"
          :class="{ active: !!selectedDatasetMeta }"
        >
          <div class="sa-side-dataset-head">
            <div class="sa-side-dataset-label">数据集</div>
            <span class="sa-ds-mode-chip" :class="{ active: !!selectedDatasetMeta }">
              {{ selectedDatasetMeta ? '已选择' : '自动路由' }}
            </span>
          </div>
          <el-select
            v-model="datasetSelectValue"
            placeholder="自动路由数据集"
            size="small"
            class="sa-side-ds-select"
            popper-class="sa-ds-popper sa-dataset-popper"
            placement="top-start"
            :fallback-placements="['top-start']"
            @change="$emit('datasetChange', $event || null)"
          >
            <template #prefix>
              <span class="sa-ds-icon" aria-hidden="true"></span>
            </template>
            <el-option label="自动路由数据集" value="">
              <div class="sa-ds-option sa-ds-option-auto">
                <div class="sa-ds-option-main">
                  <div class="sa-ds-option-title">自动路由数据集</div>
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
                </div>
              </div>
            </el-option>
          </el-select>
        </div>

        <div class="sa-composer-main">
          <div class="sa-textarea-wrap">
            <div v-if="statusText" class="sa-composer-status-capsule" :class="statusTone">
              <span class="sa-composer-status-dot"></span>
              <span class="sa-composer-status-text">{{ statusText }}</span>
              <span v-if="statusElapsed" class="sa-composer-status-time">{{ statusElapsed }}</span>
            </div>

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

            <div class="sa-composer-footer">
              <div class="sa-composer-hint">Enter 发送，Shift + Enter 换行</div>

              <div class="sa-composer-actions">
                <el-select
                  v-if="allowModelSelect"
                  v-model="modelSelectValue"
                  placeholder="Auto"
                  size="small"
                  class="sa-model-corner-select"
                  popper-class="sa-ds-popper sa-model-popper"
                  placement="top-start"
                  :fallback-placements="['top-start']"
                >
                  <template #prefix>
                    <span class="sa-model-icon" aria-hidden="true">⚡</span>
                  </template>
                  <el-option label="Auto" value="">
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
        </div>
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
  },
  statusText: {
    type: String,
    default: ''
  },
  statusElapsed: {
    type: String,
    default: ''
  },
  statusTone: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['send', 'stop', 'datasetChange'])

const inputRef = ref(null)

const datasetSelectValue = computed({
  get: () => modelDatasetId.value ?? '',
  set: value => { modelDatasetId.value = value === '' ? null : value }
})

const modelSelectValue = computed({
  get: () => modelModelId.value ?? '',
  set: value => { modelModelId.value = value === '' ? null : value }
})

const selectedDatasetMeta = computed(() => (
  (props.datasets || []).find(item => Number(item?.id) === Number(modelDatasetId.value)) || null
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
  margin: 10px 18px 16px;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 18px;
  padding: 10px 11px 11px;
  position: relative;
  overflow: hidden;
  box-shadow:
    0 8px 20px rgba(0, 0, 0, 0.04),
    0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-composer.is-running {
  border-color: rgba(26, 26, 26, 0.14);
  background:
    radial-gradient(circle at 12% 0%, rgba(26, 26, 26, 0.05), transparent 28%),
    radial-gradient(circle at 88% 100%, rgba(26, 26, 26, 0.05), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.99) 0%, rgba(243, 244, 246, 0.97) 100%);
  box-shadow:
    0 16px 38px rgba(0, 0, 0, 0.08),
    0 0 0 4px rgba(26, 26, 26, 0.04);
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
      rgba(26, 26, 26, 0.12),
      rgba(26, 26, 26, 0.8),
      rgba(26, 26, 26, 0.7),
      rgba(107, 114, 128, 0.7),
      rgba(26, 26, 26, 0.12)
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
  position: relative;
  z-index: 1;
}

.sa-composer-body {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 8px;
  align-items: stretch;
}

.sa-side-dataset-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
  padding: 8px 9px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: #ffffff;
  box-shadow:
    0 6px 14px rgba(0, 0, 0, 0.03),
    inset 3px 0 0 #E61F24;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  min-height: 76px;
}

.sa-side-dataset-card.active,
.sa-side-dataset-card:hover {
  border-color: rgba(26, 26, 26, 0.18);
  box-shadow:
    0 0 0 1px rgba(26, 26, 26, 0.06),
    0 12px 24px rgba(0, 0, 0, 0.055),
    inset 3px 0 0 #E61F24;
}

.sa-side-dataset-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.sa-side-dataset-label {
  font-size: 11px;
  font-weight: 800;
  color: #111827;
  line-height: 1.2;
}

.sa-side-ds-select {
  width: 100%;
  margin-top: auto;
}

.sa-side-ds-select :deep(.el-select__wrapper) {
  min-height: 31px;
  padding-left: 28px;
  border-radius: 9px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  box-shadow:
    inset 0 0 0 1px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.sa-side-dataset-card.active .sa-side-ds-select :deep(.el-select__wrapper) {
  box-shadow:
    inset 0 0 0 1px rgba(26, 26, 26, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 0 0 3px rgba(26, 26, 26, 0.06);
}

.sa-side-ds-select :deep(.el-select__selected-item),
.sa-side-ds-select :deep(.el-select__placeholder) {
  font-size: 11px;
  line-height: 1.2;
}

.sa-side-ds-select :deep(.el-select__selected-item) {
  max-width: 148px;
}

.sa-side-ds-select :deep(.el-select__caret) {
  color: #9CA3AF;
}

.sa-composer-main {
  min-width: 0;
}

.sa-ds-mode-chip {
  height: 16px;
  padding: 0 6px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.06);
  color: #6B7280;
  font-size: 8px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.sa-ds-mode-chip.active {
  background: #1A1A1A;
  color: #ffffff;
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.12);
}

.sa-ds-icon {
  position: absolute;
  left: 9px;
  top: 50%;
  width: 13px;
  height: 13px;
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
  border: 1px solid rgba(0, 0, 0, 0.16);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.sa-ds-icon::after {
  top: 4px;
  left: 5px;
  width: 6px;
  height: 1.5px;
  background: rgba(107, 114, 128, 0.58);
  box-shadow: 0 3px 0 rgba(107, 114, 128, 0.38), 0 6px 0 rgba(107, 114, 128, 0.24);
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
  border-radius: 8px;
  background: #E61F24;
  opacity: 0.7;
}

.sa-model-option::before {
  background: #E61F24;
}

.sa-model-option.is-default-model::before {
  width: 4px;
  background: #E61F24;
  opacity: 1;
}

.sa-ds-option-main {
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.sa-ds-option-title {
  font-size: 11px;
  font-weight: 700;
  color: #374151;
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

.sa-ds-option-auto .sa-ds-option-title {
  color: #E61F24;
}

:deep(.sa-ds-popper.el-popper) {
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.12);
  padding: 6px;
}

:deep(.sa-ds-popper .el-select-dropdown__list) {
  padding: 0;
}

:deep(.sa-ds-popper .el-select-dropdown__item) {
  min-height: 38px;
  border-radius: 10px;
  padding-top: 8px;
  padding-bottom: 8px;
  color: #374151;
}

:deep(.sa-dataset-popper .el-select-dropdown__item.is-hovering),
:deep(.sa-dataset-popper .el-select-dropdown__item:hover) {
  background: rgba(230, 31, 36, 0.07);
}

:deep(.sa-model-popper .el-select-dropdown__item.is-hovering),
:deep(.sa-model-popper .el-select-dropdown__item:hover) {
  background: rgba(230, 31, 36, 0.07);
}

.sa-textarea-wrap {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 76px;
  padding: 7px 10px 8px 22px;
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #ffffff;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 8px 16px rgba(0, 0, 0, 0.03);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.sa-textarea-wrap:focus-within {
  border-color: rgba(26, 26, 26, 0.22);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 8px 16px rgba(0, 0, 0, 0.04),
    0 0 0 3px rgba(26, 26, 26, 0.05);
}

.sa-composer-status-capsule {
  position: absolute;
  top: 8px;
  left: calc(100% - 170px);
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 250px;
  min-width: 0;
  padding: 7px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow:
    0 8px 18px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  pointer-events: none;
  white-space: nowrap;
}

.sa-composer-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #E61F24;
  flex: 0 0 auto;
  animation: pulse 1.2s ease-in-out infinite;
}

.sa-composer-status-capsule.completed .sa-composer-status-dot {
  background: #10B981;
  animation: none;
}

.sa-composer-status-capsule.error .sa-composer-status-dot {
  background: #E61F24;
  animation: none;
}

.sa-composer-status-text {
  min-width: 0;
  color: #374151;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-composer-status-time {
  color: #9CA3AF;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  flex: 0 0 auto;
  white-space: nowrap;
}

.sa-textarea-leading {
  position: absolute;
  left: 10px;
  top: 12px;
  width: 12px;
  height: 12px;
  pointer-events: none;
}

.sa-textarea-leading::before,
.sa-textarea-leading::after {
  content: '';
  position: absolute;
  border-radius: 8px;
  background: rgba(26, 26, 26, 0.75);
}

.sa-textarea-leading::before {
  inset: 4px;
}

.sa-textarea-leading::after {
  inset: 0;
  opacity: 0.28;
}

.sa-textarea {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  min-height: 24px;
  max-height: 132px;
  resize: none;
  line-height: 1.45;
  color: #111827;
  background: transparent;
}

.sa-textarea::placeholder {
  color: #9CA3AF;
  font-size: 13px;
}

.sa-composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
}

.sa-composer-hint {
  font-size: 10px;
  color: #6B7280;
  line-height: 1.2;
}

.sa-composer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.sa-model-corner-select {
  width: 118px;
}

.sa-model-corner-select :deep(.el-select__wrapper) {
  min-height: 31px;
  padding-left: 30px;
  border-radius: 9px;
  background: #ffffff;
  box-shadow:
    inset 0 0 0 1px rgba(0, 0, 0, 0.08),
    0 6px 12px rgba(0, 0, 0, 0.035);
}

.sa-model-corner-select :deep(.el-select__selected-item),
.sa-model-corner-select :deep(.el-select__placeholder) {
  font-size: 11px;
  font-weight: 700;
  line-height: 1.2;
}

.sa-model-icon {
  position: absolute;
  left: 9px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(180deg, #F8F9FA 0%, #ffffff 100%);
  border: 1px solid rgba(26, 26, 26, 0.14);
  color: #1A1A1A;
  font-size: 10px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.04);
  pointer-events: none;
}

.sa-send-btn,
.sa-stop-btn {
  width: 34px;
  height: 34px;
  min-width: 34px;
  min-height: 34px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.08);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  color: #ffffff;
  box-shadow:
    0 8px 16px rgba(0, 0, 0, 0.13),
    inset 0 1px 0 rgba(255, 255, 255, 0.14);
}

.sa-send-btn {
  background: #E61F24;
}

.sa-stop-btn {
  background: #1A1A1A;
}

.sa-send-icon,
.sa-stop-icon {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}

.sa-send-icon {
  width: 16px;
  height: 16px;
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
  background: rgba(255, 255, 255, 0.45);
  border-radius: 8px;
  transform: rotate(-8deg);
}

.sa-stop-icon {
  width: 9px;
  height: 9px;
  border-radius: 2px;
  background: currentColor;
}

.sa-model-default-badge {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  height: 18px;
  padding: 0 7px;
  border-radius: 8px;
  background: rgba(26, 26, 26, 0.08);
  color: #1A1A1A;
  font-size: 10px;
  font-weight: 800;
  box-shadow: inset 0 0 0 1px rgba(26, 26, 26, 0.12);
}

@property --sa-composer-angle {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}

@keyframes sa-composer-marquee {
  to { --sa-composer-angle: 360deg; }
}

@media (max-width: 900px) {
  .sa-composer {
    margin: 10px 14px 14px;
  }

  .sa-composer-body {
    grid-template-columns: 1fr;
  }

  .sa-side-dataset-card {
    order: 2;
  }

  .sa-composer-main {
    order: 1;
  }

  .sa-composer-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .sa-composer-actions {
    width: 100%;
    justify-content: space-between;
  }

  .sa-model-corner-select {
    flex: 1;
  }

  .sa-composer-status-capsule {
    display: none;
  }
}
</style>
