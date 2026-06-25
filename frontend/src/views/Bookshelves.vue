<template>
  <div class="bookshelf-page">
    <el-row :gutter="16" style="height: 100%;">
      <el-col :span="6" style="height:100%;">
        <el-card class="panel-card">
          <template #header>
            <div class="panel-header">
              <span>数据集书架</span>
              <el-button type="primary" size="small" @click="createDataset">新建</el-button>
            </div>
          </template>
          <el-scrollbar height="calc(100vh - 240px)">
            <div
              v-for="item in datasets"
              :key="item.id"
              class="dataset-item"
              :class="{active: selectedDatasetId === item.id}"
              @click="selectDataset(item)"
            >
              <div class="dataset-name">{{ item.dataset_name }}</div>
              <div class="dataset-meta">{{ item.dataset_code }} · SQL样本 {{ item.golden_sql_count || 0 }}</div>
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>

      <el-col :span="18" style="height:100%;">
        <el-card class="panel-card">
          <template #header>
            <div class="panel-header">
              <span>书架详情维护</span>
              <div>
                <el-button size="small" @click="saveBasic">保存基础信息</el-button>
                <el-button size="small" type="primary" @click="saveFull">保存全量书架内容</el-button>
              </div>
            </div>
          </template>

          <el-empty v-if="!selectedDatasetId" description="请选择或新建一个数据集书架" />
          <template v-else>
            <el-form :model="datasetForm" label-width="110px" class="basic-form">
              <el-row :gutter="12">
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
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item label="绑定数据源">
                    <el-select v-model="datasetForm.source_id" style="width:100%">
                      <el-option v-for="d in dataSources" :key="d.id" :label="d.name" :value="d.id" />
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

            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="说明：书架页用于统一维护数据集隔离的核心资产（替代分散维护），原飞书同步/模型/训练/提示词页面仍保留可用。"
              class="hint"
            />

            <el-tabs v-model="activeTab">
              <el-tab-pane label="Agent1同义词" name="synonyms">
                <div class="toolbar">
                  <el-button size="small" @click="addSynonym">新增同义词</el-button>
                </div>
                <el-table :data="full.synonyms" border size="small">
                  <el-table-column label="同义词">
                    <template #default="{ row }"><el-input v-model="row.synonym" /></template>
                  </el-table-column>
                  <el-table-column label="归一化">
                    <template #default="{ row }"><el-input v-model="row.normalized_synonym" /></template>
                  </el-table-column>
                  <el-table-column label="权重" width="120">
                    <template #default="{ row }"><el-input-number v-model="row.weight" :min="1" :max="10" /></template>
                  </el-table-column>
                  <el-table-column label="操作" width="90">
                    <template #default="{ $index }"><el-button link type="danger" @click="full.synonyms.splice($index,1)">删除</el-button></template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="LLD文档" name="lld">
                <div class="toolbar">
                  <el-button size="small" @click="addLld">新增版本</el-button>
                </div>
                <div v-for="(doc, idx) in full.lld_documents" :key="idx" class="block-card">
                  <el-row :gutter="8">
                    <el-col :span="6"><el-input-number v-model="doc.version" :min="1" /></el-col>
                    <el-col :span="10"><el-input v-model="doc.title" placeholder="标题" /></el-col>
                    <el-col :span="8"><el-button link type="danger" @click="full.lld_documents.splice(idx, 1)">删除</el-button></el-col>
                  </el-row>
                  <el-input type="textarea" v-model="doc.content" :rows="8" placeholder="填写 LLD 业务逻辑、隔离规则、红线..." />
                </div>
              </el-tab-pane>

              <el-tab-pane label="数据字典" name="dictionary">
                <div class="toolbar">
                  <el-button size="small" @click="addDictionary">新增字段映射</el-button>
                </div>
                <el-table :data="full.data_dictionary" border size="small">
                  <el-table-column label="表名"><template #default="{ row }"><el-input v-model="row.table_name" /></template></el-table-column>
                  <el-table-column label="字段"><template #default="{ row }"><el-input v-model="row.column_name" /></template></el-table-column>
                  <el-table-column label="JSONB Key"><template #default="{ row }"><el-input v-model="row.jsonb_key" /></template></el-table-column>
                  <el-table-column label="语义名"><template #default="{ row }"><el-input v-model="row.semantic_name" /></template></el-table-column>
                  <el-table-column label="类型" width="120"><template #default="{ row }"><el-input v-model="row.data_type" /></template></el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.data_dictionary.splice($index,1)">删除</el-button></template></el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="DDL与关联" name="schema">
                <div class="toolbar">
                  <el-button size="small" @click="addSchema">新增DDL</el-button>
                  <el-button size="small" @click="addRelation">新增关联</el-button>
                </div>
                <h4>Schema Definition</h4>
                <el-table :data="full.schema_definition" border size="small">
                  <el-table-column label="表名" width="220"><template #default="{ row }"><el-input v-model="row.table_name" /></template></el-table-column>
                  <el-table-column label="DDL"><template #default="{ row }"><el-input type="textarea" v-model="row.ddl_sql" :rows="3" /></template></el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.schema_definition.splice($index,1)">删除</el-button></template></el-table-column>
                </el-table>
                <h4 style="margin-top:16px">Table Relations</h4>
                <el-table :data="full.table_relations" border size="small">
                  <el-table-column label="左表"><template #default="{ row }"><el-input v-model="row.left_table" /></template></el-table-column>
                  <el-table-column label="左键"><template #default="{ row }"><el-input v-model="row.left_key" /></template></el-table-column>
                  <el-table-column label="右表"><template #default="{ row }"><el-input v-model="row.right_table" /></template></el-table-column>
                  <el-table-column label="右键"><template #default="{ row }"><el-input v-model="row.right_key" /></template></el-table-column>
                  <el-table-column label="关联类型" width="120"><template #default="{ row }"><el-input v-model="row.relation_type" /></template></el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.table_relations.splice($index,1)">删除</el-button></template></el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="Golden SQL(训练实例)" name="golden">
                <div class="toolbar">
                  <el-button size="small" @click="addGolden">新增训练实例</el-button>
                </div>
                <div v-for="(item, idx) in full.golden_sql_samples" :key="idx" class="block-card">
                  <el-row :gutter="8">
                    <el-col :span="6"><el-input v-model="item.intent_type" placeholder="intent(detail/summary)" /></el-col>
                    <el-col :span="6"><el-input-number v-model="item.quality_score" :min="0" :max="100" /></el-col>
                    <el-col :span="12"><el-button link type="danger" @click="full.golden_sql_samples.splice(idx,1)">删除</el-button></el-col>
                  </el-row>
                  <el-input v-model="item.question" placeholder="自然语言问题" />
                  <el-input type="textarea" v-model="item.sql_text" :rows="5" placeholder="标准 PostgreSQL SQL" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="4-Agent提示词" name="prompts">
                <div class="toolbar">
                  <el-button size="small" @click="addPrompt">新增提示词片段</el-button>
                </div>
                <el-table :data="full.agent_prompts" border size="small">
                  <el-table-column label="Agent" width="120">
                    <template #default="{ row }">
                      <el-select v-model="row.agent_no">
                        <el-option :value="1" label="Agent1 路由" />
                        <el-option :value="2" label="Agent2 SQL" />
                        <el-option :value="3" label="Agent3 审计" />
                        <el-option :value="4" label="Agent4 分析" />
                      </el-select>
                    </template>
                  </el-table-column>
                  <el-table-column label="Key" width="180"><template #default="{ row }"><el-input v-model="row.prompt_key" /></template></el-table-column>
                  <el-table-column label="Prompt Content">
                    <template #default="{ row }"><el-input type="textarea" :rows="4" v-model="row.prompt_content" /></template>
                  </el-table-column>
                  <el-table-column label="操作" width="90"><template #default="{ $index }"><el-button link type="danger" @click="full.agent_prompts.splice($index,1)">删除</el-button></template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getDataSources,
  getBookshelfDatasets,
  createBookshelfDataset,
  updateBookshelfDataset,
  getBookshelfDatasetFull,
  saveBookshelfDatasetFull
} from '../api/index.js'

const datasets = ref([])
const dataSources = ref([])
const selectedDatasetId = ref(null)
const activeTab = ref('synonyms')

const datasetForm = reactive({
  dataset_code: '',
  dataset_name: '',
  business_domain: '',
  source_id: null,
  description: '',
  is_active: true
})

const full = reactive({
  synonyms: [],
  lld_documents: [],
  data_dictionary: [],
  schema_definition: [],
  table_relations: [],
  golden_sql_samples: [],
  agent_prompts: []
})

const resetFull = () => {
  full.synonyms = []
  full.lld_documents = []
  full.data_dictionary = []
  full.schema_definition = []
  full.table_relations = []
  full.golden_sql_samples = []
  full.agent_prompts = []
}

const applyDatasetBasic = (dataset) => {
  datasetForm.dataset_code = dataset?.dataset_code || ''
  datasetForm.dataset_name = dataset?.dataset_name || ''
  datasetForm.business_domain = dataset?.business_domain || ''
  datasetForm.source_id = dataset?.source_id || null
  datasetForm.description = dataset?.description || ''
  datasetForm.is_active = dataset?.is_active !== false
}

const loadDatasets = async () => {
  const res = await getBookshelfDatasets()
  datasets.value = res.datasets || []
}

const loadDataSources = async () => {
  const res = await getDataSources()
  dataSources.value = res.databases || []
}

const selectDataset = async (item) => {
  selectedDatasetId.value = item.id
  applyDatasetBasic(item)
  const res = await getBookshelfDatasetFull(item.id)
  full.synonyms = res.synonyms || []
  full.lld_documents = res.lld_documents || []
  full.data_dictionary = res.data_dictionary || []
  full.schema_definition = res.schema_definition || []
  full.table_relations = res.table_relations || []
  full.golden_sql_samples = res.golden_sql_samples || []
  full.agent_prompts = res.agent_prompts || []
}

const createDataset = async () => {
  const res = await createBookshelfDataset({
    dataset_code: `dataset_${Date.now()}`,
    dataset_name: '新数据集',
    business_domain: '未分类',
    source_id: dataSources.value[0]?.id,
    description: ''
  })
  await loadDatasets()
  const target = datasets.value.find(d => d.id === res.dataset?.id)
  if (target) {
    await selectDataset(target)
  }
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
    synonyms: full.synonyms,
    lld_documents: full.lld_documents,
    data_dictionary: full.data_dictionary,
    schema_definition: full.schema_definition,
    table_relations: full.table_relations,
    golden_sql_samples: full.golden_sql_samples,
    agent_prompts: full.agent_prompts
  })
  ElMessage.success('书架内容已保存')
  await loadDatasets()
}

const addSynonym = () => full.synonyms.push({ synonym: '', normalized_synonym: '', weight: 1 })
const addLld = () => full.lld_documents.push({ version: full.lld_documents.length + 1, title: '', content: '', redline_rules: [] })
const addDictionary = () => full.data_dictionary.push({ table_name: '', column_name: '', jsonb_key: '', semantic_name: '', data_type: 'text', enum_mapping: {}, extraction_rule: '' })
const addSchema = () => full.schema_definition.push({ table_name: '', ddl_sql: '', description: '' })
const addRelation = () => full.table_relations.push({ left_table: '', left_key: '', right_table: '', right_key: '', relation_type: 'inner', description: '' })
const addGolden = () => full.golden_sql_samples.push({ intent_type: 'detail', question: '', sql_text: '', tags: [], quality_score: 80 })
const addPrompt = () => full.agent_prompts.push({ agent_no: 1, prompt_key: 'default', prompt_content: '' })

onMounted(async () => {
  try {
    await Promise.all([loadDataSources(), loadDatasets()])
    if (datasets.value.length > 0) {
      await selectDataset(datasets.value[0])
    } else {
      resetFull()
    }
  } catch (e) {
    ElMessage.error(e.message || '初始化失败')
  }
})
</script>

<style scoped>
.bookshelf-page {
  height: 100%;
}
.panel-card {
  height: 100%;
  border: 1px solid var(--border, #E5E7EB);
  background: var(--bg-card, #fff);
  border-radius: var(--radius-card, 12px);
  box-shadow: var(--shadow-xs);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.dataset-item {
  padding: 10px 12px;
  border: 1px solid var(--border, #E5E7EB);
  border-radius: var(--radius-md, 8px);
  margin-bottom: 8px;
  cursor: pointer;
  background: var(--bg-card, #fff);
  transition: all var(--duration-normal, 220ms) var(--ease-out);
}
.dataset-item:hover {
  border-color: var(--border-hover, #D1D5DB);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}
.dataset-item.active {
  border-color: var(--color-primary, #E61F24);
  background: var(--color-primary-light, #FEF2F2);
}
.dataset-name {
  font-weight: 600;
  color: var(--text-title, #111827);
}
.dataset-meta {
  margin-top: 4px;
  color: var(--text-muted, #9CA3AF);
  font-size: 12px;
}
.basic-form {
  margin-bottom: 12px;
}
.hint {
  margin-bottom: 12px;
}
.toolbar {
  margin-bottom: 8px;
}
.block-card {
  border: 1px solid var(--border, #E5E7EB);
  border-radius: var(--radius-md, 8px);
  padding: 12px;
  margin-bottom: 10px;
  background: var(--gray-50, #F8F9FA);
}
</style>
