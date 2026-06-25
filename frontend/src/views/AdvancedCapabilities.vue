<template>
  <div class="advanced-page">
    <section class="advanced-hero">
      <div>
        <p class="eyebrow">ADVANCED ASK</p>
        <h1>进阶能力中心</h1>
        <p>
          管理进阶问数的 Skill、MCP、SQL Server 和工具链路。这里不替代智能分析工作台，
          只为进阶流程提供可灰度、可迁移、可诊断的企业级能力配置。
        </p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="loadConfig">刷新</el-button>
        <el-button plain :loading="askFlowLoading" @click="goAskFlowControl">流程控制</el-button>
        <el-button v-if="featureAccess.advanced_capability_reset" plain type="warning" :loading="resetting" @click="handleReset">恢复默认</el-button>
        <el-button v-if="featureAccess.advanced_capability_save" type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-item">
        <span>进阶能力</span>
        <strong>{{ config.enabled ? '已开启' : '已关闭' }}</strong>
        <small>由问数流程控制器决定是否进入进阶流程</small>
      </article>
      <article class="metric-item" :class="{ 'is-warning': !askFlowReady }">
        <span>流程入口</span>
        <strong>{{ askFlowStatus.label }}</strong>
        <small>{{ askFlowStatus.hint }}</small>
      </article>
      <article class="metric-item">
        <span>启用 Skill</span>
        <strong>{{ enabledSkillCount }} / {{ config.skills.length }}</strong>
        <small>中间区会展示启用链路</small>
      </article>
      <article class="metric-item">
        <span>结果契约</span>
        <strong>保持一致</strong>
        <small>继续输出 dataset_results / report_spec</small>
      </article>
      <article class="metric-item">
        <span>外部工具</span>
        <strong>{{ externalToolSummary }}</strong>
        <small>MCP 与 SQL Server 分阶段接入</small>
      </article>
    </section>

    <section class="advanced-workbench">
      <el-tabs v-model="activeTab" class="advanced-tabs">
        <el-tab-pane label="总览" name="overview">
          <div class="overview-grid">
            <section class="plain-panel">
              <h2>进阶流程边界</h2>
              <ul>
                <li>基础问数链路不改动，进阶流程通过 ask_flow 控制器灰度进入。</li>
                <li>中间区和右侧详情区展示 Skill、Planner、工具调用和自检链路。</li>
                <li>最终报告结果保持现有结构，继续复用报告模板、图表和下载能力。</li>
                <li>数据书架、字段字典、Golden SQL、组织树和报告模板是进阶流程的资产来源。</li>
              </ul>
            </section>
            <section class="plain-panel">
              <h2>当前摘要</h2>
              <div class="summary-list">
                <div><span>能力中心</span><strong>{{ config.enabled ? '开启' : '关闭' }}</strong></div>
                <div><span>流程入口</span><strong>{{ askFlowStatus.label }}</strong></div>
                <div><span>Skill Trace</span><strong>{{ config.execution.emitSkillTrace ? '显示' : '隐藏' }}</strong></div>
                <div><span>资产预览数</span><strong>{{ config.execution.assetPreviewLimit }}</strong></div>
                <div><span>MCP</span><strong>{{ config.mcp.enabled ? '开启' : '关闭' }}</strong></div>
                <div><span>SQL Server</span><strong>{{ config.sqlServer.enabled ? '开启' : '关闭' }}</strong></div>
              </div>
              <div v-if="!askFlowReady" class="flow-warning">
                当前进阶能力已配置，但问数流程控制器还没有默认进入进阶流程。实际提问时可能仍显示基础流程，需要到“系统控制台 - 问数流程控制”开启进阶或配置数据集灰度。
              </div>
            </section>
          </div>
        </el-tab-pane>

        <el-tab-pane label="Skill 链路" name="skills">
          <section class="plain-panel">
            <div class="panel-head">
              <div>
                <h2>进阶 Skill</h2>
                <p>这些节点决定进阶流程的过程展示和后续能力接入顺序，不改变最终报告组件。</p>
              </div>
              <div class="panel-actions">
                <el-button v-if="featureAccess.advanced_skill_import" plain type="primary" @click="openImportDialog">导入 Skill</el-button>
                <el-switch v-model="config.enabled" active-text="能力中心开启" inactive-text="能力中心关闭" />
              </div>
            </div>
            <el-table :data="sortedSkills" stripe border>
              <el-table-column label="启用" width="92">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" />
                </template>
              </el-table-column>
              <el-table-column prop="label" label="Skill" min-width="180" />
              <el-table-column prop="toolType" label="类型" width="110">
                <template #default="{ row }">
                  <el-tag effect="plain">{{ toolTypeLabel(row.toolType) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="能力说明" min-width="360" show-overflow-tooltip />
              <el-table-column prop="stage" label="Trace Stage" min-width="230" show-overflow-tooltip />
              <el-table-column label="来源" width="110">
                <template #default="{ row }">
                  <el-tag v-if="row.custom" type="warning" effect="plain">导入</el-tag>
                  <el-tag v-else type="success" effect="plain">内置</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="MCP 工具" name="mcp">
          <section class="plain-panel">
            <div class="panel-head">
              <div>
                <h2>MCP 工具配置</h2>
                <p>第一阶段先作为外部工具插座管理，稳定后再接文件、知识库、飞书发送等真实调用。</p>
              </div>
              <el-switch v-model="config.mcp.enabled" active-text="开启 MCP" inactive-text="关闭 MCP" />
            </div>
            <el-form label-position="top">
              <el-form-item label="服务列表 JSON">
                <el-input
                  v-model="mcpServersText"
                  type="textarea"
                  :rows="9"
                  placeholder='例如：[{"name":"knowledge","url":"http://mcp-server:9000"}]'
                />
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="config.mcp.notes" type="textarea" :rows="3" />
              </el-form-item>
            </el-form>
          </section>
        </el-tab-pane>

        <el-tab-pane label="SQL Server" name="sqlserver">
          <section class="plain-panel">
            <div class="panel-head">
              <div>
                <h2>SQL Server 工具</h2>
                <p>优先复用数据连接管理中的 SQL Server 数据源，驱动和镜像依赖后续做容器级检测。</p>
              </div>
              <el-switch v-model="config.sqlServer.enabled" active-text="开启 SQL Server 工具" inactive-text="关闭" />
            </div>
            <el-form label-position="top" class="form-grid">
              <el-form-item label="ODBC Driver">
                <el-input v-model="config.sqlServer.driver" />
              </el-form-item>
              <el-form-item label="复用数据连接管理">
                <el-switch v-model="config.sqlServer.reuseDataSources" />
              </el-form-item>
              <el-form-item label="备注" class="form-wide">
                <el-input v-model="config.sqlServer.notes" type="textarea" :rows="4" />
              </el-form-item>
            </el-form>
          </section>
        </el-tab-pane>

        <el-tab-pane label="流程保护" name="execution">
          <section class="plain-panel">
            <h2>执行与展示策略</h2>
            <div class="switch-list">
              <label>
                <span>
                  <strong>显示 Skill Trace</strong>
                  <small>进阶流程开启后，中间区和右侧详情区展示 Skill、Planner、工具和自检链路。</small>
                </span>
                <el-switch v-model="config.execution.emitSkillTrace" />
              </label>
              <label>
                <span>
                  <strong>保持最终报告契约</strong>
                  <small>固定开启：最终仍输出现有报告组件需要的 dataset_results 和 report_spec。</small>
                </span>
                <el-switch v-model="config.execution.preserveFinalReportContract" disabled />
              </label>
              <label>
                <span>
                  <strong>基础引擎兜底</strong>
                  <small>固定开启：进阶链路异常时不影响基础问数执行结果。</small>
                </span>
                <el-switch v-model="config.execution.fallbackToBasicEngine" disabled />
              </label>
            </div>
            <div class="slider-row">
              <span>资产预览数据集数量</span>
              <el-slider v-model="config.execution.assetPreviewLimit" :min="1" :max="10" show-input />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="诊断" name="diagnostics">
          <section class="plain-panel">
            <div class="panel-head">
              <div>
                <h2>配置诊断</h2>
                <p>用于发版前核对迁移包中的进阶能力配置。</p>
              </div>
              <el-tag type="success" effect="light">运行态迁移已纳入</el-tag>
            </div>
            <pre class="json-preview">{{ prettyConfig }}</pre>
          </section>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="importDialogVisible" title="导入 Skill Manifest" width="760px" destroy-on-close>
      <div class="import-panel">
        <p>
          支持粘贴网上找到的 Skill Manifest JSON。当前只导入能力定义、提示词和工具声明，
          不执行第三方代码；内置 Skill 也不会被覆盖。
        </p>
        <el-input
          v-model="skillImportText"
          type="textarea"
          :rows="14"
          placeholder='{"skills":[{"key":"cohort_analysis","label":"客群分层分析 Skill","toolType":"python","description":"按客户/组织/指标做分层分析","prompt":"..."}]}'
        />
        <div v-if="importReport" class="import-report">
          <el-tag type="success">导入 {{ importReport.imported?.length || 0 }} 个</el-tag>
          <el-tag v-if="importReport.skipped?.length" type="warning">跳过 {{ importReport.skipped.length }} 个</el-tag>
          <ul v-if="importReport.skipped?.length">
            <li v-for="item in importReport.skipped" :key="`${item.key || item.label}-${item.reason}`">
              {{ item.key || item.label || '未命名' }}：{{ item.reason }}
            </li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImportSkills">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAdvancedCapabilitiesConfig,
  getAskFlowConfig,
  importAdvancedSkills,
  resetAdvancedCapabilitiesConfig,
  saveAdvancedCapabilitiesConfig,
} from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'

const defaultConfig = () => ({
  version: 1,
  enabled: true,
  description: '',
  execution: {
    emitSkillTrace: true,
    preserveFinalReportContract: true,
    assetPreviewLimit: 3,
    fallbackToBasicEngine: true,
  },
  skills: [],
  mcp: { enabled: false, servers: [], notes: '' },
  sqlServer: { enabled: false, reuseDataSources: true, driver: 'ODBC Driver 18 for SQL Server', notes: '' },
})

const activeTab = ref('overview')
const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const importing = ref(false)
const askFlowLoading = ref(false)
const config = ref(defaultConfig())
const askFlowConfig = ref({
  defaultFlow: 'basic',
  advancedEnabled: false,
  advancedRoles: ['super_admin'],
  datasetPolicies: {},
})
const mcpServersText = ref('[]')
const importDialogVisible = ref(false)
const skillImportText = ref('')
const importReport = ref(null)
const router = useRouter()
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const advancedFeatureKeys = [
  'advanced_capability_save',
  'advanced_skill_import',
  'advanced_capability_reset',
]
const featureAccess = computed(() => advancedFeatureKeys.reduce((map, key) => {
  map[key] = isFeatureEnabled(key)
  return map
}, {}))

const syncMcpText = () => {
  mcpServersText.value = JSON.stringify(config.value.mcp?.servers || [], null, 2)
}

const applyConfig = (payload = {}) => {
  config.value = {
    ...defaultConfig(),
    ...payload,
    execution: { ...defaultConfig().execution, ...(payload.execution || {}) },
    skills: Array.isArray(payload.skills) ? payload.skills : [],
    mcp: { ...defaultConfig().mcp, ...(payload.mcp || {}) },
    sqlServer: { ...defaultConfig().sqlServer, ...(payload.sqlServer || {}) },
  }
  config.value.execution.preserveFinalReportContract = true
  config.value.execution.fallbackToBasicEngine = true
  syncMcpText()
}

const sortedSkills = computed(() => [...(config.value.skills || [])].sort((a, b) => Number(a.order || 999) - Number(b.order || 999)))
const enabledSkillCount = computed(() => sortedSkills.value.filter(item => item.enabled !== false).length)
const externalToolSummary = computed(() => {
  const items = []
  if (config.value.mcp?.enabled) items.push('MCP')
  if (config.value.sqlServer?.enabled) items.push('SQL Server')
  return items.length ? items.join(' / ') : '未开启'
})
const hasAdvancedDatasetPolicy = computed(() => Object.values(askFlowConfig.value.datasetPolicies || {}).some(flow => flow === 'advanced'))
const askFlowReady = computed(() => {
  if (!config.value.enabled) return false
  if (!askFlowConfig.value.advancedEnabled) return false
  return askFlowConfig.value.defaultFlow === 'advanced' || hasAdvancedDatasetPolicy.value
})
const askFlowStatus = computed(() => {
  if (!config.value.enabled) {
    return { label: '能力关闭', hint: '进阶能力中心关闭，提问不会进入进阶链路' }
  }
  if (!askFlowConfig.value.advancedEnabled) {
    return { label: '未启用', hint: '当前仍会回落基础流程' }
  }
  if (askFlowConfig.value.defaultFlow === 'advanced') {
    return { label: '默认进阶', hint: '新提问默认进入进阶流程' }
  }
  if (hasAdvancedDatasetPolicy.value) {
    return { label: '数据集灰度', hint: '命中指定数据集时进入进阶流程' }
  }
  return { label: '已启用未生效', hint: '已允许进阶，但默认流程仍为基础' }
})
const prettyConfig = computed(() => JSON.stringify(config.value, null, 2))

const toolTypeLabel = (type) => ({
  dataset: '数据资产',
  sql: 'SQL',
  python: 'Python',
  report: '报告',
  fact: '规划',
  confirm: '确认',
}[type] || '通用')

const loadConfig = async () => {
  loading.value = true
  try {
    const res = await getAdvancedCapabilitiesConfig()
    applyConfig(res?.data?.config || {})
  } finally {
    loading.value = false
  }
}

const loadAskFlowState = async () => {
  askFlowLoading.value = true
  try {
    const res = await getAskFlowConfig({ silent: true })
    askFlowConfig.value = {
      ...askFlowConfig.value,
      ...(res?.data?.config || {}),
      datasetPolicies: res?.data?.config?.datasetPolicies || {},
    }
  } catch {
    // Ask-flow control is super-admin only. Keep the page usable for admins.
  } finally {
    askFlowLoading.value = false
  }
}

const goAskFlowControl = () => {
  router.push('/admin-console?tab=ask-flow')
}

const buildPayload = () => {
  let servers = []
  try {
    const parsed = JSON.parse(mcpServersText.value || '[]')
    servers = Array.isArray(parsed) ? parsed : []
  } catch {
    throw new Error('MCP 服务列表必须是 JSON 数组')
  }
  return {
    ...config.value,
    mcp: {
      ...config.value.mcp,
      servers,
    },
    execution: {
      ...config.value.execution,
      preserveFinalReportContract: true,
      fallbackToBasicEngine: true,
    },
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const payload = buildPayload()
    const res = await saveAdvancedCapabilitiesConfig(payload)
    applyConfig(res?.data?.config || payload)
    ElMessage.success('进阶能力配置已保存')
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || error?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const openImportDialog = () => {
  importReport.value = null
  if (!skillImportText.value.trim()) {
    skillImportText.value = JSON.stringify({
      skills: [
        {
          key: 'cohort_analysis',
          label: '客群分层分析 Skill',
          toolType: 'python',
          description: '按客户、组织、指标或时间窗口做分层对比和贡献度分析。',
          prompt: '根据用户问题识别分层维度，输出分组、指标、排序和异常节点。',
          safety: { executeCode: false, requiresReview: true },
        },
      ],
    }, null, 2)
  }
  importDialogVisible.value = true
}

const handleImportSkills = async () => {
  importing.value = true
  try {
    const manifest = JSON.parse(skillImportText.value || '{}')
    const res = await importAdvancedSkills(manifest)
    applyConfig(res?.data?.config || {})
    importReport.value = {
      imported: res?.data?.imported || [],
      skipped: res?.data?.skipped || [],
    }
    ElMessage.success(`Skill 导入完成：${importReport.value.imported.length} 个`)
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || error?.message || 'Skill Manifest 格式不正确')
  } finally {
    importing.value = false
  }
}

const handleReset = async () => {
  try {
    await ElMessageBox.confirm('将恢复进阶能力中心默认配置，确认继续吗？', '恢复默认', {
      type: 'warning',
      confirmButtonText: '恢复默认',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  resetting.value = true
  try {
    const res = await resetAdvancedCapabilitiesConfig()
    applyConfig(res?.data?.config || {})
    ElMessage.success('进阶能力配置已恢复默认')
  } finally {
    resetting.value = false
  }
}

watch(() => config.value.mcp?.enabled, () => {
  if (!mcpServersText.value) syncMcpText()
})

onMounted(() => {
  loadFeatureFlags()
  loadConfig()
  loadAskFlowState()
})
</script>

<style scoped>
.advanced-page {
  min-height: 100%;
  padding: 24px;
  background: #F8F9FA;
  color: #111827;
}

.advanced-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: #E61F24;
  letter-spacing: 0;
}

.advanced-hero h1 {
  margin: 0;
  font-size: 26px;
  line-height: 1.25;
}

.advanced-hero p:last-child {
  max-width: 760px;
  margin: 10px 0 0;
  color: #6B7280;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin: 16px 0;
}

.metric-item,
.plain-panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.metric-item {
  padding: 16px;
}

.metric-item.is-warning {
  border-color: #FFFBEB;
  background: #FFFBEB;
}

.metric-item span,
.summary-list span {
  display: block;
  color: #6b7280;
  font-size: 13px;
}

.metric-item strong {
  display: block;
  margin: 8px 0;
  font-size: 24px;
}

.metric-item small,
.plain-panel p,
.plain-panel li,
.switch-list small {
  color: #6b7280;
  line-height: 1.65;
}

.advanced-workbench {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  padding: 8px 18px 18px;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.6fr);
  gap: 16px;
}

.plain-panel {
  padding: 18px;
}

.plain-panel h2 {
  margin: 0 0 10px;
  font-size: 18px;
}

.plain-panel ul {
  margin: 0;
  padding-left: 18px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.panel-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.summary-list {
  display: grid;
  gap: 10px;
}

.summary-list div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #F3F4F6;
}

.flow-warning {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #FFFBEB;
  border-radius: 8px;
  background: #FFFBEB;
  color: #B45309;
  line-height: 1.7;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
}

.form-wide {
  grid-column: 1 / -1;
}

.switch-list {
  display: grid;
  gap: 12px;
}

.switch-list label {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.switch-list strong {
  display: block;
  margin-bottom: 4px;
}

.slider-row {
  margin-top: 16px;
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 18px;
  align-items: center;
}

.json-preview {
  margin: 0;
  max-height: 520px;
  overflow: auto;
  padding: 14px;
  border-radius: 8px;
  background: #111827;
  color: #e5e7eb;
  font-size: 12px;
  line-height: 1.6;
}

.import-panel p {
  margin: 0 0 12px;
  color: #6B7280;
  line-height: 1.7;
}

.import-report {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.import-report ul {
  width: 100%;
  margin: 4px 0 0;
  padding-left: 18px;
  color: #B45309;
}

@media (max-width: 1080px) {
  .advanced-hero,
  .panel-head {
    flex-direction: column;
  }

  .metric-grid,
  .overview-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .hero-actions {
    justify-content: flex-start;
  }
}
</style>
