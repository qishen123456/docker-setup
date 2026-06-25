<template>
  <div class="cs-page" v-loading="loading">
    <div class="cs-layout">
      <!-- ===== LEFT: Channel List ===== -->
      <aside class="cs-sidebar">
        <div class="cs-sidebar-head">
          <div>
            <div class="cs-sidebar-kicker">MODEL ROUTES</div>
            <div class="cs-sidebar-title">模型通道</div>
          </div>
          <span class="cs-sidebar-count">{{ channels.length }}</span>
        </div>
        <div class="cs-sidebar-scroll">
          <div
            v-for="ch in channels" :key="ch.key"
            class="cs-ch-item"
            :class="{ 'is-active': selectedChannelKey === ch.key }"
            @click="selectChannel(ch.key)"
          >
            <span class="cs-ch-icon" v-html="channelIconSvg(ch)"></span>
            <span class="cs-ch-copy">
              <span class="cs-ch-name">{{ ch._displayName || channelDisplayName(ch) }}</span>
              <span class="cs-ch-meta">{{ ch.models.length }} 个模型 · {{ ch.models.filter(m => m.is_active).length }} 启用</span>
            </span>
            <el-switch
              v-model="ch._hasActive"
              size="small"
              class="cs-ch-switch"
              :disabled="!isFeatureEnabled('ai_channel_edit')"
              @click.stop
              @change="toggleChannelActive(ch, $event)"
            />
          </div>
        </div>
        <div class="cs-sidebar-footer">
          <el-button v-if="isFeatureEnabled('ai_channel_edit')" type="primary" class="cs-add-btn" @click="openAddChannel">
            <el-icon><Plus /></el-icon>
            <span>新建通道</span>
          </el-button>
        </div>
      </aside>

      <!-- ===== RIGHT: Channel Detail ===== -->
      <main class="cs-main" v-if="activeChannel">
        <section class="cs-hero">
          <div class="cs-hero-main">
            <el-popover placement="bottom-start" trigger="click" width="260" popper-class="cs-icon-popover">
              <template #reference>
                <button v-if="isFeatureEnabled('ai_channel_edit')" class="cs-provider-icon" type="button" title="选择通道图标">
                  <span v-html="channelIconSvg(activeChannel)"></span>
                </button>
              </template>
              <div class="cs-icon-picker">
                <div class="cs-icon-picker-title">选择通道图标</div>
                <button
                  v-for="icon in channelIconOptions"
                  :key="icon.key"
                  type="button"
                  class="cs-icon-option"
                  :class="{ 'is-active': channelIconKey(activeChannel) === icon.key }"
                  @click="saveChannelIcon(icon.key)"
                >
                  <span v-html="renderTechIcon(icon.key)"></span>
                </button>
              </div>
            </el-popover>
            <div class="cs-provider-copy">
              <div class="cs-provider-kicker">当前供应商通道</div>
              <div class="cs-provider-title-row" v-if="!editingProviderName">
                <div class="cs-provider-title">{{ activeChannel._displayName || channelDisplayName(activeChannel) }}</div>
                <el-button v-if="isFeatureEnabled('ai_channel_edit')" text size="small" class="cs-provider-edit-btn" @click="startEditProviderName">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </div>
              <div class="cs-provider-title-row" v-else>
                <el-input
                  v-model="editProviderNameValue"
                  size="default"
                  class="cs-provider-name-input"
                  @keyup.enter="saveProviderName"
                  ref="providerNameInputRef"
                />
                <el-button v-if="isFeatureEnabled('ai_channel_edit')" type="primary" size="small" @click="saveProviderName">保存名称</el-button>
                <el-button size="small" @click="cancelProviderNameEdit">取消</el-button>
              </div>
              <span class="cs-provider-url-sub">{{ activeChannel.base_url || '尚未配置 API 地址' }}</span>
            </div>
          </div>
          <div class="cs-hero-stats">
            <div class="cs-stat-card">
              <span>模型数</span>
              <strong>{{ activeChannel.models.length }}</strong>
            </div>
            <div class="cs-stat-card">
              <span>已启用</span>
              <strong>{{ activeChannel.models.filter(m => m.is_active).length }}</strong>
            </div>
            <div class="cs-stat-card">
              <span>默认模型</span>
              <strong>{{ activeChannel.models.find(m => m.is_default)?.name || '未设置' }}</strong>
            </div>
          </div>
        </section>

        <section class="cs-config-grid">
          <!-- API Key Section -->
          <div class="cs-config-card cs-config-card-key">
            <div class="cs-section-head">
              <div>
                <div class="cs-section-label">API 密钥</div>
                <div class="cs-section-desc">统一应用到当前通道下的模型。</div>
              </div>
              <el-button text class="cs-icon-btn" @click="showApiKey = !showApiKey">
                <el-icon><View v-if="!showApiKey" /><Hide v-else /></el-icon>
              </el-button>
            </div>
            <div class="cs-key-row">
              <el-input
                v-model="editableApiKey"
                :type="showApiKey ? 'text' : 'password'"
                placeholder="sk-..."
                class="cs-key-input"
                :disabled="!isFeatureEnabled('ai_channel_edit')"
                @change="onApiKeyChange"
              />
              <el-button
                v-if="isFeatureEnabled('ai_model_test')"
                :loading="channelTesting === activeChannel.key"
                @click="testChannel(activeChannel)"
              >检测连接</el-button>
            </div>
          </div>

          <!-- API URL Section -->
          <div class="cs-config-card">
            <div class="cs-section-head">
              <div>
                <div class="cs-section-label">API 地址</div>
                <div class="cs-section-desc">兼容 OpenAI 格式的接口地址。</div>
              </div>
            </div>
            <div class="cs-url-row">
              <el-input v-model="editableBaseUrl" class="cs-url-input" :disabled="!isFeatureEnabled('ai_channel_edit')" @change="onBaseUrlChange" />
            </div>
          </div>
        </section>

        <!-- Models Section -->
        <section class="cs-model-panel">
          <div class="cs-models-header">
            <div>
              <div class="cs-models-label">模型资产</div>
              <div class="cs-models-desc">维护可调用模型、默认模型与连通性。</div>
            </div>
            <span class="cs-models-count">{{ activeChannel.models.length }}</span>
            <div class="cs-models-spacer"></div>
            <el-button v-if="isFeatureEnabled('ai_model_test')" @click="testAllModels(activeChannel)">全部检测</el-button>
          </div>

          <div class="cs-model-list">
            <div
              v-for="model in activeChannel.models"
              :key="model.id"
              class="cs-model-row"
              :class="{ 'is-default': model.is_default, 'is-inactive': !model.is_active }"
            >
              <span class="cs-model-emoji" v-html="channelIconSvg(activeChannel)"></span>
              <div class="cs-model-copy">
                <div class="cs-model-title-line">
                  <span class="cs-model-name">{{ model.name || model.model }}</span>
                  <el-tag v-if="model.is_default" type="warning" size="small" round effect="plain">默认</el-tag>
                  <el-tag v-if="!model.is_active" type="info" size="small" round effect="plain">禁用</el-tag>
                  <span
                    v-if="testResults[model.id]"
                    class="cs-model-dot"
                    :class="testResults[model.id] === 'success' ? 'is-ok' : 'is-err'"
                  ></span>
                </div>
                <span class="cs-model-id">{{ model.model }}</span>
              </div>
              <div class="cs-model-spacer"></div>
              <div class="cs-model-actions">
                <el-button
                  v-if="!model.is_default && model.is_active && isFeatureEnabled('ai_model_edit')"
                  text size="small" @click="setDefault(model)"
                >设默认</el-button>
                <el-button
                  v-if="isFeatureEnabled('ai_model_test')"
                  text size="small"
                  :loading="testingId === model.id"
                  @click="testModel(model)"
                >测试</el-button>
                <el-button v-if="isFeatureEnabled('ai_model_edit')" text size="small" @click="openEditModel(model)">
                  <el-icon><Setting /></el-icon>
                </el-button>
                <el-popconfirm v-if="isFeatureEnabled('ai_model_edit')" title="确认删除此模型？" @confirm="deleteModel(model.id)">
                  <template #reference>
                    <el-button text size="small" type="danger" class="cs-model-del">删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
          </div>

          <!-- Add Model Row -->
          <div class="cs-add-model-bar">
            <el-button v-if="isFeatureEnabled('ai_model_edit')" type="primary" plain @click="openAddModelInChannel(activeChannel)">
              <el-icon><Plus /></el-icon> 添加模型
            </el-button>
          </div>
        </section>
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
        <el-button v-if="isFeatureEnabled('ai_channel_edit')" type="primary" :loading="channelSaving" @click="submitChannelForm">
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
        <el-button v-if="isFeatureEnabled('ai_model_edit')" type="primary" :loading="modelSaving" @click="submitModelForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete, ArrowDown, Setting, View, Hide } from '@element-plus/icons-vue'
import { getAIModels, createAIModel, updateAIModel, deleteAIModel, testAIModel, setDefaultAIModel } from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'

const models = ref([])
const loading = ref(false)
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const testingId = ref(null)
const testResults = reactive({})
const selectedChannelKey = ref(null)
const channelTesting = ref(null)
const channelTestResult = reactive({})
const showApiKey = ref(false)
const editableApiKey = ref('')
const editableBaseUrl = ref('')
const editingProviderName = ref(false)
const editProviderNameValue = ref('')
const providerNameInputRef = ref()
const legacyChannelNames = ref(JSON.parse(localStorage.getItem('sa_channel_names') || '{}'))
const legacyChannelIcons = ref(JSON.parse(localStorage.getItem('sa_channel_icons') || '{}'))
const channelIconOptions = [
  { key: 'orbit' },
  { key: 'chip' },
  { key: 'neural' },
  { key: 'rocket' },
  { key: 'radar' },
  { key: 'cube' },
  { key: 'shield' },
  { key: 'spark' },
  { key: 'terminal' },
  { key: 'cloud' },
  { key: 'grid' },
  { key: 'bolt' },
]

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
        channelDisplayName: m.channel_display_name || '',
        channelIcon: m.channel_icon || '',
        models: [],
        _hasActive: false,
      }
    }
    map[key].models.push(m)
  }
  for (const ch of Object.values(map)) {
    ch._hasActive = ch.models.some(m => m.is_active)
    ch._displayName = ch.channelDisplayName || ch.models.find(m => m.channel_display_name)?.channel_display_name || legacyChannelNames.value[ch.key] || ''
    ch._icon = ch.channelIcon || ch.models.find(m => m.channel_icon)?.channel_icon || legacyChannelIcons.value[ch.key] || ''
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

const providerIconKey = (p) => ({
  dashscope: 'orbit',
  deepseek: 'neural',
  openai: 'spark',
  ollama: 'terminal',
  custom: 'chip'
}[p] || 'cloud')

const legacyEmojiIconMap = {
  '⚙️': 'chip',
  '🌐': 'orbit',
  '🧠': 'neural',
  '✨': 'spark',
  '🚀': 'rocket',
  '🔮': 'radar',
  '🧩': 'cube',
  '🛰️': 'radar',
  '🔥': 'bolt',
  '💎': 'cube',
  '🐋': 'neural',
  '🤖': 'spark',
  '💻': 'terminal',
  '🔌': 'cloud',
  '🛡️': 'shield',
  '📡': 'radar',
}

const normalizeIconKey = (value, provider = 'custom') => {
  if (!value) return providerIconKey(provider)
  if (legacyEmojiIconMap[value]) return legacyEmojiIconMap[value]
  return channelIconOptions.some(item => item.key === value) ? value : providerIconKey(provider)
}

const channelIconKey = (ch) => {
  if (!ch) return 'cloud'
  return normalizeIconKey(ch._icon, ch.provider)
}

const renderTechIcon = (key) => {
  const iconKey = normalizeIconKey(key)
  const paths = {
    orbit: '<circle cx="12" cy="12" r="3.2"/><ellipse cx="12" cy="12" rx="8.5" ry="3.8" transform="rotate(-24 12 12)"/><ellipse cx="12" cy="12" rx="8.5" ry="3.8" transform="rotate(24 12 12)"/>',
    chip: '<rect x="6.5" y="6.5" width="11" height="11" rx="2.4"/><path d="M9 3.5v3M15 3.5v3M9 17.5v3M15 17.5v3M3.5 9h3M3.5 15h3M17.5 9h3M17.5 15h3"/><circle cx="12" cy="12" r="2.2"/>',
    neural: '<circle cx="7" cy="8" r="2"/><circle cx="16.5" cy="6.8" r="2"/><circle cx="17" cy="16" r="2"/><circle cx="8" cy="17" r="2"/><path d="M8.8 8.7l5.1-1.2M8.2 9.7l7.1 5M9.6 16.1l5.4-.1M7.3 10l.5 5"/>',
    rocket: '<path d="M13.5 4.4c2.7.6 4.7 2.6 5.3 5.3l-5.9 5.9-4.8-4.8 5.4-6.4Z"/><path d="M8.1 10.8 5.4 12l-1.2 3.4 3.8-1.1M12.9 15.6 11.8 19l-3.4 1.2 1.2-2.7"/><circle cx="15.3" cy="8.4" r="1.2"/>',
    radar: '<path d="M12 19.5a7.5 7.5 0 1 0-7.5-7.5"/><path d="M12 15.5a3.5 3.5 0 1 0-3.5-3.5"/><path d="M12 12l6.2-6.2"/><circle cx="12" cy="12" r="1.4"/>',
    cube: '<path d="m12 3.8 7 4v8.4l-7 4-7-4V7.8l7-4Z"/><path d="m5.4 8 6.6 3.8L18.6 8M12 11.8v7.7"/>',
    shield: '<path d="M12 3.8 18.5 6v5.3c0 4.1-2.5 7.1-6.5 8.9-4-1.8-6.5-4.8-6.5-8.9V6L12 3.8Z"/><path d="m8.8 12 2.1 2.1 4.3-4.7"/>',
    spark: '<path d="M12 3.8 13.8 9l5.2 1.8-5.2 1.8L12 17.8l-1.8-5.2L5 10.8 10.2 9 12 3.8Z"/><path d="M18 16.5v3M16.5 18h3M5.8 4.5v2.6M4.5 5.8h2.6"/>',
    terminal: '<rect x="4.5" y="5.5" width="15" height="13" rx="2.4"/><path d="m8 10 2.4 2L8 14M12 14h4"/>',
    cloud: '<path d="M8.2 17.5h8.4a3.4 3.4 0 0 0 .4-6.8A5.2 5.2 0 0 0 7 9.4a4.1 4.1 0 0 0 1.2 8.1Z"/><path d="M10 13.6h4.5"/>',
    grid: '<rect x="5" y="5" width="5.2" height="5.2" rx="1.4"/><rect x="13.8" y="5" width="5.2" height="5.2" rx="1.4"/><rect x="5" y="13.8" width="5.2" height="5.2" rx="1.4"/><rect x="13.8" y="13.8" width="5.2" height="5.2" rx="1.4"/>',
    bolt: '<path d="M13.3 3.8 6.5 13h5.2l-1 7.2 6.8-9.4h-5.2l1-7Z"/>',
  }
  return `<svg viewBox="0 0 24 24" class="cs-tech-icon" aria-hidden="true">${paths[iconKey] || paths.cloud}</svg>`
}

const channelIconSvg = (ch) => renderTechIcon(channelIconKey(ch))

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

const startEditProviderName = () => {
  const ch = activeChannel.value
  if (!ch) return
  editProviderNameValue.value = ch._displayName || channelDisplayName(ch)
  editingProviderName.value = true
  nextTick(() => providerNameInputRef.value?.focus())
}

const saveProviderName = async () => {
  const ch = activeChannel.value
  if (!ch) return
  const name = editProviderNameValue.value.trim()
  for (const model of ch.models) {
    await updateAIModel(model.id, { channel_display_name: name })
  }
  editingProviderName.value = false
  ElMessage.success('通道名称已保存')
  await loadData()
}

const cancelProviderNameEdit = () => {
  editingProviderName.value = false
  editProviderNameValue.value = ''
}

const saveChannelIcon = async (icon) => {
  const ch = activeChannel.value
  if (!ch) return
  const normalizedIcon = normalizeIconKey(icon, ch.provider)
  const nextIcon = normalizedIcon && normalizedIcon !== providerIconKey(ch.provider) ? normalizedIcon : ''
  for (const model of ch.models) {
    await updateAIModel(model.id, { channel_icon: nextIcon })
  }
  ElMessage.success('通道图标已保存')
  await loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await getAIModels()
    models.value = data.models || []
    if (channels.value.length > 0 && !selectedChannelKey.value) {
      selectChannel(channels.value[0].key)
    }
    await migrateLegacyChannelMetaToBackend()
  } finally { loading.value = false }
}

const migrateLegacyChannelMetaToBackend = async () => {
  const pendingNames = legacyChannelNames.value || {}
  const pendingIcons = legacyChannelIcons.value || {}
  const entries = channels.value.filter(ch => pendingNames[ch.key] || pendingIcons[ch.key])
  if (!entries.length) return

  for (const ch of entries) {
    const payload = {}
    if (pendingNames[ch.key] && !ch.channelDisplayName) payload.channel_display_name = pendingNames[ch.key]
    if (pendingIcons[ch.key] && !ch.channelIcon) payload.channel_icon = pendingIcons[ch.key]
    if (!Object.keys(payload).length) continue
    for (const model of ch.models) {
      await updateAIModel(model.id, payload)
    }
  }
  localStorage.removeItem('sa_channel_names')
  localStorage.removeItem('sa_channel_icons')
  legacyChannelNames.value = {}
  legacyChannelIcons.value = {}
  const refreshed = await getAIModels()
  models.value = refreshed.models || []
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

onMounted(() => {
  loadFeatureFlags()
  loadData()
})
</script>

<style scoped>
.cs-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.cs-layout {
  position: relative;
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 18px;
  background:
    radial-gradient(circle at 82% 8%, rgba(230, 31, 36, 0.13), transparent 28%),
    radial-gradient(circle at 30% 0%, rgba(0, 0, 0, 0.09), transparent 24%),
    linear-gradient(135deg, #F8F9FA 0%, #F8F9FA 45%, #ffffff 100%);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.78);
}

.cs-layout::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.03) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.5), transparent 74%);
}

/* ===== LEFT SIDEBAR ===== */
.cs-sidebar {
  position: relative;
  z-index: 1;
  width: 260px;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(18px);
}

.cs-sidebar-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 16px 16px 10px;
}

.cs-sidebar-kicker {
  color: #E61F24;
  font-size: 9px;
  font-weight: 850;
  letter-spacing: 0.14em;
}

.cs-sidebar-title {
  margin-top: 4px;
  color: #111827;
  font-size: 16px;
  font-weight: 850;
}

.cs-sidebar-count {
  min-width: 26px;
  height: 26px;
  padding: 0 9px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #cc181d;
  font-size: 12px;
  font-weight: 850;
  background: #FEF2F2;
  border: 1px solid rgba(230, 31, 36, 0.16);
}

.cs-sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 4px 10px 10px;
}

.cs-ch-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 10px;
  margin-bottom: 8px;
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  user-select: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all var(--duration-normal, 220ms) var(--ease-out);
}

.cs-ch-item:hover {
  transform: translateY(-1px);
  border-color: rgba(230, 31, 36, 0.2);
  background: #ffffff;
  box-shadow: 0 12px 26px rgba(0, 0, 0, 0.08);
}

.cs-ch-item.is-active {
  border-color: rgba(230, 31, 36, 0.26);
  background:
    linear-gradient(135deg, rgba(254, 242, 242, 0.95), rgba(255, 255, 255, 0.96));
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12), inset 4px 0 0 #E61F24;
}

.cs-ch-icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: linear-gradient(135deg, #1A1A1A 0%, #E61F24 100%);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.18);
}

.cs-ch-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cs-ch-name {
  color: #111827;
  font-size: 12px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cs-ch-meta {
  color: #9CA3AF;
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cs-ch-switch {
  flex-shrink: 0;
}

.cs-sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.cs-add-btn {
  width: 100%;
  height: 36px;
}

/* ===== RIGHT MAIN ===== */
.cs-main {
  position: relative;
  z-index: 1;
  flex: 1;
  overflow-y: auto;
  padding: 20px 22px;
}

.cs-empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.cs-empty-text {
  padding: 24px 32px;
  border: 1px dashed rgba(0, 0, 0, 0.14);
  border-radius: 20px;
  color: var(--text-muted, #9CA3AF);
  font-size: 14px;
  background: rgba(255, 255, 255, 0.76);
}

/* Provider Hero */
.cs-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  padding: 18px 20px;
  margin-bottom: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 18px;
  background:
    radial-gradient(circle at 4% 10%, rgba(230, 31, 36, 0.16), transparent 32%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(248, 249, 250, 0.88));
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.055), inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.cs-hero-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
}

.cs-provider-icon {
  width: 56px;
  height: 56px;
  border: 0;
  border-radius: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  cursor: pointer;
  background:
    radial-gradient(circle at 30% 24%, rgba(255, 255, 255, 0.34), transparent 26%),
    linear-gradient(135deg, #111827 0%, #1A1A1A 48%, #E61F24 100%);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.18);
  transition: all var(--duration-normal, 220ms) var(--ease-out);
}

.cs-provider-icon:hover {
  transform: translateY(-1px) scale(1.02);
  box-shadow: 0 16px 28px rgba(0, 0, 0, 0.22);
}

.cs-provider-copy {
  min-width: 0;
}

.cs-provider-kicker {
  margin-bottom: 4px;
  color: #E61F24;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.12em;
}

.cs-provider-title-row {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.cs-provider-title {
  min-width: 0;
  color: #111827;
  font-size: 24px;
  line-height: 1.15;
  font-weight: 900;
  letter-spacing: -0.04em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cs-provider-edit-btn {
  opacity: 0.58;
  transition: opacity 0.15s;
}

.cs-hero:hover .cs-provider-edit-btn {
  opacity: 1;
}

.cs-provider-name-input {
  width: min(520px, 70vw);
}

.cs-provider-title-row .el-button + .el-button {
  margin-left: 0;
}

.cs-provider-url-sub {
  display: block;
  margin-top: 6px;
  color: #6B7280;
  font-size: 12px;
  word-break: break-all;
}

.cs-hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(96px, 1fr));
  gap: 8px;
  align-self: stretch;
}

.cs-stat-card {
  min-width: 100px;
  padding: 11px 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
}

.cs-stat-card span {
  display: block;
  color: #9CA3AF;
  font-size: 10px;
  font-weight: 750;
}

.cs-stat-card strong {
  display: block;
  margin-top: 6px;
  max-width: 150px;
  color: #111827;
  font-size: 17px;
  line-height: 1.2;
  font-weight: 900;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Config Cards */
.cs-config-grid {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(320px, 0.82fr);
  gap: 14px;
  margin-bottom: 14px;
}

.cs-config-card,
.cs-model-panel {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.045), inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.cs-config-card {
  padding: 14px;
}

.cs-config-card-key {
  background:
    radial-gradient(circle at 100% 0%, rgba(230, 31, 36, 0.12), transparent 30%),
    rgba(255, 255, 255, 0.84);
}

.cs-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.cs-section-label {
  color: #111827;
  font-size: 13px;
  font-weight: 850;
}

.cs-section-desc,
.cs-models-desc {
  margin-top: 4px;
  color: #9CA3AF;
  font-size: 11px;
}

.cs-key-row,
.cs-url-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cs-key-input,
.cs-url-input {
  flex: 1;
}

.cs-main :deep(.el-input__wrapper) {
  min-height: 34px;
}

.cs-main :deep(.el-button) {
  min-height: 32px;
}

.cs-icon-btn {
  width: 32px;
}

/* Models */
.cs-model-panel {
  padding: 14px;
}

.cs-models-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.cs-models-label {
  color: #111827;
  font-size: 14px;
  font-weight: 900;
}

.cs-models-count {
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  border-radius: var(--radius-pill, 999px);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #cc181d;
  font-size: 12px;
  font-weight: 900;
  background: #FEF2F2;
  border: 1px solid rgba(230, 31, 36, 0.16);
}

.cs-models-spacer {
  flex: 1;
}

.cs-model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cs-model-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #F8F9FA 100%);
  transition: all var(--duration-normal, 220ms) var(--ease-out);
}

.cs-model-row:hover {
  transform: translateY(-1px);
  border-color: rgba(230, 31, 36, 0.18);
  box-shadow: 0 14px 26px rgba(0, 0, 0, 0.08);
}

.cs-model-row.is-inactive {
  opacity: 0.58;
}

.cs-model-row.is-default {
  border-color: rgba(245, 158, 11, 0.2);
  background:
    radial-gradient(circle at 100% 0%, rgba(245, 158, 11, 0.1), transparent 28%),
    linear-gradient(180deg, #FFFBEB 0%, #FFFBEB 100%);
}

.cs-model-emoji {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #FEF2F2;
  border: 1px solid rgba(230, 31, 36, 0.12);
}

.cs-ch-icon :deep(.cs-tech-icon),
.cs-provider-icon :deep(.cs-tech-icon),
.cs-model-emoji :deep(.cs-tech-icon),
.cs-icon-option :deep(.cs-tech-icon) {
  width: 1em;
  height: 1em;
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.cs-ch-icon,
.cs-provider-icon {
  color: #FEF2F2;
}

.cs-ch-icon :deep(.cs-tech-icon) {
  width: 19px;
  height: 19px;
  filter: drop-shadow(0 0 8px rgba(0, 0, 0, 0.28));
}

.cs-provider-icon :deep(.cs-tech-icon) {
  width: 30px;
  height: 30px;
  stroke-width: 1.6;
  filter: drop-shadow(0 0 10px rgba(0, 0, 0, 0.34));
}

.cs-model-emoji {
  color: #E61F24;
}

.cs-model-emoji :deep(.cs-tech-icon) {
  width: 18px;
  height: 18px;
}

.cs-model-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.cs-model-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.cs-model-name {
  color: #111827;
  font-size: 13px;
  font-weight: 850;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cs-model-id {
  color: #9CA3AF;
  font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
  font-size: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cs-model-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.12);
}

.cs-model-dot.is-ok {
  background: #10B981;
}

.cs-model-dot.is-err {
  background: #E61F24;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.12);
}

.cs-model-spacer {
  flex: 1;
}

.cs-model-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.cs-model-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.cs-icon-picker {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
}

.cs-icon-picker-title {
  grid-column: 1 / -1;
  margin-bottom: 2px;
  color: #111827;
  font-size: 13px;
  font-weight: 850;
}

.cs-icon-option {
  width: 34px;
  height: 34px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.8), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #F8F9FA 100%);
  color: #6B7280;
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out);
}

.cs-icon-option:hover,
.cs-icon-option.is-active {
  border-color: rgba(230, 31, 36, 0.3);
  background:
    radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.9), transparent 30%),
    linear-gradient(135deg, #FEF2F2 0%, #ffffff 100%);
  color: #cc181d;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
}

.cs-icon-option :deep(.cs-tech-icon) {
  width: 18px;
  height: 18px;
}

.cs-add-model-bar {
  margin-top: 12px;
  padding: 14px;
  border: 1px dashed rgba(230, 31, 36, 0.22);
  border-radius: 14px;
  text-align: center;
  background: rgba(254, 242, 242, 0.38);
}

@media (max-width: 1180px) {
  .cs-layout {
    flex-direction: column;
  }

  .cs-sidebar {
    width: 100%;
    min-width: 0;
    max-height: 260px;
    border-right: 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  }

  .cs-sidebar-scroll {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 10px;
  }

  .cs-ch-item {
    margin-bottom: 0;
  }

  .cs-hero,
  .cs-config-grid {
    grid-template-columns: 1fr;
  }

  .cs-hero-stats {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 760px) {
  .cs-main {
    padding: 18px;
  }

  .cs-hero-main,
  .cs-model-row {
    align-items: flex-start;
  }

  .cs-hero-stats {
    grid-template-columns: 1fr;
  }

  .cs-model-row {
    flex-wrap: wrap;
  }

  .cs-model-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
