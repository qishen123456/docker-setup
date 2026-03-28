<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom:20px">
      <el-col :span="6">
        <el-card class="mini-stat">
          <el-statistic title="同步配置总数" :value="syncConfigs.length">
            <template #prefix><el-icon color="#409EFF"><Coin /></el-icon></template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat">
          <el-statistic title="活跃同步" :value="syncConfigs.filter(c=>c.is_active).length" value-style="color:#67c23a" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat">
          <el-statistic title="运行中" :value="syncConfigs.filter(c=>c.last_sync_status==='running').length" value-style="color:#E6A23C" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat">
          <el-statistic title="同步失败" :value="syncConfigs.filter(c=>c.last_sync_status==='failed').length" value-style="color:#F56C6C" />
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>📋 飞书多维表格同步配置</span>
          <el-button type="primary" :icon="Plus" @click="openAdd">添加同步配置</el-button>
        </div>
      </template>

      <el-table :data="syncConfigs" v-loading="loading" stripe>
        <el-table-column prop="name" label="配置名称" min-width="150">
          <template #default="{ row }">
            <el-text strong>{{ row.name }}</el-text>
            <el-tag v-if="row.is_active" type="success" size="small" style="margin-left:6px">活跃</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        
        <el-table-column label="同步方式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.sync_mode === 'incremental' ? 'primary' : 'warning'" size="small">
              {{ row.sync_mode === 'incremental' ? '增量' : '全量' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="频率" width="120">
          <template #default="{ row }">
            {{ formatFrequency(row.sync_frequency) }}
          </template>
        </el-table-column>
        
        <el-table-column label="目标表" prop="target_table" width="120" />
        
        <el-table-column label="最后同步" width="150">
          <template #default="{ row }">
            <div v-if="row.last_sync_time">
              <el-text size="small">{{ formatTime(row.last_sync_time) }}</el-text>
            </div>
            <el-text v-else size="small" type="info">未同步</el-text>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag 
              :type="getStatusType(row.last_sync_status)" 
              size="small"
              v-loading="row.last_sync_status === 'running'"
            >
              {{ getStatusText(row.last_sync_status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="380" fixed="right">
          <template #default="{ row }">
            <div style="white-space: nowrap">
              <el-button 
                link 
                :icon="VideoPlay" 
                :loading="testingId === row.id"
                @click="testConnection(row)"
              >
                测试
              </el-button>
              <el-button 
                link 
                :icon="RefreshRight" 
                :loading="row.last_sync_status === 'running'"
                @click="startSync(row)"
                :disabled="!row.is_active || row.last_sync_status === 'running'"
              >
                同步
              </el-button>
              <el-button 
                v-if="row.is_active"
                link 
                :icon="VideoPause" 
                :loading="pausingId === row.id"
                @click="pauseSync(row)"
                :disabled="row.last_sync_status === 'running'"
              >
                暂停
              </el-button>
              <el-button 
                v-else
                link 
                :icon="VideoPlay" 
                :loading="resumingId === row.id"
                @click="resumeSync(row)"
              >
                恢复
              </el-button>
              <el-button 
                link 
                :icon="Document" 
                @click="viewLogs(row)"
              >
                日志
              </el-button>
              <el-button link :icon="Edit" @click="openEdit(row)">编辑</el-button>
              <el-popconfirm title="确认删除此同步配置？" @confirm="deleteConfig(row.id)">
                <template #reference>
                  <el-button link type="danger" :icon="Delete">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑同步配置' : '添加同步配置'" width="800px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="配置名称" prop="name">
              <el-input v-model="form.name" placeholder="例如：商用事业部销售结果表" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标表名" prop="target_table">
              <el-input v-model="form.target_table" placeholder="PostgreSQL目标表名" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入配置描述" />
        </el-form-item>

        <el-divider content-position="left">飞书多维表格配置</el-divider>
        
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="飞书 App ID" prop="app_id">
              <el-input v-model="form.app_id" placeholder="cli_xxxxxxxxxxxxxxx" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="飞书 App Secret" prop="app_secret">
              <el-input v-model="form.app_secret" type="password" placeholder="输入飞书应用密钥" show-password />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="Base ID" prop="base_id">
              <el-input v-model="form.base_id" placeholder="飞书多维表格Base ID" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Table ID" prop="table_id">
              <el-input v-model="form.table_id" placeholder="飞书多维表格Table ID" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="View ID">
              <el-input v-model="form.view_id" placeholder="可选，视图ID" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="飞书链接自动解析">
              <el-input 
                v-model="feishuUrl" 
                type="textarea" 
                :rows="2"
                placeholder="粘贴飞书多维表格链接，系统将自动解析Base ID和Table ID"
                @blur="handleParseFeishuUrl"
              >
                <template #append>
                  <el-button 
                    type="primary" 
                    :icon="Link" 
                    @click="handleParseFeishuUrl"
                    :loading="parsingUrl"
                  >
                    解析链接
                  </el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">同步配置</el-divider>
        
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="同步方式">
              <el-select v-model="form.sync_mode" style="width:100%">
                <el-option label="增量同步（推荐）" value="incremental" />
                <el-option label="全量同步" value="full" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="同步频率">
              <el-select v-model="form.sync_frequency" style="width:100%" placeholder="选择同步频率">
                <el-option label="每5分钟" :value="5" />
                <el-option label="每10分钟" :value="10" />
                <el-option label="每15分钟" :value="15" />
                <el-option label="每30分钟" :value="30" />
                <el-option label="每1小时" :value="60" />
                <el-option label="每2小时" :value="120" />
                <el-option label="每4小时" :value="240" />
                <el-option label="每8小时" :value="480" />
                <el-option label="每12小时" :value="720" />
                <el-option label="每24小时" :value="1440" />
                <el-option label="自定义" :value="0" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="form.sync_frequency === 0">
            <el-form-item label="自定义频率">
              <el-input-number 
                v-model="customFrequency" 
                :min="1" 
                :max="1440"
                placeholder="分钟"
                style="width:100%"
              >
                <template #append>分钟</template>
              </el-input-number>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="启用状态">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      
      <template #footer>
        <div style="text-align: right">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 日志查看弹窗 -->
    <el-dialog v-model="logDialogVisible" :title="`日志查看 - ${currentConfig?.name || ''}`" width="80%" top="5vh">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>日志查看 - {{ currentConfig?.name || '' }}</span>
          <div>
            <el-button size="small" @click="refreshLogs" :loading="loadingLogs">
              <el-icon><RefreshRight /></el-icon>
              刷新
            </el-button>
            <el-popconfirm title="确认清空此配置的日志？" @confirm="clearLogs">
              <template #reference>
                <el-button size="small" type="danger">
                  <el-icon><Delete /></el-icon>
                  清空
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </template>
      
      <div style="height: 60vh; overflow-y: auto;">
        <el-timeline>
          <el-timeline-item
            v-for="log in logs"
            :key="log.timestamp"
            :timestamp="log.timestamp"
            :type="getLogType(log.level)"
            placement="top"
          >
            <div style="margin-bottom: 8px;">
              <el-tag :type="getLogLevelType(log.level)" size="small" style="margin-right: 8px;">
                {{ log.level }}
              </el-tag>
              <span>{{ log.message }}</span>
            </div>
            <div v-if="log.record_count || log.page_count" style="font-size: 12px; color: #909399; margin-top: 4px;">
              <span v-if="log.record_count">记录数: {{ log.record_count }}</span>
              <span v-if="log.page_count" style="margin-left: 8px;">页数: {{ log.page_count }}</span>
            </div>
          </el-timeline-item>
        </el-timeline>
        
        <div v-if="logs.length === 0" style="text-align: center; padding: 40px; color: #909399;">
          暂无日志记录
        </div>
      </div>
      
      <template #footer>
        <div style="text-align: right;">
          <el-button @click="logDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete, RefreshRight, VideoPlay, VideoPause, Link, Document } from '@element-plus/icons-vue'
import { 
  getFeishuSyncConfigs, 
  createFeishuSyncConfig, 
  updateFeishuSyncConfig, 
  deleteFeishuSyncConfig,
  startFeishuSync,
  pauseFeishuSync,
  resumeFeishuSync,
  testFeishuConnection,
  parseFeishuUrl,
  getFeishuSyncLogs,
  clearFeishuSyncLogs
} from '../api/index.js'

const syncConfigs = ref([])
const loading = ref(false)
const saving = ref(false)
const testingId = ref(null)
const pausingId = ref(null)
const resumingId = ref(null)
const parsingUrl = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const feishuUrl = ref('')

// 日志相关
const logDialogVisible = ref(false)
const currentConfig = ref(null)
const logs = ref([])
const loadingLogs = ref(false)

const defaultForm = () => ({
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
const customFrequency = ref(30)

const rules = {
  name: [{ required: true, message: '请输入配置名称' }],
  target_table: [{ required: true, message: '请输入目标表名' }],
  app_id: [{ required: true, message: '请输入飞书App ID' }],
  app_secret: [{ required: true, message: '请输入飞书App Secret' }],
  base_id: [{ required: true, message: '请输入Base ID' }],
  table_id: [{ required: true, message: '请输入Table ID' }],
  sync_frequency: [{ 
    required: true, 
    validator: (rule, value, callback) => {
      if (value === 0 && (!customFrequency.value || customFrequency.value < 1)) {
        callback(new Error('请输入有效的自定义频率'))
      } else {
        callback()
      }
    }
  }]
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await getFeishuSyncConfigs()
    syncConfigs.value = data.sync_configs || []
  } finally {
    loading.value = false
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
  
  // 处理自定义频率显示
  const frequency = parseInt(row.sync_frequency)
  const predefinedFrequencies = [5, 10, 15, 30, 60, 120, 240, 480, 720, 1440]
  if (predefinedFrequencies.includes(frequency)) {
    form.value.sync_frequency = frequency
    customFrequency.value = 30
  } else {
    form.value.sync_frequency = 0
    customFrequency.value = frequency
  }
  
  dialogVisible.value = true
}

const resetForm = () => {
  formRef.value?.resetFields()
}

const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    saving.value = true
    
    // 处理自定义频率
    const formData = { ...form.value }
    if (form.value.sync_frequency === 0) {
      formData.sync_frequency = customFrequency.value
    }
    
    if (isEdit.value) {
      await updateFeishuSyncConfig(form.value.id, formData)
      ElMessage.success('同步配置更新成功')
    } else {
      await createFeishuSyncConfig(formData)
      ElMessage.success('同步配置创建成功')
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
    ElMessage.success('同步配置删除成功')
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '删除失败')
  }
}

const startSync = async (row) => {
  try {
    await startFeishuSync(row.id)
    ElMessage.success(`已启动同步任务: ${row.name}`)
    // 刷新状态
    setTimeout(loadData, 2000)
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '启动同步失败')
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
    
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.error)
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '连接测试失败')
  } finally {
    testingId.value = null
  }
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  return new Date(timeStr).toLocaleString('zh-CN')
}

const formatFrequency = (frequency) => {
  const freq = parseInt(frequency)
  const predefinedFrequencies = {
    5: '每5分钟',
    10: '每10分钟',
    15: '每15分钟',
    30: '每30分钟',
    60: '每1小时',
    120: '每2小时',
    240: '每4小时',
    480: '每8小时',
    720: '每12小时',
    1440: '每24小时'
  }
  
  return predefinedFrequencies[freq] || `每${freq}分钟`
}

const getStatusType = (status) => {
  const types = {
    'pending': 'info',
    'running': 'warning',
    'success': 'success',
    'failed': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    'pending': '待同步',
    'running': '运行中',
    'success': '同步成功',
    'failed': '同步失败'
  }
  return texts[status] || '未知'
}

const handleParseFeishuUrl = async () => {
  if (!feishuUrl.value.trim()) {
    ElMessage.warning('请输入飞书链接')
    return
  }
  
  parsingUrl.value = true
  
  try {
    // 使用API封装调用解析接口
    const result = await parseFeishuUrl(feishuUrl.value.trim())
    
    if (result.success) {
      // 自动填充解析结果
      form.value.base_id = result.parsed.base_id
      form.value.table_id = result.parsed.table_id
      form.value.view_id = result.parsed.view_id || ''
      
      ElMessage.success('飞书链接解析成功！')
      feishuUrl.value = '' // 清空链接输入框
    } else {
      ElMessage.error(result.error || '链接解析失败')
    }
  } catch (error) {
    console.error('解析飞书链接失败:', error)
    ElMessage.error('链接解析失败，请检查链接格式')
  } finally {
    parsingUrl.value = false
  }
}

const pauseSync = async (row) => {
  try {
    pausingId.value = row.id
    await pauseFeishuSync(row.id)
    ElMessage.success(`同步配置 "${row.name}" 已暂停`)
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '暂停失败')
  } finally {
    pausingId.value = null
  }
}

const resumeSync = async (row) => {
  try {
    resumingId.value = row.id
    await resumeFeishuSync(row.id)
    ElMessage.success(`同步配置 "${row.name}" 已恢复`)
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
    const response = await getFeishuSyncLogs(currentConfig.value.id, 100)
    logs.value = response.logs || []
  } catch (error) {
    ElMessage.error('加载日志失败')
    logs.value = []
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
    ElMessage.success('日志已清空')
    logs.value = []
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '清空日志失败')
  }
}

const getLogType = (level) => {
  const types = {
    'ERROR': 'danger',
    'SUCCESS': 'success',
    'INFO': 'primary',
    'WARNING': 'warning'
  }
  return types[level] || 'info'
}

const getLogLevelType = (level) => {
  const types = {
    'ERROR': 'danger',
    'SUCCESS': 'success',
    'INFO': 'primary',
    'WARNING': 'warning'
  }
  return types[level] || 'info'
}

onMounted(() => {
  loadData()
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
