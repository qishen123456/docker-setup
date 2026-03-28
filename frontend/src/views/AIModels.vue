<template>
  <div>
    <el-row :gutter="20" style="margin-bottom:20px">
      <el-col :span="8">
        <el-card class="mini-stat"><el-statistic title="模型总数" :value="models.length"><template #prefix><el-icon color="#409EFF"><MagicStick /></el-icon></template></el-statistic></el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="mini-stat"><el-statistic title="已启用" :value="models.filter(m=>m.is_active).length" value-style="color:#67c23a" /></el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="mini-stat"><el-statistic title="默认模型" :value="models.filter(m=>m.is_default).length" value-style="color:#E6A23C" /></el-card>
      </el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>🤖 AI模型配置</span>
          <el-button type="primary" :icon="Plus" @click="openAdd">添加模型</el-button>
        </div>
      </template>

      <el-alert type="info" :closable="false" style="margin-bottom:16px">
        支持所有 OpenAI 兼容 API：通义千问、DeepSeek、OpenAI、本地 Ollama 等，只需填入对应的 API地址 和 Key。
      </el-alert>

      <el-table :data="models" v-loading="loading" stripe>
        <el-table-column prop="name" label="模型名称" min-width="160">
          <template #default="{ row }">
            <el-text strong>{{ row.name }}</el-text>
            <el-tag v-if="row.is_default" type="warning" size="small" style="margin-left:6px">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="provider" label="提供商" width="120">
          <template #default="{ row }">
            <el-tag :type="providerTag(row.provider)">{{ row.provider }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model" label="模型ID" width="160" show-overflow-tooltip>
          <template #default="{ row }"><el-text code>{{ row.model }}</el-text></template>
        </el-table-column>
        <el-table-column prop="base_url" label="API地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="api_key" label="API Key" width="130">
          <template #default="{ row }"><el-text type="info" size="small">{{ row.api_key }}</el-text></template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '已启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div style="white-space: nowrap">
              <el-button link :icon="Connection" :loading="testingId === row.id" @click="testModel(row)">测试</el-button>
              <el-button link v-if="!row.is_default" @click="setDefault(row)">设默认</el-button>
              <el-button link :icon="Edit" @click="openEdit(row)">编辑</el-button>
              <el-popconfirm title="确认删除此模型？" @confirm="deleteModel(row.id)">
                <template #reference>
                  <el-button link type="danger" :icon="Delete">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { getAIModels, createAIModel, updateAIModel, deleteAIModel, testAIModel, setDefaultAIModel } from '../api/index.js'

const models = ref([])
const loading = ref(false)
const saving = ref(false)
const testingId = ref(null)
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

const providerTag = (p) => ({ dashscope:'primary', deepseek:'warning', openai:'success', ollama:'info' }[p] || 'info')

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
  try { const r = await testAIModel(row.id); ElMessage.success(`✅ ${r.message}（${r.response_time}ms）`) }
  catch {} finally { testingId.value = null }
}

const setDefault = async (row) => {
  await setDefaultAIModel(row.id); ElMessage.success(`${row.name} 已设为默认模型`); loadData()
}

onMounted(loadData)
</script>

<style scoped>
.card-header { display:flex; justify-content:space-between; align-items:center; }
</style>
