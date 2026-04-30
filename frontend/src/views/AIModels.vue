<template>
  <div class="ai-models-page" v-loading="loading">
    <!-- 统计栏 -->
    <div class="aim-stat-bar">
      <div class="aim-stat-item">
        <span class="aim-stat-value">{{ channels.length }}</span>
        <span class="aim-stat-label">供应商通道</span>
      </div>
      <div class="aim-stat-sep"></div>
      <div class="aim-stat-item">
        <span class="aim-stat-value">{{ models.length }}</span>
        <span class="aim-stat-label">模型总数</span>
      </div>
      <div class="aim-stat-sep"></div>
      <div class="aim-stat-item">
        <span class="aim-stat-value aim-stat-active">{{ models.filter(m => m.is_active).length }}</span>
        <span class="aim-stat-label">已启用</span>
      </div>
      <div class="aim-stat-sep"></div>
      <div class="aim-stat-item">
        <span class="aim-stat-value aim-stat-default">{{ defaultModelName || '未设置' }}</span>
        <span class="aim-stat-label">默认模型</span>
      </div>
      <div class="aim-stat-spacer"></div>
      <el-button round @click="openAddChannel">+ 新建通道</el-button>
      <el-button type="primary" :icon="Plus" round @click="openAddModel">添加模型</el-button>
    </div>

    <!-- Channel 通道卡片 -->
    <div class="aim-channel-grid">
      <div
        v-for="ch in channels"
        :key="ch.key"
        class="aim-channel-card"
        :class="{ 'aim-channel-expanded': expandedChannel === ch.key }"
      >
        <!-- Channel Header -->
        <div class="aim-channel-head" @click="toggleChannel(ch.key)">
          <div class="aim-channel-icon">{{ providerEmoji(ch.provider) }}</div>
          <div class="aim-channel-info">
            <div class="aim-channel-name">{{ providerLabel(ch.provider) }}</div>
            <div class="aim-channel-url">{{ ch.base_url }}</div>
          </div>
          <div class="aim-channel-badges">
            <span class="aim-channel-count">{{ ch.models.length }} 模型</span>
            <span v-if="ch.models.some(m => m.is_active)" class="aim-channel-status aim-channel-online">在线</span>
            <span v-else class="aim-channel-status aim-channel-offline">离线</span>
          </div>
          <div class="aim-channel-actions" @click.stop>
            <el-tooltip content="测试通道连接" placement="top" :show-after="300">
              <el-button
                size="small"
                circle
                :loading="channelTesting === ch.key"
                :type="channelTestResult[ch.key] === 'success' ? 'success' : channelTestResult[ch.key] === 'error' ? 'danger' : ''"
                @click="testChannel(ch)"
              >
                <template v-if="!channelTesting || channelTesting !== ch.key">
                  <span v-if="channelTestResult[ch.key] === 'success'">✓</span>
                  <span v-else-if="channelTestResult[ch.key] === 'error'">✗</span>
                  <span v-else>⚡</span>
                </template>
              </el-button>
            </el-tooltip>
            <el-tooltip content="编辑通道 Key/URL" placement="top" :show-after="300">
              <el-button size="small" circle :icon="Edit" @click="openEditChannel(ch)" />
            </el-tooltip>
          </div>
          <div class="aim-channel-expand-arrow" :class="{ 'is-expanded': expandedChannel === ch.key }">
            <el-icon><ArrowDown /></el-icon>
          </div>
        </div>

        <!-- Channel Body: Model List -->
        <transition name="aim-expand">
          <div v-if="expandedChannel === ch.key" class="aim-channel-body">
            <div class="aim-channel-key-row">
              <span class="aim-channel-key-label">API Key</span>
              <span class="aim-channel-key-value">{{ ch.apiKeyMasked }}</span>
              <span class="aim-channel-key-label" style="margin-left: 16px">Endpoint</span>
              <span class="aim-channel-key-value aim-channel-key-mono">{{ ch.base_url }}</span>
            </div>

            <div class="aim-model-list">
              <div
                v-for="model in ch.models"
                :key="model.id"
                class="aim-model-card"
                :class="{
                  'aim-model-inactive': !model.is_active,
                  'aim-model-default': model.is_default
                }"
              >
                <div class="aim-model-top">
                  <div class="aim-model-name-row">
                    <span class="aim-model-name">{{ model.name }}</span>
                    <el-tag v-if="model.is_default" type="warning" size="small" effect="plain" round>默认</el-tag>
                    <el-tag v-if="!model.is_active" type="info" size="small" effect="plain" round>禁用</el-tag>
                  </div>
                  <div class="aim-model-id">{{ model.model }}</div>
                </div>

                <div class="aim-model-actions">
                  <el-button
                    size="small"
                    round
                    :loading="testingId === model.id"
                    :type="testResults[model.id] === 'success' ? 'success' : testResults[model.id] === 'error' ? 'danger' : ''"
                    @click="testModel(model)"
                  >
                    <template v-if="testResults[model.id] === 'success'">✓ 通过</template>
                    <template v-else-if="testResults[model.id] === 'error'">✗ 失败</template>
                    <template v-else>测试</template>
                  </el-button>
                  <el-button v-if="!model.is_default && model.is_active" size="small" round @click="setDefault(model)">设默认</el-button>
                  <el-button size="small" round :icon="Edit" @click="openEditModel(model)">编辑</el-button>
                  <el-popconfirm title="确认删除此模型？" @confirm="deleteModel(model.id)">
                    <template #reference>
                      <el-button size="small" round type="danger" plain :icon="Delete" />
                    </template>
                  </el-popconfirm>
                </div>
              </div>
            </div>

            <div class="aim-channel-add-model">
              <el-button text type="primary" @click="openAddModelInChannel(ch)">
                + 在此通道下添加模型
              </el-button>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <!-- 通道编辑弹窗 -->
    <el-dialog v-model="channelDialogVisible" :title="channelDialogIsNew ? '新建供应商通道' : '编辑通道配置'" width="560px" @close="resetChannelForm">
      <el-form ref="channelFormRef" :model="channelForm" :rules="channelRules" label-width="90px">
        <el-form-item label="供应商" prop="provider">
          <el-select v-model="channelForm.provider" style="width:100%" @change="onChannelProviderChange" allow-create filterable :disabled="!channelDialogIsNew && channelForm._existingProvider">
            <el-option label="dashscope（阿里通义）" value="dashscope" />
            <el-option label="deepseek" value="deepseek" />
            <el-option label="openai" value="openai" />
            <el-option label="ollama（本地）" value="ollama" />
            <el-option label="custom（自定义）" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="API 地址" prop="base_url">
          <el-input v-model="channelForm.base_url" placeholder="https://api.example.com/v1">
            <template #prepend>URL</template>
          </el-input>
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="channelForm.api_key" type="password" show-password placeholder="将应用到此通道下所有模型" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="channelSaving" @click="submitChannelForm">
          {{ channelDialogIsNew ? '创建通道' : '保存通道' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 模型编辑弹窗 -->
    <el-dialog v-model="modelDialogVisible" :title="modelDialogIsEdit ? '编辑模型' : '添加模型'" width="560px" @close="resetModelForm">
      <el-form ref="modelFormRef" :model="modelForm" :rules="modelRules" label-width="90px">
        <el-form-item label="所属通道" prop="provider">
          <el-select v-model="modelForm.provider" style="width:100%" @change="onModelProviderChange" allow-create filterable>
            <el-option
              v-for="ch in channels"
              :key="ch.provider"
              :label="providerLabel(ch.provider)"
              :value="ch.provider"
            />
            <el-option label="dashscope（阿里通义）" value="dashscope" />
            <el-option label="deepseek" value="deepseek" />
            <el-option label="openai" value="openai" />
            <el-option label="ollama（本地）" value="ollama" />
            <el-option label="custom（自定义）" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" prop="name">
          <el-input v-model="modelForm.name" placeholder="自定义名称，如：DeepSeek V3" />
        </el-form-item>
        <el-form-item label="模型 ID" prop="model">
          <el-input v-model="modelForm.model" placeholder="如：qwen-max / deepseek-chat / gpt-4" />
        </el-form-item>
        <el-form-item label="API 地址" prop="base_url">
          <el-input v-model="modelForm.base_url" placeholder="继承自通道，可单独覆盖">
            <template #prepend>URL</template>
          </el-input>
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="modelForm.api_key" type="password" show-password placeholder="留空则继承通道 Key" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="启用"><el-switch v-model="modelForm.is_active" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设为默认"><el-switch v-model="modelForm.is_default" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="modelDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="modelSaving" @click="submitModelForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete, ArrowDown } from '@element-plus/icons-vue'
import { getAIModels, createAIModel, updateAIModel, deleteAIModel, testAIModel, setDefaultAIModel } from '../api/index.js'

const models = ref([])
const loading = ref(false)
const testingId = ref(null)
const testResults = reactive({})
const expandedChannel = ref(null)

// Channel test
const channelTesting = ref(null)
const channelTestResult = reactive({})

// Channel dialog
const channelDialogVisible = ref(false)
const channelDialogIsNew = ref(true)
const channelSaving = ref(false)
const channelFormRef = ref()
const channelForm = ref({ provider: 'dashscope', base_url: '', api_key: '', _existingProvider: false, _modelIds: [] })
const channelRules = {
  provider: [{ required: true, message: '请选择供应商' }],
  base_url: [{ required: true, message: '请输入 API 地址' }],
}

// Model dialog
const modelDialogVisible = ref(false)
const modelDialogIsEdit = ref(false)
const modelSaving = ref(false)
const modelFormRef = ref()
const modelForm = ref({ name: '', provider: 'dashscope', model: '', base_url: '', api_key: '', is_active: true, is_default: false })
const modelRules = {
  name: [{ required: true, message: '请输入模型名称' }],
  model: [{ required: true, message: '请输入模型 ID' }],
  provider: [{ required: true, message: '请选择所属通道' }],
  base_url: [{ required: true, message: '请输入 API 地址' }],
}

const PROVIDER_URLS = {
  dashscope: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  deepseek: 'https://api.deepseek.com/v1',
  openai: 'https://api.openai.com/v1',
  ollama: 'http://localhost:11434/v1',
  custom: ''
}

// Computed: group models into channels
const channels = computed(() => {
  const map = {}
  for (const m of models.value) {
    const p = m.provider || 'custom'
    if (!map[p]) {
      map[p] = {
        key: p,
        provider: p,
        base_url: m.base_url || '',
        apiKeyMasked: m.api_key || '***已保存***',
        models: []
      }
    }
    map[p].models.push(m)
  }
  return Object.values(map)
})

const defaultModelName = computed(() => {
  const m = models.value.find(m => m.is_default)
  return m ? m.name : ''
})

const providerLabel = (p) => ({
  dashscope: '阿里通义 · DashScope',
  deepseek: 'DeepSeek',
  openai: 'OpenAI',
  ollama: 'Ollama (本地)',
  custom: '自定义 API'
}[p] || p)

const providerEmoji = (p) => ({
  dashscope: '🌐',
  deepseek: '🐋',
  openai: '🤖',
  ollama: '💻',
  custom: '⚙️'
}[p] || '🔌')

const toggleChannel = (key) => {
  expandedChannel.value = expandedChannel.value === key ? null : key
}

// Load data
const loadData = async () => {
  loading.value = true
  try {
    const data = await getAIModels()
    models.value = data.models || []
    // Auto-expand first channel
    if (channels.value.length > 0 && !expandedChannel.value) {
      expandedChannel.value = channels.value[0].key
    }
  } finally {
    loading.value = false
  }
}

// Channel operations
const openAddChannel = () => {
  channelDialogIsNew.value = true
  channelForm.value = { provider: 'custom', base_url: '', api_key: '', _existingProvider: false, _modelIds: [] }
  channelDialogVisible.value = true
}

const openEditChannel = (ch) => {
  channelDialogIsNew.value = false
  channelForm.value = {
    provider: ch.provider,
    base_url: ch.base_url,
    api_key: '',
    _existingProvider: true,
    _modelIds: ch.models.map(m => m.id)
  }
  channelDialogVisible.value = true
}

const onChannelProviderChange = (p) => {
  channelForm.value.base_url = PROVIDER_URLS[p] || channelForm.value.base_url || ''
}

const resetChannelForm = () => channelFormRef.value?.resetFields()

const submitChannelForm = async () => {
  await channelFormRef.value.validate()
  channelSaving.value = true
  try {
    if (channelDialogIsNew.value) {
      // Create a placeholder model for this new channel
      await createAIModel({
        name: `${providerLabel(channelForm.value.provider)} 默认`,
        provider: channelForm.value.provider,
        model: channelForm.value.provider === 'dashscope' ? 'qwen-max' : 'default',
        base_url: channelForm.value.base_url,
        api_key: channelForm.value.api_key || 'placeholder',
        is_active: true,
        is_default: false
      })
      ElMessage({ message: '通道已创建', type: 'success', customClass: 'sa-toast-modern' })
    } else {
      // Update all models in this channel with new key/url
      const updates = {}
      if (channelForm.value.base_url) updates.base_url = channelForm.value.base_url
      if (channelForm.value.api_key) updates.api_key = channelForm.value.api_key

      for (const modelId of channelForm.value._modelIds) {
        await updateAIModel(modelId, { ...updates, provider: channelForm.value.provider })
      }
      ElMessage({ message: '通道配置已更新，已应用到所有模型', type: 'success', customClass: 'sa-toast-modern' })
    }
    channelDialogVisible.value = false
    loadData()
  } finally {
    channelSaving.value = false
  }
}

const testChannel = async (ch) => {
  const firstActive = ch.models.find(m => m.is_active) || ch.models[0]
  if (!firstActive) return
  channelTesting.value = ch.key
  channelTestResult[ch.key] = null
  try {
    const r = await testAIModel(firstActive.id)
    channelTestResult[ch.key] = 'success'
    ElMessage({ message: `通道连接正常（${r.response_time}ms）`, type: 'success', customClass: 'sa-toast-modern' })
  } catch {
    channelTestResult[ch.key] = 'error'
    ElMessage({ message: '通道连接失败，请检查 Key 和 URL', type: 'error', customClass: 'sa-toast-modern' })
  } finally {
    channelTesting.value = null
  }
}

// Model operations
const openAddModel = () => {
  modelDialogIsEdit.value = false
  const firstChannel = channels.value[0]
  modelForm.value = {
    name: '', provider: firstChannel?.provider || 'dashscope', model: '',
    base_url: firstChannel?.base_url || PROVIDER_URLS.dashscope,
    api_key: '', is_active: true, is_default: false
  }
  modelDialogVisible.value = true
}

const openAddModelInChannel = (ch) => {
  modelDialogIsEdit.value = false
  modelForm.value = {
    name: '', provider: ch.provider, model: '',
    base_url: ch.base_url, api_key: '',
    is_active: true, is_default: false
  }
  modelDialogVisible.value = true
}

const openEditModel = (row) => {
  modelDialogIsEdit.value = true
  modelForm.value = { ...row, api_key: '' }
  modelDialogVisible.value = true
}

const onModelProviderChange = (p) => {
  const ch = channels.value.find(c => c.provider === p)
  if (ch) {
    modelForm.value.base_url = ch.base_url
  } else {
    modelForm.value.base_url = PROVIDER_URLS[p] || ''
  }
}

const resetModelForm = () => modelFormRef.value?.resetFields()

const submitModelForm = async () => {
  await modelFormRef.value.validate()
  modelSaving.value = true
  try {
    const payload = { ...modelForm.value }
    // If no api_key provided for new model, it's required
    if (!modelDialogIsEdit.value && !payload.api_key) {
      // Try to inherit from channel
      const ch = channels.value.find(c => c.provider === payload.provider)
      if (!ch) {
        ElMessage.error('新模型必须提供 API Key 或选择已有通道')
        return
      }
    }
    if (modelDialogIsEdit.value) {
      await updateAIModel(payload.id, payload)
      ElMessage({ message: '模型已更新', type: 'success', customClass: 'sa-toast-modern' })
    } else {
      await createAIModel(payload)
      ElMessage({ message: '模型已添加', type: 'success', customClass: 'sa-toast-modern' })
    }
    modelDialogVisible.value = false
    loadData()
  } finally {
    modelSaving.value = false
  }
}

const testModel = async (row) => {
  testingId.value = row.id
  testResults[row.id] = null
  try {
    const r = await testAIModel(row.id)
    testResults[row.id] = 'success'
    ElMessage({ message: `✓ ${row.name} 连接正常（${r.response_time}ms）`, type: 'success', customClass: 'sa-toast-modern' })
  } catch {
    testResults[row.id] = 'error'
    ElMessage({ message: `✗ ${row.name} 连接失败`, type: 'error', customClass: 'sa-toast-modern' })
  } finally {
    testingId.value = null
  }
}

const deleteModel = async (id) => {
  await deleteAIModel(id)
  ElMessage({ message: '已删除', type: 'success', customClass: 'sa-toast-modern' })
  loadData()
}

const setDefault = async (row) => {
  await setDefaultAIModel(row.id)
  ElMessage({ message: `${row.name} 已设为默认模型`, type: 'success', customClass: 'sa-toast-modern' })
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.ai-models-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 4px 0 32px;
}

/* 统计栏 */
.aim-stat-bar {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 14px 22px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(29, 33, 41, 0.06);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
  margin-bottom: 20px;
}

.aim-stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.aim-stat-value {
  font-size: 17px;
  font-weight: 700;
  color: #1d2129;
}

.aim-stat-active { color: #00b42a; }
.aim-stat-default { font-size: 12px; font-weight: 600; color: #e6a23c; }

.aim-stat-label {
  font-size: 10px;
  color: #86909c;
}

.aim-stat-sep {
  width: 1px;
  height: 26px;
  background: rgba(29, 33, 41, 0.08);
}

.aim-stat-spacer { flex: 1; }

/* Channel Grid */
.aim-channel-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.aim-channel-card {
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(29, 33, 41, 0.06);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.aim-channel-card:hover {
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.06);
}

.aim-channel-expanded {
  border-color: rgba(22, 93, 255, 0.12);
  box-shadow: 0 4px 20px rgba(22, 93, 255, 0.06);
}

/* Channel Header */
.aim-channel-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  cursor: pointer;
  transition: background 0.2s ease;
  user-select: none;
}

.aim-channel-head:hover {
  background: rgba(247, 248, 250, 0.6);
}

.aim-channel-icon {
  font-size: 22px;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 13px;
  background: #fff;
  border: 1px solid rgba(29, 33, 41, 0.06);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
  flex-shrink: 0;
}

.aim-channel-info {
  flex: 1;
  min-width: 0;
}

.aim-channel-name {
  font-size: 14px;
  font-weight: 700;
  color: #1d2129;
}

.aim-channel-url {
  margin-top: 2px;
  font-size: 11px;
  color: #86909c;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.aim-channel-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.aim-channel-count {
  font-size: 11px;
  font-weight: 600;
  color: #4e5969;
  background: #f2f3f5;
  padding: 2px 8px;
  border-radius: 999px;
}

.aim-channel-status {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}

.aim-channel-online {
  background: #e8ffea;
  color: #00b42a;
}

.aim-channel-offline {
  background: #f2f3f5;
  color: #86909c;
}

.aim-channel-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.aim-channel-expand-arrow {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  color: #86909c;
  flex-shrink: 0;
}

.aim-channel-expand-arrow.is-expanded {
  transform: rotate(180deg);
}

/* Channel Body */
.aim-channel-body {
  padding: 0 20px 16px;
  border-top: 1px solid rgba(229, 230, 235, 0.5);
}

.aim-channel-key-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin: 12px 0;
  border-radius: 10px;
  background: rgba(247, 248, 250, 0.7);
  font-size: 11px;
  flex-wrap: wrap;
}

.aim-channel-key-label {
  color: #86909c;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.aim-channel-key-value {
  color: #4e5969;
  font-weight: 500;
}

.aim-channel-key-mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 10px;
}

/* Model List */
.aim-model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.aim-model-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(29, 33, 41, 0.05);
  background: #fff;
  transition: all 0.2s ease;
}

.aim-model-card:hover {
  border-color: rgba(22, 93, 255, 0.1);
  box-shadow: 0 3px 12px rgba(22, 93, 255, 0.05);
  transform: translateY(-1px);
}

.aim-model-inactive { opacity: 0.5; }

.aim-model-default {
  border-color: rgba(230, 162, 60, 0.16);
  background: linear-gradient(180deg, #fffef8 0%, #fff 100%);
}

.aim-model-top {
  min-width: 0;
  flex: 1;
}

.aim-model-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.aim-model-name {
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
}

.aim-model-id {
  margin-top: 2px;
  font-size: 10px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: #4e5969;
  background: #f2f3f5;
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
}

.aim-model-actions {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}

.aim-channel-add-model {
  padding: 8px 0 0;
  text-align: center;
}

/* Expand transition */
.aim-expand-enter-active,
.aim-expand-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.aim-expand-enter-from,
.aim-expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.aim-expand-enter-to,
.aim-expand-leave-from {
  opacity: 1;
  max-height: 1200px;
}
</style>
