<template>
  <div class="analysis-prompts-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>📝 分析提示词管理</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon> 新增提示词
          </el-button>
        </div>
      </template>

      <!-- 提示词列表 -->
      <div class="prompts-list">
        <el-table :data="prompts" stripe>
          <el-table-column prop="name" label="名称" min-width="150" />
          <el-table-column prop="category" label="分类" width="120">
            <template #default="{ row }">
              <el-tag :type="getCategoryType(row.category)" size="small">
                {{ row.category }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="prompt" label="提示词内容" min-width="300">
            <template #default="{ row }">
              <div class="prompt-preview">
                {{ row.prompt.substring(0, 100) }}{{ row.prompt.length > 100 ? '...' : '' }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="is_default" label="默认" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link size="small" @click="editPrompt(row)">编辑</el-button>
              <el-button link size="small" type="danger" @click="deletePrompt(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog 
      v-model="showCreateDialog" 
      :title="editingPrompt ? '编辑提示词' : '新增提示词'" 
      width="800px"
    >
      <el-form :model="promptForm" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="promptForm.name" placeholder="请输入提示词名称" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="promptForm.category" placeholder="请选择分类">
            <el-option label="业绩分析" value="业绩分析" />
            <el-option label="趋势分析" value="趋势分析" />
            <el-option label="对比分析" value="对比分析" />
            <el-option label="异常分析" value="异常分析" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="提示词" prop="prompt">
          <el-input 
            v-model="promptForm.prompt" 
            type="textarea" 
            :rows="12" 
            placeholder="请输入分析提示词内容，支持Markdown格式"
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="promptForm.is_default" />
          <div style="color: #909399; font-size: 12px; margin-top: 4px;">
            默认提示词将在生成分析报告时自动使用
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="savePrompt" :loading="saving">
          {{ editingPrompt ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getAnalysisPrompts, createAnalysisPrompt, updateAnalysisPrompt, deleteAnalysisPrompt } from '../api/index.js'

const prompts = ref([])
const showCreateDialog = ref(false)
const editingPrompt = ref(null)
const saving = ref(false)

const promptForm = ref({
  name: '',
  category: '',
  prompt: '',
  is_default: false
})

const formRules = {
  name: [
    { required: true, message: '请输入提示词名称', trigger: 'blur' }
  ],
  category: [
    { required: true, message: '请选择分类', trigger: 'change' }
  ],
  prompt: [
    { required: true, message: '请输入提示词内容', trigger: 'blur' },
    { min: 20, message: '提示词内容至少20个字符', trigger: 'blur' }
  ]
}

const formRef = ref()

// 获取分类标签类型
const getCategoryType = (category) => {
  const typeMap = {
    '业绩分析': 'success',
    '趋势分析': 'primary',
    '对比分析': 'warning',
    '异常分析': 'danger',
    '其他': 'info'
  }
  return typeMap[category] || 'info'
}

// 加载提示词列表
const loadPrompts = async () => {
  try {
    const response = await getAnalysisPrompts()
    prompts.value = response.prompts || []
  } catch (error) {
    ElMessage.error('加载提示词列表失败: ' + error.message)
  }
}

// 编辑提示词
const editPrompt = (prompt) => {
  editingPrompt.value = prompt
  promptForm.value = {
    name: prompt.name,
    category: prompt.category,
    prompt: prompt.prompt,
    is_default: prompt.is_default
  }
  showCreateDialog.value = true
}

// 删除提示词
const deletePrompt = async (prompt) => {
  try {
    await ElMessageBox.confirm(`确定要删除提示词"${prompt.name}"吗？`, '确认删除', {
      type: 'warning'
    })
    
    await deleteAnalysisPrompt(prompt.id)
    ElMessage.success('提示词删除成功')
    await loadPrompts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + error.message)
    }
  }
}

// 保存提示词
const savePrompt = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    saving.value = true
    
    const promptData = { ...promptForm.value }
    
    if (editingPrompt.value) {
      // 更新现有提示词
      await updateAnalysisPrompt(editingPrompt.value.id, promptData)
      ElMessage.success('提示词更新成功')
    } else {
      // 创建新提示词
      await createAnalysisPrompt(promptData)
      ElMessage.success('提示词创建成功')
    }
    
    showCreateDialog.value = false
    editingPrompt.value = null
    resetForm()
    await loadPrompts()
  } catch (error) {
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

// 重置表单
const resetForm = () => {
  promptForm.value = {
    name: '',
    category: '',
    prompt: '',
    is_default: false
  }
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

onMounted(() => {
  loadPrompts()
})
</script>

<style scoped>
.analysis-prompts-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.prompts-list {
  margin-top: 20px;
}

.prompt-preview {
  color: #666;
  font-size: 13px;
  line-height: 1.4;
  max-height: 60px;
  overflow: hidden;
}
</style>
