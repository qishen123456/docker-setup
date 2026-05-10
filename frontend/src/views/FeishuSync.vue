<template>
  <div class="fs-page">
    <section class="fs-hero">
      <div class="fs-hero-orb"></div>
      <div class="fs-hero-copy">
        <div class="fs-kicker">FEISHU DATA PIPELINE</div>
        <h2>飞书同步工作台</h2>
        <p>把多维表格沉淀为可问数的数据资产，统一管理同步任务、运行状态、目标表和操作日志。</p>
      </div>
      <div class="fs-hero-actions">
        <button class="fs-btn fs-btn-ghost" @click="loadData">
          <el-icon><RefreshRight /></el-icon>
          <span>刷新状态</span>
        </button>
        <button v-if="isFeatureEnabled('feishu_sync_edit')" class="fs-btn fs-btn-primary" @click="openAdd">
          <el-icon><Plus /></el-icon>
          <span>新建同步任务</span>
        </button>
      </div>
    </section>

    <section class="fs-stat-grid">
      <article v-for="card in statCards" :key="card.label" class="fs-stat-card" :class="card.tone">
        <span class="fs-stat-icon">{{ card.icon }}</span>
        <div class="fs-stat-copy">
          <span class="fs-stat-label">{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.desc }}</small>
        </div>
      </article>
    </section>

    <section class="fs-board" v-loading="loading">
      <div class="fs-board-head">
        <div>
          <div class="fs-board-kicker">SYNC TASKS</div>
          <h3>同步任务编排</h3>
          <p>卡片展示每条同步链路，重点看启停状态、落库表、频率和最后同步结果。</p>
        </div>
        <div class="fs-board-tags">
          <span>{{ syncConfigs.length }} 个任务</span>
          <span>{{ activeCount }} 个启用</span>
        </div>
      </div>

      <div v-if="syncConfigs.length" class="fs-task-grid">
        <article v-for="row in syncConfigs" :key="row.id" class="fs-task-card" :class="statusClass(row.last_sync_status)">
          <div class="fs-task-top">
            <div class="fs-task-title-group">
              <span class="fs-task-status-dot"></span>
              <div>
                <h4>{{ row.name || '未命名同步任务' }}</h4>
                <p>{{ row.description || '暂无描述，建议补充业务口径和同步用途。' }}</p>
              </div>
            </div>
            <span class="fs-status-pill" :class="statusClass(row.last_sync_status)">
              {{ getStatusText(row.last_sync_status) }}
            </span>
          </div>

          <div class="fs-task-meta">
            <div>
              <span>目标表</span>
              <strong>{{ row.target_table || '-' }}</strong>
            </div>
            <div>
              <span>同步频率</span>
              <strong>{{ formatFrequency(row.sync_frequency) }}</strong>
            </div>
            <div>
              <span>最后同步</span>
              <strong>{{ formatTime(row.last_sync_time) || '尚未同步' }}</strong>
            </div>
          </div>

          <div class="fs-task-route">
            <span>飞书多维表格</span>
            <i></i>
            <span>本地数据表</span>
          </div>

          <div class="fs-task-actions">
            <button v-if="isFeatureEnabled('feishu_sync_test')" class="fs-action-btn" :disabled="testingId === row.id" @click="testConnection(row)">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ testingId === row.id ? '测试中' : '测试' }}</span>
            </button>
            <button
              v-if="isFeatureEnabled('feishu_sync_run')"
              class="fs-action-btn fs-action-primary"
              :disabled="!row.is_active || row.last_sync_status === 'running'"
              @click="startSync(row)"
            >
              <el-icon><RefreshRight /></el-icon>
              <span>{{ row.last_sync_status === 'running' ? '同步中' : '同步' }}</span>
            </button>
            <button v-if="row.is_active && isFeatureEnabled('feishu_sync_run')" class="fs-action-btn" :disabled="pausingId === row.id" @click="pauseSync(row)">
              <el-icon><VideoPause /></el-icon>
              <span>{{ pausingId === row.id ? '暂停中' : '暂停' }}</span>
            </button>
            <button v-else-if="isFeatureEnabled('feishu_sync_run')" class="fs-action-btn" :disabled="resumingId === row.id" @click="resumeSync(row)">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ resumingId === row.id ? '恢复中' : '恢复' }}</span>
            </button>
            <button class="fs-action-btn" @click="viewLogs(row)">
              <el-icon><Document /></el-icon>
              <span>日志</span>
            </button>
            <button v-if="isFeatureEnabled('feishu_sync_edit')" class="fs-action-btn" @click="openEdit(row)">
              <el-icon><Edit /></el-icon>
              <span>编辑</span>
            </button>
            <el-popconfirm v-if="isFeatureEnabled('feishu_sync_edit')" title="确认删除此同步配置？" @confirm="deleteConfig(row.id)">
              <template #reference>
                <button class="fs-action-btn fs-action-danger">
                  <el-icon><Delete /></el-icon>
                  <span>删除</span>
                </button>
              </template>
            </el-popconfirm>
          </div>
        </article>
      </div>

      <el-empty v-else description="还没有同步任务，先新建一条飞书到本地表的同步链路。" />
    </section>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑同步配置' : '添加同步配置'" width="880px" @close="resetForm">
      <div class="fs-url-assist">
        <div>
          <strong>粘贴飞书多维表格链接</strong>
          <span>自动识别 Base / Table / View，并生成建议目标表名。</span>
        </div>
        <div class="fs-url-row">
          <el-input
            v-model="feishuUrlInput"
            placeholder="例如：https://angelgroup.feishu.cn/base/xxx?table=tblxxx&view=vewxxx"
            clearable
            @change="parseFeishuLink"
          />
          <button v-if="isFeatureEnabled('feishu_sync_test')" class="fs-action-btn fs-action-primary" :disabled="parsingUrl || !feishuUrlInput" @click.prevent="parseFeishuLink">
            {{ parsingUrl ? '解析中' : '解析链接' }}
          </button>
        </div>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="配置名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标表" prop="target_table">
              <el-input v-model="form.target_table" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="App ID" prop="app_id">
              <el-input v-model="form.app_id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="App Secret" prop="app_secret">
              <el-input v-model="form.app_secret" type="password" show-password />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="Base ID" prop="base_id">
              <el-input v-model="form.base_id" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Table ID" prop="table_id">
              <el-input v-model="form.table_id" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="View ID">
              <el-input v-model="form.view_id" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="同步方式">
              <el-select v-model="form.sync_mode" style="width: 100%">
                <el-option label="增量" value="incremental" />
                <el-option label="全量" value="full" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="同步频率(分钟)">
              <el-input-number v-model="form.sync_frequency" :min="1" :max="1440" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>

      <section class="fs-schema-panel" :class="{ 'is-ready': schemaPreview }">
        <div class="fs-schema-head">
          <div>
            <strong>字段结构检测</strong>
            <span>同步前自动检查 PG 目标表是否存在，以及飞书字段相对历史落库字段的变化。</span>
          </div>
          <button v-if="isFeatureEnabled('feishu_sync_test')" class="fs-action-btn fs-action-primary" :disabled="schemaLoading" @click.prevent="previewSchema">
            {{ schemaLoading ? '检测中' : '检测字段与建表方案' }}
          </button>
        </div>

        <div v-if="schemaPreview" class="fs-schema-summary">
          <div>
            <span>目标表状态</span>
            <strong>{{ schemaPreview.table_exists ? '已存在' : '将自动创建' }}</strong>
          </div>
          <div>
            <span>飞书字段</span>
            <strong>{{ schemaPreview.field_count || 0 }}</strong>
          </div>
          <div>
            <span>新增字段</span>
            <strong>{{ schemaPreview.added_fields?.length || 0 }}</strong>
          </div>
          <div>
            <span>减少字段</span>
            <strong>{{ schemaPreview.removed_fields?.length || 0 }}</strong>
          </div>
          <div>
            <span>对比基线</span>
            <strong>{{ getBaselineText(schemaPreview.baseline_source) }}</strong>
          </div>
          <div>
            <span>字段来源</span>
            <strong>{{ schemaPreview.field_source_text || '飞书字段元数据' }}</strong>
          </div>
        </div>

        <div v-if="schemaPreview" class="fs-schema-alert" :class="{ 'has-diff': hasSchemaDiff }">
          <strong>{{ hasSchemaDiff ? '检测到字段变化' : '当前未发现字段差异' }}</strong>
          <span>
            {{ schemaPreview.warning || (hasSchemaDiff
              ? `新增 ${schemaPreview.added_fields?.length || 0} 个，减少 ${schemaPreview.removed_fields?.length || 0} 个。`
              : '字段名称、类型和顺序如下，可用于确认数据集 DDL 是否需要同步调整。') }}
          </span>
        </div>

        <div v-if="schemaPreview" class="fs-field-diff-grid">
          <div class="fs-field-box added">
            <div class="fs-field-box-title">飞书新增字段</div>
            <div v-if="schemaPreview.added_fields?.length" class="fs-field-tags">
              <el-tag v-for="field in schemaPreview.added_fields.slice(0, 30)" :key="field" type="success" effect="light">
                {{ field }}
              </el-tag>
            </div>
            <p v-else>没有发现新增字段。</p>
          </div>
          <div class="fs-field-box removed">
            <div class="fs-field-box-title">历史字段缺失</div>
            <div v-if="schemaPreview.removed_fields?.length" class="fs-field-tags">
              <el-tag v-for="field in schemaPreview.removed_fields.slice(0, 30)" :key="field" type="danger" effect="light">
                {{ field }}
              </el-tag>
            </div>
            <p v-else>没有发现减少字段。</p>
          </div>
        </div>

        <div v-if="schemaPreview" class="fs-field-table-wrap">
          <div class="fs-field-table-title">
            <strong>字段明细</strong>
            <span>每一行对应飞书字段元数据；减少字段为历史 PG/快照字段。</span>
          </div>
          <el-table :data="schemaFieldRows" size="small" border height="320">
            <el-table-column prop="sequence" label="序号" width="72" />
            <el-table-column prop="name" label="字段名称" min-width="220" show-overflow-tooltip />
            <el-table-column prop="type" label="字段类型" width="130" />
            <el-table-column prop="field_id" label="Field ID" min-width="180" show-overflow-tooltip />
            <el-table-column label="差异状态" width="110">
              <template #default="{ row }">
                <el-tag :type="getFieldStatusType(row.status)" effect="light">
                  {{ row.status_text || '-' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <p v-else class="fs-schema-empty">
          新表第一次同步时会自动创建 `record_id + fields(JSONB) + sync_time` 的通用表；后续字段变化会写入字段快照记录。
        </p>
      </section>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button v-if="isFeatureEnabled('feishu_sync_edit')" type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="logDialogVisible" :title="`日志查看 - ${currentConfig?.name || ''}`" width="80%">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>日志查看 - {{ currentConfig?.name || '' }}</span>
          <div>
            <el-button size="small" @click="refreshLogs" :loading="loadingLogs">刷新</el-button>
            <el-popconfirm v-if="isFeatureEnabled('feishu_log_clear')" title="确认清空日志？" @confirm="clearLogs">
              <template #reference>
                <el-button size="small" type="danger">清空</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </template>

      <div style="height: 60vh; overflow-y: auto">
        <el-timeline>
          <el-timeline-item v-for="log in logs" :key="log.timestamp + log.message" :timestamp="log.timestamp" placement="top">
            <el-tag size="small" style="margin-right: 8px">{{ log.level }}</el-tag>
            <span>{{ log.message }}</span>
          </el-timeline-item>
        </el-timeline>
        <div v-if="logs.length === 0" style="text-align: center; padding: 30px; color: #909399">暂无日志</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Document, Edit, Plus, RefreshRight, VideoPause, VideoPlay } from '@element-plus/icons-vue'
import {
  clearFeishuSyncLogs,
  createFeishuSyncConfig,
  deleteFeishuSyncConfig,
  getFeishuSyncConfigs,
  getFeishuSyncLogs,
  pauseFeishuSync,
  parseFeishuUrl,
  previewFeishuSchema,
  resumeFeishuSync,
  startFeishuSync,
  testFeishuConnection,
  updateFeishuSyncConfig
} from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'

const syncConfigs = ref([])
const loading = ref(false)
const saving = ref(false)
const testingId = ref(null)
const pausingId = ref(null)
const resumingId = ref(null)
const feishuUrlInput = ref('')
const parsingUrl = ref(false)
const schemaLoading = ref(false)
const schemaPreview = ref(null)
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()

const logDialogVisible = ref(false)
const currentConfig = ref(null)
const logs = ref([])
const loadingLogs = ref(false)

let statusPollTimer = null

const totalCount = computed(() => syncConfigs.value.length)
const activeCount = computed(() => syncConfigs.value.filter((c) => c.is_active).length)
const runningCount = computed(() => syncConfigs.value.filter((c) => c.last_sync_status === 'running').length)
const failedCount = computed(() => syncConfigs.value.filter((c) => c.last_sync_status === 'failed').length)
const successCount = computed(() => syncConfigs.value.filter((c) => c.last_sync_status === 'success').length)
const schemaFieldRows = computed(() => schemaPreview.value?.field_rows || [])
const hasSchemaDiff = computed(() => (
  Boolean(schemaPreview.value)
  && ((schemaPreview.value.added_fields?.length || 0) > 0 || (schemaPreview.value.removed_fields?.length || 0) > 0)
))
const statCards = computed(() => [
  {
    label: '同步任务',
    value: totalCount.value,
    desc: '已配置的数据管道',
    icon: '↗',
    tone: 'total'
  },
  {
    label: '启用任务',
    value: activeCount.value,
    desc: '会参与自动调度',
    icon: '●',
    tone: 'active'
  },
  {
    label: '运行中',
    value: runningCount.value,
    desc: '正在拉取飞书数据',
    icon: '◌',
    tone: 'running'
  },
  {
    label: '异常任务',
    value: failedCount.value,
    desc: successCount.value ? `${successCount.value} 个最近成功` : '等待首轮同步',
    icon: '!',
    tone: failedCount.value ? 'failed' : 'quiet'
  }
])

const defaultForm = () => ({
  id: undefined,
  name: '',
  description: '',
  app_id: '',
  app_secret: '',
  base_id: '',
  table_id: '',
  view_id: '',
  sync_mode: 'incremental',
  sync_frequency: 30,
  target_table: '',
  is_active: true
})

const form = ref(defaultForm())

const rules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  target_table: [{ required: true, message: '请输入目标表', trigger: 'blur' }],
  app_id: [{ required: true, message: '请输入App ID', trigger: 'blur' }],
  app_secret: [{ required: true, message: '请输入App Secret', trigger: 'blur' }],
  base_id: [{ required: true, message: '请输入Base ID', trigger: 'blur' }],
  table_id: [{ required: true, message: '请输入Table ID', trigger: 'blur' }]
}

const stopStatusPolling = () => {
  if (statusPollTimer) {
    clearInterval(statusPollTimer)
    statusPollTimer = null
  }
}

const updateStatusPolling = () => {
  const hasRunning = (syncConfigs.value || []).some((c) => c.last_sync_status === 'running')
  if (!hasRunning) {
    stopStatusPolling()
    return
  }
  if (statusPollTimer) return
  statusPollTimer = setInterval(() => {
    loadData()
  }, 5000)
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await getFeishuSyncConfigs()
    syncConfigs.value = data.sync_configs || []
  } finally {
    loading.value = false
    updateStatusPolling()
  }
}

const normalizeTargetTable = (value) => {
  const raw = String(value || '').trim()
  const normalized = raw
    .replace(/[^0-9A-Za-z_]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
    .toLowerCase()
  if (!normalized) return ''
  return /^\d/.test(normalized) ? `t_${normalized}` : normalized.slice(0, 60)
}

const suggestTargetTable = (tableId) => normalizeTargetTable(`feishu_${tableId || Date.now()}`)

const openAdd = () => {
  isEdit.value = false
  const reusable = syncConfigs.value.find(item => item.app_id && item.app_secret) || {}
  form.value = {
    ...defaultForm(),
    app_id: reusable.app_id || '',
    app_secret: reusable.app_secret || ''
  }
  feishuUrlInput.value = ''
  schemaPreview.value = null
  dialogVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  form.value = { ...defaultForm(), ...row }
  feishuUrlInput.value = ''
  schemaPreview.value = null
  dialogVisible.value = true
}

const resetForm = () => {
  formRef.value?.clearValidate?.()
  schemaPreview.value = null
}

const parseFeishuLink = async () => {
  const url = feishuUrlInput.value?.trim()
  if (!url) return
  parsingUrl.value = true
  try {
    const result = await parseFeishuUrl(url)
    if (!result.success) {
      ElMessage.error(result.error || '链接解析失败')
      return
    }
    const parsed = result.parsed || {}
    form.value.base_id = parsed.base_id || form.value.base_id
    form.value.table_id = parsed.table_id || form.value.table_id
    form.value.view_id = parsed.view_id || form.value.view_id
    if (!form.value.target_table && parsed.table_id) form.value.target_table = suggestTargetTable(parsed.table_id)
    if (!form.value.name && parsed.table_id) form.value.name = `飞书表 ${parsed.table_id.slice(-6)}`
    if (!form.value.description && url) form.value.description = `由飞书链接自动解析创建：${url}`
    ElMessage.success('飞书链接已解析并填充')
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '链接解析失败')
  } finally {
    parsingUrl.value = false
  }
}

const previewSchema = async () => {
  if (!form.value.target_table && form.value.table_id) {
    form.value.target_table = suggestTargetTable(form.value.table_id)
  }
  const required = ['app_id', 'app_secret', 'base_id', 'table_id', 'target_table']
  const missing = required.find(key => !form.value[key])
  if (missing) {
    ElMessage.warning('请先补齐 App ID、App Secret、Base ID、Table ID 和目标表')
    return
  }
  schemaLoading.value = true
  try {
    const result = await previewFeishuSchema({
      ...form.value,
      sample_limit: 50
    })
    if (result.success) {
      schemaPreview.value = result.preview
      form.value.target_table = result.preview?.target_table || form.value.target_table
      ElMessage.success(result.message || '字段结构检测完成')
    } else {
      ElMessage.error(result.error || '字段结构检测失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '字段结构检测失败')
  } finally {
    schemaLoading.value = false
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  saving.value = true
  try {
    if (isEdit.value && form.value.id) {
      await updateFeishuSyncConfig(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createFeishuSyncConfig(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '保存失败')
  } finally {
    saving.value = false
  }
}

const deleteConfig = async (id) => {
  try {
    await deleteFeishuSyncConfig(id)
    ElMessage.success('删除成功')
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '删除失败')
  }
}

const testConnection = async (row) => {
  testingId.value = row.id
  try {
    const result = await testFeishuConnection({
      app_id: row.app_id,
      app_secret: row.app_secret,
      base_id: row.base_id,
      table_id: row.table_id,
      view_id: row.view_id || '',
      preview_limit: 20
    })
    if (result.success) ElMessage.success(result.message || '连接成功')
    else ElMessage.error(result.error || '连接失败')
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '连接测试失败')
  } finally {
    testingId.value = null
  }
}

const startSync = async (row) => {
  try {
    await startFeishuSync(row.id)
    ElMessage.success(`已启动同步：${row.name}`)
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '启动同步失败')
  }
}

const pauseSync = async (row) => {
  pausingId.value = row.id
  try {
    await pauseFeishuSync(row.id)
    ElMessage.success(`已暂停：${row.name}`)
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '暂停失败')
  } finally {
    pausingId.value = null
  }
}

const resumeSync = async (row) => {
  resumingId.value = row.id
  try {
    await resumeFeishuSync(row.id)
    ElMessage.success(`已恢复：${row.name}`)
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '恢复失败')
  } finally {
    resumingId.value = null
  }
}

const viewLogs = async (row) => {
  currentConfig.value = row
  logDialogVisible.value = true
  await loadLogs()
}

const loadLogs = async () => {
  if (!currentConfig.value) return
  loadingLogs.value = true
  try {
    const data = await getFeishuSyncLogs(currentConfig.value.id, 100)
    logs.value = data.logs || []
  } catch {
    logs.value = []
    ElMessage.error('加载日志失败')
  } finally {
    loadingLogs.value = false
  }
}

const refreshLogs = async () => {
  await loadLogs()
}

const clearLogs = async () => {
  if (!currentConfig.value) return
  try {
    await clearFeishuSyncLogs(currentConfig.value.id)
    logs.value = []
    ElMessage.success('日志已清空')
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '清空失败')
  }
}

const formatFrequency = (f) => `每${Number(f || 0)}分钟`

const formatTime = (t) => {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

const getStatusType = (s) => {
  if (s === 'success') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'running') return 'warning'
  return 'info'
}

const getStatusText = (s) => {
  if (s === 'success') return '成功'
  if (s === 'failed') return '失败'
  if (s === 'running') return '运行中'
  return '待同步'
}

const getBaselineText = (source) => {
  if (source === 'schema_registry') return '历史快照'
  if (source === 'pg_jsonb') return 'PG现有数据'
  return '新表'
}

const getFieldStatusType = (status) => {
  if (status === 'added') return 'success'
  if (status === 'removed') return 'danger'
  if (status === 'same') return 'info'
  return 'warning'
}

const statusClass = (s) => {
  if (s === 'success') return 'is-success'
  if (s === 'failed') return 'is-failed'
  if (s === 'running') return 'is-running'
  return 'is-pending'
}

onMounted(() => {
  loadFeatureFlags()
  loadData()
})

onUnmounted(() => {
  stopStatusPolling()
})
</script>

<style scoped>
.fs-page {
  min-height: 100%;
  padding: 28px;
  color: #102033;
  background:
    radial-gradient(circle at 8% 0%, rgba(20, 184, 166, 0.13), transparent 30%),
    radial-gradient(circle at 90% 16%, rgba(14, 116, 144, 0.13), transparent 28%),
    linear-gradient(180deg, #f7fbfb 0%, #eef4f5 100%);
}

.fs-hero {
  position: relative;
  overflow: hidden;
  min-height: 138px;
  padding: 30px 32px;
  border-radius: 28px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  background:
    linear-gradient(120deg, rgba(255, 255, 255, 0.96) 0%, rgba(239, 253, 250, 0.92) 54%, rgba(227, 245, 247, 0.96) 100%);
  box-shadow: 0 22px 58px rgba(15, 72, 84, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.fs-hero-orb {
  position: absolute;
  right: 260px;
  top: -84px;
  width: 210px;
  height: 210px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(20, 184, 166, 0.28), transparent 62%);
  filter: blur(2px);
}

.fs-hero-copy {
  position: relative;
  z-index: 1;
}

.fs-kicker,
.fs-board-kicker {
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
  color: #0f766e;
}

.fs-hero h2 {
  margin: 8px 0 8px;
  font-size: 32px;
  letter-spacing: -0.04em;
  color: #071b28;
}

.fs-hero p,
.fs-board-head p {
  margin: 0;
  color: #667085;
  line-height: 1.7;
}

.fs-hero-actions {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.fs-btn,
.fs-action-btn {
  border: 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-weight: 800;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.fs-btn {
  height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 14px;
}

.fs-btn:hover,
.fs-action-btn:hover {
  transform: translateY(-1px);
}

.fs-btn-primary {
  color: #fff;
  background: linear-gradient(135deg, #0f4c81 0%, #0f766e 100%);
  box-shadow: 0 14px 28px rgba(15, 118, 110, 0.24);
}

.fs-btn-ghost {
  color: #0f3d52;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(15, 76, 129, 0.12);
  box-shadow: 0 10px 20px rgba(15, 72, 84, 0.08);
}

.fs-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin: 22px 0;
}

.fs-stat-card {
  min-height: 116px;
  padding: 22px;
  border-radius: 24px;
  border: 1px solid rgba(15, 72, 84, 0.1);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 18px 40px rgba(15, 72, 84, 0.07);
  display: flex;
  align-items: center;
  gap: 16px;
}

.fs-stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 900;
  color: #0f766e;
  background: linear-gradient(180deg, #ecfeff 0%, #d9f7f2 100%);
}

.fs-stat-card.running .fs-stat-icon {
  color: #b45309;
  background: linear-gradient(180deg, #fff7ed 0%, #ffedd5 100%);
}

.fs-stat-card.failed .fs-stat-icon {
  color: #e11d48;
  background: linear-gradient(180deg, #fff1f2 0%, #ffe4e6 100%);
}

.fs-stat-card.quiet .fs-stat-icon {
  color: #64748b;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
}

.fs-stat-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.fs-stat-label {
  font-size: 13px;
  font-weight: 800;
  color: #344054;
}

.fs-stat-copy strong {
  font-size: 31px;
  line-height: 1;
  letter-spacing: -0.04em;
  color: #071b28;
}

.fs-stat-copy small {
  color: #98a2b3;
  font-size: 12px;
}

.fs-board {
  padding: 24px;
  border-radius: 28px;
  border: 1px solid rgba(15, 72, 84, 0.1);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 24px 60px rgba(15, 72, 84, 0.08);
}

.fs-board-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 20px;
}

.fs-board-head h3 {
  margin: 6px 0 5px;
  font-size: 22px;
  color: #071b28;
}

.fs-board-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.fs-board-tags span {
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #f2fbfa;
  border: 1px solid rgba(15, 118, 110, 0.12);
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.fs-task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
}

.fs-task-card {
  position: relative;
  overflow: hidden;
  padding: 20px;
  border-radius: 22px;
  border: 1px solid rgba(15, 72, 84, 0.1);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbfb 100%);
  box-shadow: 0 14px 34px rgba(15, 72, 84, 0.07);
}

.fs-task-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  background: #94a3b8;
}

.fs-task-card.is-success::before { background: linear-gradient(90deg, #0f766e, #22c55e); }
.fs-task-card.is-running::before { background: linear-gradient(90deg, #f59e0b, #06b6d4); }
.fs-task-card.is-failed::before { background: linear-gradient(90deg, #e11d48, #fb7185); }

.fs-task-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.fs-task-title-group {
  min-width: 0;
  display: flex;
  gap: 12px;
}

.fs-task-status-dot {
  width: 12px;
  height: 12px;
  margin-top: 6px;
  border-radius: 50%;
  background: #94a3b8;
  box-shadow: 0 0 0 6px rgba(148, 163, 184, 0.12);
  flex-shrink: 0;
}

.is-success .fs-task-status-dot {
  background: #16a34a;
  box-shadow: 0 0 0 6px rgba(22, 163, 74, 0.12);
}

.is-running .fs-task-status-dot {
  background: #f59e0b;
  box-shadow: 0 0 0 6px rgba(245, 158, 11, 0.16);
  animation: fsPulse 1.3s ease-in-out infinite;
}

.is-failed .fs-task-status-dot {
  background: #e11d48;
  box-shadow: 0 0 0 6px rgba(225, 29, 72, 0.12);
}

.fs-task-title-group h4 {
  margin: 0 0 5px;
  font-size: 16px;
  color: #101828;
}

.fs-task-title-group p {
  margin: 0;
  max-width: 520px;
  color: #667085;
  line-height: 1.55;
  font-size: 13px;
}

.fs-status-pill {
  height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
  background: #f1f5f9;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.fs-status-pill.is-success {
  color: #15803d;
  background: #dcfce7;
}

.fs-status-pill.is-running {
  color: #b45309;
  background: #fef3c7;
}

.fs-status-pill.is-failed {
  color: #be123c;
  background: #ffe4e6;
}

.fs-task-meta {
  display: grid;
  grid-template-columns: 1.15fr 0.8fr 1.1fr;
  gap: 10px;
  margin: 18px 0;
}

.fs-task-meta div {
  padding: 12px;
  border-radius: 15px;
  background: #f8fafc;
  border: 1px solid rgba(15, 72, 84, 0.06);
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.fs-task-meta span {
  color: #98a2b3;
  font-size: 11px;
  font-weight: 800;
}

.fs-task-meta strong {
  min-height: 19px;
  color: #1d2939;
  font-size: 13px;
  word-break: break-all;
}

.fs-task-route {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: #667085;
  font-size: 12px;
  font-weight: 800;
}

.fs-task-route i {
  height: 1px;
  flex: 1;
  background: linear-gradient(90deg, rgba(15, 118, 110, 0.18), rgba(15, 76, 129, 0.38), rgba(15, 118, 110, 0.18));
}

.fs-task-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.fs-action-btn {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  color: #0f3d52;
  background: #f8fafc;
  border: 1px solid rgba(15, 72, 84, 0.09);
}

.fs-action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.52;
  transform: none;
}

.fs-action-primary {
  color: #0f766e;
  background: #effdfb;
}

.fs-action-danger {
  color: #e11d48;
  background: #fff1f2;
}

.fs-url-assist,
.fs-schema-panel {
  margin-bottom: 18px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(15, 118, 110, 0.12);
  background:
    radial-gradient(circle at 96% 0%, rgba(20, 184, 166, 0.12), transparent 34%),
    #f8fbfb;
}

.fs-url-assist strong,
.fs-schema-head strong {
  display: block;
  margin-bottom: 4px;
  color: #102033;
  font-size: 14px;
}

.fs-url-assist span,
.fs-schema-head span,
.fs-schema-empty,
.fs-field-box p {
  color: #667085;
  font-size: 12px;
  line-height: 1.65;
}

.fs-url-row,
.fs-schema-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.fs-url-row {
  margin-top: 12px;
}

.fs-url-row .el-input {
  flex: 1;
}

.fs-schema-panel {
  margin: 8px 0 0;
  background:
    linear-gradient(135deg, rgba(239, 253, 250, 0.92), rgba(255, 255, 255, 0.96));
}

.fs-schema-panel.is-ready {
  border-color: rgba(15, 118, 110, 0.24);
}

.fs-schema-summary {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.fs-schema-summary div {
  padding: 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid rgba(15, 72, 84, 0.08);
}

.fs-schema-summary span {
  display: block;
  margin-bottom: 5px;
  color: #98a2b3;
  font-size: 11px;
  font-weight: 800;
}

.fs-schema-summary strong {
  color: #0f3d52;
  font-size: 18px;
}

.fs-field-diff-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.fs-schema-alert {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 15px;
  border: 1px solid rgba(15, 118, 110, 0.14);
  background: rgba(240, 253, 250, 0.82);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.fs-schema-alert.has-diff {
  border-color: rgba(245, 158, 11, 0.22);
  background: rgba(255, 251, 235, 0.88);
}

.fs-schema-alert strong {
  color: #0f3d52;
  font-size: 13px;
}

.fs-schema-alert span,
.fs-field-table-title span {
  color: #667085;
  font-size: 12px;
  line-height: 1.6;
}

.fs-field-box {
  min-height: 112px;
  padding: 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid rgba(15, 72, 84, 0.08);
}

.fs-field-box.added {
  border-color: rgba(22, 163, 74, 0.18);
}

.fs-field-box.removed {
  border-color: rgba(225, 29, 72, 0.16);
}

.fs-field-box-title {
  margin-bottom: 10px;
  color: #1d2939;
  font-weight: 900;
  font-size: 13px;
}

.fs-field-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.fs-schema-empty {
  margin: 12px 0 0;
}

.fs-field-table-wrap {
  margin-top: 12px;
  padding: 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid rgba(15, 72, 84, 0.08);
}

.fs-field-table-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.fs-field-table-title strong {
  color: #1d2939;
  font-size: 13px;
}

:deep(.el-dialog) {
  border-radius: 22px;
}

@keyframes fsPulse {
  0%, 100% { transform: scale(0.9); opacity: 0.72; }
  50% { transform: scale(1.1); opacity: 1; }
}

@media (max-width: 1180px) {
  .fs-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .fs-page {
    padding: 16px;
  }

  .fs-hero,
  .fs-board-head {
    flex-direction: column;
    align-items: stretch;
  }

  .fs-stat-grid,
  .fs-task-grid,
  .fs-task-meta,
  .fs-schema-summary,
  .fs-field-diff-grid {
    grid-template-columns: 1fr;
  }

  .fs-url-row,
  .fs-schema-head {
    flex-direction: column;
    align-items: stretch;
  }

  .fs-hero h2 {
    font-size: 26px;
  }
}
</style>
