<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom:20px">
      <el-col :span="6">
        <el-card class="mini-stat"><el-statistic title="数据源总数" :value="connections.length"><template #prefix><el-icon color="#409EFF"><Coin /></el-icon></template></el-statistic></el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat"><el-statistic title="已连接" :value="connections.filter(c=>c.is_active).length" value-style="color:#67c23a" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat"><el-statistic title="MSSQL" :value="connections.filter(c=>c.type==='sqlserver').length" value-style="color:#E6A23C" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-stat"><el-statistic title="MySQL / PGSQL / SQLite" :value="connections.filter(c=>c.type!=='sqlserver').length" value-style="color:#909399" /></el-card>
      </el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>🗄️ 数据源管理</span>
          <el-button type="primary" :icon="Plus" @click="openAdd">添加数据源</el-button>
        </div>
      </template>

      <el-table :data="connections" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="{ row }">
            <el-text strong>{{ row.name }}</el-text>
            <el-tag v-if="row.is_default" type="warning" size="small" style="margin-left:6px">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.type)">{{ row.type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="主机/路径" min-width="160">
          <template #default="{ row }">
            <el-text type="info" size="small">{{ row.type === 'sqlite' ? row.sqlite_path : `${row.host}:${row.port}` }}</el-text>
          </template>
        </el-table-column>
        <el-table-column prop="database_name" label="数据库" width="130" show-overflow-tooltip />
        <el-table-column prop="username" label="用户名" width="100" />
        <el-table-column prop="is_active" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '已启用' : '已禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div style="white-space: nowrap">
              <el-button link :icon="Connection" :loading="testingId === row.id" @click="testConn(row)">测试</el-button>
              <el-button link :icon="Edit" @click="openEdit(row)">编辑</el-button>
              <el-popconfirm title="确认删除此数据源？" @confirm="deleteConn(row.id)">
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
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑数据源' : '添加数据源'" width="600px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="连接名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：生产CRM库" />
        </el-form-item>
        <el-form-item label="数据库类型" prop="type">
          <el-select v-model="form.type" style="width:100%" @change="onTypeChange">
            <el-option label="SQLite（本地文件，无需驱动）" value="sqlite" />
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL (PGSQL)" value="postgresql" />
            <el-option label="SQL Server (MSSQL)" value="sqlserver" />
          </el-select>
        </el-form-item>

        <!-- SQLite -->
        <template v-if="form.type === 'sqlite'">
          <el-form-item label="文件路径" prop="sqlite_path">
            <el-input v-model="form.sqlite_path" placeholder="例如：./test.db 或 D:/data/mydb.db" />
          </el-form-item>
        </template>

        <!-- MySQL / PostgreSQL / MSSQL -->
        <template v-else>
          <el-row :gutter="12">
            <el-col :span="16">
              <el-form-item label="主机地址" prop="host">
                <el-input v-model="form.host" placeholder="localhost 或 IP" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="端口" prop="port">
                <el-input v-model.number="form.port" :placeholder="getDefaultPort()" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="数据库名" prop="database_name">
            <el-input v-model="form.database_name" placeholder="数据库名称" />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="用户名" prop="username">
                <el-input v-model="form.username" placeholder="用户名" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="密码" prop="password">
                <el-input v-model="form.password" type="password" placeholder="密码（留空则不修改）" show-password />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item v-if="form.type === 'sqlserver'" label="ODBC驱动">
            <el-input v-model="form.driver" placeholder="ODBC Driver 17 for SQL Server" />
          </el-form-item>
          <el-form-item v-if="form.type === 'postgresql'" label="驱动类型">
            <el-input v-model="form.driver" placeholder="psycopg2" />
          </el-form-item>
        </template>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设为默认">
              <el-switch v-model="form.is_default" />
            </el-form-item>
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
import { Plus, Edit, Delete, Connection } from '@element-plus/icons-vue'
import { getDataSources, createDataSource, updateDataSource, deleteDataSource, testDataSource } from '../api/index.js'

const connections = ref([])
const loading = ref(false)
const saving = ref(false)
const testingId = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()

const defaultForm = () => ({ name:'', type:'sqlite', sqlite_path:'./test.db', host:'', port:3306, database_name:'', username:'', password:'', driver:'psycopg2', is_active:true, is_default:false })
const form = ref(defaultForm())

const rules = {
  name: [{ required: true, message: '请输入连接名称' }],
  type: [{ required: true, message: '请选择类型' }],
}

const typeTag = (type) => ({ sqlite:'info', mysql:'success', postgresql:'primary', sqlserver:'warning' }[type] || 'primary')

const loadData = async () => {
  loading.value = true
  try { const data = await getDataSources(); connections.value = data.databases || [] }
  finally { loading.value = false }
}

const getDefaultPort = () => {
  switch (form.value.type) {
    case 'mysql': return 3306
    case 'postgresql': return 5432
    case 'sqlserver': return 1433
    default: return 3306
  }
}

const onTypeChange = (t) => { 
  form.value.port = getDefaultPort()
  form.value.driver = t === 'sqlserver' ? 'ODBC Driver 17 for SQL Server' : t === 'postgresql' ? 'psycopg2' : ''
}

const openAdd = () => { isEdit.value = false; form.value = defaultForm(); dialogVisible.value = true }
const openEdit = (row) => {
  isEdit.value = true
  form.value = { ...defaultForm(), ...row, password: '' }
  dialogVisible.value = true
}
const resetForm = () => { formRef.value?.resetFields() }

const submitForm = async () => {
  await formRef.value.validate()
  saving.value = true
  try {
    if (isEdit.value) {
      await updateDataSource(form.value.id, form.value)
      ElMessage.success('数据源已更新')
    } else {
      await createDataSource(form.value)
      ElMessage.success('数据源已添加')
    }
    dialogVisible.value = false
    loadData()
  } finally { saving.value = false }
}

const deleteConn = async (id) => {
  await deleteDataSource(id)
  ElMessage.success('已删除')
  loadData()
}

const testConn = async (row) => {
  testingId.value = row.id
  try {
    const res = await testDataSource(row.id)
    ElMessage.success(res.message || '连接成功')
  } catch (e) {
    // 错误已由拦截器处理
  } finally { testingId.value = null }
}

onMounted(loadData)
</script>

<style scoped>
.card-header { display:flex; justify-content:space-between; align-items:center; }
.mini-stat .el-statistic { padding: 4px 0; }
</style>
