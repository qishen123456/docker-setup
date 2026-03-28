import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '仪表盘' }
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
    path: '/training',
    name: 'Training',
    component: () => import('../views/Training.vue'),
    meta: { title: '训练数据' }
  },
  {
    path: '/analysis-prompts',
    name: 'AnalysisPrompts',
    component: () => import('../views/AnalysisPrompts_simple.vue'),
    meta: { title: '分析提示词' }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/Chat.vue'),
    meta: { title: '智能聊天' }
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

// 动态设置页面标题
router.afterEach((to) => {
  document.title = `${to.meta.title || 'Vanna'} — 智能问数系统`
})

export default router
