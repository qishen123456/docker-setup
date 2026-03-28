<template>
  <div class="sql-prompt-manager">
    <div class="header">
      <h2>SQL生成提示词管理</h2>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>
        新建提示词
      </el-button>
    </div>

    <!-- 提示词列表 -->
    <el-card class="prompt-list">
      <el-table :data="prompts" style="width: 100%">
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="id" label="ID" width="150" />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'info'">
              {{ scope.row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="内容预览">
          <template #default="scope">
            <div class="content-preview">
              {{ scope.row.content.substring(0, 100) }}...
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="editPrompt(scope.row)">编辑</el-button>
            <el-button 
              size="small" 
              type="success" 
              @click="setDefaultPrompt(scope.row.id)"
              :disabled="scope.row.id === settings.default_prompt_id"
            >
              {{ scope.row.id === settings.default_prompt_id ? '默认' : '设为默认' }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deletePrompt(scope.row.id)"
              :disabled="scope.row.id === 'default'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 全局设置 -->
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <span>全局设置</span>
        </div>
      </template>
      <el-form :model="settings" label-width="200px">
        <el-form-item label="允许前端覆盖">
          <el-switch v-model="settings.allow_frontend_override" />
        </el-form-item>
        <el-form-item label="最大SQL行数">
          <el-input-number v-model="settings.max_sql_rows" :min="1" :max="1000" />
        </el-form-item>
        <el-form-item label="强制只读SQL">
          <el-switch v-model="settings.enforce_read_only" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveSettings">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑提示词' : '新建提示词'"
      width="80%"
    >
      <el-form :model="currentPrompt" label-width="100px">
        <el-form-item label="ID" required>
          <el-input v-model="currentPrompt.id" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="currentPrompt.name" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="currentPrompt.is_active" />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input 
            v-model="currentPrompt.content" 
            type="textarea" 
            :rows="15"
            placeholder="请输入SQL生成提示词，支持变量：{database_name}, {database_type}"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="info" @click="testPrompt">测试</el-button>
          <el-button type="primary" @click="savePrompt">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 测试对话框 -->
    <el-dialog v-model="testDialogVisible" title="测试提示词" width="70%">
      <el-form :model="testForm" label-width="120px">
        <el-form-item label="数据库名称">
          <el-input v-model="testForm.database_name" />
        </el-form-item>
        <el-form-item label="数据库类型">
          <el-select v-model="testForm.database_type">
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="MySQL" value="mysql" />
            <el-option label="SQLite" value="sqlite" />
            <el-option label="SQL Server" value="sqlserver" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <div class="test-result">
        <h4>格式化后的提示词：</h4>
        <pre>{{ formattedPrompt }}</pre>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="testDialogVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

// 数据
const prompts = ref([])
const settings = ref({})
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const isEdit = ref(false)
const currentPrompt = ref({
  id: '',
  name: '',
  content: '',
  is_active: false
})
const testForm = ref({
  database_name: 'test_db',
  database_type: 'postgresql'
})
const formattedPrompt = ref('')

// 方法
const loadPrompts = async () => {
  try {
    const response = await fetch('/api/sql-prompts')
    const data = await response.json()
    prompts.value = data.prompts
    settings.value = data.settings
  } catch (error) {
    ElMessage.error('加载SQL提示词失败')
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  currentPrompt.value = {
    id: '',
    name: '',
    content: '',
    is_active: false
  }
  dialogVisible.value = true
}

const editPrompt = (prompt) => {
  isEdit.value = true
  currentPrompt.value = { ...prompt }
  dialogVisible.value = true
}

const savePrompt = async () => {
  try {
    const url = isEdit.value 
      ? `/api/sql-prompts/${currentPrompt.value.id}`
      : '/api/sql-prompts'
    const method = isEdit.value ? 'PUT' : 'POST'
    
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(currentPrompt.value)
    })
    
    if (response.ok) {
      ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
      dialogVisible.value = false
      loadPrompts()
    } else {
      const error = await response.json()
      ElMessage.error(error.error || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const deletePrompt = async (promptId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个提示词吗？', '确认删除', {
      type: 'warning'
    })
    
    const response = await fetch(`/api/sql-prompts/${promptId}`, {
      method: 'DELETE'
    })
    
    if (response.ok) {
      ElMessage.success('删除成功')
      loadPrompts()
    } else {
      const error = await response.json()
      ElMessage.error(error.error || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const setDefaultPrompt = async (promptId) => {
  try {
    const response = await fetch(`/api/sql-prompts/${promptId}/set-default`, {
      method: 'POST'
    })
    
    if (response.ok) {
      ElMessage.success('设置默认成功')
      loadPrompts()
    } else {
      const error = await response.json()
      ElMessage.error(error.error || '设置失败')
    }
  } catch (error) {
    ElMessage.error('设置失败')
  }
}

const saveSettings = async () => {
  try {
    const response = await fetch('/api/sql-prompts/settings', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(settings.value)
    })
    
    if (response.ok) {
      ElMessage.success('设置保存成功')
    } else {
      const error = await response.json()
      ElMessage.error(error.error || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const testPrompt = async () => {
  try {
    const response = await fetch('/api/sql-prompts/test', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        prompt_id: currentPrompt.value.id,
        database_name: testForm.value.database_name,
        database_type: testForm.value.database_type
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      formattedPrompt.value = data.formatted_prompt
      testDialogVisible.value = true
    } else {
      const error = await response.json()
      ElMessage.error(error.error || '测试失败')
    }
  } catch (error) {
    ElMessage.error('测试失败')
  }
}

// 生命周期
onMounted(() => {
  loadPrompts()
})
</script>

<style scoped>
.sql-prompt-manager {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.prompt-list {
  margin-bottom: 20px;
}

.content-preview {
  max-height: 60px;
  overflow: hidden;
  line-height: 20px;
  color: #666;
}

.settings-card {
  margin-bottom: 20px;
}

.card-header {
  font-weight: bold;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.test-result {
  margin-top: 20px;
}

.test-result pre {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
}
</style>
