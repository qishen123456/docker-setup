<template>
  <div class="sql-debug-page">
    <section class="sql-debug-shell">
      <header class="sql-debug-header">
        <div>
          <h1>SQL调试台</h1>
          <p>直接查询 SQL 或用问题生成 SQL，只跑数据链路，不进入报告生成流程。</p>
        </div>
        <div class="sql-debug-header-actions">
          <el-button :type="floatEnabled ? 'success' : 'primary'" plain :icon="Monitor" @click="toggleFloat">
            {{ floatEnabled ? '关闭悬浮' : '开启悬浮' }}
          </el-button>
          <el-button :icon="Refresh" :loading="datasetsLoading" @click="loadDatasets">刷新数据集</el-button>
        </div>
      </header>

      <div v-if="!canRun" class="sql-debug-denied">
        当前账号未开通 SQL 调试台权限。
      </div>

      <template v-else>
        <div class="sql-debug-toolbar">
          <div class="sql-debug-toolbar-main">
            <span>数据集</span>
          <el-select
            v-model="selectedDatasetId"
            filterable
            clearable
            placeholder="选择数据集"
            class="sql-debug-dataset-select"
            :loading="datasetsLoading"
            @change="handleDatasetChange"
          >
            <el-option
              v-for="item in datasets"
              :key="item.id"
              :label="datasetLabel(item)"
              :value="String(item.id)"
            />
          </el-select>
          </div>
          <div class="sql-debug-limit">
            <span>最多行数</span>
            <el-input-number v-model="limit" :min="1" :max="10000" :step="100" controls-position="right" />
          </div>
        </div>

        <el-alert
          v-if="!datasetsLoading && !datasets.length"
          title="当前账号没有可调试的数据集，或数据集未授权。"
          type="warning"
          :closable="false"
          show-icon
        />

        <el-tabs v-model="activeTab" class="sql-debug-tabs">
          <el-tab-pane label="SQL查询" name="sql">
            <div class="sql-debug-workbench">
              <section class="sql-debug-editor-panel">
                <div class="sql-debug-section-head">
                  <strong>只读 SQL 查询</strong>
                  <div class="sql-debug-actions">
                    <el-button type="primary" :icon="VideoPlay" :loading="sqlLoading" @click="runSql">执行 SQL</el-button>
                    <el-button :icon="CopyDocument" :disabled="!sqlResult.rows.length || !canCopy" @click="copyRows(sqlResult, 'tsv')">复制表格</el-button>
                    <el-button :icon="CopyDocument" :disabled="!sqlResult.rows.length || !canCopy" @click="copyRows(sqlResult, 'json')">复制 JSON</el-button>
                    <el-button :icon="Download" :disabled="!sqlResult.rows.length || !canCopy" @click="exportRows(sqlResult, 'sql-result.csv')">导出 CSV</el-button>
                  </div>
                </div>
                <el-input
                  v-model="sqlText"
                  type="textarea"
                  :rows="13"
                  resize="vertical"
                  class="sql-debug-editor"
                  placeholder="输入 SELECT 或 WITH 查询，例如：SELECT * FROM your_table LIMIT 20"
                />
              </section>
              <ResultPanel :result="sqlResult" empty-text="执行 SQL 后在这里查看结果" />
            </div>
          </el-tab-pane>

          <el-tab-pane label="问数转SQL" name="ask">
            <div class="sql-debug-workbench">
              <section class="sql-debug-editor-panel">
                <div class="sql-debug-section-head">
                  <strong>问题生成 SQL</strong>
                  <div class="sql-debug-actions">
                    <el-button type="primary" :icon="VideoPlay" :loading="askLoading" @click="runAsk">生成并执行</el-button>
                    <el-button :icon="CopyDocument" :disabled="!askResult.rows.length || !canCopy" @click="copyRows(askResult, 'tsv')">复制表格</el-button>
                    <el-button :icon="CopyDocument" :disabled="!askResult.rows.length || !canCopy" @click="copyRows(askResult, 'json')">复制 JSON</el-button>
                    <el-button :icon="Download" :disabled="!askResult.rows.length || !canCopy" @click="exportRows(askResult, 'ask-sql-result.csv')">导出 CSV</el-button>
                  </div>
                </div>
                <el-input
                  v-model="questionText"
                  type="textarea"
                  :rows="5"
                  resize="vertical"
                  placeholder="输入问题，例如：本月各分公司的达成率排名"
                  @keydown.ctrl.enter.prevent="runAsk"
                />
                <div class="sql-debug-sql-grid">
                  <div class="sql-debug-code-block">
                    <div class="sql-debug-code-head">
                      <span>生成 SQL</span>
                    <button class="sql-debug-code-copy" type="button" :disabled="!askResult.generated_sql" @click="copyText(askResult.generated_sql)">复制</button>
                    </div>
                    <pre>{{ askResult.generated_sql || '生成后显示 SQL' }}</pre>
                  </div>
                  <div class="sql-debug-code-block">
                    <div class="sql-debug-code-head">
                      <span>最终执行 SQL</span>
                    <button class="sql-debug-code-copy" type="button" :disabled="!askResult.final_sql" @click="copyText(askResult.final_sql)">复制</button>
                    </div>
                    <pre>{{ askResult.final_sql || '执行前会应用权限过滤和行数限制' }}</pre>
                  </div>
                </div>
              </section>
              <ResultPanel :result="askResult" empty-text="生成 SQL 后会直接显示返回数据" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElEmpty, ElMessage, ElTable, ElTableColumn } from 'element-plus'
import { CopyDocument, Download, Monitor, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { askBookshelfDatasetSqlDebug, getBookshelfDatasets, previewBookshelfDatasetSql } from '../api/index'
import { useFeatureFlags } from '../state/featureFlags'

defineOptions({ name: 'SqlDebug' })

const STATE_KEY = 'smartask_sql_debug_page_state'
const FLOAT_ENABLED_KEY = 'smartask_sql_debug_float_enabled'
const FLOAT_TOGGLE_EVENT = 'smartask-sql-debug-float-toggle'

const createEmptyResult = () => ({
  columns: [],
  rows: [],
  row_count: 0,
  limit: 100,
  logs: [],
  error: '',
  generated_sql: '',
  final_sql: '',
})

const formatCell = (value) => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const ResultPanel = defineComponent({
  name: 'SqlDebugResultPanel',
  props: {
    result: { type: Object, required: true },
    emptyText: { type: String, default: '暂无结果' },
  },
  setup(props) {
    return () => h('section', { class: 'sql-debug-result-panel' }, [
      h('div', { class: 'sql-debug-result-head' }, [
        h('strong', '执行结果'),
        h('span', props.result?.columns?.length ? `返回 ${props.result.row_count || props.result.rows?.length || 0} 行，最多 ${props.result.limit || '-'} 行` : ''),
      ]),
      props.result?.error ? h('div', { class: 'sql-debug-error' }, props.result.error) : null,
      props.result?.columns?.length
        ? h(ElTable, {
          data: props.result.rows || [],
          border: true,
          size: 'small',
          height: 360,
          class: 'sql-debug-table',
        }, () => props.result.columns.map((column) => h(ElTableColumn, {
          key: column,
          prop: column,
          label: column,
          minWidth: 150,
          showOverflowTooltip: true,
        }, {
          default: ({ row }) => formatCell(row?.[column]),
        })))
        : h(ElEmpty, { description: props.emptyText, imageSize: 72 }),
      props.result?.logs?.length
        ? h('div', { class: 'sql-debug-logs' }, [
          h('div', { class: 'sql-debug-logs-title' }, '执行日志'),
          ...props.result.logs.map((item, index) => h('div', {
            key: `${item.ts || index}-${item.message}`,
            class: ['sql-debug-log-line', `is-${item.level || 'info'}`],
          }, [
            h('span', item.level || 'info'),
            h('strong', item.message || ''),
          ])),
        ])
        : null,
    ])
  },
})

const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const canRun = computed(() => isFeatureEnabled('dataset_sql_preview_run'))
const canCopy = computed(() => isFeatureEnabled('dataset_sql_preview_copy'))

const datasets = ref([])
const datasetsLoading = ref(false)
const selectedDatasetId = ref('')
const activeTab = ref('sql')
const limit = ref(100)
const sqlText = ref('')
const questionText = ref('')
const sqlLoading = ref(false)
const askLoading = ref(false)
const sqlResult = ref(createEmptyResult())
const askResult = ref(createEmptyResult())
const floatEnabled = ref(false)

const datasetLabel = (item) => {
  const name = item?.dataset_name || item?.dataset_code || `数据集 ${item?.id || ''}`
  const source = item?.source_name || item?.source_id
  return source ? `${name} · ${source}` : name
}

const persistState = () => {
  localStorage.setItem(STATE_KEY, JSON.stringify({
    selectedDatasetId: selectedDatasetId.value,
    activeTab: activeTab.value,
    limit: limit.value,
  }))
}

const restoreState = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(STATE_KEY) || 'null') || {}
    selectedDatasetId.value = saved.selectedDatasetId ? String(saved.selectedDatasetId) : ''
    activeTab.value = saved.activeTab || 'sql'
    limit.value = Number(saved.limit) || 100
  } catch {
    selectedDatasetId.value = ''
  }
}

const restoreFloatState = () => {
  floatEnabled.value = localStorage.getItem(FLOAT_ENABLED_KEY) === '1'
}

const toggleFloat = () => {
  floatEnabled.value = !floatEnabled.value
  localStorage.setItem(FLOAT_ENABLED_KEY, floatEnabled.value ? '1' : '0')
  window.dispatchEvent(new CustomEvent(FLOAT_TOGGLE_EVENT, {
    detail: { enabled: floatEnabled.value },
  }))
  ElMessage.success(floatEnabled.value ? 'SQL 调试悬浮已开启' : 'SQL 调试悬浮已关闭')
}

const handleFloatToggle = (event) => {
  floatEnabled.value = Boolean(event?.detail?.enabled)
}

const loadDatasets = async () => {
  datasetsLoading.value = true
  try {
    const response = await getBookshelfDatasets()
    datasets.value = response?.datasets || []
    const currentExists = datasets.value.some(item => String(item.id) === String(selectedDatasetId.value))
    if (!currentExists) {
      selectedDatasetId.value = datasets.value.length ? String(datasets.value[0].id) : ''
    }
  } finally {
    datasetsLoading.value = false
  }
}

const handleDatasetChange = () => {
  sqlResult.value = createEmptyResult()
  askResult.value = createEmptyResult()
}

const ensureDataset = () => {
  if (!selectedDatasetId.value) {
    ElMessage.warning('请先选择数据集')
    return false
  }
  return true
}

const normalizeErrorResult = (error, fallback) => ({
  ...fallback,
  error: error?.response?.data?.error || error?.message || '执行失败',
  logs: error?.response?.data?.logs || fallback.logs || [],
})

const runSql = async () => {
  if (!ensureDataset()) return
  if (!String(sqlText.value || '').trim()) {
    ElMessage.warning('请输入 SQL')
    return
  }
  sqlLoading.value = true
  sqlResult.value = createEmptyResult()
  try {
    const response = await previewBookshelfDatasetSql(selectedDatasetId.value, {
      sql: sqlText.value,
      limit: limit.value,
    })
    sqlResult.value = { ...createEmptyResult(), ...response, logs: [{ level: 'info', message: 'SQL 执行完成' }] }
  } catch (error) {
    sqlResult.value = normalizeErrorResult(error, createEmptyResult())
  } finally {
    sqlLoading.value = false
  }
}

const runAsk = async () => {
  if (!ensureDataset()) return
  if (!String(questionText.value || '').trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  askLoading.value = true
  askResult.value = createEmptyResult()
  try {
    const response = await askBookshelfDatasetSqlDebug(selectedDatasetId.value, {
      question: questionText.value,
      limit: limit.value,
    })
    askResult.value = {
      ...createEmptyResult(),
      ...response,
      final_sql: response?.preview_sql || response?.final_sql || '',
    }
  } catch (error) {
    const payload = error?.response?.data || {}
    askResult.value = normalizeErrorResult(error, {
      ...createEmptyResult(),
      generated_sql: payload.generated_sql || '',
      final_sql: payload.final_sql || '',
      logs: payload.logs || [],
    })
  } finally {
    askLoading.value = false
  }
}

const copyText = async (text) => {
  const content = String(text || '')
  if (!content) return
  try {
    await navigator.clipboard.writeText(content)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = content
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  }
  ElMessage.success('已复制')
}

const rowsToTsv = (result) => [
  result.columns.join('\t'),
  ...(result.rows || []).map(row => result.columns.map(column => formatCell(row?.[column]).replace(/\t/g, ' ').replace(/\r?\n/g, ' ')).join('\t')),
].join('\n')

function csvCell(value) {
  const text = String(value ?? '')
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

const rowsToCsv = (result) => [
  result.columns.map(csvCell).join(','),
  ...(result.rows || []).map(row => result.columns.map(column => csvCell(formatCell(row?.[column]))).join(',')),
].join('\n')

const copyRows = (result, mode) => {
  if (!canCopy.value || !result?.rows?.length) return
  copyText(mode === 'json' ? JSON.stringify(result.rows, null, 2) : rowsToTsv(result))
}

const exportRows = (result, filename) => {
  if (!canCopy.value || !result?.rows?.length) return
  const blob = new Blob([`\uFEFF${rowsToCsv(result)}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

watch([selectedDatasetId, activeTab, limit], persistState)

onMounted(async () => {
  restoreState()
  restoreFloatState()
  await loadFeatureFlags()
  await loadDatasets()
  window.addEventListener(FLOAT_TOGGLE_EVENT, handleFloatToggle)
})

onUnmounted(() => {
  window.removeEventListener(FLOAT_TOGGLE_EVENT, handleFloatToggle)
})
</script>

<style scoped>
.sql-debug-page {
  min-height: calc(100vh - 96px);
  padding: 4px;
}

.sql-debug-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: calc(100vh - 126px);
  padding: 20px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.98) 220px),
    #fff;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.06);
}

.sql-debug-header,
.sql-debug-toolbar,
.sql-debug-section-head,
.sql-debug-actions,
.sql-debug-result-head,
.sql-debug-code-head,
.sql-debug-log-line {
  display: flex;
  align-items: center;
}

.sql-debug-header {
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.sql-debug-header h1 {
  margin: 0;
  color: #0f172a;
  font-size: 26px;
  line-height: 1.25;
}

.sql-debug-header p {
  margin: 6px 0 0;
  color: #86909c;
  font-size: 13px;
}

.sql-debug-toolbar {
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.sql-debug-toolbar-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.sql-debug-dataset-select {
  width: min(620px, 62vw);
}

.sql-debug-limit {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #86909c;
  font-size: 13px;
}

.sql-debug-denied {
  padding: 18px;
  border: 1px solid rgba(245, 63, 63, 0.2);
  border-radius: 8px;
  background: #fff2f0;
  color: #c45656;
}

.sql-debug-tabs {
  flex: 1;
  min-height: 0;
}

.sql-debug-workbench {
  display: grid;
  grid-template-columns: minmax(440px, 0.92fr) minmax(500px, 1.08fr);
  gap: 16px;
  min-height: 560px;
}

.sql-debug-editor-panel,
.sql-debug-result-panel {
  min-width: 0;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  background: #fff;
  padding: 14px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.sql-debug-section-head,
.sql-debug-result-head {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  min-height: 34px;
}

.sql-debug-section-head strong,
.sql-debug-result-head strong {
  color: #0f172a;
  font-size: 15px;
}

.sql-debug-result-head span {
  color: #86909c;
  font-size: 12px;
}

.sql-debug-actions {
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.sql-debug-editor {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.sql-debug-editor :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  line-height: 1.6;
}

.sql-debug-sql-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.sql-debug-code-block {
  min-width: 0;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 10px;
  background: #0f172a;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.sql-debug-code-head {
  justify-content: space-between;
  padding: 9px 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  color: #dbeafe;
  font-size: 12px;
  font-weight: 700;
  background: #111827;
}

.sql-debug-code-copy {
  height: 26px;
  padding: 0 10px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: #cbd5e1;
  cursor: pointer;
  font-size: 12px;
}

.sql-debug-code-copy:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.sql-debug-code-copy:not(:disabled):hover {
  border-color: rgba(45, 212, 191, 0.55);
  color: #ccfbf1;
}

.sql-debug-code-block pre {
  min-height: 200px;
  max-height: 360px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  color: #d1fae5;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  background:
    linear-gradient(rgba(255, 255, 255, 0.025) 50%, transparent 50%) 0 0 / 100% 3.4em,
    #0f172a;
}

.sql-debug-table {
  width: 100%;
}

.sql-debug-error {
  margin-bottom: 10px;
  padding: 9px 10px;
  border: 1px solid rgba(245, 63, 63, 0.2);
  border-radius: 8px;
  background: #fff2f0;
  color: #c45656;
  font-size: 13px;
}

.sql-debug-logs {
  margin-top: 12px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #f8fafc;
}

.sql-debug-logs-title {
  margin-bottom: 6px;
  color: #4e5969;
  font-size: 12px;
  font-weight: 700;
}

.sql-debug-log-line {
  gap: 8px;
  min-height: 22px;
  color: #4e5969;
  font-size: 12px;
}

.sql-debug-log-line span {
  width: 48px;
  color: #86909c;
  text-transform: uppercase;
}

.sql-debug-log-line.is-error strong {
  color: #c45656;
}

@media (max-width: 1180px) {
  .sql-debug-workbench,
  .sql-debug-sql-grid {
    grid-template-columns: 1fr;
  }

  .sql-debug-dataset-select {
    width: 100%;
  }

  .sql-debug-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .sql-debug-toolbar-main {
    width: 100%;
  }
}
</style>
