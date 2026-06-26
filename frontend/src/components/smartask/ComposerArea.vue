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
              <span class="sa-ds-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" focusable="false">
                  <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
                  <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"></path>
                </svg>
              </span>
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

            <textarea
              ref="inputRef"
              v-model="modelQuery"
              class="sa-textarea"
              placeholder="请输入您的业务问题，支持自然语言提问或指令..."
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
                    <span class="sa-model-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" focusable="false">
                        <path d="M13.4 2.4 5.9 13.1h5.2l-.6 8.5 7.6-11h-5.3l.6-8.2Z" fill="currentColor" />
                      </svg>
                    </span>
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
                  <span class="sa-send-icon" aria-hidden="true">
                    <svg class="sa-send-plane" viewBox="0 0 24 24" fill="currentColor" focusable="false">
                      <path d="M9.78 18.65l.28-4.28 7.68-6.95c.33-.29-.07-.45-.51-.16l-9.5 5.98-4.15-1.3c-.9-.28-.92-.9.19-1.33L20.2 3.44c.73-.27 1.37.17 1.13 1.2l-2.8 13.23c-.2 1-.8 1.25-1.63.78l-4.25-3.13-2.05 1.98-1.02 1.15z" />
                    </svg>
                  </span>
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
  width: 100%;
  margin: 0 0 14px;
  box-sizing: border-box;
  background: #FFFFFF;
  border: 1px solid rgba(17, 24, 39, 0.06);
  border-radius: 20px;
  padding: 12px 16px 12px 18px;
  position: relative;
  overflow: hidden;
  box-shadow:
    0 12px 28px rgba(15, 23, 42, 0.06),
    0 1px 2px rgba(15, 23, 42, 0.025);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sa-composer.is-running {
  border-color: rgba(230, 31, 36, 0.14);
  background: #FFFFFF;
  box-shadow:
    0 12px 28px rgba(15, 23, 42, 0.075),
    0 0 0 3px rgba(230, 31, 36, 0.035);
}

.sa-composer.is-running::before {
  content: none;
}

.sa-composer-inner {
  position: relative;
  z-index: 1;
}

.sa-composer-body {
  display: grid;
  grid-template-columns: minmax(260px, max-content) minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
}

.sa-side-dataset-card {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  min-width: 260px;
  width: max-content;
  padding: 8px 0 8px 18px;
  border-radius: 0;
  border: 1px solid transparent;
  background: #FFFFFF;
  box-shadow: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  min-height: 74px;
}

.sa-side-dataset-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 0 999px 999px 0;
  background: #F51F19;
  pointer-events: none;
}

.sa-side-dataset-card.active,
.sa-side-dataset-card:hover {
  border-color: transparent;
  box-shadow: none;
}

.sa-side-dataset-card.active::before,
.sa-side-dataset-card:hover::before {
  background: #F51F19;
}

.sa-side-dataset-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sa-side-dataset-label {
  font-size: 15px;
  font-weight: 800;
  color: #111827;
  line-height: 1.2;
}

.sa-side-ds-select {
  width: max-content;
  min-width: 100%;
  margin-top: auto;
}

.sa-side-ds-select :deep(.el-select__wrapper) {
  min-height: 32px;
  min-width: 230px;
  padding-left: 34px;
  padding-right: 12px;
  border-radius: 12px;
  background: #F3F4F6;
  box-shadow: none;
}

.sa-side-dataset-card.active .sa-side-ds-select :deep(.el-select__wrapper) {
  box-shadow: none;
}

.sa-side-ds-select :deep(.el-select__selected-item),
.sa-side-ds-select :deep(.el-select__placeholder) {
  font-size: 12px;
  line-height: 1.2;
  font-weight: 800;
  white-space: nowrap;
}

.sa-side-ds-select :deep(.el-select__selected-item) {
  max-width: none;
  color: #111827;
}

.sa-side-ds-select :deep(.el-select__selection) {
  min-width: 0;
  width: max-content;
}

.sa-side-ds-select :deep(.el-select__selected-item span) {
  overflow: visible;
  text-overflow: clip;
}

.sa-side-ds-select :deep(.el-select__placeholder) {
  color: #8B95A1;
}

.sa-side-ds-select :deep(.el-select__caret) {
  color: #111827;
  font-weight: 900;
}

.sa-composer-main {
  min-width: 0;
}

.sa-ds-mode-chip {
  height: 20px;
  padding: 0 9px;
  border-radius: 999px;
  background: rgba(17, 24, 39, 0.74);
  color: #FFFFFF;
  font-size: 10px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.sa-ds-mode-chip.active {
  background: rgba(17, 24, 39, 0.82);
  color: #ffffff;
  box-shadow: none;
}

.sa-ds-icon {
  position: absolute;
  left: 11px;
  top: 50%;
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transform: translateY(-50%);
  pointer-events: none;
  color: #374151;
}

.sa-ds-icon svg {
  width: 16px;
  height: 16px;
  display: block;
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
  background: rgba(17, 24, 39, 0.82);
  opacity: 0.7;
}

.sa-model-option::before {
  background: rgba(17, 24, 39, 0.82);
}

.sa-model-option.is-default-model::before {
  width: 4px;
  background: rgba(230, 31, 36, 0.84);
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
  color: #1A1A1A;
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
  background: rgba(26, 26, 26, 0.07);
}

:deep(.sa-model-popper .el-select-dropdown__item.is-hovering),
:deep(.sa-model-popper .el-select-dropdown__item:hover) {
  background: rgba(26, 26, 26, 0.07);
}

.sa-textarea-wrap {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 72px;
  padding: 14px 126px 12px 18px;
  border-radius: 18px;
  border: 1px solid rgba(17, 24, 39, 0.07);
  background: #FFFFFF;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 0 0 1px rgba(17, 24, 39, 0.015);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.sa-textarea-wrap:focus-within {
  border-color: rgba(17, 24, 39, 0.09);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 0 0 3px rgba(17, 24, 39, 0.025);
}

.sa-composer-status-capsule {
  position: absolute;
  top: 8px;
  left: calc(100% - 176px);
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 210px;
  min-width: 0;
  padding: 6px 9px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(17, 24, 39, 0.06);
  box-shadow:
    0 12px 22px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  pointer-events: none;
  white-space: nowrap;
}

.sa-composer-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(230, 31, 36, 0.82);
  flex: 0 0 auto;
  animation: pulse 1.2s ease-in-out infinite;
}

.sa-composer-status-capsule.completed .sa-composer-status-dot {
  background: #10B981;
  animation: none;
}

.sa-composer-status-capsule.error .sa-composer-status-dot {
  background: rgba(17, 24, 39, 0.88);
  animation: none;
}

.sa-composer-status-text {
  min-width: 0;
  color: #374151;
  font-size: 10px;
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

.sa-textarea {
  display: block;
  width: 100%;
  flex: 1;
  border: none;
  outline: none !important;
  appearance: none;
  -webkit-appearance: none;
  padding: 0;
  margin: 0;
  box-shadow: none !important;
  font-size: 14px;
  min-height: 20px;
  max-height: 132px;
  resize: none;
  line-height: 1.45;
  color: #111827;
  background: transparent;
  caret-color: #E61F24;
  margin-top: 0;
}

.sa-textarea:focus,
.sa-textarea:focus-visible {
  border: none;
  outline: none !important;
  box-shadow: none !important;
}

.sa-textarea::placeholder {
  color: #9AA3AF;
  font-size: 14px;
  font-weight: 680;
}

.sa-composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: auto;
  min-height: 36px;
}

.sa-composer-hint {
  font-size: 11px;
  color: #6B7280;
  line-height: 1.2;
  font-weight: 650;
  display: inline-flex;
  align-items: center;
  height: 36px;
}

.sa-composer-actions {
  position: absolute;
  right: 14px;
  bottom: 12px;
  display: flex;
  align-items: center;
  gap: 9px;
  margin-left: auto;
  height: 36px;
}

.sa-model-corner-select {
  width: 120px;
}

.sa-model-corner-select :deep(.el-select__wrapper) {
  min-height: 36px;
  padding-left: 34px;
  padding-right: 12px;
  border-radius: 999px;
  background: #ffffff;
  box-shadow:
    inset 0 0 0 1px #E5E7EB;
}

.sa-model-corner-select :deep(.el-select__selected-item),
.sa-model-corner-select :deep(.el-select__placeholder) {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  color: #111827;
}

.sa-model-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(180deg, #F8F9FA 0%, #ffffff 100%);
  border: 1px solid rgba(230, 31, 36, 0.16);
  color: #E61F24;
  color: #111827;
  box-shadow: none;
  pointer-events: none;
}

.sa-model-icon svg {
  width: 12px;
  height: 12px;
  display: block;
}

.sa-send-btn,
.sa-stop-btn {
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
  border-radius: 50%;
  border: 1px solid rgba(245, 31, 25, 0.18);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  color: #ffffff;
  box-shadow:
    0 4px 12px rgba(245, 31, 25, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.18);
  transition: background-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.sa-send-btn {
  background: #F51F19;
}

.sa-send-btn:hover {
  background: #DC1C17;
  box-shadow:
    0 6px 16px rgba(245, 31, 25, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.sa-stop-btn {
  background: rgba(17, 24, 39, 0.88);
}

.sa-send-icon,
.sa-stop-icon {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}

.sa-send-icon {
  width: 20px;
  height: 20px;
  transform: translate(-1px, 0.5px);
}

.sa-send-icon svg,
.sa-send-plane {
  width: 100%;
  height: 100%;
  display: block;
}

.sa-stop-icon {
  width: 12px;
  height: 12px;
  border-radius: 2.5px;
  background: currentColor;
}

.sa-model-default-badge {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  height: 18px;
  padding: 0 7px;
  border-radius: 8px;
  background: rgba(230, 31, 36, 0.08);
  color: rgba(230, 31, 36, 0.88);
  font-size: 10px;
  font-weight: 800;
  box-shadow: inset 0 0 0 1px rgba(230, 31, 36, 0.14);
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
    margin: 0 0 10px;
    padding: 12px;
  }

  .sa-composer-body {
    grid-template-columns: 1fr;
    gap: 10px;
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
    position: static;
    justify-content: space-between;
  }

  .sa-textarea-wrap {
    padding-right: 14px;
  }

  .sa-model-corner-select {
    flex: 1;
  }

  .sa-composer-status-capsule {
    display: none;
  }
}
</style>
