<template>
  <router-view v-if="isAuthCallbackRoute" />
  <div v-else-if="!authReady" class="auth-loading-screen">
    <div class="auth-loading-card">
      <div class="auth-loading-mark"></div>
      <strong>正在校验登录状态</strong>
      <span>请稍候...</span>
    </div>
  </div>
  <AuthLogin v-else-if="!authUser" @authenticated="handleAuthenticated" />
  <el-container v-else class="app-shell">
    <el-aside class="sidebar sa-dark-panel" :class="{ 'sidebar-collapsed': collapsed }" :width="collapsed ? '72px' : '248px'">
      <div class="brand">
        <div class="brand-pill" :class="{ 'is-collapsed': collapsed }">
          <img src="/angel-logowite.png" alt="ANGEL" class="brand-logo" />
          <div v-if="!collapsed" class="brand-text">
            <div class="brand-title">ANGEL</div>
            <div class="brand-subtitle">安吉尔智能问数</div>
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
          :default-openeds="managementDefaultOpeneds"
          @select="handleMenuSelect"
        >
          <el-menu-item
            v-for="item in primaryMenuItems"
            :key="item.path"
            :index="item.path"
            :data-tooltip="item.label"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.label }}</template>
          </el-menu-item>
          <el-sub-menu
            v-if="managementMenuItems.length"
            index="management"
            class="nav-group"
            data-tooltip="管理配置"
          >
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>管理配置</span>
            </template>
            <el-menu-item
              v-for="item in managementMenuItems"
              :key="item.path"
              :index="item.path"
              :data-tooltip="item.label"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>{{ item.label }}</template>
            </el-menu-item>
          </el-sub-menu>
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
                <div class="sidebar-history-title">任务 ({{ historyPreviewList.length + (currentRunningTask ? 1 : 0) }})</div>
              </div>
              <div class="sidebar-history-actions">
                <button
                  v-if="historySessions.length"
                  class="sidebar-history-more"
                  type="button"
                  @click="historyDrawerVisible = true"
                >
                  全部 {{ historySessions.length }}
                </button>
                <button
                  v-if="historyPreviewList.length && appFeatureAccess.app_history_clear"
                  class="sidebar-history-clear"
                  type="button"
                  :disabled="isClearingHistory"
                  @click="clearHistoryList"
                >
                  {{ isClearingHistory ? '清空中...' : '清空' }}
                </button>
              </div>
            </div>

            <div v-if="historyPreviewList.length || currentRunningTask" class="sidebar-history-list">
              <!-- 虚拟"当前执行任务"行：不持久化，仅 session.status === 'running' 时显示 -->
              <article
                v-if="currentRunningTask"
                class="history-item history-item-running"
                :key="currentRunningTask.id"
                :aria-label="'当前任务：' + currentRunningTask.title"
                @click="handleRunningTaskClick"
              >
                <div class="history-item-main">
                  <div class="history-item-title">{{ currentRunningTask.title }}</div>
                  <div class="history-item-bottom">
                    <div class="history-item-time">刚刚发起</div>
                    <div class="history-item-status">
                      <TaskStatusIndicator
                        :variant="currentRunningTask.status"
                        :show-text-label="true"
                      />
                    </div>
                  </div>
                </div>
              </article>

              <article
                v-for="item in historyPreviewList"
                :key="item.id"
                class="history-item"
                :class="{ 'history-item-active': item.id === activeHistoryId }"
                @click="openHistorySession(item)"
              >
                <div class="history-item-main">
                  <div class="history-item-title">{{ item.title }}</div>
                  <div class="history-item-bottom">
                    <div class="history-item-time">{{ item.updatedAt }}</div>
                    <div class="history-item-status">
                      <TaskStatusIndicator
                        :variant="inferTaskVariant(item)"
                        :show-text-label="true"
                      />
                      <span v-if="item.id === activeHistoryId" class="history-item-badge">当前</span>
                    </div>
                  </div>
                </div>
                <button
                  v-if="appFeatureAccess.app_history_delete"
                  class="history-item-delete"
                  type="button"
                  aria-label="删除任务"
                  @click.stop="removeHistoryItem(item.id)"
                >
                  <span class="history-item-delete-icon" aria-hidden="true"></span>
                </button>
              </article>
            </div>

            <div v-else class="sidebar-history-empty">
              <div class="sidebar-history-empty-title">暂无任务</div>
              <div class="sidebar-history-empty-desc">发起分析后，这里会显示你的任务记录。</div>
            </div>
          </section>
        </transition>
      </div>

      <el-drawer
        v-model="historyDrawerVisible"
        title="全部任务"
        size="420px"
        custom-class="history-drawer"
      >
        <div class="history-drawer-head">
          <div>
            <div class="history-drawer-title">{{ historySessions.length }} 个任务</div>
            <div class="history-drawer-desc">选择任意任务可恢复到分析工作台。</div>
          </div>
          <button
            v-if="historySessions.length && appFeatureAccess.app_history_clear"
            class="history-drawer-clear"
            type="button"
            :disabled="isClearingHistory"
            @click="clearHistoryList"
          >
            {{ isClearingHistory ? '清空中...' : '清空全部' }}
          </button>
        </div>
        <div v-if="historySessions.length || currentRunningTask" class="history-drawer-list">
          <!-- 抽屉里的虚拟"当前执行任务"行 -->
          <article
            v-if="currentRunningTask"
            class="history-item history-drawer-item history-item-running"
            :key="currentRunningTask.id"
            :aria-label="'当前任务：' + currentRunningTask.title"
            @click="handleRunningTaskClick; historyDrawerVisible = false"
          >
            <div class="history-drawer-index">{{ currentRunningTask.status === 'pending_confirmation' ? '待确认' : '执行' }}</div>
            <div class="history-item-main">
              <div class="history-item-top">
                <div class="history-item-title">{{ currentRunningTask.title }}</div>
                <div class="history-item-status">
                  <TaskStatusIndicator
                    :variant="currentRunningTask.status"
                    :show-text-label="true"
                  />
                </div>
              </div>
              <div class="history-drawer-meta-row">
                <span class="history-drawer-dataset">{{ currentRunningTask.datasetName }}</span>
                <span class="history-drawer-time">刚刚发起</span>
              </div>
            </div>
          </article>

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
                <div class="history-item-status">
                  <TaskStatusIndicator
                    :variant="inferTaskVariant(item)"
                    :show-text-label="true"
                  />
                  <span v-if="item.id === activeHistoryId" class="history-item-badge">当前</span>
                </div>
              </div>
              <div class="history-drawer-meta-row">
                <span class="history-drawer-dataset">{{ item.datasetName || '自动路由数据集' }}</span>
                <span class="history-drawer-time">{{ item.updatedAt }}</span>
              </div>
            </div>
            <button
              v-if="appFeatureAccess.app_history_delete"
              class="history-item-delete"
              type="button"
              aria-label="删除任务"
              @click.stop="removeHistoryItem(item.id)"
            >
              <span class="history-item-delete-icon" aria-hidden="true"></span>
            </button>
          </article>
        </div>
        <div v-else class="sidebar-history-empty history-drawer-empty">
          <div class="sidebar-history-empty-title">暂无任务</div>
          <div class="sidebar-history-empty-desc">发起分析后，这里会显示你的任务记录。</div>
        </div>
      </el-drawer>

      <div class="sidebar-footer" @click="collapsed = !collapsed">
        <el-icon><component :is="collapsed ? 'Expand' : 'Fold'" /></el-icon>
        <span v-if="!collapsed">收起导航</span>
      </div>
    </el-aside>

    <el-container class="main-shell">
      <el-header class="topbar sa-dark-panel" :class="{ 'topbar-smart': isSmartAskRoute }">
        <div class="topbar-heading">
          <div class="topbar-title-row">
            <div class="topbar-workspace">{{ currentTitle }}</div>
            <button v-if="showBackToConsole" class="topbar-back-console" type="button" @click="backToConsole">
              返回控制台
            </button>
          </div>
        </div>
        <div class="topbar-right">
          <div class="auth-user-menu">
            <button class="auth-user-chip" type="button" @click.stop="toggleUserMenu">
              <span class="auth-user-avatar">{{ authUserInitial }}</span>
              <span class="auth-user-name">{{ authUserName }}</span>
              <span class="auth-user-role">{{ authRoleLabel }}</span>
              <span class="auth-user-arrow" aria-hidden="true"></span>
            </button>
            <div v-if="userMenuVisible" class="auth-user-dropdown" @click.stop>
              <button
                v-if="authRole === 'super_admin' && appFeatureAccess.admin_console"
                type="button"
                @click="openAdminConsole"
              >
                <strong>系统控制台</strong>
                <span>功能开关与灰度发布</span>
              </button>
              <button v-if="appFeatureAccess.app_password_change" type="button" @click="openPasswordDialog">
                <strong>修改密码</strong>
                <span>更新当前账号登录密码</span>
              </button>
              <button class="danger" type="button" @click="handleLogout">
                <strong>退出登录</strong>
                <span>清除本机登录状态</span>
              </button>
            </div>
          </div>
          <span class="backend-status-chip" :class="{ 'is-online': backendOk, 'is-offline': !backendOk }">
            <span class="backend-status-dot"></span>
            {{ backendOk ? '后端在线' : '后端异常' }}
          </span>
          <div class="clock">{{ currentTime }}</div>
        </div>
      </el-header>

      <el-main class="page-wrap" :class="{ 'page-wrap-smart': isSmartAskRoute }">
        <router-view v-slot="{ Component }">
          <keep-alive :include="cachedPageNames">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>

    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="420px"
      custom-class="password-dialog"
      :close-on-click-modal="false"
    >
      <div class="password-panel">
        <span class="password-panel-icon">锁</span>
        <div>
          <h3>更新登录密码</h3>
          <p>建议使用至少 8 位，并包含数字和字母的密码。</p>
        </div>
      </div>
      <div class="password-form">
        <label>
          <span>原密码</span>
          <div class="dialog-password-control">
            <input
              v-model="passwordForm.old_password"
              :type="passwordVisible.old ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="请输入当前密码"
              @keydown.enter="submitPasswordChange"
            />
            <button
              class="dialog-password-eye"
              type="button"
              :aria-label="passwordVisible.old ? '隐藏原密码' : '显示原密码'"
              @click="passwordVisible.old = !passwordVisible.old"
            >
              <el-icon><component :is="passwordVisible.old ? Hide : View" /></el-icon>
            </button>
          </div>
        </label>
        <label>
          <span>新密码</span>
          <div class="dialog-password-control">
            <input
              v-model="passwordForm.new_password"
              :type="passwordVisible.next ? 'text' : 'password'"
              autocomplete="new-password"
              placeholder="至少 8 位"
              @keydown.enter="submitPasswordChange"
            />
            <button
              class="dialog-password-eye"
              type="button"
              :aria-label="passwordVisible.next ? '隐藏新密码' : '显示新密码'"
              @click="passwordVisible.next = !passwordVisible.next"
            >
              <el-icon><component :is="passwordVisible.next ? Hide : View" /></el-icon>
            </button>
          </div>
        </label>
        <label>
          <span>确认新密码</span>
          <div class="dialog-password-control">
            <input
              v-model="passwordForm.confirm_password"
              :type="passwordVisible.confirm ? 'text' : 'password'"
              autocomplete="new-password"
              @keydown.enter="submitPasswordChange"
            />
            <button
              class="dialog-password-eye"
              type="button"
              :aria-label="passwordVisible.confirm ? '隐藏确认密码' : '显示确认密码'"
              @click="passwordVisible.confirm = !passwordVisible.confirm"
            >
              <el-icon><component :is="passwordVisible.confirm ? Hide : View" /></el-icon>
            </button>
          </div>
        </label>
      </div>
      <template #footer>
        <button class="dialog-ghost-button" type="button" @click="passwordDialogVisible = false">取消</button>
        <button class="dialog-primary-button" type="button" :disabled="passwordSaving" @click="submitPasswordChange">
          {{ passwordSaving ? '保存中...' : '确认修改' }}
        </button>
      </template>
    </el-dialog>

    <div
      v-if="showAdminConsoleFloat"
      class="admin-console-float"
      :style="adminConsoleFloatStyle"
      @pointerdown="startAdminConsoleFloatDrag"
    >
      <button
        class="admin-console-float-main"
        :class="{ dragging: adminConsoleFloatDragging }"
        type="button"
        @click.stop="handleAdminConsoleFloatOpen"
      >
        <el-icon><Setting /></el-icon>
        <span>控制台</span>
      </button>
      <button
        class="admin-console-float-close"
        type="button"
        aria-label="关闭控制台悬浮入口"
        @pointerdown.stop
        @click.stop="dismissAdminConsoleFloat"
      >
        x
      </button>
    </div>
    <SqlDebugFloat />
  </el-container>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { ChatLineRound, Coin, Collection, Connection, Cpu, Document, Hide, Lock, MagicStick, Monitor, Operation, Setting, Share, UploadFilled, View } from '@element-plus/icons-vue'
import AuthLogin from './auth/AuthLogin.vue'
import SqlDebugFloat from './components/SqlDebugFloat.vue'
import TaskStatusIndicator from './components/TaskStatusIndicator.vue'
import { preloadRouteComponents } from './router'
import { changePassword, clearAuthToken, getCurrentUser, healthCheck, logout } from './api/index.js'
import { useSmartAskSession } from './state/smartAskSession.js'
import { useSmartAskHistory } from './state/smartAskHistory.js'
import { useSmartAskTaskView } from './state/smartAskTaskView.js'
import { useFeatureFlags } from './state/featureFlags.js'

const route = useRoute()
const router = useRouter()
const session = useSmartAskSession()
const {
  historySessions,
  activeHistoryId,
  buildHistoryScope,
  setHistoryScope,
  loadHistory,
  syncHistory,
  removeHistory,
  clearHistory,
  requestRestore,
  setActiveHistory,
} = useSmartAskHistory()
const {
  runningSessionId,
  runningTaskStatus,
  completedTaskId,
  viewingTaskId,
  isViewingReadonly,
  setRunningSessionId,
  setViewingTask,
  switchViewToDefault,
  clearRunningSessionId,
  switchViewToRunning,
} = useSmartAskTaskView()
const {
  features: featureFlags,
  ready: featureFlagsReady,
  loadFeatureFlags,
  clearFeatureFlags,
} = useFeatureFlags()
const appFeatureKeys = [
  'app_history_clear',
  'app_history_delete',
  'admin_console',
  'app_password_change',
]
const appFeatureAccess = computed(() => appFeatureKeys.reduce((map, key) => {
  map[key] = isFeatureEnabled(key)
  return map
}, {}))
const collapsed = ref(false)
const backendOk = ref(false)
const authUser = ref(null)
const authReady = ref(false)
const passwordDialogVisible = ref(false)
const passwordSaving = ref(false)
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})
const passwordVisible = ref({
  old: false,
  next: false,
  confirm: false,
})
const currentTime = ref('')
const historyPanelRef = ref(null)
const historyPanelHighlighted = ref(false)
const historyDrawerVisible = ref(false)
const isClearingHistory = ref(false)
const userMenuVisible = ref(false)

const roleRank = {
  super_admin: 4,
  admin: 3,
  business_admin: 2,
  user: 1
}

const menuItems = [
  { path: '/smart-ask', label: '智能分析工作台', icon: ChatLineRound, minRole: 'user', featureKey: 'smart_ask_workspace' },
  { path: '/sql-debug', label: 'SQL调试台', icon: Monitor, minRole: 'user', featureKey: 'dataset_sql_preview_run' },
  { path: '/agents', label: '智能体编排配置', icon: Cpu, minRole: 'admin', featureKey: 'agent_management' },
  { path: '/datasets', label: '数据资产管理', icon: Collection, minRole: 'admin', featureKey: 'dataset_management' },
  { path: '/databases', label: '数据连接管理', icon: Coin, minRole: 'admin', featureKey: 'database_management' },
  { path: '/ai-models', label: '模型服务配置', icon: MagicStick, minRole: 'admin', featureKey: 'ai_model_config' },
  { path: '/report-config', label: '报告模板配置', icon: Document, minRole: 'admin', featureKey: 'report_config' },
  { path: '/advanced-capabilities', label: '进阶能力中心', icon: Operation, minRole: 'admin', featureKey: 'advanced_capabilities' },
  { path: '/feishu-sync', label: '飞书数据同步', icon: Connection, minRole: 'admin', featureKey: 'feishu_sync' },
  { path: '/runtime-migration', label: '迁移发布管理', icon: UploadFilled, minRole: 'super_admin', featureKey: 'runtime_migration' },
  { path: '/organization-trees', label: '组织树管理', icon: Share, minRole: 'super_admin', featureKey: 'organization_tree_management' },
  { path: '/employee-permissions', label: '角色权限管理', icon: Lock, minRole: 'super_admin', featureKey: 'employee_permissions' },
  { path: '/admin-console', label: '系统控制台', icon: Setting, minRole: 'super_admin', featureKey: 'admin_console', hidden: true }
]

const routeComponentNamesByPath = {
  '/smart-ask': 'SmartAsk',
  '/sql-debug': 'SqlDebug',
  '/agents': 'AgentManagement',
  '/datasets': 'DatasetManagement',
  '/bookshelves': 'Bookshelves',
  '/databases': 'Databases',
  '/ai-models': 'AIModels',
  '/report-config': 'DatasetReportConfig',
  '/advanced-capabilities': 'AdvancedCapabilities',
  '/feishu-sync': 'FeishuSync',
  '/runtime-migration': 'RuntimeMigration',
  '/organization-trees': 'OrganizationTrees',
  '/employee-permissions': 'EmployeePermissions',
  '/admin-console': 'AdminConsole',
}

const subtitleMap = {
  '/smart-ask': '',
  '/sql-debug': '快速生成、执行与核对问数 SQL',
  '/agents': '维护核心智能体提示词与执行规则',
  '/datasets': '治理数据集元数据、书架与Golden SQL',
  '/databases': '管理 PostgreSQL 与其他业务数据连接',
  '/ai-models': '配置默认模型、通道与调用参数',
  '/report-config': '维护数据集对应的报告模板与展示规范',
  '/advanced-capabilities': '管理进阶问数 Skill、MCP 和 SQL Server 工具链路',
  '/feishu-sync': '管理飞书多维表格同步、日志与任务控制',
  '/runtime-migration': '导出导入运行态配置，发布前自动备份可回滚',
  '/organization-trees': '维护多套独立组织树类型与树形节点',
  '/employee-permissions': '维护员工身份映射、角色与可访问范围'
}

const activeMenu = computed(() => route.path)
const isAuthCallbackRoute = computed(() => route.path === '/auth/callback')
const isSmartAskRoute = computed(() => route.path === '/smart-ask')
const showBackToConsole = computed(() => route.query?.from === 'admin-console' && route.path !== '/admin-console')
const authRole = computed(() => authUser.value?.role || 'user')
const authRoleLabel = computed(() => ({ super_admin: '超级管理员', admin: '管理员', business_admin: '业务管理员', user: '普通用户' }[authRole.value] || '普通用户'))
const canAccessRole = (minRole) => (roleRank[authRole.value] || 0) >= (roleRank[minRole] || 0)
const isFeatureEnabled = (key) => {
  if (!key) return true
  const feature = featureFlags.value?.[key]
  if (!featureFlagsReady.value || !feature) return true
  if (typeof feature.available === 'boolean') return feature.available
  return Boolean(feature.enabled)
}
const hasLoadedFeatureDecision = (key) => Boolean(key && featureFlagsReady.value && featureFlags.value?.[key])
const canAccessMenuItem = (item) => {
  if (!item) return true
  if (hasLoadedFeatureDecision(item.featureKey)) {
    return isFeatureEnabled(item.featureKey)
  }
  return canAccessRole(item.minRole)
}
const availableMenuItems = computed(() => menuItems.filter((item) => !item.hidden && canAccessMenuItem(item)))
const primaryMenuItems = computed(() => availableMenuItems.value.filter((item) => item.path === '/smart-ask' || item.path === '/sql-debug'))
const managementMenuItems = computed(() => availableMenuItems.value.filter((item) => item.path !== '/smart-ask' && item.path !== '/sql-debug'))
const cachedPageNames = computed(() => (
  Array.from(new Set(availableMenuItems.value.map((item) => routeComponentNamesByPath[item.path]).filter(Boolean)))
))
const managementDefaultOpeneds = computed(() => (
  managementMenuItems.value.some((item) => item.path === route.path) ? ['management'] : []
))
const currentTitle = computed(() => menuItems.find((item) => item.path === route.path)?.label || '智能分析工作台')
const currentSubtitle = computed(() => subtitleMap[route.path] || '经营分析工作台')
const activeDatasetIds = computed(() => session.activeDatasetIds.value || [])
const historyPreviewList = computed(() => historySessions.value.slice(0, 4))
const showHistorySidebar = computed(() => route.path === '/smart-ask' && !collapsed.value)
// 虚拟"当前执行/待确认任务"：session 在跑或待确认时显示在历史列表顶部，不持久化
const currentRunningTask = computed(() => {
  const status = session.state?.status
  if (status !== 'running' && status !== 'waiting_confirmation') return null
  const question = String(session.state?.question || '').trim()
  if (!question) return null
  return {
    id: '__current_running__',
    title: question.slice(0, 24),
    datasetName: status === 'waiting_confirmation' ? '待确认' : '正在分析中',
    status: status === 'waiting_confirmation' ? 'pending_confirmation' : 'running',
    isVirtual: true,
  }
})
const cleanDisplayName = (value) => {
  const text = String(value || '').trim()
  if (!text || /^[?\s]+$/.test(text)) return ''
  return text.replace(/^\?+\s*/, '')
}
const authUserName = computed(() => (
  cleanDisplayName(authUser.value?.name)
  || cleanDisplayName(authUser.value?.permission_name)
  || cleanDisplayName(authUser.value?.username)
  || cleanDisplayName(authUser.value?.zh_name)
  || cleanDisplayName(authUser.value?.union_id)
  || '已登录'
))
const authUserInitial = computed(() => String(authUserName.value || '登').slice(0, 1).toUpperCase())

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

const refreshAuthUser = async () => {
  try {
    const data = await getCurrentUser()
    authUser.value = data?.authenticated ? (data.user || {}) : null
    syncHistoryScope()
    if (authUser.value) {
      loadFeatureFlags(true)
        .then(() => enforceRouteAccess())
        .catch(() => {})
      syncHistory().catch(() => {})
      scheduleRoutePreload()
    } else clearFeatureFlags()
  } catch {
    authUser.value = null
    clearFeatureFlags()
    syncHistoryScope()
  } finally {
    authReady.value = true
  }
}

const syncHistoryScope = () => {
  if (!authUser.value) {
    setHistoryScope('anonymous')
    return
  }
  setHistoryScope(buildHistoryScope(authUser.value))
}

const handleAuthenticated = async (user) => {
  authUser.value = user || null
  syncHistoryScope()
  if (authUser.value) {
    loadFeatureFlags(true)
      .then(() => enforceRouteAccess())
      .catch(() => {})
    syncHistory().catch(() => {})
    scheduleRoutePreload()
  } else clearFeatureFlags()
  authReady.value = true
  enforceRouteAccess()
}

const submitPasswordChange = async () => {
  if (passwordSaving.value) return
  if (authRole.value === 'super_admin') {
    ElMessage.warning('超级管理员密码由 .env 管理，请修改 SMARTASK_ADMIN_PASSWORD')
    return
  }
  if (!passwordForm.value.old_password || !passwordForm.value.new_password) {
    ElMessage.warning('请填写原密码和新密码')
    return
  }
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (passwordForm.value.new_password.length < 8) {
    ElMessage.warning('新密码至少需要 8 位')
    return
  }
  passwordSaving.value = true
  try {
    await changePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password
    })
    passwordDialogVisible.value = false
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    passwordVisible.value = { old: false, next: false, confirm: false }
    ElMessage({
      message: '密码已修改，请重新登录',
      type: 'success',
      duration: 2200,
      customClass: 'app-toast-modern',
    })
    clearAuthToken()
    authUser.value = null
    clearFeatureFlags()
    syncHistoryScope()
  } finally {
    passwordSaving.value = false
  }
}

const toggleUserMenu = () => {
  userMenuVisible.value = !userMenuVisible.value
}

const closeUserMenu = () => {
  userMenuVisible.value = false
}

const openPasswordDialog = () => {
  closeUserMenu()
  passwordDialogVisible.value = true
}

const ADMIN_CONSOLE_LAST_ROUTE_KEY = 'smartask_admin_console_last_route'

const getAdminConsoleTarget = () => {
  const fallback = '/admin-console'
  const saved = localStorage.getItem(ADMIN_CONSOLE_LAST_ROUTE_KEY) || sessionStorage.getItem(ADMIN_CONSOLE_LAST_ROUTE_KEY) || ''
  return saved.startsWith('/admin-console') ? saved : fallback
}

const openAdminConsole = () => {
  closeUserMenu()
  router.push(getAdminConsoleTarget())
}

const backToConsole = () => {
  router.push(getAdminConsoleTarget())
}

const ADMIN_CONSOLE_FLOAT_POSITION_KEY = 'smartask_admin_console_float_position'
const ADMIN_CONSOLE_FLOAT_HIDDEN_KEY = 'smartask_admin_console_float_hidden'
const ADMIN_CONSOLE_FLOAT_TOGGLE_EVENT = 'smartask-admin-console-float-toggle'
const adminConsoleFloatVisible = ref(false)
const adminConsoleFloatDragging = ref(false)
const adminConsoleFloatPosition = ref({ x: 0, y: 0 })
let adminConsoleFloatMoved = false
let adminConsoleFloatOffset = { x: 0, y: 0 }

const getDefaultAdminConsoleFloatPosition = () => ({
  x: Math.max(16, window.innerWidth - 164),
  y: Math.max(88, window.innerHeight - 118),
})

const clampAdminConsoleFloatPosition = (position) => {
  const width = 154
  const height = 56
  return {
    x: Math.min(Math.max(12, Number(position?.x) || 0), Math.max(12, window.innerWidth - width)),
    y: Math.min(Math.max(76, Number(position?.y) || 0), Math.max(76, window.innerHeight - height)),
  }
}

const persistAdminConsoleFloatState = () => {
  sessionStorage.setItem(ADMIN_CONSOLE_FLOAT_POSITION_KEY, JSON.stringify(adminConsoleFloatPosition.value))
  sessionStorage.setItem(ADMIN_CONSOLE_FLOAT_HIDDEN_KEY, adminConsoleFloatVisible.value ? '0' : '1')
}

const restoreAdminConsoleFloatState = () => {
  const hidden = sessionStorage.getItem(ADMIN_CONSOLE_FLOAT_HIDDEN_KEY) !== '0'
  adminConsoleFloatVisible.value = !hidden
  try {
    const saved = JSON.parse(sessionStorage.getItem(ADMIN_CONSOLE_FLOAT_POSITION_KEY) || 'null')
    adminConsoleFloatPosition.value = clampAdminConsoleFloatPosition(saved || getDefaultAdminConsoleFloatPosition())
  } catch {
    adminConsoleFloatPosition.value = getDefaultAdminConsoleFloatPosition()
  }
}

const adminConsoleFloatStyle = computed(() => ({
  left: `${adminConsoleFloatPosition.value.x}px`,
  top: `${adminConsoleFloatPosition.value.y}px`,
}))

const showAdminConsoleFloat = computed(() => (
  authRole.value === 'super_admin'
  && appFeatureAccess.value.admin_console
  && adminConsoleFloatVisible.value
))

const stopAdminConsoleFloatDrag = () => {
  if (!adminConsoleFloatDragging.value) return
  adminConsoleFloatDragging.value = false
  persistAdminConsoleFloatState()
  window.removeEventListener('pointermove', handleAdminConsoleFloatDrag)
  window.removeEventListener('pointerup', stopAdminConsoleFloatDrag)
}

const handleAdminConsoleFloatDrag = (event) => {
  if (!adminConsoleFloatDragging.value) return
  adminConsoleFloatPosition.value = clampAdminConsoleFloatPosition({
    x: event.clientX - adminConsoleFloatOffset.x,
    y: event.clientY - adminConsoleFloatOffset.y,
  })
  adminConsoleFloatMoved = true
}

const startAdminConsoleFloatDrag = (event) => {
  if (event.button !== 0) return
  adminConsoleFloatDragging.value = true
  adminConsoleFloatMoved = false
  adminConsoleFloatOffset = {
    x: event.clientX - adminConsoleFloatPosition.value.x,
    y: event.clientY - adminConsoleFloatPosition.value.y,
  }
  window.addEventListener('pointermove', handleAdminConsoleFloatDrag)
  window.addEventListener('pointerup', stopAdminConsoleFloatDrag)
}

const handleAdminConsoleFloatOpen = () => {
  if (adminConsoleFloatMoved) {
    adminConsoleFloatMoved = false
    return
  }
  openAdminConsole()
}

const dismissAdminConsoleFloat = () => {
  adminConsoleFloatVisible.value = false
  persistAdminConsoleFloatState()
}

const handleAdminConsoleFloatResize = () => {
  adminConsoleFloatPosition.value = clampAdminConsoleFloatPosition(adminConsoleFloatPosition.value)
  persistAdminConsoleFloatState()
}

const handleAdminConsoleFloatToggle = (event) => {
  const visible = Boolean(event?.detail?.visible)
  adminConsoleFloatVisible.value = visible
  if (visible && (!adminConsoleFloatPosition.value.x || !adminConsoleFloatPosition.value.y)) {
    adminConsoleFloatPosition.value = getDefaultAdminConsoleFloatPosition()
  }
  persistAdminConsoleFloatState()
}

const handleLogout = async () => {
  try {
    await logout()
    clearAuthToken()
    authUser.value = null
    clearFeatureFlags()
    syncHistoryScope()
    ElMessage({
      message: '已退出登录',
      type: 'success',
      duration: 1800,
      customClass: 'app-toast-modern',
    })
  } catch {
    clearAuthToken()
    authUser.value = null
    clearFeatureFlags()
    syncHistoryScope()
  }
  if (route.path !== '/smart-ask') {
    router.replace('/smart-ask')
  }
}

const refreshCurrentPage = () => {
  window.location.reload()
}

const handleMenuSelect = (index) => {
  if (!index || index === route.path) return
  const target = menuItems.find((item) => item.path === index)
  if (target && !canAccessMenuItem(target)) {
    ElMessage.warning('该功能暂未开放')
    return
  }
  router.push(index)
}

const fallbackRoute = () => availableMenuItems.value[0]?.path || '/smart-ask'

const enforceRouteAccess = () => {
  if (!authUser.value || isAuthCallbackRoute.value) return
  const target = menuItems.find((item) => item.path === route.path)
  if (target && !canAccessMenuItem(target)) {
    const nextPath = fallbackRoute()
    if (route.path !== nextPath) router.replace(nextPath)
  }
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
  // 如果点击的就是当前运行中/待确认/刚完成的任务，直接切回对应视图
  if (runningSessionId.value === item.id || completedTaskId.value === item.id) {
    switchViewToRunning()
    await router.push('/smart-ask')
    pulseHistoryPanel()
  } else if (runningSessionId.value) {
    // 只要有后台运行中/待确认任务，都以只读模式打开历史，不打断当前任务
    setViewingTask(item.id)
    await requestRestore(item.id, { readonly: true })
    await router.push('/smart-ask')
    pulseHistoryPanel()
  } else {
    // 没有活动任务时才恢复历史并重置当前会话
    switchViewToDefault()
    requestRestore(item.id)
    await router.push('/smart-ask')
    pulseHistoryPanel()
  }
}

const removeHistoryItem = (id) => {
  removeHistory(id)
}

// 根据 history item 推断 TaskStatusIndicator 的 variant（仅历史项）
// 注意：执行中状态由 currentRunningTask 虚拟行单独处理
const inferTaskVariant = (item) => {
  if (item?.status === 'running' || (runningSessionId.value === item?.id && runningTaskStatus.value === 'running')) return 'running'
  const result = item?.reportSnapshot?.result || {}
  if (result.requires_confirmation) return 'pending_confirmation'
  if (result.error) return 'failed'
  return 'completed'
}

const createFreshChat = async () => {
  setActiveHistory('')
  switchViewToDefault()
  await router.push('/smart-ask')
  window.dispatchEvent(new CustomEvent('smartask-create-fresh-chat'))
  pulseHistoryPanel()
}

// 点击左侧执行中虚拟任务行：直接切回实时执行视图
const handleRunningTaskClick = async () => {
  switchViewToRunning()
  setActiveHistory(runningSessionId.value || '')
  await router.push('/smart-ask')
  pulseHistoryPanel()
}

const clearHistoryList = async () => {
  try {
    await ElMessageBox.confirm(
      '清空后将删除当前保存的全部任务记录。',
      '清空任务',
      {
        type: 'info',
        confirmButtonText: '确认清空',
        cancelButtonText: '取消',
        customClass: 'sa-message-box',
      }
    )
  } catch {
    // user cancelled
    return
  }

  isClearingHistory.value = true
  try {
    await clearHistory()
    ElMessage.success('任务已清空')
  } catch (error) {
    console.error('[clearHistoryList] failed to clear history', error)
    ElMessage.error('清空失败，任务记录已恢复，请稍后重试')
  } finally {
    isClearingHistory.value = false
  }
}

let clockTimer = null
let healthTimer = null
let historyFocusTimer = null
let routePreloadScheduled = false

const scheduleRoutePreload = () => {
  if (routePreloadScheduled) return
  routePreloadScheduled = true
  const preload = () => {
    preloadRouteComponents(cachedPageNames.value).catch(() => {})
  }
  if (typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(preload, { timeout: 2000 })
  } else {
    window.setTimeout(preload, 800)
  }
}

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

const handleGlobalClick = () => {
  closeUserMenu()
}

const handleFeatureFlagsUpdated = async () => {
  if (authUser.value) {
    await loadFeatureFlags(true)
  } else {
    clearFeatureFlags()
  }
  enforceRouteAccess()
}

onMounted(() => {
  refreshClock()
  pingBackend()
  refreshAuthUser()
  clockTimer = setInterval(refreshClock, 1000)
  healthTimer = setInterval(pingBackend, 10000)
  window.addEventListener('smartask-history-focus', handleHistoryFocus)
  window.addEventListener('click', handleGlobalClick)
  window.addEventListener('smartask-feature-flags-updated', handleFeatureFlagsUpdated)
})

onUnmounted(() => {
  clearInterval(clockTimer)
  clearInterval(healthTimer)
  if (historyFocusTimer) {
    clearTimeout(historyFocusTimer)
  }
  window.removeEventListener('smartask-history-focus', handleHistoryFocus)
  window.removeEventListener('click', handleGlobalClick)
  window.removeEventListener('smartask-feature-flags-updated', handleFeatureFlagsUpdated)
})

watch(() => route.path, (path) => {
  enforceRouteAccess()
  if (path === '/smart-ask') {
    loadHistory()
    syncHistory()
  }
})

watch(authUser, () => {
  syncHistoryScope()
  if (authUser.value) syncHistory()
  enforceRouteAccess()
})
onMounted(() => {
  restoreAdminConsoleFloatState()
  window.addEventListener('resize', handleAdminConsoleFloatResize)
  window.addEventListener(ADMIN_CONSOLE_FLOAT_TOGGLE_EVENT, handleAdminConsoleFloatToggle)
})

onUnmounted(() => {
  stopAdminConsoleFloatDrag()
  window.removeEventListener('resize', handleAdminConsoleFloatResize)
  window.removeEventListener(ADMIN_CONSOLE_FLOAT_TOGGLE_EVENT, handleAdminConsoleFloatToggle)
})
</script>

<style>
:root {
  --shell-bg: var(--bg-page, #F8F9FA);
  --panel-bg: var(--bg-card, #FFFFFF);
  --panel-border: var(--border, #E5E7EB);
  --ink-strong: var(--text-title, #111827);
  --ink-soft: var(--text-muted, #9CA3AF);
  --brand: #E61F24;
  --brand-soft: #FEF2F2;
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  margin: 0;
  height: 100%;
  background: var(--bg-page);
  font-family: var(--font-sans, 'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC', sans-serif);
  color: var(--text-title, #111827);
}

.app-shell {
  height: 100%;
}

.auth-loading-screen {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--bg-page, #F2EDE8);
}

.auth-loading-card {
  width: 260px;
  padding: 26px;
  border-radius: var(--radius-lg, 16px);
  display: grid;
  justify-items: center;
  gap: 9px;
  background: var(--bg-card, #FFFFFF);
  border: 1px solid var(--border, #E5E7EB);
  box-shadow: var(--shadow-lg, 0 4px 8px rgba(0,0,0,0.03), 0 16px 40px rgba(0,0,0,0.07));
  color: var(--text-title, #111827);
}

.auth-loading-card span {
  color: var(--text-secondary, #6B7280);
  font-size: 12px;
}

.auth-loading-mark {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: rgba(26, 24, 22, 0.88);
  animation: auth-loading-pulse 1.2s ease-in-out infinite alternate;
}

@keyframes auth-loading-pulse {
  from { transform: scale(0.92); opacity: 0.72; }
  to { transform: scale(1); opacity: 1; }
}

.sidebar {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 14px 12px;
  transition: width var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
  overflow: hidden;
  height: 100vh;
  box-sizing: border-box;
  border-right: none !important;
  box-shadow: 8px 0 32px rgba(0, 0, 0, 0.08) !important;
}

.sidebar::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: none;
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
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.sidebar.sidebar-collapsed .brand {
  width: 100%;
  padding: 0;
  justify-content: center;
}

.brand-pill {
  display: flex;
  align-items: center;
}

.brand-pill.is-collapsed {
  justify-content: center;
}

.brand-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
  flex-shrink: 0;
  opacity: 0.92;
}

.sidebar.sidebar-collapsed .brand-logo {
  height: 28px;
}

.brand-text,
.brand-caret {
  display: none !important;
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
  display: flex !important;
  align-items: center !important;
  gap: 10px;
  margin: 4px 0;
  padding: 0 14px !important;
  border-radius: var(--radius-sm, 8px);
  height: 42px;
  color: rgba(255, 255, 255, 0.65) !important;
  border: 1px solid transparent;
  font-weight: 650;
  transition: all var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
}

.nav-menu .el-sub-menu__title {
  position: relative;
  display: flex !important;
  align-items: center !important;
  gap: 10px;
  height: 42px;
  margin: 8px 0 4px;
  padding: 0 14px !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-sm, 8px);
  color: rgba(255, 255, 255, 0.65) !important;
  background: rgba(255, 255, 255, 0.04);
  font-weight: 800;
  transition: all var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
}

.nav-menu .el-menu-item .el-icon,
.nav-menu .el-sub-menu__title .el-icon:first-child {
  width: 20px;
  height: 20px;
  margin: 0 !important;
  flex: 0 0 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  font-size: 18px;
}

.nav-menu .el-menu-item span,
.nav-menu .el-sub-menu__title span {
  flex: 1;
  min-width: 0;
  line-height: 42px;
}

.nav-menu .el-sub-menu__title .el-sub-menu__icon-arrow {
  position: static;
  width: 16px;
  height: 16px;
  margin: 0 0 0 auto;
  transform: none;
  flex: 0 0 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.nav-menu .el-sub-menu.is-opened > .el-sub-menu__title .el-sub-menu__icon-arrow {
  transform: rotate(180deg);
}

.nav-menu .el-sub-menu__title:hover {
  color: #ffffff !important;
  background: rgba(255, 255, 255, 0.08) !important;
  border-color: rgba(255, 255, 255, 0.14);
}

.nav-menu .el-menu-item:hover {
  color: #ffffff !important;
  background: rgba(255, 255, 255, 0.08) !important;
  border-color: transparent;
}

.nav-menu .el-sub-menu .el-menu {
  padding: 2px 0 4px 12px;
  background: transparent !important;
}

.nav-menu .el-sub-menu .el-menu-item {
  height: 36px;
  margin: 3px 0;
  border-radius: 11px;
  font-size: 13px;
}

.nav-menu .el-sub-menu .el-menu-item .el-icon {
  font-size: 16px;
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
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow: visible !important;
  line-height: 44px !important;
  transition: all var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
  color: rgba(255, 255, 255, 0.65) !important;
}

.sidebar.sidebar-collapsed .nav-menu .el-sub-menu__title {
  width: 44px !important;
  min-width: 44px !important;
  max-width: 44px !important;
  height: 44px !important;
  margin: 4px auto !important;
  padding: 0 !important;
  border-radius: 12px;
  justify-content: center;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.65) !important;
}

.sidebar.sidebar-collapsed .nav-menu .el-sub-menu__title .el-sub-menu__icon-arrow,
.sidebar.sidebar-collapsed .nav-menu .el-sub-menu__title span {
  display: none;
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item:hover {
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.12);
  color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item.is-active {
  background: rgba(255, 255, 255, 0.06) !important;
  border-color: rgba(255, 255, 255, 0.10) !important;
  color: #ffffff !important;
  box-shadow: inset 3px 0 0 #F51F19 !important;
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item.is-active .el-icon {
  color: #ffffff !important;
}

.sidebar.sidebar-collapsed .nav-menu .el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  bottom: auto;
  width: 3px;
  height: 60%;
  border-radius: 0 999px 999px 0;
  background: #F51F19;
  clip-path: none;
  opacity: 1;
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 1;
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
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  line-height: 44px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
  color: rgba(255, 255, 255, 0.65) !important;
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
  background: rgba(255, 255, 255, 0.06) !important;
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.10);
  box-shadow: none;
  font-weight: 800;
}

.nav-menu .el-menu-item.is-active::before {
  left: 0;
  top: 50%;
  bottom: auto;
  width: 3px;
  height: 60%;
  border-radius: 0 999px 999px 0;
  background: #F51F19;
  transform: translateY(-50%);
}

.nav-menu .el-menu-item.is-active .el-icon,
.nav-menu .el-menu-item.is-active span {
  color: #ffffff !important;
}

.sidebar-history {
  position: relative;
  margin: 12px 0 12px;
  padding: 14px 12px 12px;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--radius-card, 12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
  backdrop-filter: blur(10px);
}

.sidebar-history-highlight {
  border-color: var(--brand-primary, #E61F24);
  box-shadow:
    0 0 0 3px var(--brand-primary-focus, rgba(230, 31, 36, 0.16)),
    var(--shadow-md, 0 2px 4px rgba(0,0,0,0.03), 0 8px 24px rgba(0,0,0,0.05));
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
  color: #ffffff;
}

.sidebar-history-subtitle {
  margin-top: 3px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
}

.sidebar-history-clear {
  height: 28px;
  padding: 0 9px;
  border: 1px solid var(--error-soft, #FEF2F2);
  border-radius: 999px;
  background: var(--error-soft, #FEF2F2);
  color: var(--error, #E61F24);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: none;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-history-more {
  height: 28px;
  padding: 0 9px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.8);
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: none;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-history-more:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.12);
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.sidebar-history-clear:hover {
  transform: translateY(-1px);
  border-color: rgba(230, 31, 36, 0.24);
  background: #fee2e2;
  color: var(--brand-primary-hover, #cc181d);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
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
  border: 1px solid var(--border, #E5E7EB);
  border-radius: 999px;
  background: var(--bg-card, #FFFFFF);
  color: var(--text-body, #374151);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(0,0,0,0.04));
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-history-new:hover {
  transform: translateY(-1px);
  border-color: var(--border-hover, #D1D5DB);
  background: var(--bg-soft, #F3F4F6);
  color: var(--text-title, #111827);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
}

.sidebar-history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 2px;
}

.history-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  /* 卡片均分列表剩余高度，填满面板不留底部空白 */
  flex: 1 1 0;
  min-height: 0;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  animation: history-item-enter 0.24s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.history-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 999px;
  background: transparent;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.history-item:hover {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.07);
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  transform: translateY(-1px);
}

.history-item-active {
  border-color: rgba(230, 31, 36, 0.25);
  background: rgba(230, 31, 36, 0.1);
  box-shadow: 0 2px 8px rgba(230, 31, 36, 0.08);
}

.history-item-active::before {
  background: var(--brand-primary, #E61F24);
}

.history-item-active .history-item-title {
  color: #ffffff;
  font-weight: 600;
}

.history-item-main {
  min-width: 0;
  flex: 1;
  /* 卡片内容垂直居中：标题在上，底行(时间+状态)在下 */
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  gap: 6px;
}

/* 卡片底行：时间靠左，状态靠右 */
.history-item-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
}

.history-item-top {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding-right: 2px;
  min-width: 0;
  flex: 1;
}

.history-item-title {
  font-size: 12px;
  line-height: 1.52;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-width: 0;
  /* 标题只占自然高度，不拉伸，由 main 垂直居中 */
  flex: 0 0 auto;
  /* 避免两行标题贴到右侧删除按钮 */
  padding-right: 4px;
}

.history-item-badge {
  flex-shrink: 0;
  height: 17px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--brand-primary, #E61F24);
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

/* 状态指示容器：标题 + 状态指示器 + 当前 badge 同行排列 */
.history-item-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  margin-left: auto;
}

/* 虚拟"当前执行任务"行：与历史项区分，左红竖条 + 微红底 */
.history-item-running {
  position: relative;
  background: linear-gradient(135deg, rgba(230, 31, 36, 0.1) 0%, rgba(230, 31, 36, 0.06) 100%);
  border: 1px solid rgba(230, 31, 36, 0.2);
  border-radius: 12px;
  margin-bottom: 10px;
  padding-right: 14px;
}

.history-item-running::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 2px;
  background: var(--brand-primary, #E61F24);
  opacity: 0.9;
}

.history-item-running .history-item-title {
  font-weight: 600;
}

.history-item-meta,
.history-item-time {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.55);
}

.history-item-delete {
  width: 22px;
  height: 22px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.6);
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
  border-color: var(--border, #E5E7EB);
  background: var(--bg-card, #FFFFFF);
  color: var(--text-secondary, #6B7280);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(0,0,0,0.04));
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
  border: 1px dashed var(--border-hover, #D1D5DB);
  border-radius: var(--radius-md, 12px);
  background: var(--bg-soft, #F3F4F6);
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
  color: var(--text-title, #111827);
}

.sidebar-history-empty-desc {
  margin-top: 6px;
  font-size: 10px;
  line-height: 1.6;
  color: var(--text-secondary, #6B7280);
}

.history-drawer {
  border-radius: 20px 0 0 20px;
  overflow: hidden;
  border-left: 1px solid rgba(17, 24, 39, 0.08);
  box-shadow: 0 24px 56px rgba(15, 23, 42, 0.12);
}

.history-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 24px 26px 16px;
  border-bottom: 1px solid var(--border, #E5E7EB);
  background: var(--bg-card, #FFFFFF);
}

.history-drawer .el-drawer__title {
  color: var(--text-title, #111827);
  font-size: 20px;
  font-weight: 900;
  letter-spacing: -0.02em;
}

.history-drawer .el-drawer__body {
  padding: 18px 18px 22px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #F8F8F7;
}

.history-drawer-head {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 16px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 16px;
  background: #FFFFFF;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.045);
}

.history-drawer-title {
  color: var(--text-title, #111827);
  font-size: 16px;
  font-weight: 900;
}

.history-drawer-desc {
  margin-top: 4px;
  color: var(--text-secondary, #6B7280);
  font-size: 12px;
}

.history-drawer-clear {
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--error-soft, #FEF2F2);
  border-radius: 999px;
  background: var(--error-soft, #FEF2F2);
  color: var(--error, #E61F24);
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
  gap: 14px;
  padding-right: 4px;
}

.history-drawer-item {
  position: relative;
  margin: 0;
  align-items: center;
  /* 抽屉内卡片保持自然高度，不参与侧栏卡片的均分拉伸 */
  flex: 0 0 auto;
  gap: 14px;
  min-height: 94px;
  padding: 18px 46px 18px 18px;
  border-radius: 16px;
  border-color: rgba(17, 24, 39, 0.07);
  background: #FFFFFF;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.035);
}

.history-drawer-item:hover {
  border-color: rgba(17, 24, 39, 0.12);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.055);
  background: #FFFFFF;
}

.history-drawer-item.history-item-active {
  border-color: rgba(230, 31, 36, 0.18);
  background: #F5F6F8;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.045),
    inset 4px 0 0 #E61F24;
}

.history-drawer-item.history-item-active::before {
  background: transparent;
}

.history-drawer-index {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
  font-size: 13px;
  font-weight: 900;
  background: #F1F0EE;
  border: 1px solid rgba(17, 24, 39, 0.08);
}

.history-drawer-item .history-item-title {
  color: #111827;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.45;
  text-shadow: none;
  -webkit-line-clamp: 2;
}

.history-drawer-item.history-item-active .history-item-title {
  color: #111827;
  font-weight: 900;
}

.history-drawer-meta-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

/* 抽屉内 main 恢复默认块布局，不继承侧栏卡片的垂直居中 */
.history-drawer-item .history-item-main {
  display: block;
  height: auto;
  justify-content: normal;
  gap: 0;
}

.history-drawer-dataset {
  max-width: 210px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  color: #6B7280;
  font-size: 12px;
  font-weight: 800;
  background: #F1F0EE;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-drawer-time {
  color: #9CA3AF;
  font-size: 12px;
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
  border-radius: var(--radius-xl, 20px) !important;
  border: 1px solid var(--border, #E5E7EB) !important;
  box-shadow: var(--shadow-lg, 0 4px 8px rgba(0,0,0,0.03), 0 16px 40px rgba(0,0,0,0.07)) !important;
  padding: 18px 18px 16px !important;
}

.sa-message-box .el-message-box__header {
  padding-bottom: 6px;
}

.sa-message-box .el-message-box__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-title, #111827);
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
  background: var(--bg-soft, #F3F4F6);
  color: var(--text-secondary, #6B7280) !important;
}

.sa-message-box .el-message-box__content {
  padding-top: 4px;
  padding-bottom: 8px;
}

.sa-message-box .el-message-box__message {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-body, #374151);
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
  color: rgba(255, 255, 255, 0.6);
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
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.6);
}

.sidebar-footer:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.14);
  color: #ffffff;
}

.main-shell {
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  height: 56px !important;
  border-bottom: none !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08) !important;
}

.topbar-smart {
  padding: 0 24px;
}

.topbar-heading {
  display: flex;
  align-items: center;
  min-width: 0;
}

.topbar-title-row {
  display: flex;
  align-items: center;
  gap: 0;
  min-width: 0;
}

.topbar-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
  /* logo 是黑色+白底，在深色topbar上需要做白色反转处理 */
  opacity: 0.92;
  flex-shrink: 0;
}

.topbar-brand {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #ffffff;
  white-space: nowrap;
}

.topbar-divider {
  display: inline-block;
  width: 1px;
  height: 18px;
  margin: 0 14px;
  background: rgba(255, 255, 255, 0.18);
  align-self: center;
  flex-shrink: 0;
}

.topbar-workspace {
  font-size: 14px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.72);
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.topbar-back-console {
  height: 28px;
  margin-left: 12px;
  padding: 0 11px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.86);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.topbar-back-console:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.22);
  color: #ffffff;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.admin-login-button,
.feishu-login-button {
  height: 30px;
  padding: 0 14px;
  border: 1px solid var(--border, #E5E7EB);
  border-radius: 999px;
  background: var(--bg-card, #FFFFFF);
  color: var(--text-body, #374151);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(0,0,0,0.04));
  transition: all 0.2s ease;
}

.admin-login-button {
  border-color: var(--border, #E5E7EB);
  background: var(--bg-card, #FFFFFF);
  color: var(--text-body, #374151);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(0,0,0,0.04));
}

.admin-login-button:hover,
.feishu-login-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.feishu-login-button:hover:not(:disabled) {
  border-color: var(--border-hover, #D1D5DB);
  background: var(--bg-soft, #F3F4F6);
}

.admin-login-button:hover {
  border-color: var(--border-hover, #D1D5DB);
  background: var(--bg-soft, #F3F4F6);
}

.feishu-login-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.auth-user-chip {
  height: 30px;
  padding: 3px 5px 3px 3px;
  border: 1px solid var(--border, #E5E7EB);
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: var(--bg-card, #FFFFFF);
  color: var(--text-title, #111827);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(0,0,0,0.04));
  cursor: pointer;
}

.auth-user-menu {
  position: relative;
  display: inline-flex;
}

.admin-console-float {
  position: fixed;
  z-index: 1200;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  touch-action: none;
}

.admin-console-float-main,
.admin-console-float-close {
  border: 1px solid var(--border, #E5E7EB);
  color: var(--text-title, #111827);
  background: var(--bg-card, #FFFFFF);
  box-shadow: var(--shadow-lg, 0 4px 8px rgba(0,0,0,0.03), 0 16px 40px rgba(0,0,0,0.07));
}

.admin-console-float-main {
  height: 44px;
  padding: 0 16px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: grab;
}

.admin-console-float-main.dragging {
  cursor: grabbing;
}

.admin-console-float-main .el-icon {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: var(--brand-black, #1A1A1A);
}

.admin-console-float-close {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.admin-console-float-main:hover,
.admin-console-float-close:hover {
  transform: translateY(-1px);
}

.auth-user-avatar {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-black, #1A1A1A);
  color: #fff;
  font-size: 11px;
  font-weight: 900;
}

.auth-user-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 750;
}

.auth-user-role {
  height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: var(--bg-soft, #F3F4F6);
  color: var(--text-secondary, #6B7280);
  font-size: 10px;
  font-weight: 900;
}

.auth-user-arrow {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: var(--text-muted, #9CA3AF);
  background: var(--bg-soft, #F3F4F6);
}

.auth-user-arrow::before {
  content: '';
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid currentColor;
  transform: translateY(1px);
}

.auth-user-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 40;
  width: 230px;
  padding: 8px;
  border: 1px solid var(--border, #E5E7EB);
  border-radius: var(--radius-lg, 16px);
  background: var(--bg-card, #FFFFFF);
  box-shadow: var(--shadow-lg, 0 4px 8px rgba(0,0,0,0.03), 0 16px 40px rgba(0,0,0,0.07));
  backdrop-filter: blur(12px);
}

.auth-user-dropdown::before {
  content: '';
  position: absolute;
  top: -6px;
  right: 24px;
  width: 10px;
  height: 10px;
  border-left: 1px solid var(--border, #E5E7EB);
  border-top: 1px solid var(--border, #E5E7EB);
  background: var(--bg-card, #FFFFFF);
  transform: rotate(45deg);
}

.auth-user-dropdown button {
  width: 100%;
  padding: 11px 12px;
  border: 0;
  border-radius: var(--radius-sm, 8px);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  background: transparent;
  color: var(--text-title, #111827);
  cursor: pointer;
  text-align: left;
}

.auth-user-dropdown button:hover {
  background: var(--bg-soft, #F3F4F6);
}

.auth-user-dropdown button strong {
  font-size: 13px;
}

.auth-user-dropdown button span {
  color: var(--text-secondary, #6B7280);
  font-size: 12px;
}

.auth-user-dropdown button.danger strong {
  color: var(--error, #E61F24);
}

.auth-logout-button {
  height: 22px;
  padding: 0 8px;
  border: 0;
  border-radius: 999px;
  background: var(--bg-soft, #F3F4F6);
  color: var(--text-secondary, #6B7280);
  font-size: 11px;
  font-weight: 750;
  cursor: pointer;
}

.auth-logout-button:hover {
  background: var(--border-light, #F3F4F6);
}

.admin-login-dialog {
  border-radius: 18px !important;
}

.admin-login-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.admin-login-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: var(--text-body, #374151);
  font-size: 13px;
  font-weight: 700;
}

.admin-login-field input {
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--border, #E5E7EB);
  border-radius: var(--radius-sm, 8px);
  outline: none;
  color: var(--text-title, #111827);
  font-size: 14px;
  transition: all 0.18s ease;
}

.admin-login-field input:focus {
  border-color: var(--brand-primary, #E61F24);
  box-shadow: 0 0 0 3px var(--brand-primary-focus, rgba(230, 31, 36, 0.16));
}

.auth-password-button {
  height: 22px;
  padding: 0 8px;
  border: 0;
  border-radius: 999px;
  background: var(--bg-soft, #F3F4F6);
  color: var(--text-secondary, #6B7280);
  font-size: 11px;
  font-weight: 750;
  cursor: pointer;
}

.auth-password-button:hover {
  background: var(--border-light, #F3F4F6);
}

.password-dialog {
  border-radius: var(--radius-lg, 16px) !important;
  overflow: hidden;
  box-shadow: var(--shadow-xl, 0 8px 16px rgba(0,0,0,0.04), 0 24px 56px rgba(0,0,0,0.08)) !important;
}

.password-dialog .el-dialog__header {
  padding: 22px 28px 14px;
  margin: 0;
  border-bottom: 0;
}

.password-dialog .el-dialog__title {
  font-size: 18px;
  font-weight: 900;
  color: var(--text-title, #111827);
}

.password-dialog .el-dialog__body {
  padding: 8px 28px 24px;
}

.password-dialog .el-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 18px 28px 24px;
  border-top: 1px solid var(--border-light, #F3F4F6);
  background: var(--bg-card, #FFFFFF);
}

.password-panel {
  margin-bottom: 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--brand-primary-soft, #FEF2F2);
  border-radius: var(--radius-md, 12px);
  background: var(--brand-primary-soft, #FEF2F2);
}

.password-panel-icon {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm, 8px);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--brand-black, #1A1A1A);
  color: #fff;
  font-size: 13px;
  font-weight: 900;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
}

.password-panel h3 {
  margin: 0;
  color: var(--text-title, #111827);
  font-size: 14px;
  font-weight: 900;
}

.password-panel p {
  margin: 6px 0 0;
  color: var(--text-secondary, #6B7280);
  font-size: 12px;
  line-height: 1.5;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.password-form label {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: var(--text-body, #374151);
  font-size: 13px;
  font-weight: 800;
}

.password-form input {
  width: 100%;
  height: 40px;
  box-sizing: border-box;
  padding: 0 13px;
  border: 1px solid var(--border, #E5E7EB);
  border-radius: var(--radius-sm, 8px);
  outline: none;
  color: var(--text-title, #111827);
  font-size: 14px;
  background: var(--bg-card, #FFFFFF);
  transition: all 0.18s ease;
}

.dialog-password-control {
  position: relative;
}

.dialog-password-control input {
  padding-right: 44px;
}

.dialog-password-control input[type="password"] {
  font-size: 20px;
}

.dialog-password-control input::placeholder {
  font-size: 13px;
}

.dialog-password-eye {
  position: absolute;
  right: 6px;
  top: 50%;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-xs, 6px);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted, #9CA3AF);
  background: transparent;
  cursor: pointer;
  transition: all 0.18s ease;
  transform: translateY(-50%);
}

.dialog-password-eye:hover {
  color: var(--text-secondary, #6B7280);
  background: var(--bg-soft, #F3F4F6);
}

.dialog-password-eye .el-icon {
  font-size: 16px;
}

.password-form input:focus {
  border-color: var(--brand-primary, #E61F24);
  box-shadow: 0 0 0 3px var(--brand-primary-focus, rgba(230, 31, 36, 0.16));
}

.dialog-ghost-button,
.dialog-primary-button {
  min-width: 82px;
  height: 38px;
  padding: 0 18px;
  border-radius: 11px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.18s ease;
}

.dialog-ghost-button {
  border: 1px solid var(--border, #E5E7EB);
  background: var(--bg-card, #FFFFFF);
  color: var(--text-body, #374151);
}

.dialog-primary-button {
  border: 1px solid var(--brand-primary, #E61F24);
  background: var(--brand-primary, #E61F24);
  color: #fff;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
}

.dialog-ghost-button:hover {
  border-color: var(--border-hover, #D1D5DB);
  background: var(--bg-soft, #F3F4F6);
}

.dialog-primary-button:hover {
  background: var(--brand-primary-hover, #cc181d);
  border-color: var(--brand-primary-hover, #cc181d);
}

.dialog-primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.app-toast-modern.el-message {
  min-width: 0;
  width: auto;
  max-width: min(360px, calc(100vw - 32px));
  padding: 9px 13px;
  border: 1px solid var(--border, #E5E7EB);
  border-radius: var(--radius-sm, 8px);
  background: var(--bg-card, #FFFFFF);
  box-shadow: var(--shadow-md, 0 2px 4px rgba(0,0,0,0.03), 0 8px 24px rgba(0,0,0,0.05));
  backdrop-filter: blur(10px);
}

.app-toast-modern .el-message__content {
  color: var(--text-title, #111827);
  font-size: 12px;
  font-weight: 760;
  line-height: 1.35;
}

.app-toast-modern .el-message__icon {
  margin-right: 8px;
  color: var(--brand-black, #1A1A1A);
  font-size: 14px;
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
  border: 1px solid var(--border, #E5E7EB);
  background: var(--bg-card, #FFFFFF);
  color: var(--text-secondary, #6B7280);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(0,0,0,0.04));
}

.backend-status-chip.is-online {
  border-color: rgba(16, 185, 129, 0.24);
  background: var(--success-soft, #ECFDF5);
  color: var(--success, #10B981);
}

.backend-status-chip.is-offline {
  border-color: rgba(230, 31, 36, 0.2);
  background: var(--error-soft, #FEF2F2);
  color: var(--error, #E61F24);
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
  color: var(--text-muted, #9CA3AF);
  font-size: 12px;
}

.page-wrap {
  padding: 0 24px 24px;
  overflow: auto;
  background: var(--bg-page, #F2EDE8);
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

