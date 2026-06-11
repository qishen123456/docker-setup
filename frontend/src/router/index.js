import { createRouter, createWebHistory } from 'vue-router'

const viewLoaders = {
  SmartAsk: () => import('../views/SmartAsk.vue'),
  SqlDebug: () => import('../views/SqlDebug.vue'),
  AuthCallback: () => import('../views/AuthCallback.vue'),
  AgentManagement: () => import('../views/AgentManagement.vue'),
  DatasetManagement: () => import('../views/DatasetManagement.vue'),
  Bookshelves: () => import('../views/Bookshelves.vue'),
  Databases: () => import('../views/Databases.vue'),
  AIModels: () => import('../views/AIModels.vue'),
  DatasetReportConfig: () => import('../views/DatasetReportConfig.vue'),
  AdvancedCapabilities: () => import('../views/AdvancedCapabilities.vue'),
  FeishuSync: () => import('../views/FeishuSync.vue'),
  EmployeePermissions: () => import('../views/EmployeePermissions.vue'),
  RuntimeMigration: () => import('../views/RuntimeMigration.vue'),
  OrganizationTrees: () => import('../views/OrganizationTrees.vue'),
  AdminConsole: () => import('../views/AdminConsole.vue'),
  NotFound: () => import('../views/NotFound.vue'),
}

const routes = [
  {
    path: '/',
    redirect: '/smart-ask'
  },
  {
    path: '/smart-ask',
    name: 'SmartAsk',
    component: viewLoaders.SmartAsk,
    meta: { title: '智能分析工作台', roles: ['super_admin', 'admin', 'user'] }
  },
  {
    path: '/sql-debug',
    name: 'SqlDebug',
    component: viewLoaders.SqlDebug,
    meta: { title: 'SQL调试台', roles: ['super_admin', 'admin', 'business_admin', 'user'] }
  },
  {
    path: '/chat',
    redirect: '/smart-ask'
  },
  {
    path: '/auth/callback',
    name: 'AuthCallback',
    component: viewLoaders.AuthCallback,
    meta: { title: '飞书登录', public: true }
  },
  {
    path: '/agents',
    name: 'Agents',
    component: viewLoaders.AgentManagement,
    meta: { title: '智能体编排配置', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/datasets',
    name: 'Datasets',
    component: viewLoaders.DatasetManagement,
    meta: { title: '数据资产管理', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/bookshelves',
    name: 'Bookshelves',
    component: viewLoaders.Bookshelves,
    meta: { title: '数据书架治理', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/databases',
    name: 'Databases',
    component: viewLoaders.Databases,
    meta: { title: '数据连接管理', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/ai-models',
    name: 'AIModels',
    component: viewLoaders.AIModels,
    meta: { title: '模型服务配置', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/report-config',
    name: 'DatasetReportConfig',
    component: viewLoaders.DatasetReportConfig,
    meta: { title: '报告模板配置', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/advanced-capabilities',
    name: 'AdvancedCapabilities',
    component: viewLoaders.AdvancedCapabilities,
    meta: { title: '进阶能力中心', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/feishu-sync',
    name: 'FeishuSync',
    component: viewLoaders.FeishuSync,
    meta: { title: '飞书数据同步', roles: ['super_admin', 'admin'] }
  },
  {
    path: '/employee-permissions',
    name: 'EmployeePermissions',
    component: viewLoaders.EmployeePermissions,
    meta: { title: '角色权限管理', roles: ['super_admin'] }
  },
  {
    path: '/runtime-migration',
    name: 'RuntimeMigration',
    component: viewLoaders.RuntimeMigration,
    meta: { title: '迁移发布管理', roles: ['super_admin'] }
  },
  {
    path: '/organization-trees',
    name: 'OrganizationTrees',
    component: viewLoaders.OrganizationTrees,
    meta: { title: '组织树管理', roles: ['super_admin'] }
  },
  {
    path: '/admin-console',
    name: 'AdminConsole',
    component: viewLoaders.AdminConsole,
    meta: { title: '系统控制台', roles: ['super_admin'] }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: viewLoaders.NotFound,
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const preloadCache = new Map()

export const preloadRouteComponents = (routeNames = []) => {
  const names = routeNames.length ? routeNames : Object.keys(viewLoaders)
  return Promise.allSettled(names.map((name) => {
    const loader = viewLoaders[name]
    if (!loader) return Promise.resolve()
    if (!preloadCache.has(name)) {
      preloadCache.set(name, loader().catch((error) => {
        preloadCache.delete(name)
        throw error
      }))
    }
    return preloadCache.get(name)
  }))
}

router.afterEach((to) => {
  document.title = `${to.meta.title || '智能分析'} - Data Agent`
})

export default router
