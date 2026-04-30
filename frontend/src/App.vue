<template>
  <el-container class="app-shell">
    <el-aside class="sidebar" :class="{ 'sidebar-collapsed': collapsed }" :width="collapsed ? '72px' : '248px'">
      <div class="brand">
        <div class="brand-pill" :class="{ 'is-collapsed': collapsed }">
          <div class="brand-mark" aria-hidden="true">
            <span class="brand-mark-ring"></span>
            <span class="brand-mark-core"></span>
            <span class="brand-mark-dot brand-mark-dot-top"></span>
            <span class="brand-mark-dot brand-mark-dot-right"></span>
            <span class="brand-mark-dot brand-mark-dot-bottom"></span>
            <span class="brand-mark-dot brand-mark-dot-left"></span>
          </div>
          <div v-if="!collapsed" class="brand-text">
            <div class="brand-title">Data Agent</div>
            <div class="brand-subtitle">经营分析工作台</div>
          </div>
          <span v-if="!collapsed" class="brand-caret" aria-hidden="true"></span>
        </div>
      </div>

      <div class="sidebar-body">
        <el-menu
          :default-active="activeMenu"
          class="nav-menu"
          :collapse="collapsed"
          background-color="transparent"
          text-color="#8c919b"
          active-text-color="#22252b"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/smart-ask">
            <el-icon><ChatLineRound /></el-icon>
            <template #title>问数会话</template>
          </el-menu-item>
          <el-menu-item index="/agents">
            <el-icon><Cpu /></el-icon>
            <template #title>AGENT管理</template>
          </el-menu-item>
          <el-menu-item index="/datasets">
            <el-icon><Collection /></el-icon>
            <template #title>数据集管理</template>
          </el-menu-item>
          <el-menu-item index="/databases">
            <el-icon><Coin /></el-icon>
            <template #title>数据源管理</template>
          </el-menu-item>
          <el-menu-item index="/ai-models">
            <el-icon><MagicStick /></el-icon>
            <template #title>AI模型配置</template>
          </el-menu-item>
          <el-menu-item index="/feishu-sync">
            <el-icon><Connection /></el-icon>
            <template #title>飞书同步</template>
          </el-menu-item>
          <el-menu-item index="/">
            <el-icon><Odometer /></el-icon>
            <template #title>仪表盘</template>
          </el-menu-item>
        </el-menu>

        <transition name="history-panel">
          <section
            v-if="showHistorySidebar"
            ref="historyPanelRef"
            class="sidebar-history"
            :class="{ 'sidebar-history-highlight': historyPanelHighlighted }"
          >
            <div class="sidebar-history-head">
              <div>
                <div class="sidebar-history-title">历史对话</div>
                <div class="sidebar-history-subtitle">最近 {{ historyPreviewList.length }} 条问数记录</div>
              </div>
              <div class="sidebar-history-actions">
                <button class="sidebar-history-new" type="button" @click="createFreshChat">
                  新对话
                </button>
                <el-button
                  v-if="historyPreviewList.length"
                  link
                  type="primary"
                  class="sidebar-history-clear"
                  @click="clearHistoryList"
                >
                  清空
                </el-button>
              </div>
            </div>

            <div v-if="historyPreviewList.length" class="sidebar-history-list">
              <article
                v-for="item in historyPreviewList"
                :key="item.id"
                class="history-item"
                :class="{ 'history-item-active': item.id === activeHistoryId }"
                @click="openHistorySession(item)"
              >
                <div class="history-item-main">
                  <div class="history-item-top">
                    <div class="history-item-title">{{ item.title }}</div>
                    <span v-if="item.id === activeHistoryId" class="history-item-badge">当前</span>
                  </div>
                  <div class="history-item-meta">{{ item.datasetName || '自动路由数据集' }}</div>
                  <div class="history-item-time">{{ item.updatedAt }}</div>
                </div>
                <button
                  class="history-item-delete"
                  type="button"
                  aria-label="删除历史对话"
                  @click.stop="removeHistoryItem(item.id)"
                >
                  <span class="history-item-delete-icon" aria-hidden="true"></span>
                </button>
              </article>
            </div>

            <div v-else class="sidebar-history-empty">
              <div class="sidebar-history-empty-title">暂无历史记录</div>
              <div class="sidebar-history-empty-desc">发起问数后，这里会沉淀可恢复的对话记录。</div>
            </div>
          </section>
        </transition>
      </div>

      <div class="sidebar-footer" @click="collapsed = !collapsed">
        <el-icon><component :is="collapsed ? 'Expand' : 'Fold'" /></el-icon>
        <span v-if="!collapsed">收起导航</span>
      </div>
    </el-aside>

    <el-container class="main-shell">
      <el-header class="topbar" :class="{ 'topbar-smart': isSmartAskRoute }">
        <div class="topbar-heading">
          <div class="topbar-title-row">
            <div class="topbar-brand">Data Agent</div>
            <span class="topbar-divider"></span>
            <div class="topbar-workspace">{{ currentTitle }}</div>
          </div>
        </div>
        <div class="topbar-right">
          <el-tag :type="backendOk ? 'success' : 'danger'" effect="plain" round size="small">
            {{ backendOk ? '后端在线' : '后端异常' }}
          </el-tag>
          <div class="clock">{{ currentTime }}</div>
        </div>
      </el-header>

      <el-main class="page-wrap" :class="{ 'page-wrap-smart': isSmartAskRoute }">
        <router-view v-slot="{ Component }">
          <keep-alive :include="['SmartAsk']">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { ChatLineRound } from '@element-plus/icons-vue'
import { healthCheck } from './api/index.js'
import { useSmartAskSession } from './state/smartAskSession.js'
import { useSmartAskHistory } from './state/smartAskHistory.js'

const route = useRoute()
const router = useRouter()
const session = useSmartAskSession()
const {
  historySessions,
  activeHistoryId,
  loadHistory,
  removeHistory,
  clearHistory,
  requestRestore,
  setActiveHistory,
} = useSmartAskHistory()
const collapsed = ref(false)
const backendOk = ref(false)
const currentTime = ref('')
const historyPanelRef = ref(null)
const historyPanelHighlighted = ref(false)

const titleMap = {
  '/': '仪表盘',
  '/smart-ask': '经营问答台',
  '/agents': 'AGENT管理',
  '/datasets': '数据集管理',
  '/databases': '数据源管理',
  '/ai-models': 'AI模型配置',
  '/feishu-sync': '飞书同步'
}

const subtitleMap = {
  '/': '系统概览与运行状态',
  '/smart-ask': '',
  '/agents': '维护四个核心Agent的系统提示词与知识规则',
  '/datasets': '维护每个数据集的书架元数据与Golden SQL',
  '/databases': '管理PostgreSQL与其他连接源',
  '/ai-models': '配置默认模型与模型连接',
  '/feishu-sync': '飞书多维表格同步、日志与任务控制'
}

const activeMenu = computed(() => route.path)
const isSmartAskRoute = computed(() => route.path === '/smart-ask')
const currentTitle = computed(() => titleMap[route.path] || '经营问答台')
const currentSubtitle = computed(() => subtitleMap[route.path] || '经营分析工作台')
const activeDatasetIds = computed(() => session.activeDatasetIds.value || [])
const historyPreviewList = computed(() => historySessions.value.slice(0, 8))
const showHistorySidebar = computed(() => route.path === '/smart-ask' && !collapsed.value)

const refreshClock = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

const pingBackend = async () => {
  try {
    await healthCheck()
    backendOk.value = true
  } catch {
    backendOk.value = false
  }
}

const refreshCurrentPage = () => {
  window.location.reload()
}

const handleMenuSelect = (index) => {
  if (!index || index === route.path) return
  router.push(index)
}

const pulseHistoryPanel = () => {
  if (!showHistorySidebar.value) return
  historyPanelHighlighted.value = true
  nextTick(() => {
    historyPanelRef.value?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
  })
  window.setTimeout(() => {
    historyPanelHighlighted.value = false
  }, 1600)
}

const openHistorySession = async (item) => {
  if (!item?.id) return
  setActiveHistory(item.id)
  requestRestore(item.id)
  await router.push('/smart-ask')
  pulseHistoryPanel()
}

const removeHistoryItem = (id) => {
  removeHistory(id)
}

const createFreshChat = async () => {
  setActiveHistory('')
  await router.push('/smart-ask')
  window.dispatchEvent(new CustomEvent('smartask-create-fresh-chat'))
  pulseHistoryPanel()
}

const clearHistoryList = async () => {
  try {
    await ElMessageBox.confirm(
      '清空后将删除当前保存的全部历史对话记录。',
      '清空历史对话',
      {
        type: 'info',
        confirmButtonText: '确认清空',
        cancelButtonText: '取消',
        customClass: 'sa-message-box',
      }
    )
    clearHistory()
  } catch {
    // user cancelled
  }
}

let clockTimer = null
let healthTimer = null
let historyFocusTimer = null

const handleHistoryFocus = () => {
  if (collapsed.value) {
    collapsed.value = false
  }
  if (route.path !== '/smart-ask') {
    router.push('/smart-ask')
  }
  if (historyFocusTimer) {
    clearTimeout(historyFocusTimer)
  }
  historyFocusTimer = window.setTimeout(() => {
    pulseHistoryPanel()
  }, 60)
}

onMounted(() => {
  loadHistory()
  refreshClock()
  pingBackend()
  clockTimer = setInterval(refreshClock, 1000)
  healthTimer = setInterval(pingBackend, 10000)
  window.addEventListener('smartask-history-focus', handleHistoryFocus)
})

onUnmounted(() => {
  clearInterval(clockTimer)
  clearInterval(healthTimer)
  if (historyFocusTimer) {
    clearTimeout(historyFocusTimer)
  }
  window.removeEventListener('smartask-history-focus', handleHistoryFocus)
})

watch(() => route.path, (path) => {
  if (path === '/smart-ask') {
    loadHistory()
  }
})
</script>

<style>
:root {
  --shell-bg: #eceef1;
  --panel-bg: rgba(255, 255, 255, 0.72);
  --panel-border: rgba(114, 120, 128, 0.16);
  --ink-strong: #20242b;
  --ink-soft: #6f7681;
  --brand: #3d434d;
  --brand-soft: #d8dbe0;
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  margin: 0;
  height: 100%;
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.88), transparent 28%),
    radial-gradient(circle at bottom right, rgba(201, 206, 214, 0.35), transparent 25%),
    linear-gradient(135deg, #eef0f2, #dfe3e8 48%, #f5f6f8);
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: var(--ink-strong);
}

.app-shell {
  height: 100%;
}

.sidebar {
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  backdrop-filter: blur(16px);
  background: rgba(245, 246, 248, 0.74);
  border-right: 1px solid var(--panel-border);
}

.sidebar.sidebar-collapsed {
  padding: 14px 8px 12px;
  align-items: center;
}

.brand {
  padding: 8px 8px 16px;
}

.sidebar.sidebar-collapsed .brand {
  width: 100%;
  padding: 4px 0 14px;
  display: flex;
  justify-content: center;
}

.brand-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 8px 10px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 245, 248, 0.9));
  border: 1px solid rgba(29, 33, 41, 0.08);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 12px 24px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.brand-pill.is-collapsed {
  justify-content: center;
  width: 52px;
  min-height: 52px;
  padding: 6px;
  margin: 0 auto;
  border-radius: 18px;
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.brand-mark {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: block;
  overflow: hidden;
  background:
    radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 0.24), transparent 34%),
    linear-gradient(180deg, #4a505a, #272c34);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.14),
    0 10px 22px rgba(36, 41, 49, 0.22);
  flex-shrink: 0;
}

.sidebar.sidebar-collapsed .brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 13px;
}

.brand-mark-ring,
.topbar-mark-ring {
  position: absolute;
  inset: 9px;
  border-radius: 999px;
  border: 1.5px solid rgba(255, 255, 255, 0.28);
  opacity: 0.92;
}

.brand-mark-core,
.topbar-mark-core {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle at 35% 35%, #ffffff 0%, #bcd2ff 35%, #4f8cff 100%);
  box-shadow:
    0 0 0 3px rgba(110, 153, 255, 0.16),
    0 0 16px rgba(79, 140, 255, 0.35);
}

.brand-mark-dot,
.topbar-mark-dot {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  box-shadow: 0 0 10px currentColor;
}

.brand-mark-dot-top,
.topbar-mark-dot-top {
  left: 50%;
  top: 7px;
  transform: translateX(-50%);
  background: #7bb0ff;
  color: #7bb0ff;
}

.brand-mark-dot-right,
.topbar-mark-dot-right {
  right: 7px;
  top: 50%;
  transform: translateY(-50%);
  background: #7de0d4;
  color: #7de0d4;
}

.brand-mark-dot-bottom,
.topbar-mark-dot-bottom {
  left: 50%;
  bottom: 7px;
  transform: translateX(-50%);
  background: #ffd36f;
  color: #ffd36f;
}

.brand-mark-dot-left,
.topbar-mark-dot-left {
  left: 7px;
  top: 50%;
  transform: translateY(-50%);
  background: #d39cff;
  color: #d39cff;
}

.brand-text {
  min-width: 0;
  flex: 1;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #20242b;
}

.brand-subtitle {
  margin-top: 2px;
  font-size: 11px;
  color: #747c88;
  letter-spacing: 0.01em;
}

.brand-caret {
  width: 8px;
  height: 8px;
  border-right: 1.5px solid #8b93a0;
  border-bottom: 1.5px solid #8b93a0;
  transform: rotate(45deg) translateY(-1px);
  flex-shrink: 0;
}

.sidebar-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.sidebar.sidebar-collapsed .sidebar-body {
  width: 100%;
  align-items: center;
}

.nav-menu {
  flex: none;
  border-right: none !important;
}

.sidebar.sidebar-collapsed .nav-menu {
  width: 44px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.nav-menu.el-menu {
  border-right: none;
}

.nav-menu .el-menu-item {
  margin: 3px 0;
  border-radius: 14px;
  height: 42px;
  transition: all 0.24s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item {
  width: 44px;
  min-width: 44px;
  height: 44px;
  margin: 6px auto;
  padding: 0 !important;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 44px;
  text-align: center;
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item .el-icon {
  width: 20px;
  height: 20px;
  margin: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  font-size: 17px;
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item > * {
  flex-shrink: 0;
}

.nav-menu .el-menu-item.is-active {
  background: #ffffff !important;
  border: 1px solid rgba(32, 36, 43, 0.08);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 20px rgba(15, 23, 42, 0.04);
}

.sidebar-history {
  position: relative;
  margin: 14px 0 12px;
  padding: 14px 12px 12px;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(29, 33, 41, 0.07);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(250, 251, 253, 0.72));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.52),
    0 12px 28px rgba(15, 23, 42, 0.04);
  backdrop-filter: blur(10px);
}

.sidebar-history-highlight {
  border-color: rgba(22, 93, 255, 0.22);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.58),
    0 0 0 3px rgba(22, 93, 255, 0.08),
    0 14px 30px rgba(22, 93, 255, 0.07);
}

.sidebar-history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.sidebar-history-head > div:first-child {
  min-width: 0;
  flex: 1;
}

.sidebar-history-title {
  font-size: 13px;
  font-weight: 700;
  color: #20242b;
}

.sidebar-history-subtitle {
  margin-top: 3px;
  font-size: 10px;
  color: #7a818d;
}

.sidebar-history-clear {
  padding: 0;
  font-size: 11px;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-history-clear:hover {
  transform: translateY(-1px);
}

.sidebar-history-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  white-space: nowrap;
}

.sidebar-history-new {
  height: 28px;
  padding: 0 12px;
  min-width: 58px;
  border: 1px solid rgba(29, 33, 41, 0.1);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: #3f4650;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-history-new:hover {
  transform: translateY(-1px);
  border-color: rgba(22, 93, 255, 0.18);
  background: #f8fbff;
  color: #165dff;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    0 10px 22px rgba(22, 93, 255, 0.06);
}

.sidebar-history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.history-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  padding: 11px 12px;
  border: 1px solid rgba(29, 33, 41, 0.06);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.94);
  cursor: pointer;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  animation: history-item-enter 0.24s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.history-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 999px;
  background: transparent;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.history-item:hover {
  border-color: rgba(22, 93, 255, 0.14);
  background: rgba(255, 255, 255, 0.99);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    0 12px 24px rgba(15, 23, 42, 0.04);
  transform: translateY(-1px);
}

.history-item-active {
  border-color: rgba(22, 93, 255, 0.1);
  background: #f7f8fa;
  box-shadow: none;
}

.history-item-active::before {
  background: #165dff;
}

.history-item-active .history-item-title {
  color: #1d2129;
  font-weight: 500;
}

.history-item-main {
  min-width: 0;
  flex: 1;
}

.history-item-top {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding-right: 2px;
}

.history-item-title {
  font-size: 12px;
  line-height: 1.52;
  font-weight: 500;
  color: #20242b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-item-badge {
  flex-shrink: 0;
  height: 17px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(22, 93, 255, 0.1);
  color: #165dff;
  font-size: 10px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.history-item-meta,
.history-item-time {
  margin-top: 4px;
  font-size: 10px;
  line-height: 1.35;
  color: #7a818d;
}

.history-item-delete {
  width: 22px;
  height: 22px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: rgba(247, 248, 250, 0.72);
  color: #9aa2ad;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 1px;
  transition: all 0.18s ease;
}

.history-item-delete-icon {
  position: relative;
  width: 10px;
  height: 10px;
  display: inline-flex;
}

.history-item-delete-icon::before,
.history-item-delete-icon::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 0;
  width: 1.5px;
  height: 10px;
  border-radius: 999px;
  background: currentColor;
}

.history-item-delete-icon::before {
  transform: rotate(45deg);
}

.history-item-delete-icon::after {
  transform: rotate(-45deg);
}

.history-item-delete:hover {
  border-color: rgba(29, 33, 41, 0.08);
  background: #ffffff;
  color: #5c6470;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.05);
}

@keyframes history-item-enter {
  from {
    opacity: 0;
    transform: translateX(-5px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.sidebar-history-empty {
  min-height: 176px;
  border: 1px dashed rgba(129, 137, 151, 0.26);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.52), rgba(247, 248, 250, 0.82));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 18px;
}

.sidebar-history-empty-title {
  font-size: 12px;
  font-weight: 600;
  color: #20242b;
}

.sidebar-history-empty-desc {
  margin-top: 6px;
  font-size: 10px;
  line-height: 1.6;
  color: #7a818d;
}

.sa-message-box {
  border-radius: 20px !important;
  border: 1px solid rgba(29, 33, 41, 0.08) !important;
  box-shadow:
    0 18px 44px rgba(15, 23, 42, 0.12),
    0 2px 8px rgba(15, 23, 42, 0.06) !important;
  padding: 18px 18px 16px !important;
}

.sa-message-box .el-message-box__header {
  padding-bottom: 6px;
}

.sa-message-box .el-message-box__title {
  font-size: 20px;
  font-weight: 700;
  color: #20242b;
}

.sa-message-box .el-message-box__headerbtn {
  top: 16px;
  right: 16px;
}

.sa-message-box .el-message-box__status {
  width: 22px;
  height: 22px;
  margin-right: 10px;
  border-radius: 999px;
  background: rgba(22, 93, 255, 0.08);
  color: #165dff !important;
}

.sa-message-box .el-message-box__content {
  padding-top: 4px;
  padding-bottom: 8px;
}

.sa-message-box .el-message-box__message {
  font-size: 14px;
  line-height: 1.7;
  color: #4e5969;
}

.sa-message-box .el-message-box__btns {
  padding-top: 8px;
}

.sa-message-box .el-button {
  min-width: 96px;
  height: 36px;
  border-radius: 999px;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 14px;
  cursor: pointer;
  color: #6b7280;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(29, 33, 41, 0.06);
  font-size: 12px;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar.sidebar-collapsed .sidebar-footer {
  width: 44px;
  min-width: 44px;
  height: 44px;
  padding: 0;
  margin: 8px auto 0;
  border-radius: 14px;
  justify-content: center;
  align-items: center;
  align-self: center;
  gap: 0;
  display: flex;
}

.sidebar-footer:hover {
  background: #ffffff;
  border-color: rgba(22, 93, 255, 0.12);
  color: #165dff;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
  transform: translateY(-1px);
}

.main-shell {
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  gap: 18px;
  background: transparent;
}

.topbar-smart {
  padding: 10px 24px 8px;
}

.topbar-heading {
  display: flex;
  align-items: center;
  min-width: 0;
}

.topbar-title-row {
  display: flex;
  align-items: baseline;
  gap: 0;
  min-width: 0;
}

.topbar-brand {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #171a20;
  white-space: nowrap;
}

.topbar-divider {
  display: inline-block;
  width: 1px;
  height: 18px;
  margin: 0 14px;
  background: rgba(29, 33, 41, 0.12);
  align-self: center;
  flex-shrink: 0;
}

.topbar-workspace {
  font-size: 14px;
  font-weight: 400;
  color: #888;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.clock {
  font-variant-numeric: tabular-nums;
  color: var(--ink-soft);
  font-size: 12px;
}

.page-wrap {
  padding: 0 18px 18px;
  overflow: auto;
}

.page-wrap-smart {
  overflow: hidden;
  display: flex;
  min-height: 0;
}

.page-wrap-smart > * {
  flex: 1;
  min-height: 0;
}

.page-wrap > * {
  animation: page-enter 0.28s ease;
}

.history-panel-enter-active,
.history-panel-leave-active {
  transition: all 0.2s ease;
}

.history-panel-enter-from,
.history-panel-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@keyframes page-enter {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1080px) {
  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .topbar-title-row {
    gap: 10px;
  }

  .topbar-right {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
