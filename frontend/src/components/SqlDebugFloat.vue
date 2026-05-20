<template>
  <teleport to="body">
    <div
      v-if="visible"
      class="sql-debug-float"
      :style="floatStyle"
      @pointerdown="startDrag"
    >
      <button
        class="sql-debug-float-main"
        :class="{ dragging }"
        type="button"
        @click.stop="openSqlDebugPage"
      >
        <el-icon><Monitor /></el-icon>
        <span>SQL调试台</span>
      </button>
      <button
        class="sql-debug-float-close"
        type="button"
        aria-label="关闭 SQL 调试悬浮入口"
        @pointerdown.stop
        @click.stop="disableFloat"
      >
        x
      </button>
    </div>
  </teleport>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElIcon, ElMessage } from 'element-plus'
import { Monitor } from '@element-plus/icons-vue'
import { useFeatureFlags } from '../state/featureFlags'

const FLOAT_ENABLED_KEY = 'smartask_sql_debug_float_enabled'
const FLOAT_POSITION_KEY = 'smartask_sql_debug_float_position'
const FLOAT_TOGGLE_EVENT = 'smartask-sql-debug-float-toggle'

const router = useRouter()
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const canRun = computed(() => isFeatureEnabled('dataset_sql_preview_run'))
const enabled = ref(false)
const visible = computed(() => enabled.value && canRun.value)
const dragging = ref(false)
const position = ref({ x: 0, y: 0 })
let moved = false
let offset = { x: 0, y: 0 }

const defaultPosition = () => ({
  x: Math.max(20, window.innerWidth - 174),
  y: Math.max(88, window.innerHeight - 126),
})

const clampPosition = (value) => {
  const width = 164
  const height = 54
  return {
    x: Math.min(Math.max(12, Number(value?.x) || 0), Math.max(12, window.innerWidth - width)),
    y: Math.min(Math.max(76, Number(value?.y) || 0), Math.max(76, window.innerHeight - height)),
  }
}

const floatStyle = computed(() => ({
  left: `${position.value.x}px`,
  top: `${position.value.y}px`,
}))

const persistPosition = () => {
  localStorage.setItem(FLOAT_POSITION_KEY, JSON.stringify(position.value))
}

const restore = () => {
  enabled.value = localStorage.getItem(FLOAT_ENABLED_KEY) === '1'
  try {
    position.value = clampPosition(JSON.parse(localStorage.getItem(FLOAT_POSITION_KEY) || 'null') || defaultPosition())
  } catch {
    position.value = defaultPosition()
  }
}

const handleToggle = (event) => {
  enabled.value = Boolean(event?.detail?.enabled)
  localStorage.setItem(FLOAT_ENABLED_KEY, enabled.value ? '1' : '0')
  if (enabled.value && (!position.value.x || !position.value.y)) {
    position.value = defaultPosition()
  }
}

const openSqlDebugPage = () => {
  if (moved) {
    moved = false
    return
  }
  router.push('/sql-debug')
}

const disableFloat = () => {
  enabled.value = false
  localStorage.setItem(FLOAT_ENABLED_KEY, '0')
  window.dispatchEvent(new CustomEvent(FLOAT_TOGGLE_EVENT, { detail: { enabled: false } }))
  ElMessage.success('已关闭 SQL 调试悬浮入口')
}

const startDrag = (event) => {
  if (event.button !== 0) return
  dragging.value = true
  moved = false
  offset = {
    x: event.clientX - position.value.x,
    y: event.clientY - position.value.y,
  }
  window.addEventListener('pointermove', handleDrag)
  window.addEventListener('pointerup', stopDrag)
}

const handleDrag = (event) => {
  if (!dragging.value) return
  position.value = clampPosition({
    x: event.clientX - offset.x,
    y: event.clientY - offset.y,
  })
  moved = true
}

const stopDrag = () => {
  if (!dragging.value) return
  dragging.value = false
  persistPosition()
  window.removeEventListener('pointermove', handleDrag)
  window.removeEventListener('pointerup', stopDrag)
}

const handleResize = () => {
  position.value = clampPosition(position.value)
  persistPosition()
}

onMounted(async () => {
  restore()
  await loadFeatureFlags()
  window.addEventListener(FLOAT_TOGGLE_EVENT, handleToggle)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener(FLOAT_TOGGLE_EVENT, handleToggle)
  window.removeEventListener('resize', handleResize)
  stopDrag()
})
</script>

<style scoped>
.sql-debug-float {
  position: fixed;
  z-index: 2100;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: grab;
}

.sql-debug-float-main,
.sql-debug-float-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(20, 184, 166, 0.28);
  background: rgba(15, 118, 110, 0.96);
  color: #fff;
  box-shadow: 0 16px 36px rgba(15, 118, 110, 0.24);
  cursor: pointer;
}

.sql-debug-float-main {
  gap: 8px;
  height: 42px;
  padding: 0 14px;
  border-radius: 999px;
  font-weight: 800;
}

.sql-debug-float-main.dragging {
  cursor: grabbing;
}

.sql-debug-float-close {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  font-size: 14px;
  line-height: 1;
}

.sql-debug-float-main:hover,
.sql-debug-float-close:hover {
  background: #0f766e;
  transform: translateY(-1px);
}
</style>
