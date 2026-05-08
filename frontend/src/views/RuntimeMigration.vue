<template>
  <div class="migration-page">
    <section class="hero-card">
      <div>
        <p class="eyebrow">RELEASE GUARD</p>
        <h1>迁移发布与配置保护</h1>
        <p class="hero-copy">
          管理数据源、数据集、字段字典、Agent 提示词、模型配置、报告模板和员工权限等运行态资源。
          发布代码前后可以在这里导出、预检、备份和导入，避免生产环境配置被误覆盖。
        </p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="loadSummary">刷新状态</el-button>
        <el-button type="primary" :loading="exporting" @click="handleExport">导出运行态包</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-card">
        <span>配置文件</span>
        <strong>{{ summaryStats.configCount }}</strong>
        <small>不含 token、历史记录、local 配置</small>
      </article>
      <article class="metric-card">
        <span>数据集</span>
        <strong>{{ datasetCount }}</strong>
        <small>来自 bs_datasets</small>
      </article>
      <article class="metric-card">
        <span>书架记录</span>
        <strong>{{ summaryStats.tableRows }}</strong>
        <small>字段字典、Golden SQL、提示词等</small>
      </article>
      <article class="metric-card">
        <span>最近备份</span>
        <strong>{{ backups.length }}</strong>
        <small>导入前会自动生成回滚包</small>
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
          <label class="file-picker">
            选择文件
            <input type="file" accept="application/json,.json" @change="handleFileChange" />
          </label>
        </div>

        <div class="option-row">
          <el-radio-group v-model="importMode">
            <el-radio-button value="merge">合并导入</el-radio-button>
            <el-radio-button value="replace">替换书架表</el-radio-button>
          </el-radio-group>
          <el-switch v-model="overwriteConfigs" active-text="覆盖已有 JSON 配置" />
        </div>

        <el-alert
          v-if="importMode === 'replace'"
          type="warning"
          show-icon
          :closable="false"
          title="替换模式会先清空书架运行态表，再写入导入包。生产环境请先确认备份。"
        />

        <div class="action-row">
          <el-button :disabled="!bundle" :loading="previewing" @click="handlePreview">预检导入</el-button>
          <el-button type="danger" plain :disabled="!bundle" :loading="importing" @click="handleImport">
            确认导入
          </el-button>
          <el-button :loading="backingUp" @click="handleBackup">手动备份当前环境</el-button>
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
          <div class="preview-summary">
            <el-tag>{{ previewResult.mode === 'replace' ? '替换模式' : '合并模式' }}</el-tag>
            <el-tag type="warning" v-if="previewResult.overwrite_configs">覆盖配置</el-tag>
            <el-tag type="success" v-else>保留已有配置</el-tag>
          </div>
          <el-table :data="configPlan" size="small" max-height="180">
            <el-table-column prop="file" label="配置文件" />
            <el-table-column prop="action" label="动作" width="140">
              <template #default="{ row }">{{ actionLabel(row.action) }}</template>
            </el-table-column>
          </el-table>
          <el-table :data="tablePlan" size="small" max-height="260" class="table-plan">
            <el-table-column prop="table" label="书架表" min-width="210" />
            <el-table-column prop="incoming" label="导入记录" width="90" />
            <el-table-column prop="existing" label="现有记录" width="90" />
            <el-table-column prop="id_overlaps" label="ID 重合" width="90" />
            <el-table-column prop="action" label="动作" width="100" />
          </el-table>
        </div>
      </el-card>
    </section>

    <el-card class="panel-card backup-card" shadow="never">
      <template #header>
        <div class="panel-title">
          <div>
            <h2>备份与回滚线索</h2>
            <p>每次正式导入前都会自动生成当前环境的完整运行态包，误操作时可用该包回滚。</p>
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

const summaryStats = computed(() => {
  const current = summary.value || {}
  const tableCounts = current.table_counts || {}
  return {
    configCount: (current.config_files || []).length,
    tableRows: Object.values(tableCounts).reduce((sum, value) => sum + Number(value || 0), 0),
  }
})

const datasetCount = computed(() => summary.value?.table_counts?.bs_datasets || 0)
const configPlan = computed(() => previewResult.value?.config_plan || [])
const tablePlan = computed(() => {
  const plan = previewResult.value?.table_plan || {}
  return Object.entries(plan).map(([table, item]) => ({ table, ...item }))
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
      ElMessage.success('运行态包已读取，可以先预检')
    } catch (error) {
      bundle.value = null
      ElMessage.error('JSON 文件解析失败')
    }
  }
  reader.readAsText(file, 'utf-8')
}

const importOptions = () => ({
  mode: importMode.value,
  overwrite_configs: overwriteConfigs.value,
})

const handlePreview = async () => {
  if (!bundle.value) return
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
  await ElMessageBox.confirm(
    '导入前系统会自动生成当前环境备份。确认继续导入运行态资源吗？',
    '确认导入',
    { type: 'warning', confirmButtonText: '确认导入', cancelButtonText: '取消' }
  )
  importing.value = true
  try {
    const res = await importRuntimeMigrationBundle(bundle.value, { ...importOptions(), auto_backup: true })
    previewResult.value = res.result?.preview || previewResult.value
    await loadSummary()
    ElMessage.success('导入完成，已生成回滚备份')
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
  overwrite: '覆盖',
  skip_existing: '跳过已有',
}[action] || action)

const formatSize = (size) => {
  const value = Number(size || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

onMounted(loadSummary)
</script>

<style scoped>
.migration-page {
  padding: 24px;
  background: #f5f7fb;
  min-height: 100%;
}

.hero-card,
.panel-card,
.metric-card {
  border: 1px solid #e7edf6;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 16px 40px rgba(31, 45, 61, 0.06);
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  background:
    radial-gradient(circle at right top, rgba(24, 144, 255, 0.16), transparent 32%),
    linear-gradient(135deg, #ffffff 0%, #f7fbff 100%);
}

.eyebrow {
  margin: 0 0 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.hero-card h1,
.panel-title h2 {
  margin: 0;
  color: #0f172a;
}

.hero-copy,
.panel-title p,
.metric-card small,
.upload-zone p {
  color: #64748b;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  white-space: nowrap;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin: 18px 0;
}

.metric-card {
  padding: 20px;
}

.metric-card span {
  color: #64748b;
  font-weight: 700;
}

.metric-card strong {
  display: block;
  margin: 10px 0 4px;
  color: #1d4ed8;
  font-size: 30px;
}

.workbench {
  display: grid;
  grid-template-columns: minmax(360px, 0.95fr) minmax(480px, 1.05fr);
  gap: 18px;
}

.panel-card :deep(.el-card__header) {
  border-bottom: 1px solid #eef2f7;
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
  border: 1px dashed #bfdbfe;
  border-radius: 16px;
  background: #f8fbff;
}

.upload-zone.ready {
  border-color: #22c55e;
  background: #f4fdf7;
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
  background: #2563eb;
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
}
</style>
