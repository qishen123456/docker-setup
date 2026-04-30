<template>
  <div class="ai-models-page" v-loading="loading">
    <!-- Channel 通道卡片列表 -->
    <div class="ch-grid">
      <div v-for="ch in channels" :key="ch.key" class="ch-card">
        <!-- Provider Header -->
        <div class="ch-head">
          <div class="ch-head-left">
            <div class="ch-icon">{{ providerEmoji(ch.provider) }}</div>
            <div class="ch-meta">
              <div class="ch-name">{{ providerLabel(ch.provider) }}</div>
              <div class="ch-url">{{ ch.base_url }}</div>
            </div>
          </div>
          <div class="ch-head-right">
            <span class="ch-badge">{{ ch.models.length }} 模型</span>
            <span
              class="ch-status"
              :class="channelTestResult[ch.key] === 'success' ? 'is-ok' : channelTestResult[ch.key] === 'error' ? 'is-err' : ch.models.some(m => m.is_active) ? 'is-ok' : 'is-off'"
            >
              <template v-if="channelTestResult[ch.key] === 'success'">✓</template>
              <template v-else-if="channelTestResult[ch.key] === 'error'">✗</template>
            </span>
            <el-button size="small" circle :icon="Edit" @click="openEditChannel(ch)" />
            <el-icon class="ch-arrow" :class="{ 'is-open': expandedChannel === ch.key }" @click="toggleChannel(ch.key)"><ArrowDown /></el-icon>
          </div>
        </div>

        <!-- API Key Row -->
        <div class="ch-key-row">
          <div class="ch-key-group">
            <span class="ch-key-label">API 密钥</span>
            <span class="ch-key-dots">{{ ch.apiKeyMasked }}</span>
          </div>
          <el-button
            size="small"
            round
            :loading="channelTesting === ch.key"
            @click="testChannel(ch)"
          >检 测</el-button>
        </div>

        <!-- API URL Row -->
        <div class="ch-url-row">
          <span class="ch-url-label">API 地址</span>
          <span class="ch-url-value">{{ ch.base_url }}</span>
        </div>

        <!-- Models Section -->
        <div class="ch-models-head">
          <span class="ch-models-title">模型</span>
          <span class="ch-models-count">{{ ch.models.length }}</span>
          <div class="ch-models-spacer"></div>
          <el-button text size="small" @click="testAllModels(ch)">全部检测</el-button>
        </div>

        <transition name="ch-expand">
          <div v-if="expandedChannel === ch.key" class="ch-model-list">
            <div
              v-for="model in ch.models"
              :key="model.id"
              class="ch-model-row"
              :class="{ 'is-inactive': !model.is_active, 'is-default': model.is_default }"
            >
              <div class="ch-model-info">
                <span class="ch-model-name">{{ model.name || model.model }}</span>
                <el-tag v-if="model.is_default" type="warning" size="small" round effect="plain">默认</el-tag>
                <el-tag v-if="!model.is_active" type="info" size="small" round effect="plain">禁用</el-tag>
                <span
                  v-if="testResults[model.id]"
                  class="ch-model-test-dot"
                  :class="testResults[model.id] === 'success' ? 'is-ok' : 'is-err'"
                ></span>
              </div>
              <div class="ch-model-id">{{ model.model }}</div>
              <div class="ch-model-actions">
                <el-button
                  v-if="!model.is_default && model.is_active"
                  text size="small" @click="setDefault(model)"
                >设默认</el-button>
                <el-button
                  text size="small"
                  :loading="testingId === model.id"
                  @click="testModel(model)"
                >测试</el-button>
                <el-button text size="small" :icon="Edit" @click="openEditModel(model)" />
                <el-popconfirm title="确认删除此模型？" @confirm="deleteModel(model.id)">
                  <template #reference>
                    <el-button text size="small" class="ch-model-remove">—</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
          </div>
        </transition>

        <!-- Bottom Actions -->
        <div class="ch-bottom">
          <el-button text type="primary" size="small" @click="openAddModelInChannel(ch)">+ 添加</el-button>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="ch-footer-bar">
      <el-button round @click="openAddChannel">+ 新建通道</el-button>
    </div>

    <!-- 通道编辑弹窗 -->
    <el-dialog v-model="channelDialogVisible" :title="channelDialogIsNew ? '新建供应商通道' : '编辑通道配置'" width="520px" @close="resetChannelForm">
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

    <!-- 添加模型弹窗（CherryStudio 风格：只填 名称+ID） -->
    <el-dialog v-model="modelDialogVisible" :title="modelDialogIsEdit ? '编辑模型' : '添加模型'" width="520px" @close="resetModelForm">
      <el-form ref="modelFormRef" :model="modelForm" :rules="modelRules" label-width="80px">
        <el-form-item label="所属通道" prop="provider">
          <el-select v-model="modelForm.provider" style="width:100%" @change="onModelProviderChange" filterable>
            <el-option
              v-for="ch in channels"
              :key="ch.key"
              :label="`${providerEmoji(ch.provider)} ${providerLabel(ch.provider)}`"
              :value="ch.provider"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" prop="name">
          <el-input v-model="modelForm.name" placeholder="自定义名称，如：DeepSeek V3">
            <template #suffix>
              <span class="ch-form-hint">请输入模型名称</span>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="模型 ID" prop="model">
          <el-input v-model="modelForm.model" placeholder="如：qwen-max / deepseek-chat / gpt-4">
            <template #suffix>
              <span class="ch-form-hint">请输入模型 ID</span>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item v-if="modelDialogIsEdit" label="API 地址">
          <el-input v-model="modelForm.base_url" placeholder="继承自通道，可单独覆盖" />
        </el-form-item>
        <el-form-item v-if="modelDialogIsEdit" label="API Key">
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
const modelForm = ref({ name: '', provider: '', model: '', base_url: '', api_key: '', is_active: true, is_default: false })
const modelRules = {
  name: [{ required: true, message: '请输入模型名称' }],
  model: [{ required: true, message: '请输入模型 ID' }],
  provider: [{ required: true, message: '请选择所属通道' }],
}

const PROVIDER_URLS = {
  dashscope: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  deepseek: 'https://api.deepseek.com/v1',
  openai: 'https://api.openai.com/v1',
  ollama: 'http://localhost:11434/v1',
  custom: ''
}

// Channel = provider + base_url combination (like CherryStudio)
const channels = computed(() => {
  const map = {}
  for (const m of models.value) {
    const p = m.provider || 'custom'
    const url = m.base_url || ''
    const key = `${p}||${url}`
    if (!map[key]) {
      map[key] = {
        key,
        provider: p,
        base_url: url,
        apiKeyMasked: m.api_key || '••••••••••••••••••••',
        models: []
      }
    }
    map[key].models.push(m)
  }
  return Object.values(map)
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

const toggleChannel = (key) => { expandedChannel.value = expandedChannel.value === key ? null : key }

const loadData = async () => {
  loading.value = true
  try {
    const data = await getAIModels()
    models.value = data.models || []
    if (channels.value.length > 0 && !expandedChannel.value) expandedChannel.value = channels.value[0].key
  } finally { loading.value = false }
}

// --- Channel CRUD ---
const openAddChannel = () => {
  channelDialogIsNew.value = true
  channelForm.value = { provider: 'custom', base_url: '', api_key: '', _existingProvider: false, _modelIds: [] }
  channelDialogVisible.value = true
}
const openEditChannel = (ch) => {
  channelDialogIsNew.value = false
  channelForm.value = { provider: ch.provider, base_url: ch.base_url, api_key: '', _existingProvider: true, _modelIds: ch.models.map(m => m.id) }
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
      const r = await testAIModel(model.id)
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

// --- Model CRUD ---
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
const onModelProviderChange = (p) => {
  const ch = channels.value.find(c => c.provider === p)
  modelForm.value.base_url = ch?.base_url || PROVIDER_URLS[p] || ''
}
const resetModelForm = () => modelFormRef.value?.resetFields()

const submitModelForm = async () => {
  await modelFormRef.value.validate()
  modelSaving.value = true
  try {
    const payload = { ...modelForm.value }
    // Inherit channel key/url for new models
    if (!modelDialogIsEdit.value) {
      const ch = channels.value.find(c => c.provider === payload.provider)
      if (!payload.base_url && ch) payload.base_url = ch.base_url
      if (!payload.api_key && ch) payload.api_key = 'inherit-channel'
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

const deleteModel = async (id) => { await deleteAIModel(id); ElMessage.success('已删除'); loadData() }
const setDefault = async (row) => { await setDefaultAIModel(row.id); ElMessage.success(`${row.name} 已设为默认`); loadData() }

onMounted(loadData)
</script>

<style scoped>
.ai-models-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 4px 0 32px;
}

/* ========== Channel Card (CherryStudio Style) ========== */
.ch-grid { display: flex; flex-direction: column; gap: 16px; }

.ch-card {
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(29, 33, 41, 0.06);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
  overflow: hidden;
}

/* --- Header --- */
.ch-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px 12px;
}
.ch-head-left { display: flex; align-items: center; gap: 12px; min-width: 0; flex: 1; }
.ch-head-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.ch-icon {
  width: 38px; height: 38px; border-radius: 12px;
  background: #f7f8fa; border: 1px solid rgba(29,33,41,0.05);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; flex-shrink: 0;
}
.ch-meta { min-width: 0; }
.ch-name { font-size: 14px; font-weight: 700; color: #1d2129; }
.ch-url { font-size: 11px; color: #86909c; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 1px; }
.ch-badge {
  font-size: 11px; font-weight: 600; color: #4e5969;
  background: #f2f3f5; padding: 2px 8px; border-radius: 999px;
}
.ch-status {
  width: 24px; height: 24px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
}
.ch-status.is-ok { background: #00b42a; color: #fff; }
.ch-status.is-err { background: #f53f3f; color: #fff; }
.ch-status.is-off { background: #e5e6eb; color: #86909c; }
.ch-arrow {
  cursor: pointer; color: #86909c; font-size: 14px;
  transition: transform 0.2s ease; padding: 4px;
}
.ch-arrow.is-open { transform: rotate(180deg); }

/* --- API Key Row --- */
.ch-key-row {
  display: flex; align-items: center; gap: 10px;
  padding: 0 20px; margin-bottom: 8px;
}
.ch-key-group { flex: 1; display: flex; align-items: center; gap: 8px; min-width: 0; }
.ch-key-label { font-size: 12px; font-weight: 600; color: #4e5969; white-space: nowrap; }
.ch-key-dots {
  font-size: 12px; color: #86909c; font-family: monospace;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* --- API URL Row --- */
.ch-url-row {
  display: flex; align-items: center; gap: 8px;
  padding: 0 20px; margin-bottom: 12px;
}
.ch-url-label { font-size: 12px; font-weight: 600; color: #4e5969; white-space: nowrap; }
.ch-url-value { font-size: 12px; color: #86909c; font-family: 'SF Mono', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* --- Models Section --- */
.ch-models-head {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 20px 6px;
  border-top: 1px solid rgba(229, 230, 235, 0.5);
}
.ch-models-title { font-size: 12px; font-weight: 700; color: #1d2129; }
.ch-models-count {
  font-size: 10px; font-weight: 700; color: #fff; background: #165dff;
  min-width: 18px; height: 18px; border-radius: 999px;
  display: inline-flex; align-items: center; justify-content: center;
  padding: 0 5px;
}
.ch-models-spacer { flex: 1; }

.ch-model-list { padding: 0 12px 4px; }
.ch-model-row {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 10px;
  transition: background 0.15s ease;
}
.ch-model-row:hover { background: rgba(247, 248, 250, 0.7); }
.ch-model-row.is-inactive { opacity: 0.45; }
.ch-model-row.is-default { background: rgba(255, 250, 235, 0.6); }

.ch-model-info { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.ch-model-name { font-size: 13px; font-weight: 600; color: #1d2129; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ch-model-id { font-size: 10px; color: #86909c; font-family: 'SF Mono', monospace; white-space: nowrap; }
.ch-model-test-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ch-model-test-dot.is-ok { background: #00b42a; }
.ch-model-test-dot.is-err { background: #f53f3f; }

.ch-model-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.ch-model-remove { color: #86909c !important; font-weight: 700; }

/* --- Bottom --- */
.ch-bottom {
  padding: 6px 20px 12px;
  border-top: 1px solid rgba(229, 230, 235, 0.3);
}

.ch-footer-bar {
  display: flex; justify-content: center;
  padding: 20px 0 0;
}

/* --- Expand transition --- */
.ch-expand-enter-active, .ch-expand-leave-active { transition: all 0.2s ease; overflow: hidden; }
.ch-expand-enter-from, .ch-expand-leave-to { opacity: 0; max-height: 0; }
.ch-expand-enter-to, .ch-expand-leave-from { opacity: 1; max-height: 2000px; }

/* --- Dialog hint --- */
.ch-form-hint { font-size: 10px; color: #c9cdd4; white-space: nowrap; }
</style>
