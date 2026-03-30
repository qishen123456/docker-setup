<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom:24px">
      <el-col :span="6" v-for="stat in statCards" :key="stat.key">
        <el-card :style="{ background: stat.gradient, border:'none' }" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon size="32" color="rgba(255,255,255,0.9)">
                <component :is="stat.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats[stat.key] ?? 0 }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 最近问答 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📋 最近问答记录</span>
              <el-button link @click="goToChat">开始问答 →</el-button>
            </div>
          </template>
          <el-table :data="recentQueries" v-loading="loading" size="small">
            <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="sql" label="生成的SQL" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160" />
          </el-table>
          <div v-if="!loading && recentQueries.length === 0" style="text-align:center;padding:40px;color:#8c8c8c">
            暂无问答记录，<el-button link @click="goToChat">立即提问</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 系统状态 + 快速操作 -->
      <el-col :span="8">
        <el-card style="margin-bottom:16px">
          <template #header><span>🔌 系统状态</span></template>
          <div class="status-list">
            <div class="status-item" v-for="s in systemStatus" :key="s.label">
              <span>{{ s.label }}</span>
              <el-tag :type="s.ok ? 'success' : 'warning'" size="small">
                {{ s.ok ? s.okText : s.failText }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <el-card>
          <template #header><span>⚡ 快速操作</span></template>
          <div class="quick-btns">
            <el-button type="primary" block @click="goToChat">🚀 开始智能问答</el-button>
            <el-button block @click="router.push('/databases')">🔗 配置数据库</el-button>
            <el-button block @click="router.push('/ai-models')">🤖 设置AI模型</el-button>
            <el-button block @click="router.push('/datasets')">📚 数据集书架维护</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboard } from '../api/index.js'

const router = useRouter()
const loading = ref(false)
const stats = ref({})
const recentQueries = ref([])
const rawStatus = ref({})

const statCards = [
  { key: 'total_queries', label: '总提问次数', icon: 'ChatLineRound', gradient: 'linear-gradient(135deg,#667eea,#764ba2)' },
  { key: 'today_queries', label: '今日提问', icon: 'Sunrise', gradient: 'linear-gradient(135deg,#f093fb,#f5576c)' },
  { key: 'db_count', label: '数据源数量', icon: 'Coin', gradient: 'linear-gradient(135deg,#4facfe,#00f2fe)' },
  { key: 'ai_model_count', label: 'AI模型数量', icon: 'MagicStick', gradient: 'linear-gradient(135deg,#43e97b,#38f9d7)' },
]

const systemStatus = computed(() => [
  { label: '后端服务', ok: true, okText: '运行中', failText: '异常' },
  { label: '数据源', ok: (stats.value.active_db_count || 0) > 0, okText: `${stats.value.active_db_count || 0}个活跃`, failText: '未配置' },
  { label: 'AI模型', ok: (stats.value.active_ai_count || 0) > 0, okText: `${stats.value.active_ai_count || 0}个已配置`, failText: '未配置' },
])

const loadData = async () => {
  loading.value = true
  try {
    const data = await getDashboard()
    stats.value = data.stats || {}
    recentQueries.value = data.recent_queries || []
    rawStatus.value = data.system_status || {}
  } finally {
    loading.value = false
  }
}

const goToChat = () => router.push('/chat')

onMounted(loadData)
</script>

<style scoped>
.stat-card { cursor: default; }
.stat-content { display: flex; align-items: center; gap: 16px; padding: 4px 0; }
.stat-value { font-size: 32px; font-weight: 700; color: #fff; line-height: 1; }
.stat-label { font-size: 13px; color: rgba(255,255,255,0.85); margin-top: 4px; }
.stat-icon { opacity: 0.9; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.status-list { display: flex; flex-direction: column; gap: 12px; }
.status-item { display: flex; justify-content: space-between; align-items: center; }
.quick-btns { display: flex; flex-direction: column; gap: 10px; }
.quick-btns .el-button { width: 100%; }
</style>
