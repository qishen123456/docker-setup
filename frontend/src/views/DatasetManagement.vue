<template>
  <div class="dataset-page">
    <el-row :gutter="18">
      <el-col :span="6">
        <el-card class="glass-card sidebar-card">
          <template #header>
            <div class="header-row">
              <div class="panel-title">数据集列表</div>
              <el-button type="primary" size="small" @click="createDataset">新建</el-button>
            </div>
          </template>

          <div class="toolbar-col">
            <el-select v-model="listFilterSourceId" clearable placeholder="按默认来源筛选">
              <el-option label="全部来源" value="" />
              <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
            </el-select>
            <el-select v-model="newDatasetSourceId" clearable placeholder="新建时默认来源（可空）">
              <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
            </el-select>
          </div>

          <div
            v-for="item in filteredDatasets"
            :key="item.id"
            class="dataset-tile"
            :class="{ active: selectedDatasetId === item.id }"
            @click="selectDataset(item)"
          >
            <div class="dataset-tile-title">{{ item.dataset_name || '未命名数据集' }}</div>
            <div class="dataset-tile-meta">{{ item.dataset_code }}</div>
            <div class="dataset-tile-sub">
              SQL样本 {{ item.golden_sql_count || 0 }} · 默认来源 {{ sourceNameById(item.source_id) }}
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card class="glass-card">
          <template #header>
            <div class="header-row">
              <div class="panel-title">数据集书架维护（跨数据源混搭）</div>
              <div class="header-actions">
                <el-button @click="saveBasic">保存基础信息</el-button>
                <el-button type="danger" plain @click="removeDataset" :disabled="!selectedDatasetId">删除数据集</el-button>
                <el-button type="warning" @click="importLegacy">导入历史训练/飞书/SQL提示词</el-button>
                <el-button type="primary" @click="saveFull">保存书架内容</el-button>
              </div>
            </div>
          </template>

          <el-empty v-if="!selectedDatasetId" description="请选择一个数据集后开始维护。" />
          <template v-else>
            <el-form label-width="120px" class="base-form">
              <el-row :gutter="14">
                <el-col :span="8">
                  <el-form-item label="数据集编码">
                    <el-input v-model="datasetForm.dataset_code" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="数据集名称">
                    <el-input v-model="datasetForm.dataset_name" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="业务域">
                    <el-input v-model="datasetForm.business_domain" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="14">
                <el-col :span="8">
                  <el-form-item label="默认来源(可空)">
                    <el-select v-model="datasetForm.source_id" clearable style="width: 100%">
                      <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="启用状态">
                    <el-switch v-model="datasetForm.is_active" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="描述">
                    <el-input v-model="datasetForm.description" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>

            <el-tabs v-model="activeTab">
              <el-tab-pane label="常见问题" name="common_questions">
                <div class="toolbar"><el-button size="small" @click="addCommonQuestion">新增常见问题</el-button></div>
                <el-table :data="full.common_questions" border>
                  <el-table-column label="问题">
                    <template #default="{ row }"><el-input v-model="row.question_text" /></template>
                  </el-table-column>
                  <el-table-column label="排序" width="140">
                    <template #default="{ row }"><el-input-number v-model="row.sort_order" :min="1" :max="9999" /></template>
                  </el-table-column>
                  <el-table-column label="操作" width="90">
                    <template #default="{ $index }"><el-button link type="danger" @click="full.common_questions.splice($index, 1)">删除</el-button></template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="路由词/别名" name="synonyms">
                <div class="toolbar"><el-button size="small" @click="addSynonym">新增路由词</el-button></div>
                <el-table :data="full.synonyms" border>
                  <el-table-column label="同义词"><template #default="{ row }"><el-input v-model="row.synonym" /></template></el-table-column>
                  <el-table-column label="归一词"><template #default="{ row }"><el-input v-model="row.normalized_synonym" /></template></el-table-column>
                  <el-table-column label="权重" width="120"><template #default="{ row }"><el-input-number v-model="row.weight" :min="1" :max="10" /></template></el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.synonyms.splice($index, 1)">删除</el-button></template></el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="LLD 文档" name="lld">
                <div class="toolbar"><el-button size="small" @click="addLld">新增 LLD</el-button></div>
                <div v-for="(item, index) in full.lld_documents" :key="`lld-${index}`" class="editor-card">
                  <div class="editor-row">
                    <el-input-number v-model="item.version" :min="1" />
                    <el-input v-model="item.title" placeholder="标题" />
                    <el-button link type="danger" @click="full.lld_documents.splice(index, 1)">删除</el-button>
                  </div>
                  <el-input v-model="item.content" type="textarea" :rows="8" placeholder="业务逻辑、红线、隔离规则..." />
                </div>
              </el-tab-pane>

              <el-tab-pane label="数据字典" name="dictionary">
                <div class="toolbar"><el-button size="small" @click="addDictionary">新增字段</el-button></div>
                <el-table :data="full.data_dictionary" border>
                  <el-table-column label="表名"><template #default="{ row }"><el-input v-model="row.table_name" /></template></el-table-column>
                  <el-table-column label="字段"><template #default="{ row }"><el-input v-model="row.column_name" /></template></el-table-column>
                  <el-table-column label="JSONB Key"><template #default="{ row }"><el-input v-model="row.jsonb_key" /></template></el-table-column>
                  <el-table-column label="语义名"><template #default="{ row }"><el-input v-model="row.semantic_name" /></template></el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.data_dictionary.splice($index, 1)">删除</el-button></template></el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="DDL + 表关联" name="schema">
                <div class="toolbar">
                  <el-button size="small" @click="openSourceTableDialog">从数据源拉表</el-button>
                  <el-button size="small" @click="addSchema">新增DDL</el-button>
                  <el-button size="small" @click="addRelation">新增关联</el-button>
                </div>
                <div class="section-title">表清单和 DDL（可混搭多数据源）</div>
                <el-table :data="full.schema_definition" border>
                  <el-table-column label="来源" width="180">
                    <template #default="{ row }">
                      <el-select v-model="row.source_id" clearable placeholder="来源">
                        <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
                      </el-select>
                    </template>
                  </el-table-column>
                  <el-table-column label="表名" width="240"><template #default="{ row }"><el-input v-model="row.table_name" /></template></el-table-column>
                  <el-table-column label="DDL"><template #default="{ row }"><el-input v-model="row.ddl_sql" type="textarea" :rows="3" /></template></el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.schema_definition.splice($index, 1)">删除</el-button></template></el-table-column>
                </el-table>

                <div class="section-title">表关联</div>
                <el-table :data="full.table_relations" border>
                  <el-table-column label="左表"><template #default="{ row }"><el-input v-model="row.left_table" /></template></el-table-column>
                  <el-table-column label="左键"><template #default="{ row }"><el-input v-model="row.left_key" /></template></el-table-column>
                  <el-table-column label="右表"><template #default="{ row }"><el-input v-model="row.right_table" /></template></el-table-column>
                  <el-table-column label="右键"><template #default="{ row }"><el-input v-model="row.right_key" /></template></el-table-column>
                  <el-table-column label="关系"><template #default="{ row }"><el-input v-model="row.relation_type" /></template></el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.table_relations.splice($index, 1)">删除</el-button></template></el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="Golden SQL" name="golden">
                <div class="toolbar"><el-button size="small" @click="addGolden">新增训练实例</el-button></div>
                <div v-for="(item, index) in full.golden_sql_samples" :key="`golden-${index}`" class="editor-card">
                  <div class="editor-row">
                    <el-input v-model="item.intent_type" placeholder="intent" />
                    <el-input-number v-model="item.quality_score" :min="0" :max="100" />
                    <el-button link type="danger" @click="full.golden_sql_samples.splice(index, 1)">删除</el-button>
                  </div>
                  <el-input v-model="item.question" placeholder="自然语言问题" />
                  <el-input v-model="item.sql_text" type="textarea" :rows="6" placeholder="标准 PostgreSQL SQL" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="数据集 Agent 提示片段" name="prompts">
                <div class="toolbar"><el-button size="small" @click="addPrompt">新增片段</el-button></div>
                <el-table :data="full.agent_prompts" border>
                  <el-table-column label="Agent" width="120">
                    <template #default="{ row }">
                      <el-select v-model="row.agent_no">
                        <el-option :value="1" label="Agent1" />
                        <el-option :value="2" label="Agent2" />
                        <el-option :value="3" label="Agent3" />
                        <el-option :value="4" label="Agent4" />
                      </el-select>
                    </template>
                  </el-table-column>
                  <el-table-column label="Key" width="180"><template #default="{ row }"><el-input v-model="row.prompt_key" /></template></el-table-column>
                  <el-table-column label="Prompt"><template #default="{ row }"><el-input v-model="row.prompt_content" type="textarea" :rows="3" /></template></el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.agent_prompts.splice($index, 1)">删除</el-button></template></el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="飞书/外部配置" name="external">
                <div class="toolbar"><el-button size="small" @click="addExternalConfig">新增配置</el-button></div>
                <el-table :data="full.external_configs" border>
                  <el-table-column label="类型" width="140"><template #default="{ row }"><el-input v-model="row.config_type" /></template></el-table-column>
                  <el-table-column label="Key" width="220"><template #default="{ row }"><el-input v-model="row.config_key" /></template></el-table-column>
                  <el-table-column label="配置(JSON)">
                    <template #default="{ row }">
                      <el-input type="textarea" :rows="4" :model-value="jsonString(row.config_value)" @update:model-value="(v) => updateExternalJson(row, v)" />
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.external_configs.splice($index, 1)">删除</el-button></template></el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="sourceDialogVisible" title="从数据源拉表进数据集" width="72%">
      <div class="toolbar-col" style="margin-bottom: 10px">
        <el-select v-model="sourceDialogSourceId" placeholder="选择数据源" style="width: 320px">
          <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
        </el-select>
        <el-button type="primary" @click="loadSourceTables">加载表清单</el-button>
      </div>
      <el-table :data="sourceTables" border @selection-change="onSourceTableSelection">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="full_table_name" label="表名" min-width="260" />
        <el-table-column prop="column_count" label="字段数" width="100" />
        <el-table-column label="DDL预览" min-width="280">
          <template #default="{ row }">
            <el-input :model-value="row.ddl_sql" type="textarea" :rows="2" readonly />
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="sourceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="appendSelectedSourceTables">加入当前数据集</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createBookshelfDataset,
  deleteBookshelfDataset,
  getBookshelfDatasetFull,
  getBookshelfDatasets,
  getDataSources,
  getSourceTables,
  importLegacyToDataset,
  saveBookshelfDatasetFull,
  updateBookshelfDataset
} from '../api/index.js'

const datasets = ref([])
const dataSources = ref([])
const listFilterSourceId = ref('')
const selectedDatasetId = ref(null)
const activeTab = ref('common_questions')
const newDatasetSourceId = ref(null)

const sourceDialogVisible = ref(false)
const sourceDialogSourceId = ref(null)
const sourceTables = ref([])
const selectedSourceTables = ref([])

const datasetForm = reactive({
  dataset_code: '',
  dataset_name: '',
  business_domain: '',
  source_id: null,
  description: '',
  is_active: true
})

const full = reactive({
  common_questions: [],
  synonyms: [],
  lld_documents: [],
  data_dictionary: [],
  schema_definition: [],
  table_relations: [],
  golden_sql_samples: [],
  agent_prompts: [],
  external_configs: []
})

const filteredDatasets = computed(() => {
  if (!listFilterSourceId.value) return datasets.value
  return datasets.value.filter((item) => Number(item.source_id) === Number(listFilterSourceId.value))
})

const sourceNameById = (id) => {
  const item = dataSources.value.find((x) => Number(x.id) === Number(id))
  return item?.name || '未设置'
}

const applyDataset = (dataset) => {
  datasetForm.dataset_code = dataset?.dataset_code || ''
  datasetForm.dataset_name = dataset?.dataset_name || ''
  datasetForm.business_domain = dataset?.business_domain || ''
  datasetForm.source_id = dataset?.source_id || null
  datasetForm.description = dataset?.description || ''
  datasetForm.is_active = dataset?.is_active !== false
}

const resetFull = () => {
  full.common_questions = []
  full.synonyms = []
  full.lld_documents = []
  full.data_dictionary = []
  full.schema_definition = []
  full.table_relations = []
  full.golden_sql_samples = []
  full.agent_prompts = []
  full.external_configs = []
}

const loadDatasets = async () => {
  const result = await getBookshelfDatasets()
  datasets.value = result.datasets || []
}

const loadDataSources = async () => {
  const result = await getDataSources()
  dataSources.value = result.databases || []
  if (!newDatasetSourceId.value && dataSources.value.length > 0) {
    newDatasetSourceId.value = dataSources.value[0].id
  }
}

const selectDataset = async (dataset) => {
  selectedDatasetId.value = dataset.id
  applyDataset(dataset)
  const result = await getBookshelfDatasetFull(dataset.id)
  full.common_questions = result.common_questions || []
  full.synonyms = result.synonyms || []
  full.lld_documents = result.lld_documents || []
  full.data_dictionary = result.data_dictionary || []
  full.schema_definition = result.schema_definition || []
  full.table_relations = result.table_relations || []
  full.golden_sql_samples = result.golden_sql_samples || []
  full.agent_prompts = result.agent_prompts || []
  full.external_configs = result.external_configs || []
}

const createDataset = async () => {
  const result = await createBookshelfDataset({
    dataset_code: `dataset_${Date.now()}`,
    dataset_name: '新数据集',
    business_domain: '未分类',
    source_id: newDatasetSourceId.value || undefined,
    description: ''
  })
  await loadDatasets()
  const target = datasets.value.find((item) => item.id === result.dataset?.id)
  if (target) await selectDataset(target)
}

const removeDataset = async () => {
  if (!selectedDatasetId.value) return
  await ElMessageBox.confirm('确认删除当前数据集吗？删除后会从列表隐藏。', '删除确认', { type: 'warning' })
  await deleteBookshelfDataset(selectedDatasetId.value)
  ElMessage.success('数据集已删除')
  selectedDatasetId.value = null
  resetFull()
  await loadDatasets()
}

const importLegacy = async () => {
  if (!selectedDatasetId.value) {
    ElMessage.warning('请先选择一个数据集')
    return
  }
  const result = await importLegacyToDataset(selectedDatasetId.value, {
    include_query_history: true,
    include_feishu_sync: true,
    include_sql_prompts: true,
    include_ai_models: true,
    max_history: 300
  })
  ElMessage.success(
    `导入完成：SQL ${result.imported.golden_sql_samples}，常见问题 ${result.imported.common_questions}，外部配置 ${result.imported.external_configs}`
  )
  await selectDataset({ id: selectedDatasetId.value, ...datasetForm })
}

const saveBasic = async () => {
  if (!selectedDatasetId.value) return
  await updateBookshelfDataset(selectedDatasetId.value, { ...datasetForm })
  ElMessage.success('基础信息已保存')
  await loadDatasets()
}

const saveFull = async () => {
  if (!selectedDatasetId.value) return
  await saveBookshelfDatasetFull(selectedDatasetId.value, {
    common_questions: full.common_questions,
    synonyms: full.synonyms,
    lld_documents: full.lld_documents,
    data_dictionary: full.data_dictionary,
    schema_definition: full.schema_definition,
    table_relations: full.table_relations,
    golden_sql_samples: full.golden_sql_samples,
    agent_prompts: full.agent_prompts,
    external_configs: full.external_configs
  })
  ElMessage.success('数据集书架内容已保存')
}

const openSourceTableDialog = () => {
  sourceDialogVisible.value = true
  sourceDialogSourceId.value = datasetForm.source_id || dataSources.value[0]?.id || null
  sourceTables.value = []
  selectedSourceTables.value = []
}

const loadSourceTables = async () => {
  if (!sourceDialogSourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }
  const result = await getSourceTables(sourceDialogSourceId.value)
  sourceTables.value = result.tables || []
}

const onSourceTableSelection = (rows) => {
  selectedSourceTables.value = rows || []
}

const appendSelectedSourceTables = () => {
  if (selectedSourceTables.value.length === 0) {
    ElMessage.warning('请先勾选表')
    return
  }
  selectedSourceTables.value.forEach((table) => {
    const exists = full.schema_definition.some((x) => x.table_name === table.full_table_name)
    if (exists) return
    full.schema_definition.push({
      table_name: table.full_table_name,
      ddl_sql: table.ddl_sql || '',
      description: '',
      source_id: sourceDialogSourceId.value
    })
  })
  sourceDialogVisible.value = false
  ElMessage.success('已加入表清单')
}

const addCommonQuestion = () => full.common_questions.push({ question_text: '', sort_order: (full.common_questions.length + 1) * 10, is_active: true })
const addSynonym = () => full.synonyms.push({ synonym: '', normalized_synonym: '', weight: 1 })
const addLld = () => full.lld_documents.push({ version: full.lld_documents.length + 1, title: '', content: '' })
const addDictionary = () => full.data_dictionary.push({ table_name: '', column_name: '', jsonb_key: '', semantic_name: '', data_type: 'text' })
const addSchema = () => full.schema_definition.push({ table_name: '', ddl_sql: '', description: '', source_id: null })
const addRelation = () => full.table_relations.push({ left_table: '', left_key: '', right_table: '', right_key: '', relation_type: 'inner' })
const addGolden = () => full.golden_sql_samples.push({ intent_type: 'detail', question: '', sql_text: '', quality_score: 80 })
const addPrompt = () => full.agent_prompts.push({ agent_no: 1, prompt_key: 'default', prompt_content: '' })
const addExternalConfig = () => full.external_configs.push({ config_type: 'feishu_sync', config_key: `config_${Date.now()}`, config_value: {} })

const jsonString = (value) => {
  try {
    return JSON.stringify(value || {}, null, 2)
  } catch {
    return '{}'
  }
}

const updateExternalJson = (row, text) => {
  try {
    row.config_value = JSON.parse(text || '{}')
  } catch {
    // ignore parse error while typing
  }
}

onMounted(async () => {
  await Promise.all([loadDatasets(), loadDataSources()])
  if (datasets.value.length > 0) await selectDataset(datasets.value[0])
  else resetFull()
})
</script>

<style scoped>
.dataset-page {
  min-height: calc(100vh - 150px);
}
.glass-card {
  border: 1px solid rgba(118, 124, 133, 0.18);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
}
.sidebar-card {
  min-height: calc(100vh - 150px);
}
.panel-title {
  font-size: 18px;
  font-weight: 700;
}
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-actions {
  display: flex;
  gap: 10px;
}
.toolbar-col {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}
.dataset-tile {
  padding: 14px 16px;
  border-radius: 16px;
  margin-bottom: 10px;
  border: 1px solid #d7dbe1;
  background: linear-gradient(135deg, #fcfcfd, #edf1f5);
  cursor: pointer;
}
.dataset-tile.active {
  border-color: #7f8792;
  box-shadow: 0 12px 26px rgba(93, 100, 110, 0.12);
}
.dataset-tile-title {
  font-weight: 700;
}
.dataset-tile-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #707783;
}
.dataset-tile-sub {
  margin-top: 6px;
  font-size: 12px;
  color: #6d7480;
}
.base-form {
  margin-bottom: 12px;
}
.toolbar {
  margin-bottom: 12px;
}
.section-title {
  margin: 18px 0 10px;
  font-weight: 700;
}
.editor-card {
  padding: 14px;
  border: 1px solid #d7dbe1;
  border-radius: 16px;
  margin-bottom: 12px;
  background: rgba(245, 246, 248, 0.72);
}
.editor-row {
  display: grid;
  grid-template-columns: 120px 1fr 90px;
  gap: 12px;
  margin-bottom: 10px;
}
</style>
