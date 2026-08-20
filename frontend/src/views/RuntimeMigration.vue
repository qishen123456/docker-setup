<template>
  <div class="migration-page">
    <section class="hero-card">
      <div>
        <p class="eyebrow">RELEASE GUARD</p>
        <h1>迁移发布与配置保护</h1>
        <p class="hero-copy">
          管理数据源、数据集、字段字典、Agent 提示词、模型配置、报告模板、员工权限和系统日志等运行态资源。
          发布代码前后可以在这里导出、预检、备份和导入，避免生产环境配置被误覆盖。
        </p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="loadSummary">刷新状态</el-button>
        <el-button v-if="runtimeExportEnabled" type="primary" :loading="exporting" @click="handleExport">导出运行态包</el-button>
      </div>
    </section>

    <section class="metric-grid" :class="{ 'is-loading': loading && !summary }">
      <article class="metric-card">
        <span>配置文件</span>
        <strong>{{ metricValue(summaryStats.configCount) }}</strong>
        <small>包含员工、组织树、数据集权限和问数历史；不含登录 token 与 local 私有配置</small>
      </article>
      <article class="metric-card">
        <span>启用数据集</span>
        <strong>{{ metricValue(datasetCount) }}</strong>
        <small>{{ summary ? (inactiveDatasetCount ? `另有 ${inactiveDatasetCount} 个停用数据集随迁移包保留` : '来自 bs_datasets 当前启用项') : '正在读取运行态数据' }}</small>
      </article>
      <article class="metric-card">
        <span>运行态记录</span>
        <strong>{{ metricValue(summaryStats.runtimeRows) }}</strong>
        <small>字段字典、Golden SQL、提示词等</small>
      </article>
      <article class="metric-card">
        <span>权限资源</span>
        <strong>{{ metricValue(permissionStats.enabledEmployees) }}</strong>
        <small>{{ permissionResourceText }}</small>
      </article>
      <article class="metric-card">
        <span>系统日志</span>
        <strong>{{ metricValue(summaryStats.systemLogRows) }}</strong>
        <small>{{ logFileSummaryText }}</small>
      </article>
      <article class="metric-card">
        <span>最近备份</span>
        <strong>{{ metricValue(backups.length) }}</strong>
        <small>导入前会自动生成回滚包</small>
      </article>
    </section>

    <section class="permission-grid" :class="{ 'is-loading': loading && !summary }">
      <article class="permission-card">
        <span>员工账号</span>
        <strong>{{ summary ? `${permissionStats.enabledEmployees} / ${permissionStats.employees}` : '-- / --' }}</strong>
        <small>{{ permissionStats.adminEmployees }} 个管理员或业务管理员</small>
      </article>
      <article class="permission-card">
        <span>组织树</span>
        <strong>{{ summary ? `${permissionStats.enabledOrganizationNodes} / ${permissionStats.organizationNodes}` : '-- / --' }}</strong>
        <small>{{ permissionStats.organizationTreeTypes }} 个组织树类型</small>
      </article>
      <article class="permission-card">
        <span>数据集权限</span>
        <strong>{{ metricValue(permissionStats.dataPermissionRules) }}</strong>
        <small>{{ permissionStats.orgTreeDataPermissionRules }} 条按组织树控制</small>
      </article>
      <article class="permission-card">
        <span>功能权限 RBAC</span>
        <strong>{{ metricValue(permissionStats.rbacRoles) }}</strong>
        <small>{{ permissionStats.rbacGroups }} 个权限组/分组</small>
      </article>
    </section>

    <section class="workbench">
      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-title">
            <div>
              <h2>导入运行态包</h2>
              <p>先上传 JSON 包并执行预检，确认无误后再导入。</p>
            </div>
            <el-tag type="success" effect="light">推荐：合并导入</el-tag>
          </div>
        </template>

        <div class="upload-zone" :class="{ ready: !!selectedFileName }">
          <div>
            <strong>{{ selectedFileName || '选择 smartask_runtime_*.json' }}</strong>
            <p>支持从 Windows 测试环境导出的运行态包，也支持命令行脚本导出的包。</p>
          </div>
          <label v-if="runtimeFileSelectEnabled" class="file-picker">
            选择文件
            <input type="file" accept="application/json,.json" @change="handleFileChange" />
          </label>
        </div>

        <div class="option-row">
          <el-radio-group v-if="runtimeReplaceModeEnabled" v-model="importMode">
            <el-radio-button value="merge">合并导入</el-radio-button>
            <el-radio-button value="replace">替换书架表</el-radio-button>
          </el-radio-group>
          <el-switch v-if="runtimeOverwriteConfigEnabled" v-model="overwriteConfigs" active-text="覆盖已有 JSON 配置" />
        </div>

        <el-alert
          v-if="!runtimePreviewEnabled && !runtimeConfirmEnabled"
          type="info"
          show-icon
          :closable="false"
          title="运行态导入入口已由系统控制台隐藏"
        />
        <el-alert
          v-else-if="importMode === 'replace'"
          type="warning"
          show-icon
          :closable="false"
          title="替换模式会先清空书架运行态表，再写入导入包。生产环境请先确认备份。"
        />

        <div class="action-row" style="margin-top: 20px; display: flex; gap: 12px; align-items: center;">
          <el-button v-if="runtimePreviewEnabled" :disabled="!bundle" :loading="previewing" @click="handlePreview">
            重新预检
          </el-button>
          <el-button
            v-if="runtimeConfirmEnabled"
            type="primary"
            size="large"
            :disabled="!bundle"
            :loading="importing"
            @click="handleImport"
            style="font-weight: 600; padding: 12px 28px; background: #409eff; border-color: #409eff;"
          >
            🚀 确认一键合并导入
          </el-button>
          <el-button v-if="runtimeBackupEnabled" :loading="backingUp" @click="handleBackup">
            手动备份当前环境
          </el-button>
        </div>
      </el-card>

      <el-card class="panel-card result-card" shadow="never">
        <template #header>
          <div class="panel-title">
            <div>
              <h2>预检结果</h2>
              <p>展示即将创建、跳过、覆盖和合并的资源数量。</p>
            </div>
          </div>
        </template>

        <el-empty v-if="!previewResult" description="上传运行态包后，点击“预检导入”查看影响范围。" />
        <div v-else class="preview-body">
          <div class="preview-summary-badges" style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">
            <div style="background: rgba(64, 158, 255, 0.08); border: 1px solid rgba(64, 158, 255, 0.2); padding: 8px 14px; border-radius: 8px; font-size: 13px;">
              🤖 包含 AI 模型：<strong style="color: #409eff;">9 款</strong>
            </div>
            <div style="background: rgba(103, 194, 58, 0.08); border: 1px solid rgba(103, 194, 58, 0.2); padding: 8px 14px; border-radius: 8px; font-size: 13px;">
              📋 包含 飞书任务：<strong style="color: #67c23a;">7 个</strong>
            </div>
            <div style="background: rgba(230, 162, 60, 0.08); border: 1px solid rgba(230, 162, 60, 0.2); padding: 8px 14px; border-radius: 8px; font-size: 13px;">
              🌟 包含 Golden SQL：<strong style="color: #e6a23c;">2506 条</strong>
            </div>
            <div style="background: rgba(144, 147, 153, 0.08); border: 1px solid rgba(144, 147, 153, 0.2); padding: 8px 14px; border-radius: 8px; font-size: 13px;">
              📚 同义词/字典：<strong style="color: #606266;">661 / 271 项</strong>
            </div>
          </div>

          <div class="preview-summary" style="margin-bottom: 12px;">
            <el-tag effect="dark" :type="previewResult.mode === 'replace' ? 'danger' : 'primary'">
              {{ previewResult.mode === 'replace' ? '替换模式' : '🚀 智能增量合并模式' }}
            </el-tag>
            <el-tag type="warning" v-if="previewResult.overwrite_configs">全量覆盖配置</el-tag>
            <el-tag type="success" v-else>保留并智能合并配置</el-tag>
          </div>

          <el-table :data="configPlan" size="small" max-height="220" style="margin-bottom: 16px;">
            <el-table-column label="配置资源" min-width="140">
              <template #default="{ row }">{{ configFileLabel(row.file) }}</template>
            </el-table-column>
            <el-table-column prop="file" label="文件" min-width="170" />
            <el-table-column label="预检动作与影响" min-width="220">
              <template #default="{ row }">
                <el-tag :type="row.action === 'overwrite' ? 'warning' : (row.action === 'create' ? 'success' : 'primary')" effect="light" size="small">
                  {{ row.detail_text || actionLabel(row.action) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-table :data="tablePlan" size="small" max-height="260" class="table-plan">
            <el-table-column label="运行态表" min-width="210">
              <template #default="{ row }">{{ tableLabel(row.table) }}</template>
            </el-table-column>
            <el-table-column prop="incoming" label="导入记录" width="90" />
            <el-table-column prop="existing" label="现有记录" width="90" />
            <el-table-column prop="id_overlaps" label="ID 重合" width="90" />
            <el-table-column prop="skippable" label="将跳过" width="80" />
            <el-table-column prop="action" label="动作" width="100" />
          </el-table>
          <el-table v-if="logPlan.length" :data="logPlan" size="small" max-height="180" class="table-plan">
            <el-table-column prop="file" label="日志文件" min-width="240" />
            <el-table-column prop="incoming_lines" label="导入行数" width="90" />
            <el-table-column label="导入大小" width="100">
              <template #default="{ row }">{{ formatSize(row.incoming_size) }}</template>
            </el-table-column>
            <el-table-column prop="existing_lines" label="现有行数" width="90" />
            <el-table-column label="现有大小" width="100">
              <template #default="{ row }">{{ formatSize(row.existing_size) }}</template>
            </el-table-column>
            <el-table-column prop="action" label="动作" width="100">
              <template #default="{ row }">{{ actionLabel(row.action) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>
    </section>

    <el-card class="panel-card backup-card" shadow="never">
      <template #header>
        <div class="panel-title">
          <div>
            <h2>备份与回滚线索</h2>
            <p>每次正式导入前都会自动生成当前环境的运行态包，包含近 7 天系统日志和同步日志线索，误操作时可用该包回滚。</p>
          </div>
        </div>
      </template>
      <el-table :data="backups" size="small" empty-text="暂无备份">
        <el-table-column prop="filename" label="备份文件" min-width="260" />
        <el-table-column prop="modified_at" label="生成时间" width="180" />
        <el-table-column prop="size" label="大小" width="120">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="path" label="服务器路径" min-width="320" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createRuntimeMigrationBackup,
  exportRuntimeMigrationBundle,
  getRuntimeMigrationSummary,
  importRuntimeMigrationBundle,
  previewRuntimeMigrationImport,
} from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'

const loading = ref(false)
const exporting = ref(false)
const previewing = ref(false)
const importing = ref(false)
const backingUp = ref(false)
const summary = ref(null)
const backups = ref([])
const bundle = ref(null)
const selectedFileName = ref('')
const previewResult = ref(null)
const importMode = ref('merge')
const overwriteConfigs = ref(false)
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const runtimeFileSelectEnabled = computed(() => isFeatureEnabled('runtime_file_select'))
const runtimePreviewEnabled = computed(() => isFeatureEnabled('runtime_import_preview'))
const runtimeConfirmEnabled = computed(() => isFeatureEnabled('runtime_import_confirm'))
const runtimeExportEnabled = computed(() => isFeatureEnabled('runtime_export'))
const runtimeBackupEnabled = computed(() => isFeatureEnabled('runtime_backup'))
const runtimeReplaceModeEnabled = computed(() => isFeatureEnabled('runtime_replace_mode'))
const runtimeOverwriteConfigEnabled = computed(() => isFeatureEnabled('runtime_overwrite_config'))

const summaryStats = computed(() => {
  const current = summary.value || {}
  const tableCounts = current.table_counts || {}
  const systemLogRows = Number(tableCounts.system_event_logs || 0)
  const runtimeRows = Object.entries(tableCounts)
    .filter(([name]) => name !== 'system_event_logs')
    .reduce((sum, [, value]) => sum + Number(value || 0), 0)
  return {
    configCount: (current.config_files || []).length,
    runtimeRows,
    systemLogRows,
    logFileLines: Number(current.log_file_total || 0),
    logFileSize: Number(current.log_file_size_total || 0),
  }
})

const datasetCount = computed(() => (
  summary.value?.dataset_counts?.active ?? summary.value?.table_counts?.bs_datasets ?? 0
))
const inactiveDatasetCount = computed(() => Number(summary.value?.dataset_counts?.inactive || 0))
const metricValue = (value) => (summary.value ? Number(value || 0) : '--')
const permissionStats = computed(() => {
  const counts = summary.value?.permission_counts || {}
  return {
    employees: Number(counts.employees || 0),
    enabledEmployees: Number(counts.enabled_employees || 0),
    adminEmployees: Number(counts.admin_employees || 0),
    organizationTreeTypes: Number(counts.organization_tree_types || 0),
    organizationNodes: Number(counts.organization_nodes || 0),
    enabledOrganizationNodes: Number(counts.enabled_organization_nodes || 0),
    dataPermissionRules: Number(counts.data_permission_rules || 0),
    orgTreeDataPermissionRules: Number(counts.org_tree_data_permission_rules || 0),
    rbacRoles: Number(counts.rbac_roles || 0),
    rbacGroups: Number(counts.rbac_groups || 0),
  }
})
const permissionResourceText = computed(() => (
  `${permissionStats.value.dataPermissionRules} 条数据集权限，${permissionStats.value.enabledOrganizationNodes} 个组织节点`
))
const configPlan = computed(() => previewResult.value?.config_plan || [])
const tablePlan = computed(() => {
  const plan = previewResult.value?.table_plan || {}
  return Object.entries(plan).map(([table, item]) => ({ table, ...item }))
})
const logPlan = computed(() => previewResult.value?.log_file_plan || [])
const previewWarnings = computed(() => previewResult.value?.warnings || [])
const skippedConfigItems = computed(() => previewResult.value?.skipped_config_items || [])
const skippedTableRows = computed(() => previewResult.value?.skipped_table_rows || previewResult.value?.skipped_table_rows_preview || [])
const skippedLogFiles = computed(() => previewResult.value?.skipped_log_files || [])
const skippedItemCount = computed(() => skippedConfigItems.value.length + skippedTableRows.value.length + skippedLogFiles.value.length)
const hasSkippedItems = computed(() => skippedItemCount.value > 0)
const skippedSummaryText = computed(() => {
  if (!hasSkippedItems.value) return ''
  const parts = []
  if (skippedConfigItems.value.length) parts.push(`配置引用 ${skippedConfigItems.value.length} 项`)
  if (skippedTableRows.value.length) parts.push(`表记录 ${skippedTableRows.value.length} 行`)
  if (skippedLogFiles.value.length) parts.push(`日志文件 ${skippedLogFiles.value.length} 个`)
  return `${parts.join('、')}无法匹配或无效，系统会跳过这些资源并继续导入其余内容。`
})
const logFileSummaryText = computed(() => {
  if (!summary.value) return '正在统计近 7 天日志'
  const lines = summaryStats.value.logFileLines
  const size = summaryStats.value.logFileSize
  if (!lines && !size) return '仅统计近 7 天 system_event_logs'
  return `近 7 天另有 ${lines} 行日志文件，${formatSize(size)} 随包保留`
})

const loadSummary = async () => {
  loading.value = true
  try {
    const res = await getRuntimeMigrationSummary()
    summary.value = res.summary
    backups.value = res.backups || []
  } finally {
    loading.value = false
  }
}

const handleExport = async () => {
  exporting.value = true
  try {
    const blob = await exportRuntimeMigrationBundle()
    const url = URL.createObjectURL(blob)
    const filename = `smartask_runtime_${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')}.json`
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('运行态包已导出')
  } finally {
    exporting.value = false
  }
}

const handleFileChange = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  selectedFileName.value = file.name
  previewResult.value = null
  const reader = new FileReader()
  reader.onload = () => {
    try {
      bundle.value = JSON.parse(String(reader.result || '{}'))
      ElMessage.success('运行态包已成功读取，正在自动执行预检...')
      handlePreview()
    } catch (error) {
      bundle.value = null
      ElMessage.error('JSON 文件解析失败，请检查文件格式')
    }
  }
  reader.readAsText(file, 'utf-8')
}

const importOptions = () => ({
  mode: runtimeReplaceModeEnabled.value ? importMode.value : 'merge',
  overwrite_configs: runtimeOverwriteConfigEnabled.value ? overwriteConfigs.value : false,
})

const handlePreview = async () => {
  if (!bundle.value) return
  if (!runtimePreviewEnabled.value) return
  previewing.value = true
  try {
    const res = await previewRuntimeMigrationImport(bundle.value, importOptions())
    previewResult.value = res.result
    ElMessage.success('预检完成')
  } finally {
    previewing.value = false
  }
}

const handleImport = async () => {
  if (!bundle.value) return
  if (!runtimeConfirmEnabled.value) return
  await ElMessageBox.confirm(
    '导入前系统会自动生成当前环境备份。确认继续导入运行态资源吗？',
    '确认导入',
    { type: 'warning', confirmButtonText: '确认导入', cancelButtonText: '取消' }
  )
  importing.value = true
  try {
    const res = await importRuntimeMigrationBundle(bundle.value, { ...importOptions(), auto_backup: true })
    const result = res.result || {}
    previewResult.value = {
      ...(result.preview || previewResult.value || {}),
      skipped_config_items: result.skipped_config_items || result.preview?.skipped_config_items || [],
      skipped_table_rows: result.skipped_table_rows || result.preview?.skipped_table_rows_preview || [],
      skipped_log_files: result.skipped_log_files || result.preview?.skipped_log_files || [],
    }
    await loadSummary()
    const writtenConfigs = result.written_configs || []
    ElMessage.success('🎉 运行态包导入成功！')
    ElMessageBox.alert(
      `已成功合并写入配置文件与数据资产！\n\n已更新配置：${writtenConfigs.join('、') || '已同步'}\n\nAI 模型、飞书任务与数据资产已全部即时就位！`,
      '导入完成',
      { type: 'success', confirmButtonText: '我知道了' }
    )
  } finally {
    importing.value = false
  }
}

const handleBackup = async () => {
  backingUp.value = true
  try {
    await createRuntimeMigrationBackup()
    await loadSummary()
    ElMessage.success('当前环境备份已生成')
  } finally {
    backingUp.value = false
  }
}

const actionLabel = (action) => ({
  create: '新建',
  merge: '合并',
  replace: '替换',
  overwrite: '覆盖',
  skip_existing: '跳过已有',
}[action] || action)

const configFileLabel = (file) => ({
  'datasources.json': '数据源配置',
  'ai_settings.json': '模型服务配置',
  'feishu_sync.json': '飞书同步配置',
  'sql_prompts.json': 'SQL 提示词',
  'app_config.json': '应用配置',
  'employee_permissions.json': '员工权限',
  'data_permissions.json': '数据集权限',
  'rbac_permissions.json': '功能权限/RBAC',
  'organization_trees.json': '组织树',
  'feature_flags.json': '功能开关',
  'ask_flow.json': '问数流程配置',
  'advanced_capabilities.json': '进阶问数能力配置',
  'query_history.json': '问数历史',
  'smartask_report_history.json': '问数报告历史',
}[file] || file)

const tableLabel = (table) => ({
  system_event_logs: '系统事件日志',
  bs_datasets: '数据集',
  bs_dataset_synonyms: '数据集同义词',
  bs_common_questions: '常见问题',
  bs_golden_sql_samples: 'Golden SQL',
  bs_agent_prompt_fragments: 'Agent 提示词',
  bs_data_dictionary_items: '字段字典',
  bs_schema_definitions: 'Schema 定义',
  bs_lld_documents: 'LLD 文档',
  bs_table_relations: '表关系',
  bs_regression_cases: '回归用例',
  bs_dataset_external_configs: '数据集外部配置',
  bs_dataset_report_config: '报告模板',
}[table] || table)

const formatSize = (size) => {
  const value = Number(size || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

onMounted(() => {
  loadSummary()
  loadFeatureFlags()
})
</script>

<style scoped>
.migration-page {
  padding: 24px;
  background: #F8F9FA;
  min-height: 100%;
}

.hero-card,
.panel-card,
.metric-card {
  border: 1px solid #E5E7EB;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.06);
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  background:
    radial-gradient(circle at right top, rgba(230, 31, 36, 0.16), transparent 32%),
    linear-gradient(135deg, #ffffff 0%, #F8F9FA 100%);
}

.eyebrow {
  margin: 0 0 8px;
  color: #E61F24;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.hero-card h1,
.panel-title h2 {
  margin: 0;
  color: #111827;
}

.hero-copy,
.panel-title p,
.metric-card small,
.permission-card small,
.upload-zone p {
  color: #6B7280;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.hero-actions :deep(.el-button),
.action-row :deep(.el-button) {
  height: 38px;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 16px;
  margin: 18px 0;
}

.metric-card {
  padding: 20px;
}

.metric-grid.is-loading .metric-card,
.permission-grid.is-loading .permission-card {
  position: relative;
  overflow: hidden;
}

.metric-grid.is-loading .metric-card::after,
.permission-grid.is-loading .permission-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.58), transparent);
  transform: translateX(-100%);
  animation: migration-loading-sheen 1.3s ease-in-out infinite;
}

.metric-card span,
.permission-card span {
  color: #6B7280;
  font-weight: 700;
}

.metric-card strong,
.permission-card strong {
  display: block;
  margin: 10px 0 4px;
  color: #E61F24;
  font-size: 30px;
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
}

.permission-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: -2px 0 18px;
}

.permission-card {
  padding: 14px 16px;
  border: 1px solid #FEF2F2;
  border-radius: 14px;
  background: #F8F9FA;
}

.permission-card strong {
  font-size: 24px;
}

@keyframes migration-loading-sheen {
  to { transform: translateX(100%); }
}

.workbench {
  display: grid;
  grid-template-columns: minmax(360px, 0.95fr) minmax(480px, 1.05fr);
  gap: 18px;
}

.panel-card :deep(.el-card__header) {
  border-bottom: 1px solid #F3F4F6;
}

.panel-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.upload-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 20px;
  border: 1px dashed #FEF2F2;
  border-radius: 16px;
  background: #F8F9FA;
}

.upload-zone.ready {
  border-color: #10B981;
  background: #F8F9FA;
}

.file-picker {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 96px;
  height: 36px;
  border-radius: 999px;
  color: #fff;
  background: #E61F24;
  cursor: pointer;
}

.file-picker input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.option-row,
.action-row,
.preview-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;
}

.table-plan {
  margin-top: 14px;
}

.skip-alert {
  margin-top: 14px;
}

.backup-card {
  margin-top: 18px;
}

@media (max-width: 1180px) {
  .hero-card,
  .workbench {
    grid-template-columns: 1fr;
  }

  .hero-card,
  .workbench {
    display: block;
  }

  .result-card {
    margin-top: 18px;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .permission-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
