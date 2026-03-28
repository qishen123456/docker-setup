<template>
  <el-container class="app-layout">
    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo-area">
        <el-icon size="28" color="#409EFF"><DataAnalysis /></el-icon>
        <span v-if="!collapsed" class="logo-text">智能问数</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        :collapse="collapsed"
        background-color="#001529"
        text-color="#a6b0c3"
        active-text-color="#409EFF"
      >
        <!-- 智能聊天 - 置顶且特殊样式 -->
        <el-menu-item index="/chat" class="chat-menu-item">
          <el-icon><ChatLineRound /></el-icon>
          <template #title>智能聊天</template>
        </el-menu-item>
        
        <el-divider style="margin: 8px 0; border-color: rgba(255,255,255,0.1)" />
        
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        <el-menu-item index="/databases">
          <el-icon><Coin /></el-icon>
          <template #title>数据源管理</template>
        </el-menu-item>
        <el-menu-item index="/ai-models">
          <el-icon><MagicStick /></el-icon>
          <template #title>AI模型配置</template>
        </el-menu-item>
        <el-menu-item index="/training">
          <el-icon><DataBoard /></el-icon>
          <template #title>训练数据</template>
        </el-menu-item>
        <el-menu-item index="/analysis-prompts">
          <el-icon><Document /></el-icon>
          <template #title>分析提示词</template>
        </el-menu-item>
        <el-menu-item index="/feishu-sync">
          <el-icon><Connection /></el-icon>
          <template #title>飞书同步</template>
        </el-menu-item>
      </el-menu>
      <div class="collapse-btn" @click="collapsed = !collapsed">
        <el-icon>
          <component :is="collapsed ? 'Expand' : 'Fold'" />
        </el-icon>
      </div>
    </el-aside>

    <!-- 主区域 -->
    <el-container class="main-area">
      <!-- 顶栏 -->
      <el-header class="top-header">
        <div class="header-left">
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <!-- 新增：元素直连按钮 -->
          <el-button 
            :type="inspectMode ? 'primary' : ''" 
            :icon="inspectMode ? 'Aim' : 'Search'"
            size="small"
            @click="toggleInspectMode"
            :title="inspectMode ? '正在寻找元素...点击目标以复制信息' : '开启元素直连：点击页面元素告诉助手该改哪里'"
          >
            {{ inspectMode ? '正在定位...' : 'UI 元素直连' }}
          </el-button>

          <el-tag :type="backendOk ? 'success' : 'danger'" size="small">
            <el-icon class="is-loading" v-if="checkingBackend"><Loading /></el-icon>
            {{ backendOk ? '后端已连接' : '后端未连接' }}
          </el-tag>
          <span class="time-label">{{ currentTime }}</span>
        </div>
      </el-header>

      <!-- 页面内容 -->
      <el-main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 元素信息对话框 -->
    <el-dialog v-model="showInspectorDialog" title="选中元素信息" width="500px">
      <div v-if="inspectedInfo" class="inspector-box">
        <p class="inspect-desc">已成功提取该元素的元数据，您可以直接点击下方按钮复制，并粘贴给助手。</p>
        <div class="inspect-item">
          <label>标签 & 路径:</label>
          <code>{{ inspectedInfo.tagName }}{{ inspectedInfo.id ? '#' + inspectedInfo.id : '' }}{{ inspectedInfo.className ? '.' + inspectedInfo.className.replace(/ /g, '.') : '' }}</code>
        </div>
        <div class="inspect-item">
          <label>包含文字:</label>
          <div class="inspect-text">{{ inspectedInfo.innerText || '(无文字内容)' }}</div>
        </div>
        <div class="inspect-item">
          <label>所属页面:</label>
          <span>{{ currentTitle }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="showInspectorDialog = false">取消</el-button>
        <el-button type="primary" @click="copyInspectInfo">点击复制并发送给助手</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { healthCheck } from './api/index.js'

const route = useRoute()
const collapsed = ref(false)
const backendOk = ref(false)
const checkingBackend = ref(true)
const currentTime = ref('')

// --- 新置：UI 元素直连逻辑 ---
const inspectMode = ref(false)
const showInspectorDialog = ref(false)
const inspectedInfo = ref(null)

const toggleInspectMode = () => {
  inspectMode.value = !inspectMode.value
  if (inspectMode.value) {
    document.body.classList.add('inspect-active')
    window.addEventListener('click', handleGlobalClick, true)
    ElMessage.info('元素直连模式已开启，请点击页面上的任何元素获取信息')
  } else {
    document.body.classList.remove('inspect-active')
    window.removeEventListener('click', handleGlobalClick, true)
  }
}

const handleGlobalClick = (e) => {
  if (!inspectMode.value) return
  
  // 阻止默认行为和冒泡，防止点击按钮触发原始逻辑或跳转
  e.preventDefault()
  e.stopPropagation()

  const target = e.target
  inspectedInfo.value = {
    tagName: target.tagName.toLowerCase(),
    className: target.className && typeof target.className === 'string' ? target.className : '',
    id: target.id || '',
    innerText: target.innerText?.trim().substring(0, 100) || '',
    path: route.path
  }
  
  showInspectorDialog.value = true
  toggleInspectMode() // 选中后自动关闭模式
}

const copyInspectInfo = () => {
  const info = inspectedInfo.value
  const text = `### UI 元素修改反馈\n**位置**: ${currentTitle.value} (${info.path})\n**元素**: \`${info.tagName}${info.id ? '#' + info.id : ''}${info.className ? '.' + info.className.replace(/ /g, '.') : ''}\`\n**文字内容**: "${info.innerText}"\n\n请帮我修改这个元素，我的需求是：`
  
  navigator.clipboard.writeText(text)
  ElMessage.success('元素信息已复制，请粘贴发送给助手并描述您的修改需求')
  showInspectorDialog.value = false
}
// --- 逻辑结束 ---

const titleMap = {
  '/': '仪表盘',
  '/databases': '数据源管理',
  '/ai-models': 'AI模型配置',
  '/training': '训练数据',
  '/chat': '智能聊天',
  '/feishu-sync': '飞书同步'
}

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => titleMap[route.path] || '页面不存在')

// 更新系统时间
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', { hour12: false })
}

// 检测后端连接状态
const checkBackend = async () => {
  try {
    await healthCheck()
    backendOk.value = true
  } catch (e) {
    backendOk.value = false
  } finally {
    checkingBackend.value = false
  }
}

let timeTimer, backendTimer
onMounted(() => {
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
  checkBackend()
  backendTimer = setInterval(checkBackend, 10000)
})
onUnmounted(() => {
  clearInterval(timeTimer)
  clearInterval(backendTimer)
  window.removeEventListener('click', handleGlobalClick, true)
  document.body.classList.remove('inspect-active')
})
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0f2f5; }

/* 元素直连激活状态 */
body.inspect-active * { cursor: crosshair !important; }
body.inspect-active *:hover { outline: 2px solid #409EFF !important; outline-offset: -2px; background: rgba(64,158,255,0.05) !important; }

/* 弹窗样式 */
.inspector-box { padding: 10px 0; }
.inspect-desc { font-size: 13px; color: #606266; margin-bottom: 20px; border-left: 4px solid #409EFF; padding-left: 10px; }
.inspect-item { margin-bottom: 16px; }
.inspect-item label { display: block; font-weight: 600; font-size: 12px; color: #909399; text-transform: uppercase; margin-bottom: 6px; }
.inspect-item code { background: #f4f4f5; color: #409EFF; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 13px; word-break: break-all; }
.inspect-text { font-size: 14px; color: #303133; background: #fafafa; padding: 10px; border-radius: 4px; border: 1px solid #ebeef5; font-style: italic; }

.app-layout { height: 100vh; overflow: hidden; }

/* 侧边栏 */
.sidebar {
  background: #001529;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
}
.sidebar .el-menu { border-right: none; flex: 1; }
.logo-area {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  white-space: nowrap;
  overflow: hidden;
}
.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
}
.collapse-btn {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a6b0c3;
  cursor: pointer;
  border-top: 1px solid rgba(255,255,255,0.1);
  transition: background 0.2s;
}
.collapse-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }

/* 顶栏 */
.top-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #f0f0f0;
  height: 64px;
  box-shadow: 0 1px 4px rgba(0,21,41,0.08);
}
.page-title { font-size: 18px; font-weight: 600; color: #262626; }
.header-right { display: flex; align-items: center; gap: 16px; }
.time-label { color: #8c8c8c; font-size: 13px; }

/* 主内容区 */
.page-content {
  background: #f0f2f5;
  padding: 24px;
  overflow-y: auto;
  height: calc(100vh - 64px);
}

/* 路由切换动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 全局样式微调 */
.el-card { border-radius: 8px; border: none; box-shadow: 0 1px 8px rgba(0,0,0,0.07)!important; }
.el-card__header { font-weight: 600; color: #262626; }

/* 智能聊天菜单项特殊样式 */
.chat-menu-item {
  background: linear-gradient(135deg, #409EFF 0%, #36cfc9 100%) !important;
  margin: 8px;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
}

.chat-menu-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transition: left 0.5s;
}

.chat-menu-item:hover::before {
  left: 100%;
}

.chat-menu-item:hover {
  background: linear-gradient(135deg, #66b1ff 0%, #5cdbd3 100%) !important;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64,158,255,0.3) !important;
}

.chat-menu-item.is-active {
  background: linear-gradient(135deg, #2e7cd6 0%, #2ba891 100%) !important;
  box-shadow: 0 2px 8px rgba(64,158,255,0.4) !important;
}

.chat-menu-item .el-icon {
  color: #fff !important;
  font-size: 18px;
}

.chat-menu-item .el-menu-item__title {
  color: #fff !important;
  font-weight: 600 !important;
  font-size: 15px !important;
}

/* 分割线样式 */
.el-divider {
  border-color: rgba(255,255,255,0.08) !important;
}
</style>
