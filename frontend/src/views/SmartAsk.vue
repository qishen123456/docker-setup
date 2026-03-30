<template>
  <div class="smart-page">
    <el-row :gutter="18">
      <el-col :span="17">
        <el-card class="panel-card">
          <template #header>
            <div class="header-row">
              <div>
                <div class="title">智能问数</div>
                <div class="subtitle">四中枢流程：匹配 -> 确认 -> 生成SQL -> 审计 -> 执行 -> 业务解读</div>
              </div>
              <el-tag :type="vannaReady ? 'success' : 'warning'" effect="plain">
                {{ vannaReady ? '服务可用' : '服务未就绪' }}
              </el-tag>
            </div>
          </template>

          <div class="query-bar">
            <el-select
              v-model="selectedDatasetId"
              clearable
              filterable
              placeholder="可选：锁定某个数据集；不选则由 Agent1 自动匹配"
              style="width: 420px"
              @change="loadCommonQuestions"
            >
              <el-option v-for="d in datasets" :key="d.id" :label="`${d.dataset_name} (${d.dataset_code})`" :value="d.id" />
            </el-select>
            <el-button @click="loadCommonQuestions">刷新常见问题</el-button>
          </div>

          <div class="common-box" v-if="commonQuestions.length > 0">
            <div class="common-title">常见问题</div>
            <div class="chips">
              <el-tag v-for="(q, i) in commonQuestions" :key="`q-${i}`" class="chip" @click="question = q.question_text">
                {{ q.question_text }}
              </el-tag>
            </div>
          </div>

          <div class="composer">
            <el-input
              v-model="question"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="请输入业务问题，例如：东部分公司今年的达成率和剩余任务是多少？"
            />
            <div class="composer-actions">
              <el-button :disabled="asking" @click="question = ''">清空</el-button>
              <el-button type="primary" :loading="asking" @click="submitQuestion">开始问数</el-button>
            </div>
          </div>

          <el-alert v-if="apiError" :title="apiError" type="error" :closable="false" style="margin-bottom: 12px" />
          <el-skeleton v-if="asking" :rows="6" animated />
          <el-empty v-else-if="!result" description="提交问题后，这里会展示完整结果。" />

          <div v-else class="result-stack">
            <el-card class="inner-card">
              <template #header>Agent1 路由结果</template>
              <pre class="json-box">{{ pretty(result.route || {}) }}</pre>
            </el-card>

            <el-card class="inner-card" v-if="result.requires_confirmation">
              <template #header>老板确认</template>
              <div class="confirm-q">{{ result.confirmation_question || '请确认口径后继续' }}</div>
              <div class="confirm-actions">
                <el-button
                  v-for="option in result.confirmation_options || []"
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

            <el-card class="inner-card" v-if="datasetResults.length > 0">
              <template #header>查询与分析结果</template>
              <el-tabs v-model="activeResultTab">
                <el-tab-pane
                  v-for="item in datasetResults"
                  :key="`tab-${item.dataset_id}`"
                  :name="String(item.dataset_id)"
                  :label="item.dataset_name || `数据集${item.dataset_id}`"
                >
                  <div class="metrics">
                    <el-tag type="success" size="small">返回行数 {{ item.row_count || 0 }}</el-tag>
                    <el-tag size="small">来源ID {{ item.source_id || '-' }}</el-tag>
                  </div>

                  <el-collapse>
                    <el-collapse-item title="最终SQL" name="sql">
                      <pre class="sql-box">{{ item.sql || '' }}</pre>
                    </el-collapse-item>
                    <el-collapse-item title="Agent3 审计结果" name="audit">
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

                  <div class="analysis-box" v-if="item.analysis">
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
          <template #header><div class="title">执行轨迹</div></template>
          <el-timeline>
            <el-timeline-item
              v-for="(s, i) in (result?.steps || [])"
              :key="`step-${i}`"
              :type="s.status === 'success' ? 'success' : s.status === 'error' ? 'danger' : 'primary'"
              :timestamp="`${s.duration || 0} ms`"
            >
              {{ s.title }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { confirmByBoss, getBookshelfDatasets, getCommonQuestions, getVannaStatus, sendSmartChat } from '../api/index.js'

const vannaReady = ref(false)
const datasets = ref([])
const selectedDatasetId = ref(null)
const commonQuestions = ref([])
const question = ref('')
const asking = ref(false)
const result = ref(null)
const apiError = ref('')
const confirmingOption = ref('')
const activeResultTab = ref('')

const datasetResults = computed(() => {
  const arr = result.value?.dataset_results
  if (Array.isArray(arr) && arr.length > 0) return arr
  if (!result.value) return []
  return [{
    dataset_id: result.value.route?.dataset_ids?.[0] || 0,
    dataset_name: result.value.data_source || '主结果',
    source_id: '',
    agent3_review: {},
    columns: result.value.columns || [],
    rows: result.value.rows || [],
    row_count: result.value.row_count || 0,
    analysis: result.value.analysis || '',
    sql: result.value.sql || ''
  }]
})

const pretty = (obj) => JSON.stringify(obj || {}, null, 2)

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
  datasets.value = (data.datasets || []).filter((d) => d.is_active !== false)
}

const loadCommonQuestions = async () => {
  const data = await getCommonQuestions(selectedDatasetId.value || undefined)
  commonQuestions.value = (data.common_questions || []).slice(0, 16)
}

const submitQuestion = async () => {
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  apiError.value = ''
  asking.value = true
  result.value = null
  try {
    const selected = selectedDatasetId.value ? [selectedDatasetId.value] : undefined
    const data = await sendSmartChat(question.value.trim(), undefined, selected)
    result.value = data
    if (data.error) apiError.value = data.error
    activeResultTab.value = String((data.dataset_results || [])[0]?.dataset_id || 0)
  } catch (error) {
    apiError.value = error?.response?.data?.error || '请求失败'
  } finally {
    asking.value = false
  }
}

const submitBossConfirm = async (option) => {
  if (!result.value?.session_id) {
    ElMessage.warning('会话已过期，请重新提问')
    return
  }
  confirmingOption.value = option
  try {
    const data = await confirmByBoss({
      session_id: result.value.session_id,
      selected_option: option
    })
    result.value = data
    activeResultTab.value = String((data.dataset_results || [])[0]?.dataset_id || 0)
  } finally {
    confirmingOption.value = ''
  }
}

onMounted(async () => {
  await Promise.all([loadStatus(), loadDatasets()])
  await loadCommonQuestions()
})
</script>

<style scoped>
.smart-page { min-height: calc(100vh - 150px); }
.panel-card {
  border: 1px solid rgba(110, 116, 126, 0.2);
  background: linear-gradient(145deg, rgba(255,255,255,0.86), rgba(244,246,249,0.9));
  backdrop-filter: blur(12px);
}
.side-card { min-height: calc(100vh - 150px); }
.header-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.title { font-size: 18px; font-weight: 700; color: #242a33; }
.subtitle { margin-top: 4px; font-size: 12px; color: #6c7480; }
.query-bar { display: flex; gap: 10px; margin-bottom: 12px; align-items: center; }
.common-box { padding: 10px; border-radius: 12px; background: #f5f7fa; border: 1px solid #e6e9ee; margin-bottom: 12px; }
.common-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #4f5762; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { cursor: pointer; }
.composer { margin-bottom: 12px; }
.composer-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
.result-stack { display: flex; flex-direction: column; gap: 12px; }
.inner-card { border-radius: 14px; }
.metrics { margin-bottom: 10px; display: flex; gap: 8px; }
.sql-box, .json-box {
  margin: 0;
  padding: 12px;
  border-radius: 10px;
  background: #212832;
  color: #edf1f8;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 320px;
  overflow: auto;
}
.confirm-q { margin-bottom: 10px; line-height: 1.65; }
.confirm-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.analysis-box { margin-top: 12px; border: 1px solid #e4e8ee; border-radius: 10px; background: #f8f9fb; padding: 12px; }
.analysis-title { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.analysis-content { white-space: pre-wrap; line-height: 1.7; color: #2f3742; }
</style>
