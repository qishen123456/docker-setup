<template>
  <div class="ai-models-page" v-loading="loading">
    <!-- 统计栏 -->
    <div class="aim-stat-bar">
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
      <el-button type="primary" :icon="Plus" round @click="openAdd">添加模型</el-button>
    </div>

    <!-- 供应商分组卡片 -->
    <div class="aim-provider-grid">
      <div
        v-for="group in providerGroups"
        :key="group.provider"
        class="aim-provider-card"
      >
        <div class="aim-provider-head">
          <div class="aim-provider-icon">{{ providerEmoji(group.provider) }}</div>
          <div class="aim-provider-info">
            <div class="aim-provider-name">{{ providerLabel(group.provider) }}</div>
            <div class="aim-provider-meta">{{ group.models.length }} 个模型</div>
          </div>
        </div>

        <div class="aim-model-list">
          <div
            v-for="model in group.models"
            :key="model.id"
            class="aim-model-card"
            :class="{ 'aim-model-inactive': !model.is_active, 'aim-model-default': model.is_default }"
          >
            <div class="aim-model-top">
              <div class="aim-model-name-row">
                <span class="aim-model-name">{{ model.name }}</span>
                <el-tag v-if="model.is_default" type="warning" size="small" effect="plain" round>默认</el-tag>
                <el-tag v-if="!model.is_active" type="info" size="small" effect="plain" round>禁用</el-tag>
              </div>
              <div class="aim-model-id">{{ model.model }}</div>
              <div class="aim-model-url">{{ model.base_url }}</div>
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
                <template v-else>测试连接</template>
              </el-button>
              <el-button v-if="!model.is_default && model.is_active" size="small" round @click="setDefault(model)">设默认</el-button>
              <el-button size="small" round :icon="Edit" @click="openEdit(model)">编辑</el-button>
              <el-popconfirm title="确认删除此模型？" @confirm="deleteModel(model.id)">
                <template #reference>
                  <el-button size="small" round type="danger" plain :icon="Delete">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑AI模型' : '添加AI模型'" width="620px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="模型名称" prop="name">
              <el-input v-model="form.name" placeholder="自定义名称，如：DeepSeek V3" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="提供商" prop="provider">
              <el-select v-model="form.provider" style="width:100%" @change="onProviderChange" allow-create filterable>
                <el-option label="dashscope（阿里通义）" value="dashscope" />
                <el-option label="deepseek" value="deepseek" />
                <el-option label="openai" value="openai" />
                <el-option label="ollama（本地）" value="ollama" />
                <el-option label="custom（自定义）" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="模型ID" prop="model">
          <el-input v-model="form.model" placeholder="如：qwen-max / deepseek-chat / gpt-4" />
        </el-form-item>

        <el-form-item label="API地址" prop="base_url">
          <el-input v-model="form.base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1">
            <template #prepend>URL</template>
          </el-input>
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="输入后安全存储（Base64 混淆）" />
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设为默认"><el-switch v-model="form.is_default" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { getAIModels, createAIModel, updateAIModel, deleteAIModel, testAIModel, setDefaultAIModel } from '../api/index.js'

const models = ref([])
const loading = ref(false)
const saving = ref(false)
const testingId = ref(null)
const testResults = reactive({})
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()

const PROVIDER_URLS = {
  dashscope: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  deepseek: 'https://api.deepseek.com/v1',
  openai: 'https://api.openai.com/v1',
  ollama: 'http://localhost:11434/v1',
  custom: ''
}

const defaultForm = () => ({ name:'', provider:'dashscope', model:'qwen-max', base_url: PROVIDER_URLS.dashscope, api_key:'', is_active:true, is_default:false })
const form = ref(defaultForm())

const rules = {
  name: [{ required: true, message: '请输入模型名称' }],
  model: [{ required: true, message: '请输入模型ID' }],
  base_url: [{ required: true, message: '请输入API地址' }],
  api_key: [{ required: true, message: '请输入API Key' }],
}

const defaultModelName = computed(() => {
  const m = models.value.find(m => m.is_default)
  return m ? m.name : ''
})

const providerGroups = computed(() => {
  const map = {}
  for (const m of models.value) {
    const p = m.provider || 'custom'
    if (!map[p]) map[p] = { provider: p, models: [] }
    map[p].models.push(m)
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

const loadData = async () => {
  loading.value = true
  try { const data = await getAIModels(); models.value = data.models || [] }
  finally { loading.value = false }
}

const onProviderChange = (p) => { form.value.base_url = PROVIDER_URLS[p] || '' }
const openAdd = () => { isEdit.value = false; form.value = defaultForm(); dialogVisible.value = true }
const openEdit = (row) => { isEdit.value = true; form.value = { ...defaultForm(), ...row, api_key: '' }; dialogVisible.value = true }
const resetForm = () => formRef.value?.resetFields()

const submitForm = async () => {
  await formRef.value.validate()
  saving.value = true
  try {
    if (isEdit.value) { await updateAIModel(form.value.id, form.value); ElMessage.success('模型已更新') }
    else { await createAIModel(form.value); ElMessage.success('模型已添加') }
    dialogVisible.value = false; loadData()
  } finally { saving.value = false }
}

const deleteModel = async (id) => { await deleteAIModel(id); ElMessage.success('已删除'); loadData() }

const testModel = async (row) => {
  testingId.value = row.id
  testResults[row.id] = null
  try {
    const r = await testAIModel(row.id)
    testResults[row.id] = 'success'
    ElMessage.success(`✅ ${r.message}（${r.response_time}ms）`)
  } catch {
    testResults[row.id] = 'error'
  } finally {
    testingId.value = null
  }
}

const setDefault = async (row) => {
  await setDefaultAIModel(row.id); ElMessage.success(`${row.name} 已设为默认模型`); loadData()
}

onMounted(loadData)
</script>

<style scoped>
.ai-models-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 4px 0 32px;
}

/* 统计栏 */
.aim-stat-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 24px;
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
  font-size: 18px;
  font-weight: 700;
  color: #1d2129;
}

.aim-stat-active { color: #00b42a; }
.aim-stat-default { font-size: 13px; font-weight: 600; color: #e6a23c; }

.aim-stat-label {
  font-size: 11px;
  color: #86909c;
}

.aim-stat-sep {
  width: 1px;
  height: 28px;
  background: rgba(29, 33, 41, 0.08);
}

.aim-stat-spacer { flex: 1; }

/* 供应商分组 */
.aim-provider-grid {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.aim-provider-card {
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(29, 33, 41, 0.06);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
  overflow: hidden;
}

.aim-provider-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 22px;
  border-bottom: 1px solid rgba(229, 230, 235, 0.6);
  background: rgba(247, 248, 250, 0.5);
}

.aim-provider-icon {
  font-size: 24px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: #fff;
  border: 1px solid rgba(29, 33, 41, 0.06);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
}

.aim-provider-name {
  font-size: 14px;
  font-weight: 700;
  color: #1d2129;
}

.aim-provider-meta {
  font-size: 11px;
  color: #86909c;
  margin-top: 1px;
}

/* 模型列表 */
.aim-model-list {
  padding: 12px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.aim-model-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border-radius: 14px;
  border: 1px solid rgba(29, 33, 41, 0.05);
  background: #fff;
  transition: all 0.2s ease;
}

.aim-model-card:hover {
  border-color: rgba(22, 93, 255, 0.12);
  box-shadow: 0 4px 16px rgba(22, 93, 255, 0.06);
  transform: translateY(-1px);
}

.aim-model-inactive {
  opacity: 0.55;
}

.aim-model-default {
  border-color: rgba(230, 162, 60, 0.18);
  background: linear-gradient(180deg, #fffdf5 0%, #fff 100%);
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
  font-weight: 700;
  color: #1d2129;
}

.aim-model-id {
  margin-top: 3px;
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: #4e5969;
  background: #f2f3f5;
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
}

.aim-model-url {
  margin-top: 3px;
  font-size: 10px;
  color: #86909c;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}

.aim-model-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
</style>
