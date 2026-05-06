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
          <el-menu-item index="/smart-ask" data-tooltip="问数会话">
            <el-icon><ChatLineRound /></el-icon>
            <template #title>问数会话</template>
          </el-menu-item>
          <el-menu-item index="/agents" data-tooltip="AGENT管理">
            <el-icon><Cpu /></el-icon>
            <template #title>AGENT管理</template>
          </el-menu-item>
          <el-menu-item index="/datasets" data-tooltip="数据集管理">
            <el-icon><Collection /></el-icon>
            <template #title>数据集管理</template>
          </el-menu-item>
          <el-menu-item index="/databases" data-tooltip="数据源管理">
            <el-icon><Coin /></el-icon>
            <template #title>数据源管理</template>
          </el-menu-item>
          <el-menu-item index="/ai-models" data-tooltip="AI模型配置">
            <el-icon><MagicStick /></el-icon>
            <template #title>AI模型配置</template>
          </el-menu-item>
          <el-menu-item index="/report-config" data-tooltip="报告配置">
            <el-icon><Document /></el-icon>
            <template #title>报告配置</template>
          </el-menu-item>
          <el-menu-item index="/feishu-sync" data-tooltip="飞书同步">
            <el-icon><Connection /></el-icon>
            <template #title>飞书同步</template>
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
                <button
                  v-if="historySessions.length"
                  class="sidebar-history-more"
                  type="button"
                  @click="historyDrawerVisible = true"
                >
                  全部 {{ historySessions.length }}
                </button>
                <button
                  v-if="historyPreviewList.length"
                  class="sidebar-history-clear"
                  type="button"
                  @click="clearHistoryList"
                >
                  清空
                </button>
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

      <el-drawer
        v-model="historyDrawerVisible"
        title="全部历史对话"
        size="420px"
        custom-class="history-drawer"
      >
        <div class="history-drawer-head">
          <div>
            <div class="history-drawer-title">{{ historySessions.length }} 条问数记录</div>
            <div class="history-drawer-desc">选择任意记录可恢复到问数会话。</div>
          </div>
          <button v-if="historySessions.length" class="history-drawer-clear" type="button" @click="clearHistoryList">
            清空全部
          </button>
        </div>
        <div v-if="historySessions.length" class="history-drawer-list">
          <article
            v-for="(item, index) in historySessions"
            :key="item.id"
            class="history-item history-drawer-item"
            :class="{ 'history-item-active': item.id === activeHistoryId }"
            @click="openHistorySession(item); historyDrawerVisible = false"
          >
            <div class="history-drawer-index">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="history-item-main">
              <div class="history-item-top">
                <div class="history-item-title">{{ item.title }}</div>
                <span v-if="item.id === activeHistoryId" class="history-item-badge">当前</span>
              </div>
              <div class="history-drawer-meta-row">
                <span class="history-drawer-dataset">{{ item.datasetName || '自动路由数据集' }}</span>
                <span class="history-drawer-time">{{ item.updatedAt }}</span>
              </div>
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
        <div v-else class="sidebar-history-empty history-drawer-empty">
          <div class="sidebar-history-empty-title">暂无历史记录</div>
          <div class="sidebar-history-empty-desc">发起问数后，这里会沉淀可恢复的对话记录。</div>
        </div>
      </el-drawer>

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
          <span class="backend-status-chip" :class="{ 'is-online': backendOk, 'is-offline': !backendOk }">
            <span class="backend-status-dot"></span>
            {{ backendOk ? '后端在线' : '后端异常' }}
          </span>
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
const historyDrawerVisible = ref(false)

const titleMap = {
  '/smart-ask': '经营问答台',
  '/agents': 'AGENT管理',
  '/datasets': '数据集管理',
  '/databases': '数据源管理',
  '/ai-models': 'AI模型配置',
  '/report-config': '报告配置',
  '/feishu-sync': '飞书同步'
}

const subtitleMap = {
  '/smart-ask': '',
  '/agents': '维护四个核心Agent的系统提示词与知识规则',
  '/datasets': '维护每个数据集的书架元数据与Golden SQL',
  '/databases': '管理PostgreSQL与其他连接源',
  '/ai-models': '配置默认模型与模型连接',
  '/report-config': '为数据集配置独立的报告渲染规则',
  '/feishu-sync': '飞书多维表格同步、日志与任务控制'
}

const activeMenu = computed(() => route.path)
const isSmartAskRoute = computed(() => route.path === '/smart-ask')
const currentTitle = computed(() => titleMap[route.path] || '经营问答台')
const currentSubtitle = computed(() => subtitleMap[route.path] || '经营分析工作台')
const activeDatasetIds = computed(() => session.activeDatasetIds.value || [])
const historyPreviewList = computed(() => historySessions.value.slice(0, 5))
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
  --shell-bg: var(--bg-page, #f9fafb);
  --panel-bg: var(--bg-card, #ffffff);
  --panel-border: var(--border, #e5e6eb);
  --ink-strong: var(--text-title, #1d2129);
  --ink-soft: var(--text-muted, #86909c);
  --brand: #3370ff;
  --brand-soft: #e1ecff;
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  margin: 0;
  height: 100%;
  background: var(--bg-page, #f9fafb);
  font-family: var(--font-sans, 'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC', sans-serif);
  color: var(--ink-strong);
}

.app-shell {
  height: 100%;
}

.sidebar {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 14px 12px;
  background:
    radial-gradient(circle at 22% 0%, rgba(15, 118, 110, 0.1), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(247, 250, 252, 0.92) 100%);
  border-right: 1px solid rgba(18, 48, 79, 0.08);
  box-shadow: 8px 0 28px rgba(18, 48, 79, 0.045);
  transition: width var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
  overflow-x: hidden;
}

.sidebar::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(18, 48, 79, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(18, 48, 79, 0.02) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.65), transparent 70%);
}

.sidebar.sidebar-collapsed {
  padding: 14px 8px 12px;
  align-items: center;
  overflow-x: hidden;
  scrollbar-width: none;
}

.sidebar.sidebar-collapsed::-webkit-scrollbar,
.sidebar.sidebar-collapsed *::-webkit-scrollbar {
  width: 0 !important;
  height: 0 !important;
  display: none;
}

.sidebar.sidebar-collapsed * {
  scrollbar-width: none;
}

.brand {
  position: relative;
  z-index: 1;
  padding: 6px 6px 14px;
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
  min-height: 54px;
  padding: 8px 10px;
  border-radius: 16px;
  background:
    radial-gradient(circle at 0% 0%, rgba(15, 118, 110, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(246, 249, 250, 0.9));
  border: 1px solid rgba(18, 48, 79, 0.08);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 10px 20px rgba(18, 48, 79, 0.06),
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
    linear-gradient(135deg, #122033 0%, #123f68 50%, #0f766e 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.14),
    0 10px 22px rgba(18, 48, 79, 0.2);
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
  font-size: 14px;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: #20242b;
}

.brand-subtitle {
  margin-top: 2px;
  font-size: 10px;
  color: #667085;
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
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  scrollbar-width: none;
}

.sidebar-body::-webkit-scrollbar {
  display: none;
}

.sidebar.sidebar-collapsed .sidebar-body {
  width: 100%;
  align-items: center;
}

.nav-menu {
  flex: none;
  border-right: none !important;
  padding-top: 4px;
  overflow-x: hidden;
  scrollbar-width: none;
}

.nav-menu::-webkit-scrollbar {
  display: none;
}

.sidebar.sidebar-collapsed .nav-menu {
  width: 100% !important;
  margin: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow-x: hidden;
  scrollbar-width: none;
}

.sidebar.sidebar-collapsed .nav-menu::-webkit-scrollbar {
  display: none;
}

.nav-menu.el-menu {
  border-right: none;
}

.nav-menu .el-menu-item {
  position: relative;
  margin: 4px 0;
  border-radius: 14px;
  height: 42px;
  color: #667085 !important;
  border: 1px solid transparent;
  font-weight: 650;
  transition: all var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
}

.nav-menu .el-menu-item::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 11px;
  bottom: 11px;
  width: 3px;
  border-radius: 999px;
  background: transparent;
  transition: all var(--duration-normal, 220ms) var(--ease-out);
}

.nav-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.78) !important;
  border-color: rgba(18, 48, 79, 0.07);
  color: #1f3349 !important;
  box-shadow: 0 8px 18px rgba(18, 48, 79, 0.05);
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item {
  position: relative;
  width: 44px !important;
  min-width: 44px !important;
  max-width: 44px !important;
  height: 44px !important;
  margin: 4px auto !important;
  padding: 0 !important;
  border-radius: 12px;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-sizing: border-box !important;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-light, #f0f1f3);
  overflow: visible !important;
  line-height: 44px !important;
  transition: all var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item:hover {
  border-color: rgba(15, 118, 110, 0.18);
  background: #e8f6f4;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item.is-active {
  background: linear-gradient(135deg, #e8f6f4, #ffffff) !important;
  border-color: rgba(15, 118, 110, 0.24) !important;
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.12) !important;
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item .el-icon {
  width: 20px;
  height: 20px;
  margin: 0 !important;
  padding: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  font-size: 18px;
}

/* ===== Collapsed Tooltip — 升级版 ===== */
.sidebar.sidebar-collapsed .nav-menu .el-menu-item::after {
  content: attr(data-tooltip);
  position: absolute;
  left: calc(100% + 10px);
  top: 50%;
  transform: translateY(-50%) translateX(4px);
  padding: 6px 12px;
  border-radius: 6px;
  background: rgba(29, 33, 41, 0.88);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.02em;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  transition: opacity var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1)),
              transform var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
  z-index: 2000;
}

/* Tooltip 小三角 */
.sidebar.sidebar-collapsed .nav-menu .el-menu-item::before {
  content: '';
  position: absolute;
  left: calc(100% + 4px);
  top: 50%;
  transform: translateY(-50%) translateX(4px);
  width: 6px;
  height: 6px;
  background: rgba(29, 33, 41, 0.88);
  clip-path: polygon(0 50%, 100% 0, 100% 100%);
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1)),
              transform var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
  z-index: 2000;
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item:hover::after,
.sidebar.sidebar-collapsed .nav-menu .el-menu-item:hover::before {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

/* Override Element Plus el-menu--collapse internal structure */
/* 注意：<style> 非 scoped，:deep() 无效，必须用普通选择器 */
.sidebar.sidebar-collapsed .el-menu--collapse {
  width: 100% !important;
  overflow-x: hidden !important;
  scrollbar-width: none;
}

.sidebar.sidebar-collapsed .el-menu--collapse::-webkit-scrollbar {
  display: none;
}

.sidebar.sidebar-collapsed .el-menu,
.sidebar.sidebar-collapsed .el-menu--collapse,
.sidebar.sidebar-collapsed .el-menu--collapse > * {
  max-width: 100% !important;
}

/* 菜单项外壳 */
.sidebar.sidebar-collapsed .el-menu--collapse .el-menu-item {
  position: relative;
  width: 44px !important;
  min-width: 44px !important;
  max-width: 44px !important;
  height: 44px !important;
  margin: 4px auto !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-light, #f0f1f3);
  border-radius: 12px;
  line-height: 44px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}

/* ★ 关键：el-tooltip__trigger 是导致偏移的元凶 —— 强制它也 flex 居中且无 padding */
.sidebar.sidebar-collapsed .el-menu--collapse .el-menu-item .el-tooltip__trigger {
  width: 100% !important;
  height: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  line-height: 1 !important;
  box-sizing: border-box !important;
}

/* ★ 图标层：确保无任何干扰 */
.sidebar.sidebar-collapsed .el-menu--collapse .el-menu-item .el-icon {
  width: 20px !important;
  height: 20px !important;
  margin: 0 !important;
  padding: 0 !important;
  font-size: 18px !important;
  line-height: 1 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  flex-shrink: 0 !important;
}

/* ★ 图标内的 SVG 确保不溢出 */
.sidebar.sidebar-collapsed .el-menu--collapse .el-menu-item .el-icon svg {
  width: 18px !important;
  height: 18px !important;
}

/* 隐藏折叠态的文字 span（Element Plus 内部会生成一个 span 放 title） */
.sidebar.sidebar-collapsed .el-menu--collapse .el-menu-item span:not(.el-icon) {
  display: none !important;
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item > * {
  flex-shrink: 0;
}

.nav-menu .el-menu-item.is-active {
  background:
    radial-gradient(circle at 0% 0%, rgba(15, 118, 110, 0.1), transparent 36%),
    linear-gradient(135deg, #e8f6f4 0%, #ffffff 100%) !important;
  color: #0b625d !important;
  border: 1px solid rgba(15, 118, 110, 0.2);
  box-shadow: 0 8px 20px rgba(15, 118, 110, 0.1);
  font-weight: 800;
}

.nav-menu .el-menu-item.is-active::before {
  background: #0f766e;
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
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  margin-bottom: 12px;
}

.sidebar-history-head > div:first-child {
  min-width: 0;
  flex: none;
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
  height: 28px;
  padding: 0 9px;
  border: 1px solid rgba(218, 45, 59, 0.14);
  border-radius: 999px;
  background: #fff1f2;
  color: #c52b35;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-history-more {
  height: 28px;
  padding: 0 9px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 999px;
  background: #e8f6f4;
  color: #0b625d;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-history-more:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 118, 110, 0.3);
  background: #d9f0ed;
  color: #084f4b;
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.1);
}

.sidebar-history-clear:hover {
  transform: translateY(-1px);
  border-color: rgba(218, 45, 59, 0.28);
  background: #ffe4e6;
  color: #a61f2b;
  box-shadow: 0 8px 18px rgba(218, 45, 59, 0.1);
}

.sidebar-history-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  white-space: nowrap;
  flex-wrap: nowrap;
  justify-content: flex-start;
}

.sidebar-history-new {
  height: 28px;
  padding: 0 10px;
  min-width: 54px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff 0%, #f1faf9 100%);
  color: #0b625d;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-history-new:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 118, 110, 0.32);
  background: #e8f6f4;
  color: #084f4b;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    0 10px 22px rgba(15, 118, 110, 0.1);
}

.sidebar-history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: none;
  min-height: 0;
  overflow: hidden;
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

.history-drawer {
  border-radius: 24px 0 0 24px;
  overflow: hidden;
  border-left: 1px solid rgba(18, 48, 79, 0.08);
  box-shadow: -18px 0 46px rgba(18, 48, 79, 0.14);
}

.history-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 24px 26px 16px;
  border-bottom: 1px solid rgba(18, 48, 79, 0.08);
  background:
    radial-gradient(circle at 100% 0%, rgba(15, 118, 110, 0.12), transparent 30%),
    linear-gradient(180deg, #ffffff 0%, #f8fbfa 100%);
}

.history-drawer .el-drawer__title {
  color: #101828;
  font-size: 20px;
  font-weight: 900;
  letter-spacing: -0.02em;
}

.history-drawer .el-drawer__body {
  padding: 18px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background:
    radial-gradient(circle at 100% 0%, rgba(15, 118, 110, 0.09), transparent 30%),
    radial-gradient(circle at 0% 18%, rgba(18, 63, 104, 0.06), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.history-drawer-head {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 16px;
  border: 1px solid rgba(15, 118, 110, 0.14);
  border-radius: 20px;
  background:
    radial-gradient(circle at 0% 0%, rgba(15, 118, 110, 0.12), transparent 36%),
    rgba(255, 255, 255, 0.84);
  box-shadow: 0 10px 24px rgba(18, 48, 79, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.history-drawer-title {
  color: #101828;
  font-size: 16px;
  font-weight: 900;
}

.history-drawer-desc {
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
}

.history-drawer-clear {
  height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(218, 45, 59, 0.14);
  border-radius: 999px;
  background: #fff1f2;
  color: #c52b35;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.history-drawer-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 4px;
}

.history-drawer-item {
  position: relative;
  margin: 0;
  align-items: center;
  gap: 12px;
  min-height: 78px;
  padding: 14px 42px 14px 14px;
  border-radius: 20px;
  border-color: rgba(18, 48, 79, 0.07);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.92));
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.history-drawer-item:hover {
  border-color: rgba(15, 118, 110, 0.2);
  box-shadow: 0 12px 26px rgba(18, 48, 79, 0.08);
}

.history-drawer-item.history-item-active {
  border-color: rgba(15, 118, 110, 0.26);
  background:
    radial-gradient(circle at 100% 0%, rgba(15, 118, 110, 0.1), transparent 30%),
    linear-gradient(135deg, #e8f6f4 0%, #ffffff 100%);
  box-shadow: 0 12px 28px rgba(15, 118, 110, 0.1), inset 4px 0 0 #0f766e;
}

.history-drawer-index {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #0b625d;
  font-size: 11px;
  font-weight: 900;
  background: #e8f6f4;
  border: 1px solid rgba(15, 118, 110, 0.15);
}

.history-drawer-meta-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.history-drawer-dataset {
  max-width: 190px;
  height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  color: #0b625d;
  font-size: 11px;
  font-weight: 750;
  background: #e8f6f4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-drawer-time {
  color: #8a94a6;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.history-drawer-item .history-item-delete {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
}

.history-drawer-item:hover .history-item-delete {
  opacity: 1;
}

.history-drawer-empty {
  flex: 1;
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
  border-radius: 10px;
  cursor: pointer;
  color: var(--text-muted, #86909c);
  background: transparent;
  border: 1px solid transparent;
  font-size: 12px;
  transition: all var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
}

.sidebar.sidebar-collapsed .sidebar-footer {
  width: 44px;
  min-width: 44px;
  height: 44px;
  padding: 0;
  margin: 8px auto 0;
  border-radius: 12px;
  justify-content: center;
  align-items: center;
  align-self: center;
  gap: 0;
  display: flex;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-light, #f0f1f3);
}

.sidebar-footer:hover {
  background: var(--color-primary-light, #f0f5ff);
  border-color: rgba(51, 112, 255, 0.12);
  color: var(--color-primary, #3370ff);
}

.main-shell {
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 28px;
  gap: 18px;
  background: transparent;
  border-bottom: 1px solid var(--border-light, #f0f1f3);
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
  gap: 10px;
  flex-shrink: 0;
}

.backend-status-chip {
  height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 750;
  letter-spacing: 0.01em;
  border: 1px solid rgba(18, 48, 79, 0.1);
  background: linear-gradient(180deg, #ffffff 0%, #f6f8fb 100%);
  color: #4b5565;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.backend-status-chip.is-online {
  border-color: rgba(15, 118, 110, 0.22);
  background: linear-gradient(180deg, #f5fbfa 0%, #e8f6f4 100%);
  color: #0b625d;
}

.backend-status-chip.is-offline {
  border-color: rgba(218, 45, 59, 0.2);
  background: linear-gradient(180deg, #fff7f7 0%, #ffecec 100%);
  color: #a61f2b;
}

.backend-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 14%, transparent);
}

.clock {
  font-variant-numeric: tabular-nums;
  color: #667085;
  font-size: 12px;
}

.page-wrap {
  padding: 0 24px 24px;
  overflow: auto;
  background: var(--bg-page, #f9fafb);
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
