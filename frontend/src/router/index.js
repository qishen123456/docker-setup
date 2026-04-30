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
    meta: { title: '智能问数' }
  },
  {
    path: '/chat',
    redirect: '/smart-ask'
  },
  {
    path: '/agents',
    name: 'Agents',
    component: () => import('../views/AgentManagement.vue'),
    meta: { title: 'AGENT管理' }
  },
  {
    path: '/datasets',
    name: 'Datasets',
    component: () => import('../views/DatasetManagement.vue'),
    meta: { title: '数据集管理' }
  },
  {
    path: '/bookshelves',
    name: 'Bookshelves',
    component: () => import('../views/Bookshelves.vue'),
    meta: { title: '数据集书架' }
  },
  {
    path: '/databases',
    name: 'Databases',
    component: () => import('../views/Databases.vue'),
    meta: { title: '数据源管理' }
  },
  {
    path: '/ai-models',
    name: 'AIModels',
    component: () => import('../views/AIModels.vue'),
    meta: { title: 'AI模型配置' }
  },
  {
    path: '/report-config',
    name: 'DatasetReportConfig',
    component: () => import('../views/DatasetReportConfig.vue'),
    meta: { title: '报告配置' }
  },
  {
    path: '/feishu-sync',
    name: 'FeishuSync',
    component: () => import('../views/FeishuSync.vue'),
    meta: { title: '飞书同步' }
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
  document.title = `${to.meta.title || '智能问数'} - 智能问数系统`
})

export default router
