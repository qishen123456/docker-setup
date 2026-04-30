<template>
  <div class="cs-page" v-loading="loading">
    <div class="cs-layout">
      <!-- ===== LEFT: Channel List ===== -->
      <aside class="cs-sidebar">
        <div class="cs-sidebar-scroll">
          <div
            v-for="ch in channels" :key="ch.key"
            class="cs-ch-item"
            :class="{ 'is-active': selectedChannelKey === ch.key }"
            @click="selectChannel(ch.key)"
          >
            <span class="cs-ch-icon">{{ providerEmoji(ch.provider) }}</span>
            <span class="cs-ch-name">{{ channelDisplayName(ch) }}</span>
            <el-switch
              v-model="ch._hasActive"
              size="small"
              class="cs-ch-switch"
              @click.stop
              @change="toggleChannelActive(ch, $event)"
            />
          </div>
        </div>
        <div class="cs-sidebar-footer">
          <el-button class="cs-add-btn" @click="openAddChannel">
            <el-icon><Plus /></el-icon>
            <span>添加</span>
          </el-button>
        </div>
      </aside>

      <!-- ===== RIGHT: Channel Detail ===== -->
      <main class="cs-main" v-if="activeChannel">
        <!-- Provider Header -->
        <div class="cs-provider-header">
          <div class="cs-provider-icon">{{ providerEmoji(activeChannel.provider) }}</div>
          <div class="cs-provider-title">{{ channelDisplayName(activeChannel) }}</div>
          <span class="cs-provider-url-sub">{{ activeChannel.base_url }}</span>
        </div>

        <!-- API Key Section -->
        <div class="cs-section">
          <div class="cs-section-label">API 密钥</div>
          <div class="cs-key-row">
            <el-input
              v-model="editableApiKey"
              :type="showApiKey ? 'text' : 'password'"
              placeholder="sk-..."
              class="cs-key-input"
              @change="onApiKeyChange"
            />
            <el-button text @click="showApiKey = !showApiKey">
              <el-icon><View v-if="!showApiKey" /><Hide v-else /></el-icon>
            </el-button>
            <el-button
              round size="small"
              :loading="channelTesting === activeChannel.key"
              @click="testChannel(activeChannel)"
            >检 测</el-button>
          </div>
        </div>

        <!-- API URL Section -->
        <div class="cs-section">
          <div class="cs-section-label">API 地址</div>
          <div class="cs-url-row">
            <el-input v-model="editableBaseUrl" class="cs-url-input" @change="onBaseUrlChange" />
          </div>
        </div>

        <!-- Models Section -->
        <div class="cs-models-header">
          <span class="cs-models-label">模型</span>
          <span class="cs-models-count">{{ activeChannel.models.length }}</span>
          <div class="cs-models-spacer"></div>
          <el-button text size="small" @click="testAllModels(activeChannel)">全部检测</el-button>
        </div>

        <div class="cs-model-list">
          <div
            v-for="model in activeChannel.models"
            :key="model.id"
            class="cs-model-row"
            :class="{ 'is-default': model.is_default, 'is-inactive': !model.is_active }"
          >
            <span class="cs-model-emoji">{{ providerEmoji(activeChannel.provider) }}</span>
            <span class="cs-model-name">{{ model.name || model.model }}</span>
            <el-tag v-if="model.is_default" type="warning" size="small" round effect="plain">默认</el-tag>
            <el-tag v-if="!model.is_active" type="info" size="small" round effect="plain">禁用</el-tag>
            <span
              v-if="testResults[model.id]"
              class="cs-model-dot"
              :class="testResults[model.id] === 'success' ? 'is-ok' : 'is-err'"
            ></span>
            <div class="cs-model-spacer"></div>
            <span class="cs-model-id">{{ model.model }}</span>
            <el-button
              v-if="!model.is_default && model.is_active"
              text size="small" @click="setDefault(model)"
            >设默认</el-button>
            <el-button
              text size="small"
              :loading="testingId === model.id"
              @click="testModel(model)"
            >测试</el-button>
            <el-button text size="small" @click="openEditModel(model)">
              <el-icon><Setting /></el-icon>
            </el-button>
            <el-popconfirm title="确认删除此模型？" @confirm="deleteModel(model.id)">
              <template #reference>
                <el-button text size="small" class="cs-model-del">—</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>

        <!-- Add Model Row -->
        <div class="cs-add-model-bar">
          <el-button text type="primary" @click="openAddModelInChannel(activeChannel)">
            <el-icon><Plus /></el-icon> 添加模型
          </el-button>
        </div>
      </main>

      <!-- Empty State -->
      <main class="cs-main cs-empty" v-else>
        <div class="cs-empty-text">请在左侧选择或添加一个通道</div>
      </main>
    </div>

    <!-- ===== Channel Dialog ===== -->
    <el-dialog v-model="channelDialogVisible" :title="channelDialogIsNew ? '新建供应商通道' : '编辑通道'" width="480px" @close="resetChannelForm">
      <el-form ref="channelFormRef" :model="channelForm" :rules="channelRules" label-width="80px">
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
          <el-input v-model="channelForm.base_url" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="channelForm.api_key" type="password" show-password placeholder="将应用到此通道下所有模型" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="channelSaving" @click="submitChannelForm">
          {{ channelDialogIsNew ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== Model Dialog ===== -->
    <el-dialog v-model="modelDialogVisible" :title="modelDialogIsEdit ? '编辑模型' : '添加模型'" width="480px" @close="resetModelForm">
      <el-form ref="modelFormRef" :model="modelForm" :rules="modelRules" label-width="80px">
        <el-form-item label="模型名称" prop="name">
          <el-input v-model="modelForm.name" placeholder="自定义名称，如 DeepSeek V3" />
        </el-form-item>
        <el-form-item label="模型 ID" prop="model">
          <el-input v-model="modelForm.model" placeholder="如 qwen-max / deepseek-chat / gpt-4" />
        </el-form-item>
        <template v-if="modelDialogIsEdit">
          <el-form-item label="API 地址">
            <el-input v-model="modelForm.base_url" placeholder="继承自通道，可单独覆盖" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="modelForm.api_key" type="password" show-password placeholder="留空则继承通道 Key" />
          </el-form-item>
        </template>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="启用"><el-switch v-model="modelForm.is_active" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="默认"><el-switch v-model="modelForm.is_default" /></el-form-item>
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
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete, ArrowDown, Setting, View, Hide } from '@element-plus/icons-vue'
import { getAIModels, createAIModel, updateAIModel, deleteAIModel, testAIModel, setDefaultAIModel } from '../api/index.js'

const models = ref([])
const loading = ref(false)
const testingId = ref(null)
const testResults = reactive({})
const selectedChannelKey = ref(null)
const channelTesting = ref(null)
const channelTestResult = reactive({})
const showApiKey = ref(false)
const editableApiKey = ref('')
const editableBaseUrl = ref('')

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
const modelForm = ref({ name: '', provider: '', model: '', base_url: '', api_key: '', is_active: true, is_default: false })
const modelRules = {
  name: [{ required: true, message: '请输入模型名称' }],
  model: [{ required: true, message: '请输入模型 ID' }],
}

const PROVIDER_URLS = {
  dashscope: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  deepseek: 'https://api.deepseek.com/v1',
  openai: 'https://api.openai.com/v1',
  ollama: 'http://localhost:11434/v1',
  custom: ''
}

// Channel = provider + base_url (CherryStudio: one url + one key = one channel)
const channels = computed(() => {
  const map = {}
  for (const m of models.value) {
    const p = m.provider || 'custom'
    const url = m.base_url || ''
    const key = `${p}||${url}`
    if (!map[key]) {
      map[key] = {
        key, provider: p, base_url: url,
        apiKeyRaw: m.api_key || '',
        apiKeyMasked: m.api_key ? '***已保存***' : '',
        models: [],
        _hasActive: false,
      }
    }
    map[key].models.push(m)
  }
  for (const ch of Object.values(map)) {
    ch._hasActive = ch.models.some(m => m.is_active)
  }
  return Object.values(map)
})

const activeChannel = computed(() => channels.value.find(c => c.key === selectedChannelKey.value) || null)

const channelDisplayName = (ch) => {
  const label = providerLabel(ch.provider)
  // Shorten for sidebar
  const host = ch.base_url ? new URL(ch.base_url).hostname : ''
  if (host && label === '自定义 API') return host
  return label
}

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

const selectChannel = (key) => {
  selectedChannelKey.value = key
  showApiKey.value = false
  const ch = channels.value.find(c => c.key === key)
  editableApiKey.value = ch?.apiKeyRaw || ''
  editableBaseUrl.value = ch?.base_url || ''
}

// When active channel changes, sync editable fields
watch(activeChannel, (ch) => {
  if (ch) {
    editableApiKey.value = ch.apiKeyRaw || ''
    editableBaseUrl.value = ch.base_url || ''
  }
})

const toggleChannelActive = async (ch, val) => {
  for (const m of ch.models) {
    await updateAIModel(m.id, { is_active: val })
  }
  ElMessage.success(val ? '通道已启用' : '通道已禁用')
  loadData()
}

const onApiKeyChange = async () => {
  const ch = activeChannel.value
  if (!ch || !editableApiKey.value) return
  for (const m of ch.models) {
    await updateAIModel(m.id, { api_key: editableApiKey.value })
  }
  ElMessage.success('API Key 已保存')
  loadData()
}

const onBaseUrlChange = async () => {
  const ch = activeChannel.value
  if (!ch || !editableBaseUrl.value) return
  for (const m of ch.models) {
    await updateAIModel(m.id, { base_url: editableBaseUrl.value })
  }
  ElMessage.success('API 地址已保存')
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await getAIModels()
    models.value = data.models || []
    if (channels.value.length > 0 && !selectedChannelKey.value) {
      selectChannel(channels.value[0].key)
    }
  } finally { loading.value = false }
}

// Channel CRUD
const openAddChannel = () => {
  channelDialogIsNew.value = true
  channelForm.value = { provider: 'custom', base_url: '', api_key: '', _existingProvider: false, _modelIds: [] }
  channelDialogVisible.value = true
}
const onChannelProviderChange = (p) => { channelForm.value.base_url = PROVIDER_URLS[p] || channelForm.value.base_url || '' }
const resetChannelForm = () => channelFormRef.value?.resetFields()

const submitChannelForm = async () => {
  await channelFormRef.value.validate()
  channelSaving.value = true
  try {
    if (channelDialogIsNew.value) {
      await createAIModel({
        name: `${providerLabel(channelForm.value.provider)} 默认`,
        provider: channelForm.value.provider,
        model: channelForm.value.provider === 'dashscope' ? 'qwen-max' : 'default',
        base_url: channelForm.value.base_url,
        api_key: channelForm.value.api_key || 'sk-placeholder',
        is_active: true, is_default: false
      })
      ElMessage.success('通道已创建')
    } else {
      const updates = {}
      if (channelForm.value.base_url) updates.base_url = channelForm.value.base_url
      if (channelForm.value.api_key) updates.api_key = channelForm.value.api_key
      for (const id of channelForm.value._modelIds) await updateAIModel(id, updates)
      ElMessage.success('通道配置已更新')
    }
    channelDialogVisible.value = false; loadData()
  } finally { channelSaving.value = false }
}

const testChannel = async (ch) => {
  const target = ch.models.find(m => m.is_active) || ch.models[0]
  if (!target) return
  channelTesting.value = ch.key
  channelTestResult[ch.key] = null
  try {
    const r = await testAIModel(target.id)
    channelTestResult[ch.key] = 'success'
    ElMessage.success(`通道连接正常（${r.response_time}ms）`)
  } catch {
    channelTestResult[ch.key] = 'error'
    ElMessage.error('通道连接失败')
  } finally { channelTesting.value = null }
}

const testAllModels = async (ch) => {
  for (const model of ch.models) {
    testingId.value = model.id
    testResults[model.id] = null
    try {
      await testAIModel(model.id)
      testResults[model.id] = 'success'
    } catch {
      testResults[model.id] = 'error'
    }
  }
  testingId.value = null
  const ok = ch.models.filter(m => testResults[m.id] === 'success').length
  const fail = ch.models.filter(m => testResults[m.id] === 'error').length
  ElMessage.info(`检测完成：${ok} 通过，${fail} 失败`)
}

// Model CRUD
const openAddModelInChannel = (ch) => {
  modelDialogIsEdit.value = false
  modelForm.value = { name: '', provider: ch.provider, model: '', base_url: ch.base_url, api_key: '', is_active: true, is_default: false }
  modelDialogVisible.value = true
}
const openEditModel = (row) => {
  modelDialogIsEdit.value = true
  modelForm.value = { ...row, api_key: '' }
  modelDialogVisible.value = true
}
const resetModelForm = () => modelFormRef.value?.resetFields()

const submitModelForm = async () => {
  await modelFormRef.value.validate()
  modelSaving.value = true
  try {
    const payload = { ...modelForm.value }
    if (!modelDialogIsEdit.value) {
      const ch = activeChannel.value
      if (!payload.base_url && ch) payload.base_url = ch.base_url
      if (!payload.api_key && ch) payload.api_key = 'inherit-channel'
      if (!payload.provider && ch) payload.provider = ch.provider
    }
    if (modelDialogIsEdit.value) {
      await updateAIModel(payload.id, payload)
      ElMessage.success('模型已更新')
    } else {
      await createAIModel(payload)
      ElMessage.success('模型已添加')
    }
    modelDialogVisible.value = false; loadData()
  } finally { modelSaving.value = false }
}

const testModel = async (row) => {
  testingId.value = row.id; testResults[row.id] = null
  try { const r = await testAIModel(row.id); testResults[row.id] = 'success'; ElMessage.success(`✓ ${row.name}（${r.response_time}ms）`) }
  catch { testResults[row.id] = 'error'; ElMessage.error(`✗ ${row.name} 连接失败`) }
  finally { testingId.value = null }
}

const deleteModel = async (id) => {
  await deleteAIModel(id)
  ElMessage.success('已删除')
  loadData()
}
const setDefault = async (row) => { await setDefaultAIModel(row.id); ElMessage.success(`${row.name} 已设为默认`); loadData() }

onMounted(loadData)
</script>

<style scoped>
.cs-page { height: 100%; display: flex; flex-direction: column; }

.cs-layout {
  flex: 1; display: flex; min-height: 0;
  background: #f7f8fa;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(229,230,235,0.6);
}

/* ===== LEFT SIDEBAR ===== */
.cs-sidebar {
  width: 240px; min-width: 240px;
  background: #fff;
  border-right: 1px solid rgba(229,230,235,0.6);
  display: flex; flex-direction: column;
}
.cs-sidebar-scroll {
  flex: 1; overflow-y: auto; padding: 8px;
}
.cs-ch-item {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-radius: 10px;
  cursor: pointer; transition: all 0.15s ease;
  margin-bottom: 2px; user-select: none;
}
.cs-ch-item:hover { background: rgba(22,93,255,0.04); }
.cs-ch-item.is-active {
  background: rgba(22,93,255,0.08);
  box-shadow: inset 3px 0 0 #165dff;
}
.cs-ch-icon { font-size: 18px; flex-shrink: 0; width: 24px; text-align: center; }
.cs-ch-name {
  flex: 1; font-size: 13px; font-weight: 500; color: #1d2129;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cs-ch-switch { flex-shrink: 0; }

.cs-sidebar-footer {
  padding: 12px; border-top: 1px solid rgba(229,230,235,0.5);
}
.cs-add-btn {
  width: 100%; border-radius: 8px; height: 36px;
  font-size: 13px; font-weight: 500;
}

/* ===== RIGHT MAIN ===== */
.cs-main {
  flex: 1; overflow-y: auto; padding: 24px 32px;
}
.cs-empty {
  display: flex; align-items: center; justify-content: center;
}
.cs-empty-text { color: #86909c; font-size: 14px; }

/* Provider Header */
.cs-provider-header {
  text-align: center; margin-bottom: 24px;
}
.cs-provider-icon {
  font-size: 40px; margin-bottom: 8px;
}
.cs-provider-title {
  font-size: 18px; font-weight: 700; color: #1d2129;
}
.cs-provider-url-sub {
  display: block; font-size: 12px; color: #86909c; margin-top: 4px;
}

/* Sections */
.cs-section { margin-bottom: 20px; }
.cs-section-label {
  font-size: 13px; font-weight: 700; color: #1d2129;
  margin-bottom: 8px;
}

.cs-key-row { display: flex; align-items: center; gap: 8px; }
.cs-key-input { flex: 1; }
.cs-url-row { display: flex; align-items: center; gap: 8px; }
.cs-url-input { flex: 1; }

/* Models */
.cs-models-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px; padding-top: 8px;
  border-top: 1px solid rgba(229,230,235,0.5);
}
.cs-models-label { font-size: 13px; font-weight: 700; color: #1d2129; }
.cs-models-count {
  font-size: 10px; font-weight: 700; color: #fff; background: #165dff;
  min-width: 18px; height: 18px; border-radius: 999px;
  display: inline-flex; align-items: center; justify-content: center; padding: 0 5px;
}
.cs-models-spacer { flex: 1; }

.cs-model-list { display: flex; flex-direction: column; gap: 2px; }

.cs-model-row {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-radius: 10px;
  transition: background 0.15s ease;
  background: rgba(255,255,255,0.7);
}
.cs-model-row:hover { background: rgba(22,93,255,0.03); }
.cs-model-row.is-inactive { opacity: 0.4; }
.cs-model-row.is-default { background: rgba(255,250,235,0.6); }

.cs-model-emoji { font-size: 16px; flex-shrink: 0; }
.cs-model-name {
  font-size: 13px; font-weight: 600; color: #1d2129;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cs-model-id {
  font-size: 10px; color: #86909c; font-family: 'SF Mono', monospace;
  white-space: nowrap; flex-shrink: 0;
}
.cs-model-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.cs-model-dot.is-ok { background: #00b42a; }
.cs-model-dot.is-err { background: #f53f3f; }
.cs-model-spacer { flex: 1; }
.cs-model-del { color: #86909c !important; font-weight: 700; }

.cs-add-model-bar {
  padding: 8px 0; text-align: center;
  border-top: 1px solid rgba(229,230,235,0.3);
  margin-top: 4px;
}
</style>
