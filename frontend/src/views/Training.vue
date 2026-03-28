<template>
  <div>
    <el-row :gutter="20" style="margin-bottom:20px">
      <el-col :span="8">
        <el-card><el-statistic title="训练数据总量" :value="trainingData.length" value-style="color:#409EFF" /></el-card>
      </el-col>
      <el-col :span="8">
        <el-card><el-statistic title="问答对" :value="trainingData.filter(t=>t.training_data_type==='sql').length" value-style="color:#67c23a" /></el-card>
      </el-col>
      <el-col :span="8">
        <el-card><el-statistic title="DDL/文档" :value="trainingData.filter(t=>t.training_data_type!=='sql').length" value-style="color:#E6A23C" /></el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 左：添加训练数据 -->
      <el-col :span="10">
        <el-card>
          <template #header><span>➕ 添加训练数据</span></template>

          <el-tabs v-model="addTab">
            <!-- DDL -->
            <el-tab-pane label="📄 DDL 建表语句" name="ddl">
              <el-form label-position="top">
                <el-form-item label="DDL 语句">
                  <el-input v-model="ddlForm.ddl" type="textarea" :rows="8" placeholder="粘贴 CREATE TABLE 语句..." />
                </el-form-item>
                <el-button type="primary" :loading="addingDDL" @click="addDDL">添加 DDL</el-button>
              </el-form>
            </el-tab-pane>

            <!-- 文档 -->
            <el-tab-pane label="📚 文档说明" name="documentation">
              <el-form label-position="top">
                <el-form-item label="文档内容">
                  <el-input v-model="docForm.documentation" type="textarea" :rows="8" placeholder="描述数据库表结构、业务含义..." />
                </el-form-item>
                <el-button type="primary" :loading="addingDoc" @click="addDoc">添加文档</el-button>
              </el-form>
            </el-tab-pane>

            <!-- 问答对 -->
            <el-tab-pane label="💬 问答对 (SQL)" name="sql">
              <el-form label-position="top">
                <el-form-item label="问题（自然语言）">
                  <el-input v-model="sqlForm.question" placeholder="例如：查询最近7天的新增客户数" />
                </el-form-item>
                <el-form-item label="对应的 SQL">
                  <el-input v-model="sqlForm.sql" type="textarea" :rows="6" placeholder="对应的 SQL 语句..." />
                </el-form-item>
                <el-button type="primary" :loading="addingSQL" @click="addSQL">添加问答对</el-button>
              </el-form>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>

      <!-- 右：训练数据列表 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📋 已有训练数据</span>
              <el-button link @click="loadTrainingData">刷新</el-button>
            </div>
          </template>

          <el-table :data="trainingData" v-loading="loading" size="small" max-height="550">
            <el-table-column prop="training_data_type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag :type="typeTagMap[row.training_data_type] || 'info'" size="small">
                  {{ typeNameMap[row.training_data_type] || row.training_data_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="内容预览" min-width="220">
              <template #default="{ row }">
                <el-text size="small" truncated>
                  {{ row.question || row.content || row.ddl || '—' }}
                </el-text>
              </template>
            </el-table-column>
            <el-table-column label="SQL" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <el-text code size="small">{{ row.sql || '' }}</el-text>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <div style="white-space: nowrap">
                  <!-- DDL类型显示修改按钮 -->
                  <el-button 
                    v-if="row.training_data_type === 'ddl'" 
                    link 
                    :icon="Edit" 
                    size="small" 
                    @click="editDDL(row)"
                  >
                    修改
                  </el-button>
                  <!-- 文档类型显示修改按钮 -->
                  <el-button 
                    v-if="row.training_data_type === 'documentation'" 
                    link 
                    :icon="Edit" 
                    size="small" 
                    @click="editDocumentation(row)"
                  >
                    修改
                  </el-button>
                  <!-- 问答对类型显示修改按钮 -->
                  <el-button 
                    v-if="row.training_data_type === 'sql'" 
                    link 
                    :icon="Edit" 
                    size="small" 
                    @click="editSQL(row)"
                  >
                    修改
                  </el-button>
                  <el-popconfirm title="确认删除此训练数据？" @confirm="deleteData(row.id)">
                    <template #reference>
                      <el-button link type="danger" :icon="Delete" size="small">删除</el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!loading && trainingData.length === 0" style="text-align:center;padding:40px;color:#8c8c8c">
            暂无训练数据，请先在左侧添加
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- DDL编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="修改 DDL 训练数据" width="600px">
      <el-form label-position="top">
        <el-form-item label="DDL 语句">
          <el-input 
            v-model="editForm.ddl" 
            type="textarea" 
            :rows="10" 
            placeholder="修改 CREATE TABLE 语句..." 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updatingDDL" @click="updateDDL">保存并重新训练</el-button>
      </template>
    </el-dialog>

    <!-- 文档编辑弹窗 -->
    <el-dialog v-model="editDocDialogVisible" title="修改文档训练数据" width="600px">
      <el-form label-position="top">
        <el-form-item label="文档内容">
          <el-input 
            v-model="editDocForm.documentation" 
            type="textarea" 
            :rows="10" 
            placeholder="修改文档说明内容..." 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDocDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updatingDoc" @click="updateDocumentation">保存并重新训练</el-button>
      </template>
    </el-dialog>

    <!-- 问答对编辑弹窗 -->
    <el-dialog v-model="editSQLDialogVisible" title="修改问答对训练数据" width="600px">
      <el-form label-position="top">
        <el-form-item label="问题（自然语言）">
          <el-input 
            v-model="editSQLForm.question" 
            placeholder="例如：查询最近7天的新增客户数" 
          />
        </el-form-item>
        <el-form-item label="对应的 SQL">
          <el-input 
            v-model="editSQLForm.sql" 
            type="textarea" 
            :rows="6" 
            placeholder="对应的 SQL 语句..." 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editSQLDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updatingSQL" @click="updateSQL">保存并重新训练</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Edit } from '@element-plus/icons-vue'
import { getTrainingData, addTrainingData, deleteTrainingData, batchTrain } from '../api/index.js'

const trainingData = ref([])
const loading = ref(false)
const addTab = ref('ddl')
const addingDDL = ref(false)
const addingDoc = ref(false)
const addingSQL = ref(false)

const ddlForm = ref({ ddl: '' })
const docForm = ref({ documentation: '' })
const sqlForm = ref({ question: '', sql: '' })

// DDL编辑相关
const editDialogVisible = ref(false)
const updatingDDL = ref(false)
const editForm = ref({ id: null, ddl: '' })

// 文档编辑相关
const editDocDialogVisible = ref(false)
const updatingDoc = ref(false)
const editDocForm = ref({ id: null, documentation: '' })

// 问答对编辑相关
const editSQLDialogVisible = ref(false)
const updatingSQL = ref(false)
const editSQLForm = ref({ id: null, question: '', sql: '' })

const typeTagMap = { sql: 'success', ddl: 'primary', documentation: 'warning' }
const typeNameMap = { sql: '问答对', ddl: 'DDL', documentation: '文档' }

const loadTrainingData = async () => {
  loading.value = true
  try { const data = await getTrainingData(); trainingData.value = data.training_data || [] }
  catch (e) { trainingData.value = [] }
  finally { loading.value = false }
}

const addDDL = async () => {
  if (!ddlForm.value.ddl.trim()) { ElMessage.warning('请输入 DDL 语句'); return }
  addingDDL.value = true
  try { await addTrainingData({ type: 'ddl', ddl: ddlForm.value.ddl }); ElMessage.success('DDL 已添加'); ddlForm.value.ddl = ''; loadTrainingData() }
  finally { addingDDL.value = false }
}

const addDoc = async () => {
  if (!docForm.value.documentation.trim()) { ElMessage.warning('请输入文档内容'); return }
  addingDoc.value = true
  try { await addTrainingData({ type: 'documentation', documentation: docForm.value.documentation }); ElMessage.success('文档已添加'); docForm.value.documentation = ''; loadTrainingData() }
  finally { addingDoc.value = false }
}

const addSQL = async () => {
  if (!sqlForm.value.question || !sqlForm.value.sql) { ElMessage.warning('问题和 SQL 都不能为空'); return }
  addingSQL.value = true
  try { await addTrainingData({ type: 'sql', question: sqlForm.value.question, sql: sqlForm.value.sql }); ElMessage.success('问答对已添加'); sqlForm.value = { question:'', sql:'' }; loadTrainingData() }
  finally { addingSQL.value = false }
}

const deleteData = async (id) => {
  await deleteTrainingData(id); ElMessage.success('已删除'); loadTrainingData()
}

// DDL编辑功能
const editDDL = (row) => {
  editForm.value = {
    id: row.id,
    ddl: row.content || row.ddl || ''  // 使用content字段，兼容ddl字段
  }
  editDialogVisible.value = true
}

const updateDDL = async () => {
  if (!editForm.value.ddl.trim()) {
    ElMessage.warning('请输入 DDL 语句')
    return
  }
  
  updatingDDL.value = true
  try {
    // 先删除旧的DDL
    await deleteTrainingData(editForm.value.id)
    
    // 添加新的DDL
    await addTrainingData({ 
      type: 'ddl', 
      ddl: editForm.value.ddl 
    })
    
    // 重新训练Vanna
    await batchTrain({
      ddls: [editForm.value.ddl],
      documentations: [],
      sql_pairs: []
    })
    
    ElMessage.success('DDL 已更新并重新训练完成')
    editDialogVisible.value = false
    loadTrainingData()
  } catch (error) {
    ElMessage.error('更新失败：' + (error.message || '未知错误'))
  } finally {
    updatingDDL.value = false
  }
}

// 文档编辑功能
const editDocumentation = (row) => {
  editDocForm.value = {
    id: row.id,
    documentation: row.content || row.documentation || ''
  }
  editDocDialogVisible.value = true
}

const updateDocumentation = async () => {
  if (!editDocForm.value.documentation.trim()) {
    ElMessage.warning('请输入文档内容')
    return
  }
  
  updatingDoc.value = true
  try {
    // 先删除旧的文档
    await deleteTrainingData(editDocForm.value.id)
    
    // 添加新的文档
    await addTrainingData({ 
      type: 'documentation', 
      documentation: editDocForm.value.documentation 
    })
    
    // 重新训练Vanna
    await batchTrain({
      ddls: [],
      documentations: [editDocForm.value.documentation],
      sql_pairs: []
    })
    
    ElMessage.success('文档已更新并重新训练完成')
    editDocDialogVisible.value = false
    loadTrainingData()
  } catch (error) {
    ElMessage.error('更新失败：' + (error.message || '未知错误'))
  } finally {
    updatingDoc.value = false
  }
}

// 问答对编辑功能
const editSQL = (row) => {
  editSQLForm.value = {
    id: row.id,
    question: row.question || '',
    sql: row.sql || row.content || ''  // 兼容sql和content字段
  }
  editSQLDialogVisible.value = true
}

const updateSQL = async () => {
  if (!editSQLForm.value.question.trim() || !editSQLForm.value.sql.trim()) {
    ElMessage.warning('问题和 SQL 都不能为空')
    return
  }
  
  updatingSQL.value = true
  try {
    // 先删除旧的问答对
    await deleteTrainingData(editSQLForm.value.id)
    
    // 添加新的问答对
    await addTrainingData({ 
      type: 'sql', 
      question: editSQLForm.value.question,
      sql: editSQLForm.value.sql
    })
    
    // 重新训练Vanna
    await batchTrain({
      ddls: [],
      documentations: [],
      sql_pairs: [{
        question: editSQLForm.value.question,
        sql: editSQLForm.value.sql
      }]
    })
    
    ElMessage.success('问答对已更新并重新训练完成')
    editSQLDialogVisible.value = false
    loadTrainingData()
  } catch (error) {
    ElMessage.error('更新失败：' + (error.message || '未知错误'))
  } finally {
    updatingSQL.value = false
  }
}

onMounted(loadTrainingData)
</script>

<style scoped>
.card-header { display:flex; justify-content:space-between; align-items:center; }
</style>
