<template>
  <div class="smart-page">
    <el-row :gutter="18">
      <el-col :span="17">
        <el-card class="panel-card">
          <template #header>
            <div class="header-row">
              <div>
                <div class="title">智能问数</div>
                <div class="subtitle">Four-Agent 协作：路由 -> SQL 生成 -> 复核 -> 执行 -> 业务解读</div>
              </div>
              <div class="header-actions">
                <el-tag :type="vannaReady ? 'success' : 'warning'" effect="plain">
                  {{ vannaReady ? '服务可用' : '服务未就绪' }}
                </el-tag>
                <el-button @click="refreshPageData">刷新问数页</el-button>
              </div>
            </div>
          </template>

          <el-card v-if="session.state.status !== 'idle'" class="status-overview">
            <div class="status-grid">
              <div>
                <div class="status-label">当前问题</div>
                <div class="status-value">{{ session.state.question }}</div>
              </div>
              <div>
                <div class="status-label">执行状态</div>
                <el-tag :type="statusTagType">{{ statusText }}</el-tag>
              </div>
              <div>
                <div class="status-label">当前命中数据集</div>
                <div class="status-value">
                  <span v-if="matchedDatasetNames.length > 0">{{ matchedDatasetNames.join('、') }}</span>
                  <span v-else>{{ matchedDatasetIds.length > 0 ? `ID: ${matchedDatasetIds.join(', ')}` : '待识别' }}</span>
                </div>
              </div>
              <div>
                <div class="status-label">最近更新</div>
                <div class="status-value">{{ formatDateTime(session.state.updatedAt) || '-' }}</div>
              </div>
            </div>
          </el-card>

          <div class="query-bar">
            <el-select
              v-model="selectedDatasetId"
              clearable
              filterable
              placeholder="可选：锁定某个数据集；不选则由 Agent1 自动匹配"
              style="width: 420px"
              @change="loadCommonQuestions"
            >
              <el-option
                v-for="d in datasets"
                :key="d.id"
                :label="`${d.dataset_name} (${d.dataset_code})`"
                :value="d.id"
              />
            </el-select>
            <el-button @click="loadCommonQuestions">刷新常见问题</el-button>
          </div>

          <div v-if="commonQuestions.length > 0" class="common-box">
            <div class="common-title">常见问题</div>
            <div class="chips">
              <el-tag
                v-for="(q, i) in commonQuestions"
                :key="`q-${i}`"
                class="chip"
                @click="questionInput = q.question_text"
              >
                {{ q.question_text }}
              </el-tag>
            </div>
          </div>

          <div class="composer">
            <el-input
              v-model="questionInput"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="请输入业务问题，例如：商用的业绩怎么样"
            />
            <div class="composer-actions">
              <el-button :disabled="isRunning" @click="clearInput">清空输入</el-button>
              <el-button @click="session.resetSession">清空记录</el-button>
              <el-button type="primary" :loading="isRunning" @click="submitQuestion">开始问数</el-button>
            </div>
          </div>

          <el-alert
            v-if="session.state.error"
            :title="session.state.error"
            type="error"
            :closable="false"
            style="margin-bottom: 12px"
          />

          <el-empty
            v-if="!session.state.result && session.state.status === 'idle'"
            description="提交问题后，这里会展示命中数据集、SQL、结果和 Agent 执行状态。"
          />

          <div v-else class="result-stack">
            <el-card v-if="session.state.result?.route" class="inner-card">
              <template #header>命中数据集 / Agent1 路由</template>
              <div class="route-pills">
                <el-tag v-for="name in matchedDatasetNames" :key="name" type="success" effect="plain">{{ name }}</el-tag>
                <el-tag v-if="matchedDatasetNames.length === 0 && matchedDatasetIds.length > 0" effect="plain">
                  {{ matchedDatasetIds.join(', ') }}
                </el-tag>
              </div>
              <pre class="json-box">{{ pretty(session.state.result.route || {}) }}</pre>
            </el-card>

            <el-card v-if="session.state.result?.requires_confirmation" class="inner-card">
              <template #header>等待老板确认</template>
              <div class="confirm-q">{{ session.state.result.confirmation_question || '请确认统计口径后继续。' }}</div>
              <div class="confirm-actions">
                <el-button
                  v-for="option in session.state.result.confirmation_options || []"
                  :key="option"
                  type="primary"
                  plain
                  :loading="confirmingOption === option"
                  @click="submitBossConfirm(option)"
                >
                  {{ option }}
                </el-button>
              </div>
            </el-card>

            <el-card v-if="datasetResults.length > 0" class="inner-card">
              <template #header>查询结果</template>
              <el-tabs v-model="activeResultTab">
                <el-tab-pane
                  v-for="item in datasetResults"
                  :key="`tab-${item.dataset_id}`"
                  :name="String(item.dataset_id)"
                  :label="item.dataset_name || `数据集 ${item.dataset_id}`"
                >
                  <div class="metrics">
                    <el-tag type="success" size="small">返回行数 {{ item.row_count || 0 }}</el-tag>
                    <el-tag size="small">来源 ID {{ item.source_id || '-' }}</el-tag>
                    <el-tag size="small">数据集编码 {{ item.dataset_code || '-' }}</el-tag>
                  </div>

                  <el-collapse>
                    <el-collapse-item title="最终 SQL" name="sql">
                      <pre class="sql-box">{{ item.sql || '' }}</pre>
                    </el-collapse-item>
                    <el-collapse-item title="Agent3 复核结果" name="audit">
                      <pre class="json-box">{{ pretty(item.agent3_review || {}) }}</pre>
                    </el-collapse-item>
                  </el-collapse>

                  <el-table :data="item.rows || []" border max-height="360" style="margin-top: 10px">
                    <el-table-column
                      v-for="col in item.columns || []"
                      :key="`${item.dataset_id}-${col}`"
                      :prop="col"
                      :label="col"
                      min-width="130"
                      show-overflow-tooltip
                    />
                  </el-table>

                  <div v-if="item.analysis" class="analysis-box">
                    <div class="analysis-title">Agent4 业务解读</div>
                    <div class="analysis-content">{{ item.analysis }}</div>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </el-card>
          </div>
        </el-card>
      </el-col>

      <el-col :span="7">
        <el-card class="panel-card side-card">
          <template #header>
            <div class="title">按阶段流式状态</div>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="(log, i) in session.state.logs"
              :key="`${log.key}-${i}`"
              :type="timelineType(log.status)"
              :timestamp="log.time || ''"
              placement="top"
            >
              <div class="timeline-title">{{ log.title }}</div>
              <div class="timeline-detail">{{ log.detail }}</div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-if="session.state.logs.length === 0" description="当前还没有执行记录。" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getBookshelfDatasets, getCommonQuestions, getVannaStatus } from '../api/index.js'
import { useSmartAskSession } from '../state/smartAskSession.js'

const session = useSmartAskSession()

const vannaReady = ref(false)
const datasets = ref([])
const commonQuestions = ref([])
const confirmingOption = ref('')
const activeResultTab = ref('')

const questionInput = computed({
  get: () => session.state.question,
  set: (value) => {
    session.state.question = value
  },
})

const selectedDatasetId = computed({
  get: () => session.state.selectedDatasetId,
  set: (value) => {
    session.state.selectedDatasetId = value
  },
})

const isRunning = computed(() => session.state.status === 'running')
const matchedDatasetIds = computed(() => session.activeDatasetIds.value || [])
const matchedDatasetNames = computed(() => {
  if (session.state.result?.dataset_results?.length) {
    return session.state.result.dataset_results.map((item) => item.dataset_name).filter(Boolean)
  }

  return matchedDatasetIds.value
    .map((id) => datasets.value.find((item) => Number(item.id) === Number(id))?.dataset_name)
    .filter(Boolean)
})

const datasetResults = computed(() => {
  const arr = session.state.result?.dataset_results
  if (Array.isArray(arr) && arr.length > 0) return arr
  if (!session.state.result || session.state.result.requires_confirmation) return []

  return [
    {
      dataset_id: session.state.result.route?.dataset_ids?.[0] || 0,
      dataset_code: '',
      dataset_name: session.state.result.data_source || '主结果',
      source_id: '',
      agent3_review: {},
      columns: session.state.result.columns || [],
      rows: session.state.result.rows || [],
      row_count: session.state.result.row_count || 0,
      analysis: session.state.result.analysis || '',
      sql: session.state.result.sql || '',
    },
  ]
})

const statusTagType = computed(() => {
  if (session.state.status === 'completed') return 'success'
  if (session.state.status === 'waiting_confirmation') return 'warning'
  if (session.state.status === 'error') return 'danger'
  if (session.state.status === 'running') return 'primary'
  return 'info'
})

const statusText = computed(() => {
  if (session.state.status === 'completed') return '已完成'
  if (session.state.status === 'waiting_confirmation') return '待确认'
  if (session.state.status === 'error') return '执行失败'
  if (session.state.status === 'running') return '执行中'
  return '空闲'
})

const pretty = (obj) => JSON.stringify(obj || {}, null, 2)

const timelineType = (status) => {
  if (status === 'success') return 'success'
  if (status === 'error') return 'danger'
  if (status === 'warning') return 'warning'
  if (status === 'running') return 'primary'
  return 'info'
}

const formatDateTime = (value) => {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

const loadStatus = async () => {
  try {
    const data = await getVannaStatus()
    vannaReady.value = !!data.ready
  } catch {
    vannaReady.value = false
  }
}

const loadDatasets = async () => {
  const data = await getBookshelfDatasets()
  datasets.value = (data.datasets || []).filter((item) => item.is_active !== false)
}

const loadCommonQuestions = async () => {
  const data = await getCommonQuestions(selectedDatasetId.value || undefined)
  commonQuestions.value = (data.common_questions || []).slice(0, 16)
}

const refreshPageData = async () => {
  await Promise.all([loadStatus(), loadDatasets()])
  await loadCommonQuestions()
}

const submitQuestion = async () => {
  if (!questionInput.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }

  try {
    const data = await session.startAsk(questionInput.value, selectedDatasetId.value)
    activeResultTab.value = String((data?.dataset_results || [])[0]?.dataset_id || 0)
  } catch {
    // axios interceptor already shows error
  }
}

const submitBossConfirm = async (option) => {
  confirmingOption.value = option
  try {
    const data = await session.submitBossConfirmation(option)
    activeResultTab.value = String((data?.dataset_results || [])[0]?.dataset_id || 0)
  } finally {
    confirmingOption.value = ''
  }
}

const clearInput = () => {
  session.state.question = ''
}

onMounted(async () => {
  await refreshPageData()
  if (datasetResults.value.length > 0) {
    activeResultTab.value = String(datasetResults.value[0].dataset_id || 0)
  }
})
</script>

<style scoped>
.smart-page { min-height: calc(100vh - 150px); }

.panel-card {
  border: 1px solid rgba(110, 116, 126, 0.2);
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.86), rgba(244, 246, 249, 0.9));
  backdrop-filter: blur(12px);
}

.side-card { min-height: calc(100vh - 150px); }

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title {
  font-size: 18px;
  font-weight: 700;
  color: #242a33;
}

.subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #6c7480;
}

.status-overview {
  margin-bottom: 12px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f9fbfd, #eef3f8);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
}

.status-label {
  margin-bottom: 4px;
  font-size: 12px;
  color: #7a8391;
}

.status-value {
  font-size: 14px;
  line-height: 1.6;
  color: #28313d;
  word-break: break-word;
}

.query-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.common-box {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid #e6e9ee;
  border-radius: 12px;
  background: #f5f7fa;
}

.common-title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #4f5762;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip { cursor: pointer; }

.composer { margin-bottom: 12px; }

.composer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

.result-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.inner-card { border-radius: 14px; }

.route-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.sql-box,
.json-box {
  max-height: 320px;
  margin: 0;
  overflow: auto;
  padding: 12px;
  border-radius: 10px;
  background: #212832;
  color: #edf1f8;
  white-space: pre-wrap;
  word-break: break-word;
}

.confirm-q {
  margin-bottom: 10px;
  line-height: 1.65;
}

.confirm-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.analysis-box {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #e4e8ee;
  border-radius: 10px;
  background: #f8f9fb;
}

.analysis-title {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
}

.analysis-content {
  color: #2f3742;
  line-height: 1.7;
  white-space: pre-wrap;
}

.timeline-title {
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 700;
  color: #293241;
}

.timeline-detail {
  color: #5f6978;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
