<template>
  <div>
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card class="mini-stat">
          <el-statistic title="同步配置总数" :value="syncConfigs.length" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat">
          <el-statistic title="活跃同步" :value="syncConfigs.filter((c) => c.is_active).length" value-style="color:#67c23a" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat">
          <el-statistic title="运行中" :value="syncConfigs.filter((c) => c.last_sync_status === 'running').length" value-style="color:#E6A23C" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat">
          <el-statistic title="同步失败" :value="syncConfigs.filter((c) => c.last_sync_status === 'failed').length" value-style="color:#F56C6C" />
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>飞书多维表格同步配置</span>
          <div style="display: flex; gap: 8px; align-items: center">
            <el-button :icon="RefreshRight" @click="loadData">刷新</el-button>
            <el-button type="primary" :icon="Plus" @click="openAdd">添加同步配置</el-button>
          </div>
        </div>
      </template>

      <el-table :data="syncConfigs" v-loading="loading" stripe>
        <el-table-column prop="name" label="配置名称" min-width="140" />
        <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
        <el-table-column prop="target_table" label="目标表" width="140" />
        <el-table-column label="频率" width="120">
          <template #default="{ row }">{{ formatFrequency(row.sync_frequency) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.last_sync_status)">{{ getStatusText(row.last_sync_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后同步" width="170">
          <template #default="{ row }">{{ formatTime(row.last_sync_time) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="420" fixed="right">
          <template #default="{ row }">
            <el-button link :icon="VideoPlay" :loading="testingId === row.id" @click="testConnection(row)">测试</el-button>
            <el-button
              link
              :icon="RefreshRight"
              :loading="row.last_sync_status === 'running'"
              :disabled="!row.is_active || row.last_sync_status === 'running'"
              @click="startSync(row)"
            >同步</el-button>
            <el-button v-if="row.is_active" link :icon="VideoPause" :loading="pausingId === row.id" @click="pauseSync(row)">暂停</el-button>
            <el-button v-else link :icon="VideoPlay" :loading="resumingId === row.id" @click="resumeSync(row)">恢复</el-button>
            <el-button link :icon="Document" @click="viewLogs(row)">日志</el-button>
            <el-button link :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除此同步配置？" @confirm="deleteConfig(row.id)">
              <template #reference>
                <el-button link type="danger" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑同步配置' : '添加同步配置'" width="760px" @close="resetForm">
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

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="logDialogVisible" :title="`日志查看 - ${currentConfig?.name || ''}`" width="80%">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>日志查看 - {{ currentConfig?.name || '' }}</span>
          <div>
            <el-button size="small" @click="refreshLogs" :loading="loadingLogs">刷新</el-button>
            <el-popconfirm title="确认清空日志？" @confirm="clearLogs">
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
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Document, Edit, Plus, RefreshRight, VideoPause, VideoPlay } from '@element-plus/icons-vue'
import {
  clearFeishuSyncLogs,
  createFeishuSyncConfig,
  deleteFeishuSyncConfig,
  getFeishuSyncConfigs,
  getFeishuSyncLogs,
  pauseFeishuSync,
  resumeFeishuSync,
  startFeishuSync,
  testFeishuConnection,
  updateFeishuSyncConfig
} from '../api/index.js'

const syncConfigs = ref([])
const loading = ref(false)
const saving = ref(false)
const testingId = ref(null)
const pausingId = ref(null)
const resumingId = ref(null)

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()

const logDialogVisible = ref(false)
const currentConfig = ref(null)
const logs = ref([])
const loadingLogs = ref(false)

let statusPollTimer = null

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

const openAdd = () => {
  isEdit.value = false
  form.value = defaultForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  form.value = { ...defaultForm(), ...row }
  dialogVisible.value = true
}

const resetForm = () => {
  formRef.value?.clearValidate?.()
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
      table_id: row.table_id
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

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  stopStatusPolling()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mini-stat {
  text-align: center;
}
</style>
