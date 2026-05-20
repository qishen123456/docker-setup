import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/smart-ask'
  },
  {
    path: '/smart-ask',
    name: 'SmartAsk',
    component: () => import('../views/SmartAsk.vue'),
    meta: { title: '智能分析工作台', roles: ['super_admin', 'admin', 'user'] }
  },
  {
    path: '/chat',
    redirect: '/smart-ask'
  },
  {
    path: '/auth/callback',
    name: 'AuthCallback',
    component: () => import('../views/AuthCallback.vue'),
    meta: { title: '飞书登录', public: true }
  },
  {
    path: '/agents',
    name: 'Agents',
    component: () => import('../views/AgentManagement.vue'),
    meta: { title: '智能体编排配置', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/datasets',
    name: 'Datasets',
    component: () => import('../views/DatasetManagement.vue'),
    meta: { title: '数据资产管理', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/bookshelves',
    name: 'Bookshelves',
    component: () => import('../views/Bookshelves.vue'),
    meta: { title: '数据书架治理', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/databases',
    name: 'Databases',
    component: () => import('../views/Databases.vue'),
    meta: { title: '数据连接管理', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/ai-models',
    name: 'AIModels',
    component: () => import('../views/AIModels.vue'),
    meta: { title: '模型服务配置', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/report-config',
    name: 'DatasetReportConfig',
    component: () => import('../views/DatasetReportConfig.vue'),
    meta: { title: '报告模板配置', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/advanced-capabilities',
    name: 'AdvancedCapabilities',
    component: () => import('../views/AdvancedCapabilities.vue'),
    meta: { title: '进阶能力中心', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/feishu-sync',
    name: 'FeishuSync',
    component: () => import('../views/FeishuSync.vue'),
    meta: { title: '飞书数据同步', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/employee-permissions',
    name: 'EmployeePermissions',
    component: () => import('../views/EmployeePermissions.vue'),
    meta: { title: '角色权限管理', roles: ['super_admin'] }
  },
  {
    path: '/runtime-migration',
    name: 'RuntimeMigration',
    component: () => import('../views/RuntimeMigration.vue'),
    meta: { title: '迁移发布管理', roles: ['super_admin'] }
  },
  {
    path: '/organization-trees',
    name: 'OrganizationTrees',
    component: () => import('../views/OrganizationTrees.vue'),
    meta: { title: '组织树管理', roles: ['super_admin'] }
  },
  {
    path: '/admin-console',
    name: 'AdminConsole',
    component: () => import('../views/AdminConsole.vue'),
    meta: { title: '系统控制台', roles: ['super_admin'] }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '智能分析'} - Data Agent`
})

export default router
