<template>
  <el-container class="app-shell">
    <el-aside class="sidebar" :width="collapsed ? '78px' : '244px'">
      <div class="brand">
        <div class="brand-mark">VA</div>
        <div v-if="!collapsed" class="brand-text">
          <div class="brand-title">智能问数</div>
          <div class="brand-subtitle">Four-Agent Workspace</div>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        class="nav-menu"
        router
        :collapse="collapsed"
        background-color="transparent"
        text-color="#8c919b"
        active-text-color="#22252b"
      >
        <el-menu-item index="/smart-ask">
          <el-icon><ChatLineRound /></el-icon>
          <template #title>智能问数</template>
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

      <div class="sidebar-footer" @click="collapsed = !collapsed">
        <el-icon><component :is="collapsed ? 'Expand' : 'Fold'" /></el-icon>
        <span v-if="!collapsed">收起导航</span>
      </div>
    </el-aside>

    <el-container class="main-shell">
      <el-header class="topbar">
        <div>
          <div class="topbar-title">{{ currentTitle }}</div>
          <div class="topbar-subtitle">{{ currentSubtitle }}</div>
        </div>
        <div class="topbar-right">
          <el-tag :type="backendOk ? 'success' : 'danger'" effect="plain" round>
            {{ backendOk ? '后端在线' : '后端异常' }}
          </el-tag>
          <div class="clock">{{ currentTime }}</div>
        </div>
      </el-header>

      <el-main class="page-wrap">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { healthCheck } from './api/index.js'

const route = useRoute()
const collapsed = ref(false)
const backendOk = ref(false)
const currentTime = ref('')

const titleMap = {
  '/': '仪表盘',
  '/smart-ask': '智能问数',
  '/agents': 'AGENT管理',
  '/datasets': '数据集管理',
  '/databases': '数据源管理',
  '/ai-models': 'AI模型配置',
  '/feishu-sync': '飞书同步'
}

const subtitleMap = {
  '/': '系统概览与运行状态',
  '/smart-ask': '四Agent 协作式问数与老板确认流转',
  '/agents': '维护四个中枢大脑的系统提示词与知识规则',
  '/datasets': '维护每个数据集的书架元数据与 Golden SQL',
  '/databases': '管理 PostgreSQL 与其他连接源',
  '/ai-models': '配置默认模型与模型连接',
  '/feishu-sync': '飞书多维表格同步、日志与运行控制'
}

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => titleMap[route.path] || '智能问数')
const currentSubtitle = computed(() => subtitleMap[route.path] || '企业级问数工作台')

const refreshClock = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

const pingBackend = async () => {
  try {
    await healthCheck()
    backendOk.value = true
  } catch (error) {
    backendOk.value = false
  }
}

let clockTimer = null
let healthTimer = null

onMounted(() => {
  refreshClock()
  pingBackend()
  clockTimer = setInterval(refreshClock, 1000)
  healthTimer = setInterval(pingBackend, 10000)
})

onUnmounted(() => {
  clearInterval(clockTimer)
  clearInterval(healthTimer)
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
  padding: 18px 14px;
  backdrop-filter: blur(16px);
  background: rgba(245, 246, 248, 0.74);
  border-right: 1px solid var(--panel-border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 10px 18px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: white;
  background: linear-gradient(135deg, #545c67, #242931);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
}

.brand-title {
  font-size: 18px;
  font-weight: 700;
}

.brand-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: var(--ink-soft);
}

.nav-menu {
  flex: 1;
  border-right: none !important;
}

.nav-menu.el-menu {
  border-right: none;
}

.nav-menu .el-menu-item {
  margin: 6px 0;
  border-radius: 14px;
  height: 48px;
  transition: all 0.2s ease;
}

.nav-menu .el-menu-item.is-active {
  background: linear-gradient(135deg, #ffffff, #dde1e7) !important;
  box-shadow: 0 10px 24px rgba(80, 87, 96, 0.14);
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 14px;
  cursor: pointer;
  color: var(--ink-soft);
  background: rgba(255, 255, 255, 0.45);
}

.main-shell {
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 26px;
  background: transparent;
}

.topbar-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.topbar-subtitle {
  margin-top: 4px;
  color: var(--ink-soft);
  font-size: 13px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.clock {
  font-variant-numeric: tabular-nums;
  color: var(--ink-soft);
  font-size: 13px;
}

.page-wrap {
  padding: 0 24px 24px;
  overflow: auto;
}

.page-wrap > * {
  animation: page-enter 0.28s ease;
}

@keyframes page-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
