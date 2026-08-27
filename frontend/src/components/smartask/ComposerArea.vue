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
          <div class="sa-textarea-wrap" :class="{ 'is-running': isRunning, 'has-query': hasQuery }">
            <div v-if="isRunning || disabled" class="sa-composer-running-mask" aria-hidden="true">
              <div class="sa-composer-running-panel">
                <span class="sa-composer-running-line"></span>
                <span class="sa-composer-running-text">{{ disabled ? '正在查看历史任务，请先返回执行中的对话' : '正在生成结果，输入区暂不可编辑' }}</span>
              </div>
            </div>

            <textarea
              ref="inputRef"
              v-model="modelQuery"
              class="sa-textarea"
              placeholder="请输入您的业务问题，支持自然语言提问或指令..."
              rows="2"
              :disabled="isRunning || disabled"
              @input="autoGrow"
              @keydown="handleKeydown"
            ></textarea>
            <div v-if="!statusText && !hasQuery" class="sa-composer-hint sa-composer-hint-float">Enter 发送，Shift + Enter 换行</div>

            <div class="sa-composer-footer">
              <div v-if="statusText" class="sa-composer-status-capsule" :class="statusTone">
                <span class="sa-composer-status-dot"></span>
                <span class="sa-composer-status-text">{{ statusText }}</span>
                <span v-if="statusElapsed" class="sa-composer-status-time">{{ statusElapsed }}</span>
              </div>

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
                          <div class="sa-model-option-left">
                            <span class="sa-model-icon-mini" aria-hidden="true">
                              <svg viewBox="0 0 24 24" focusable="false"><path d="M13.4 2.4 5.9 13.1h5.2l-.6 8.5 7.6-11h-5.3l.6-8.2Z" fill="currentColor"/></svg>
                            </span>
                            <span class="sa-model-option-name">{{ m.name }}</span>
                            <span v-if="m.is_default" class="sa-model-default-badge">默认</span>
                          </div>
                          <div class="sa-model-option-right">
                            <span v-if="m.channel_display_name" class="sa-model-option-channel">
                              {{ m.channel_display_name }}
                            </span>
                            <span v-if="m.is_default" class="sa-model-check" aria-hidden="true">✓</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-option>
                </el-select>

                <!-- 语音输入：WorkBuddy 式录音条（桌面点击开始/结束，移动端按住说话） -->
                <button
                  v-if="canRecord && recorderState === 'idle' && !isRunning && !disabled"
                  class="sa-mic-btn"
                  aria-label="语音输入"
                  @click="handleMicClick"
                  @touchstart.prevent="handleMicTouchStart"
                  @touchend.prevent="handleMicTouchEnd"
                  @touchmove="handleMicTouchMove"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" focusable="false">
                    <rect x="9" y="2" width="6" height="12" rx="3"></rect>
                    <path d="M5 10a7 7 0 0 0 14 0"></path>
                    <line x1="12" y1="17" x2="12" y2="22"></line>
                  </svg>
                </button>

                <div
                  v-else-if="recorderState !== 'idle'"
                  class="sa-recorder-pill"
                  :class="{ 'is-cancel-pending': touchCancelPending, 'is-clickable': recorderState === 'recording' && !isTouchDevice, 'is-recording': recorderState === 'recording' }"
                  :title="recorderState === 'recording' && !isTouchDevice ? '点击结束并识别，Esc 取消' : ''"
                  @click="handlePillClick"
                >
                  <span class="sa-recorder-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" focusable="false">
                      <rect x="9" y="2" width="6" height="12" rx="3"></rect>
                      <path d="M5 10a7 7 0 0 0 14 0"></path>
                      <line x1="12" y1="17" x2="12" y2="22"></line>
                    </svg>
                  </span>
                  <span class="sa-recorder-timer">{{ recordTimerText }}</span>
                  <!-- 谷歌式极简：无 ✕/✓，闪烁+计时，点击结束识别，Esc 取消（2026-08-27 按用户要求改） -->
                  <span v-if="recorderState === 'recording' && isTouchDevice" class="sa-recorder-hint">
                    {{ touchCancelPending ? '松手取消' : '松手结束，上滑取消' }}
                  </span>
                  <span v-else-if="recorderState === 'transcribing'" class="sa-recorder-hint">识别中…</span>
                </div>

                <button
                  v-if="!isRunning && allowSend"
                  class="sa-send-btn"
                  :class="{ 'is-disabled': recorderState !== 'idle' }"
                  aria-label="发送问题"
                  @click="recorderState === 'idle' && $emit('send')"
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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getAsrConfig, transcribeAudio } from '../../api/index'

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
  disabled: {
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
  get: () => {
    // bug 2026-08-26：aiModels 异步加载未到位时，modelModelId 已是有效 ID（如 13），
    // el-select 找不到匹配 option 会把原始 ID 当文字渲染（"神马13" 闪烁）。
    // 守卫：列表未就绪 或 当前 ID 不在列表中 → 返回 '' 显示 placeholder "Auto"
    // 注意：props 必须用 props.aiModels 访问（defineProps 对象方式下裸写 aiModels 是未定义变量，
    // 上一版因此 ReferenceError → 点击模型选项无反应，2026-08-26 二次修复）
    if (!modelModelId.value) return ''
    const models = props.aiModels || []
    if (models.length === 0) return ''
    if (!models.some(m => String(m.id) === String(modelModelId.value))) return ''
    return modelModelId.value
  },
  set: value => { modelModelId.value = value === '' ? null : value }
})

const selectedDatasetMeta = computed(() => (
  (props.datasets || []).find(item => Number(item?.id) === Number(modelDatasetId.value)) || null
))

const hasQuery = computed(() => String(modelQuery.value || '').trim().length > 0)

const resizeTextarea = () => {
  const textarea = inputRef.value
  if (!textarea) return
  if (!hasQuery.value) {
    textarea.style.height = '20px'
    textarea.style.overflowY = 'hidden'
    return
  }
  textarea.style.height = '52px'
  textarea.style.overflowY = textarea.scrollHeight > textarea.clientHeight ? 'auto' : 'hidden'
}

const autoGrow = () => {
  resizeTextarea()
}

const handleKeydown = (event) => {
  if (event.key !== 'Enter') return
  if (event.shiftKey) return
  if (!props.allowSend || props.isRunning) return
  if (recorderState.value !== 'idle') return // 录音/识别中不触发发送
  event.preventDefault()
  emit('send')
}

// ===================== 语音输入（ASR，方案见 docs/voice-input-design-2026-08-26.md） =====================
// 飞书 file_recognize 只收 16k PCM：用 AudioWorklet 直接采 PCM，不走 MediaRecorder（webm 不被接受）
const recorderState = ref('idle') // idle | recording | transcribing
const asrEnabled = ref(false)
const asrMaxDurationSec = ref(60)
const recordSeconds = ref(0)
const touchCancelPending = ref(false)
// 只用主指针判定触屏：带触屏的 Windows 笔记本 'ontouchstart' 也为 true，
// 会被误判成移动端导致桌面点击失效（2026-08-27 实测 bug）
const isTouchDevice = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches)

const canRecord = computed(() => (
  asrEnabled.value
  && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
  && typeof (window.AudioContext || window.webkitAudioContext) !== 'undefined'
))

const recordTimerText = computed(() => {
  const s = recordSeconds.value
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})

let audioCtx = null
let mediaStream = null
let workletNode = null
let pcmChunks = []
let recordTimer = null
let recordMaxTimer = null
let recordStartedAt = 0
let touchStartY = 0

const WORKLET_CODE = `
class PCMCollector extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0]
    if (input && input[0] && input[0].length) this.port.postMessage(input[0].slice(0))
    return true
  }
}
registerProcessor('pcm-collector', PCMCollector)
`

const startRecording = async () => {
  if (recorderState.value !== 'idle') return
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch (e) {
    ElMessage.warning('请允许浏览器使用麦克风')
    return
  }
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    audioCtx = new Ctx()
    const source = audioCtx.createMediaStreamSource(mediaStream)
    const workletUrl = URL.createObjectURL(new Blob([WORKLET_CODE], { type: 'application/javascript' }))
    await audioCtx.audioWorklet.addModule(workletUrl)
    URL.revokeObjectURL(workletUrl)
    workletNode = new AudioWorkletNode(audioCtx, 'pcm-collector')
    pcmChunks = []
    workletNode.port.onmessage = (e) => { pcmChunks.push(e.data) }
    // 不接 destination 时 Chrome 不驱动 process()；接零增益节点避免外放回录
    const mute = audioCtx.createGain()
    mute.gain.value = 0
    source.connect(workletNode)
    workletNode.connect(mute)
    mute.connect(audioCtx.destination)
  } catch (e) {
    cleanupAudio()
    ElMessage.error('当前浏览器不支持录音')
    return
  }
  recordStartedAt = Date.now()
  recordSeconds.value = 0
  touchCancelPending.value = false
  recorderState.value = 'recording'
  recordTimer = setInterval(() => {
    recordSeconds.value = Math.floor((Date.now() - recordStartedAt) / 1000)
  }, 500)
  recordMaxTimer = setTimeout(() => finishRecording(), asrMaxDurationSec.value * 1000)
}

const cleanupAudio = () => {
  if (recordTimer) { clearInterval(recordTimer); recordTimer = null }
  if (recordMaxTimer) { clearTimeout(recordMaxTimer); recordMaxTimer = null }
  if (workletNode) { try { workletNode.disconnect() } catch (e) {} workletNode = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (audioCtx) { audioCtx.close().catch(() => {}); audioCtx = null }
}

const cancelRecording = () => {
  cleanupAudio()
  pcmChunks = []
  recorderState.value = 'idle'
}

const mergeChunks = (chunks) => {
  const total = chunks.reduce((n, c) => n + c.length, 0)
  const merged = new Float32Array(total)
  let offset = 0
  for (const c of chunks) { merged.set(c, offset); offset += c.length }
  return merged
}

const downsampleTo16k = (samples, srcRate) => {
  if (srcRate === 16000) return samples
  const ratio = srcRate / 16000
  const out = new Float32Array(Math.floor(samples.length / ratio))
  for (let i = 0; i < out.length; i++) {
    out[i] = samples[Math.min(samples.length - 1, Math.floor(i * ratio))]
  }
  return out
}

const floatTo16BitPcmBase64 = (samples) => {
  const buf = new ArrayBuffer(samples.length * 2)
  const view = new DataView(buf)
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  const bytes = new Uint8Array(buf)
  let binary = ''
  const step = 0x8000
  for (let i = 0; i < bytes.length; i += step) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + step))
  }
  return btoa(binary)
}

const finishRecording = async () => {
  if (recorderState.value !== 'recording') return
  const srcRate = audioCtx ? audioCtx.sampleRate : 48000
  const chunks = pcmChunks
  cleanupAudio()
  pcmChunks = []
  const samples = downsampleTo16k(mergeChunks(chunks), srcRate)
  // 少于 0.3 秒视为误触
  if (!samples || samples.length < 16000 * 0.3) {
    recorderState.value = 'idle'
    return
  }
  recorderState.value = 'transcribing'
  try {
    const res = await transcribeAudio(floatTo16BitPcmBase64(samples))
    const text = String(res?.text || '').trim()
    if (text) {
      const cur = String(modelQuery.value || '').trimEnd()
      modelQuery.value = cur ? `${cur} ${text}` : text
      nextTick(() => { resizeTextarea(); inputRef.value && inputRef.value.focus() })
    } else {
      ElMessage.info('未检测到语音内容，请重试。')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '语音识别失败，请稍后重试')
  } finally {
    recorderState.value = 'idle'
  }
}

// 桌面端：点击开始；录音条点击=结束识别，Esc=取消（谷歌式极简）
const handleMicClick = () => {
  if (isTouchDevice) return // 触屏走 press-hold，避免 touch 合成 click 冲突
  startRecording()
}
const handlePillClick = () => {
  if (isTouchDevice) return
  if (recorderState.value === 'recording') finishRecording()
}
const handleEscKey = (e) => {
  if (e.key === 'Escape' && recorderState.value === 'recording') cancelRecording()
}
// 移动端：按住说话，上滑取消
const handleMicTouchStart = (e) => {
  touchStartY = e.touches && e.touches[0] ? e.touches[0].clientY : 0
  startRecording()
}
const handleMicTouchMove = (e) => {
  if (recorderState.value !== 'recording') return
  const y = e.touches && e.touches[0] ? e.touches[0].clientY : touchStartY
  touchCancelPending.value = (touchStartY - y) > 60
}
const handleMicTouchEnd = () => {
  if (recorderState.value !== 'recording') return
  if (touchCancelPending.value) cancelRecording()
  else finishRecording()
}

watch(modelQuery, () => nextTick(resizeTextarea))

onMounted(() => {
  nextTick(() => {
    resizeTextarea()
    inputRef.value?.focus()
  })
  getAsrConfig()
    .then((res) => {
      asrEnabled.value = !!(res && res.enabled)
      if (res && res.max_duration_sec) asrMaxDurationSec.value = res.max_duration_sec
    })
    .catch(() => { asrEnabled.value = false })
  window.addEventListener('keydown', handleEscKey)
})

onUnmounted(() => {
  // 组件销毁时释放麦克风，避免录音中路由跳走导致设备占用
  window.removeEventListener('keydown', handleEscKey)
  cleanupAudio()
})
</script>

<style scoped>
.sa-composer {
  width: 100%;
  margin: 0 0 14px;
  box-sizing: border-box;
  container-type: inline-size;
  --sa-side-width: 180px;
  --sa-composer-gap: 16px;
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
  border-color: rgba(148, 163, 184, 0.22);
  background: linear-gradient(180deg, #fcfcfd 0%, #f7f8fb 100%);
  box-shadow:
    0 12px 28px rgba(15, 23, 42, 0.06),
    0 0 0 3px rgba(148, 163, 184, 0.05);
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
  grid-template-columns: var(--sa-side-width) minmax(0, 1fr);
  gap: var(--sa-composer-gap);
  align-items: stretch;
}

.sa-side-dataset-card {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
  width: var(--sa-side-width);
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
  width: 100%;
  min-width: 0;
  margin-top: auto;
}

.sa-side-ds-select :deep(.el-select__wrapper) {
  min-height: 32px;
  min-width: 0;
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
  max-width: 92px;
  color: #111827;
}

.sa-side-ds-select :deep(.el-select__selection) {
  min-width: 0;
  width: 100%;
}

.sa-side-ds-select :deep(.el-select__selected-item span) {
  overflow: hidden;
  text-overflow: ellipsis;
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

.sa-model-option-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1 1 auto;
}

.sa-model-option-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-model-option-channel {
  flex: 0 0 auto;
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.05);
  font-size: 10px;
  font-weight: 600;
  color: #6B7280;
  line-height: 1.2;
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

/* 模型下拉弹层：scoped 选择器对 teleport 到 body 的 element-plus popper 失效
   （已下沉到下方非 scoped 块） */


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
  display: grid;
  grid-template-columns: minmax(0, 1fr) 190px;
  grid-template-rows: 52px;
  column-gap: 12px;
  height: 88px;
  min-height: 88px;
  padding: 12px 18px 10px;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(17, 24, 39, 0.07);
  background: #FFFFFF;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 0 0 1px rgba(17, 24, 39, 0.015);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease, opacity 0.2s ease;
}

.sa-textarea-wrap.is-running {
  border-color: rgba(17, 24, 39, 0.07);
  background: #FFFFFF;
  animation: none;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 0 0 1px rgba(17, 24, 39, 0.015);
}

.sa-textarea-wrap:focus-within {
  border-color: rgba(17, 24, 39, 0.09);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 0 0 3px rgba(17, 24, 39, 0.025);
}

.sa-textarea-wrap.is-running:focus-within {
  border-color: rgba(17, 24, 39, 0.07);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 0 0 1px rgba(17, 24, 39, 0.015);
}

.sa-composer-running-mask {
  position: absolute;
  left: 18px;
  right: 18px;
  top: 14px;
  height: 20px;
  z-index: 1;
  pointer-events: none;
  overflow: hidden;
}

.sa-composer-running-panel {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.sa-composer-running-line {
  width: 18px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(148, 163, 184, 0.2) 0%, rgba(148, 163, 184, 0.8) 50%, rgba(148, 163, 184, 0.2) 100%);
  animation: sa-running-line-pulse 1.4s ease-in-out infinite;
  flex: 0 0 auto;
}

.sa-composer-running-text {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
  text-align: left;
  white-space: nowrap;
  background: linear-gradient(110deg, rgba(100, 116, 139, 0.82) 0%, rgba(148, 163, 184, 1) 48%, rgba(100, 116, 139, 0.82) 100%);
  background-size: 220px 100%;
  background-repeat: no-repeat;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: sa-composer-shimmer 2.2s ease-in-out infinite;
}

.sa-composer-status-capsule {
  position: absolute;
  right: 0;
  bottom: 44px;
  left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 260px;
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
  grid-column: 1;
  grid-row: 1;
  align-self: start;
  width: 100%;
  max-width: 100%;
  border: none;
  outline: none !important;
  appearance: none;
  -webkit-appearance: none;
  padding: 0;
  margin: 0;
  box-shadow: none !important;
  font-size: 14px;
  height: 20px;
  min-height: 20px;
  max-height: 52px;
  resize: none;
  overflow-y: hidden;
  line-height: 1.45;
  color: #111827;
  background: transparent;
  caret-color: #E61F24;
  margin-top: 0;
}

.sa-textarea:disabled {
  color: rgba(123, 135, 152, 0.14);
  cursor: not-allowed;
  caret-color: transparent;
  -webkit-text-fill-color: rgba(123, 135, 152, 0.14);
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

.sa-textarea:disabled::placeholder {
  color: rgba(168, 178, 193, 0.16);
}

.sa-textarea-wrap.has-query .sa-textarea {
  height: 52px;
  min-height: 52px;
  max-height: 52px;
}

.sa-composer-footer {
  display: grid;
  /* 右列原固定 118px，加入麦克风后动作区变宽会重叠溢出（2026-08-27 bug）；改 auto 由内容撑开 */
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: 12px;
  align-items: end;
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 12px;
  min-width: 0;
  pointer-events: none;
}

.sa-textarea-wrap.has-query .sa-composer-hint {
  display: none;
}

.sa-composer-hint-float {
  position: absolute;
  left: 18px;
  bottom: 0;
  z-index: 1;
  pointer-events: none;
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
  grid-column: 2;
  justify-self: end;
  /* 原固定 190px/两列网格只容得下 模型选择器+发送键，麦克风/录音条会被挤到第二行重叠
     （2026-08-27 bug）；改 flex 自适应宽度，内容多少都能排开 */
  display: flex;
  align-items: center;
  column-gap: 10px;
  pointer-events: auto;
}

.sa-model-corner-select {
  width: 150px;
  flex: 0 0 auto;
}

.sa-model-corner-select :deep(.el-select__wrapper) {
  min-height: 32px;
  padding-left: 26px;
  padding-right: 6px;
  border-radius: 999px;
  background: #ffffff;
  box-shadow:
    inset 0 0 0 1px #E5E7EB;
}

.sa-composer.is-running .sa-model-corner-select {
  opacity: 1;
}

.sa-composer.is-running .sa-model-corner-select :deep(.el-select__wrapper) {
  background: #ffffff;
  box-shadow:
    inset 0 0 0 1px #E5E7EB;
}

.sa-model-corner-select :deep(.el-select__selected-item),
.sa-model-corner-select :deep(.el-select__placeholder) {
  font-size: 11px;
  font-weight: 600;
  line-height: 1.2;
  color: #111827;
}

.sa-model-icon {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
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
  width: 9px;
  height: 9px;
  display: block;
}

.sa-send-btn,
.sa-stop-btn {
  grid-column: 2;
  justify-self: center;
  align-self: center;
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
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
  width: 16px;
  height: 16px;
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

@keyframes sa-composer-shimmer {
  0% { background-position: -240px 0, 0 0; }
  100% { background-position: calc(100% + 240px) 0, 0 0; }
}

@keyframes sa-running-line-pulse {
  0%, 100% { opacity: 0.45; transform: scaleX(0.88); }
  50% { opacity: 1; transform: scaleX(1); }
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
    width: 100%;
  }

  .sa-composer-main {
    order: 1;
  }

  .sa-composer-footer {
    left: 14px;
    right: 14px;
    bottom: 12px;
    column-gap: 10px;
    align-items: end;
  }

  .sa-composer-actions {
    column-gap: 6px;
  }

  .sa-textarea-wrap {
    grid-template-columns: minmax(0, 1fr) 150px;
    column-gap: 10px;
    padding-left: 14px;
    padding-right: 14px;
  }

  .sa-model-corner-select {
    width: 110px;
  }

  .sa-model-corner-select :deep(.el-select__wrapper) {
    padding-left: 24px;
    padding-right: 4px;
  }

  .sa-composer-hint-float {
    left: 14px;
  }

  .sa-composer-status-capsule {
    display: none;
  }

  .sa-composer-running-panel {
    padding: 0 12px;
  }

  .sa-composer-running-mask {
    right: 14px;
  }
}

/* 语音输入：麦克风按钮 + 录音条（WorkBuddy 式） */
.sa-mic-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #6B7280;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  flex: 0 0 auto;
}
.sa-mic-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #111827;
}
.sa-mic-btn svg {
  width: 18px;
  height: 18px;
}

.sa-recorder-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.08);
  flex: 0 0 auto;
}
/* 外框呼吸闪烁只在录音中进行（2026-08-27 用户反馈闪烁不明显） */
.sa-recorder-pill.is-recording {
  animation: sa-recorder-glow 1.2s ease-in-out infinite;
}
.sa-recorder-pill.is-cancel-pending {
  border-color: #FCA5A5;
  background: #FEF2F2;
}
.sa-recorder-icon {
  display: flex;
  color: #F51F19;
}
.sa-recorder-pill.is-recording .sa-recorder-icon {
  animation: sa-recorder-pulse 1.2s ease-in-out infinite;
}
.sa-recorder-icon svg {
  width: 16px;
  height: 16px;
}
/* 图标：红→橙→红 变色 + 缩放，比单纯透明度闪更明显 */
@keyframes sa-recorder-pulse {
  0%, 100% { color: #F51F19; transform: scale(1); }
  50% { color: #F97316; transform: scale(1.25); }
}
/* 外框：边框色 + 红色光晕呼吸 */
@keyframes sa-recorder-glow {
  0%, 100% {
    border-color: #E5E7EB;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.08);
  }
  50% {
    border-color: #F51F19;
    box-shadow: 0 0 0 4px rgba(245, 31, 25, 0.18), 0 1px 6px rgba(245, 31, 25, 0.35);
  }
}
.sa-recorder-timer {
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: #111827;
  min-width: 38px;
}
.sa-recorder-pill.is-clickable {
  cursor: pointer;
}
.sa-recorder-pill.is-clickable:hover {
  border-color: #D1D5DB;
  box-shadow: 0 2px 6px rgba(16, 24, 40, 0.12);
}
.sa-recorder-hint {
  font-size: 12px;
  color: #6B7280;
  white-space: nowrap;
}
.sa-send-btn.is-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>

<style>
/* ============================================================
   模型下拉弹层 — 浅色高端版（参考用户截图的版式 / 配色与整体协调）
   触发器保持原色；弹层浅色面板 + 精致边框 + 柔和投影
   布局参考截图：左=闪电+名称+默认徽章 / 右=通道+对勾
   ============================================================ */
.sa-model-popper.el-popper {
  min-width: 280px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  box-shadow: 0 2px 4px rgba(16, 24, 40, 0.04), 0 12px 32px rgba(16, 24, 40, 0.12);
  max-height: 380px;
  overflow: hidden;
}
.sa-model-popper .el-select-dropdown__list {
  max-height: 368px;
  overflow-y: auto;
  padding: 6px;
}
/* 滚动条：白底弹层配黑灰半透明（bug 2026-08-25 反馈"太白"） */
.sa-model-popper .el-select-dropdown__list::-webkit-scrollbar {
  width: 5px;
}
.sa-model-popper .el-select-dropdown__list::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.22);
  border-radius: 3px;
}
.sa-model-popper .el-select-dropdown__list::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.34);
}
.sa-model-popper .el-select-dropdown__list::-webkit-scrollbar-track {
  background: transparent;
}
.sa-model-popper .el-select-dropdown__item {
  background: transparent;
  border-radius: 10px;
  margin: 2px 0;
  padding: 10px 12px;
  border: 1px solid transparent;
}
.sa-model-popper .el-select-dropdown__item:hover,
.sa-model-popper .el-select-dropdown__item.is-hovering {
  background: #F9FAFB;
  border-color: #E5E7EB;
}
.sa-model-popper .el-select-dropdown__item.is-selected {
  background: #ECFDF5;
  border-color: #A7F3D0;
}
.sa-model-option-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.sa-model-option-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1 1 auto;
}
.sa-model-option-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}
.sa-model-icon-mini {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: #E61F24;
}
.sa-model-icon-mini svg {
  width: 14px;
  height: 14px;
}
.sa-model-option-name {
  color: #111827;
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sa-model-default-badge {
  flex: 0 0 auto;
  padding: 1px 6px;
  border-radius: 4px;
  background: #ECFDF5;
  color: #047857;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.3;
}
.sa-model-option-channel {
  flex: 0 0 auto;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 1px 6px;
  border-radius: 4px;
  background: #F3F4F6;
  color: #4B5563;
  font-size: 10px;
  font-weight: 500;
  line-height: 1.3;
}
.sa-model-check {
  color: #10B981;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
}
</style>
