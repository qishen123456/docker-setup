<template>
  <div class="dataset-page">
    <el-row :gutter="18">
      <el-col :span="6">
        <el-card class="glass-card sidebar-card">
          <template #header>
            <div class="header-row">
              <div class="panel-title">数据集列表</div>
              <div class="header-actions compact-actions">
                <el-button v-if="isFeatureEnabled('dataset_prompt_generate')" plain size="small" @click="openPromptDatasetDialog">提示词生成</el-button>
                <el-button v-if="isFeatureEnabled('dataset_create')" type="primary" size="small" @click="createDataset">新建</el-button>
              </div>
            </div>
          </template>

          <div class="toolbar-col">
            <el-input v-model="searchKeyword" clearable placeholder="搜索数据集名称/编码..." size="small" />
            <el-radio-group v-model="listStatusFilter" size="small" class="dataset-status-filter">
              <el-radio-button value="all">全部 {{ datasetStatusCounts.all }}</el-radio-button>
              <el-radio-button value="active">启用 {{ datasetStatusCounts.active }}</el-radio-button>
              <el-radio-button value="inactive">停用 {{ datasetStatusCounts.inactive }}</el-radio-button>
            </el-radio-group>
            <el-select v-model="listFilterSourceId" clearable placeholder="按来源筛选" size="small">
              <el-option label="全部来源" value="" />
              <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
            </el-select>
          </div>

          <el-scrollbar height="calc(100vh - 340px)">
            <div
              v-for="item in filteredDatasets"
              :key="item.id"
              class="dataset-tile"
              :class="{ active: selectedDatasetId === item.id, inactive: item.is_active === false, readonly: item.dataset_readonly }"
              @click="onSelectDataset(item)"
            >
              <div class="dataset-tile-head">
                <div class="dataset-tile-title">{{ item.dataset_name || '未命名数据集' }}</div>
                <div class="dataset-tile-tags">
                  <el-tag v-if="item.dataset_readonly" size="small" effect="plain" type="warning">只读</el-tag>
                  <el-tag v-else-if="item.can_edit" size="small" effect="plain" type="success">可编辑</el-tag>
                  <el-tag size="small" effect="plain" :type="item.is_active === false ? 'info' : 'success'">
                    {{ item.is_active === false ? '停用' : '启用' }}
                  </el-tag>
                </div>
              </div>
              <div class="dataset-tile-meta">{{ item.dataset_code }}</div>
              <div class="dataset-tile-sub">
                SQL {{ item.golden_sql_count || 0 }} · {{ sourceNameById(item.source_id) }}
              </div>
            </div>
            <el-empty v-if="filteredDatasets.length === 0" description="没有匹配的数据集" :image-size="60" />
          </el-scrollbar>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card class="glass-card">
          <template #header>
            <div class="header-row">
              <div class="panel-title">
                {{ canViewDatasetShelfDetails ? '数据集书架维护' : '数据集信息' }}
                <el-tag v-if="isDirty" type="warning" size="small" effect="plain" style="margin-left:8px">有未保存修改</el-tag>
              </div>
              <div class="header-actions">
                <el-button v-if="isFeatureEnabled('dataset_autofill')" plain :disabled="!selectedDatasetId || !selectedCanEdit" @click="autofillSelectedDataset">智能补齐</el-button>
                <el-button v-if="isFeatureEnabled('dataset_delete')" type="danger" plain @click="removeDataset" :disabled="!selectedCanDelete">删除</el-button>
                <el-button v-if="canSaveShelfContent" type="primary" :disabled="!isDirty || !canSaveShelfContent" @click="saveFull">保存书架内容</el-button>
              </div>
            </div>
          </template>

          <el-empty v-if="!selectedDatasetId" description="请选择一个数据集后开始维护。" />
          <template v-else>
            <el-alert
              v-if="selectedDatasetReadonly"
              :title="readonlyAlertTitle"
              type="warning"
              :closable="false"
              show-icon
              class="readonly-alert"
            />
            <el-form label-width="120px" class="base-form" :disabled="!selectedCanEdit">
              <el-row :gutter="14">
                <el-col :span="8"><el-form-item label="数据集编码"><el-input v-model="datasetForm.dataset_code" @input="markDirty" /></el-form-item></el-col>
                <el-col :span="8"><el-form-item label="数据集名称"><el-input v-model="datasetForm.dataset_name" @input="markDirty" /></el-form-item></el-col>
                <el-col :span="8"><el-form-item label="业务域"><el-input v-model="datasetForm.business_domain" @input="markDirty" /></el-form-item></el-col>
              </el-row>
              <el-row :gutter="14">
                <el-col :span="8">
                  <el-form-item label="默认来源(可空)">
                    <el-select v-model="datasetForm.source_id" clearable style="width:100%" @change="markDirty">
                      <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8"><el-form-item label="启用状态"><el-switch v-model="datasetForm.is_active" @change="markDirty" /></el-form-item></el-col>
                <el-col :span="8"><el-form-item label="描述"><el-input v-model="datasetForm.description" @input="markDirty" /></el-form-item></el-col>
              </el-row>
            </el-form>

            <el-alert
              v-if="qualitySummary && canViewDatasetShelfDetails"
              :title="`书架健康度 ${qualitySummary.score} / 100 · ${qualitySummary.label}`"
              :type="qualityAlertType"
              :closable="false"
              show-icon
              class="quality-alert"
            >
              <template #default>
                <div class="quality-overview">
                  <el-progress :percentage="qualitySummary.score" :stroke-width="10" :show-text="false" />
                  <div class="quality-checks">
                    <el-tag
                      v-for="item in qualitySummary.checks"
                      :key="item.key"
                      size="small"
                      effect="plain"
                      :type="qualityCheckTagType(item.status)"
                    >
                      {{ item.label }} {{ item.score }}/{{ item.max_score }}
                    </el-tag>
                  </div>
                  <div v-if="qualitySummary.gaps?.length" class="quality-gaps">
                    <div v-for="(gap, index) in qualitySummary.gaps.slice(0, 4)" :key="index">{{ gap }}</div>
                  </div>
                </div>
              </template>
            </el-alert>

            <div v-if="!canViewDatasetShelfDetails" class="readonly-summary-card">
              <div class="readonly-summary-title">当前账号仅开放数据集基础信息</div>
              <div class="readonly-summary-desc">
                书架维护内容、训练样例、DDL 和 Agent 提示词仅对有维护权限的账号展示；SQL 调试请到智能问数首页使用调试台。
              </div>
              <div class="readonly-summary-grid">
                <div>
                  <span>数据集</span>
                  <strong>{{ datasetForm.dataset_name || '-' }}</strong>
                </div>
                <div>
                  <span>编码</span>
                  <strong>{{ datasetForm.dataset_code || '-' }}</strong>
                </div>
                <div>
                  <span>业务域</span>
                  <strong>{{ datasetForm.business_domain || '-' }}</strong>
                </div>
                <div>
                  <span>状态</span>
                  <strong>{{ datasetForm.is_active === false ? '停用' : '启用' }}</strong>
                </div>
              </div>
            </div>

            <el-tabs v-else v-model="activeTab">
              <!-- 常见问题 -->
              <el-tab-pane label="常见问题" name="common_questions">
                <div class="toolbar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <div><el-button v-if="canUseDatasetAction('question', 'create')" size="small" @click="openItemEditor('question', -1)">新增常见问题</el-button></div>
                  <el-input v-model="tabPagination.common_questions.search" placeholder="搜索问题内容..." size="small" clearable style="width: 220px;" @input="tabPagination.common_questions.page = 1" />
                </div>
                <el-table :data="pagedQuestions.rows" border size="small">
                  <el-table-column label="问题" min-width="300"><template #default="{ row }">{{ row.question_text || '(空)' }}</template></el-table-column>
                  <el-table-column label="排序" width="80"><template #default="{ row }">{{ row.sort_order }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ row }">
                      <el-button v-if="canUseDatasetAction('question', 'update')" link type="primary" @click="openItemEditor('question', row._rawIndex)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('question', 'delete')" link type="danger" @click="deleteCollectionItem('question', row._rawIndex)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div style="margin-top: 10px; display: flex; justify-content: flex-end;">
                  <el-pagination
                    v-model:current-page="tabPagination.common_questions.page"
                    v-model:page-size="tabPagination.common_questions.pageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="pagedQuestions.total"
                    layout="total, sizes, prev, pager, next, jumper"
                    size="small"
                  />
                </div>
              </el-tab-pane>

              <el-tab-pane label="标准题集" name="regression_cases">
                <div class="toolbar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <div><el-button v-if="canUseDatasetAction('regression', 'create')" size="small" @click="openItemEditor('regression', -1)">新增回归题</el-button></div>
                  <el-input v-model="tabPagination.regression_cases.search" placeholder="搜索题干 / 预期焦点..." size="small" clearable style="width: 220px;" @input="tabPagination.regression_cases.page = 1" />
                </div>
                <el-table :data="pagedRegression.rows" border size="small">
                  <el-table-column label="类型" width="110"><template #default="{ row }">{{ row.case_type }}</template></el-table-column>
                  <el-table-column label="问题" min-width="260"><template #default="{ row }">{{ row.question_text || '(空)' }}</template></el-table-column>
                  <el-table-column label="预期焦点" min-width="260"><template #default="{ row }">{{ row.expected_focus || '-' }}</template></el-table-column>
                  <el-table-column label="执行预期" width="120"><template #default="{ row }">{{ row.expected_intent || '-' }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ row }">
                      <el-button v-if="canUseDatasetAction('regression', 'update')" link type="primary" @click="openItemEditor('regression', row._rawIndex)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('regression', 'delete')" link type="danger" @click="deleteCollectionItem('regression', row._rawIndex)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div style="margin-top: 10px; display: flex; justify-content: flex-end;">
                  <el-pagination
                    v-model:current-page="tabPagination.regression_cases.page"
                    v-model:page-size="tabPagination.regression_cases.pageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="pagedRegression.total"
                    layout="total, sizes, prev, pager, next, jumper"
                    size="small"
                  />
                </div>
              </el-tab-pane>

              <!-- 路由词/别名 -->
              <el-tab-pane label="路由词/别名" name="synonyms">
                <div class="toolbar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <div><el-button v-if="canUseDatasetAction('synonym', 'create')" size="small" @click="openItemEditor('synonym', -1)">新增路由词</el-button></div>
                  <el-input v-model="tabPagination.synonyms.search" placeholder="搜索同义词 / 归一词..." size="small" clearable style="width: 220px;" @input="tabPagination.synonyms.page = 1" />
                </div>
                <el-table :data="pagedSynonyms.rows" border size="small">
                  <el-table-column label="同义词" min-width="180"><template #default="{ row }">{{ row.synonym }}</template></el-table-column>
                  <el-table-column label="归一词" min-width="180"><template #default="{ row }">{{ row.normalized_synonym }}</template></el-table-column>
                  <el-table-column label="权重" width="80"><template #default="{ row }">{{ row.weight }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ row }">
                      <el-button v-if="canUseDatasetAction('synonym', 'update')" link type="primary" @click="openItemEditor('synonym', row._rawIndex)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('synonym', 'delete')" link type="danger" @click="deleteCollectionItem('synonym', row._rawIndex)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div style="margin-top: 10px; display: flex; justify-content: flex-end;">
                  <el-pagination
                    v-model:current-page="tabPagination.synonyms.page"
                    v-model:page-size="tabPagination.synonyms.pageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="pagedSynonyms.total"
                    layout="total, sizes, prev, pager, next, jumper"
                    size="small"
                  />
                </div>
              </el-tab-pane>

              <!-- LLD 文档 -->
              <el-tab-pane label="LLD 文档" name="lld">
                <div v-if="canUseDatasetAction('lld', 'create')" class="toolbar"><el-button size="small" @click="openItemEditor('lld', -1)">新增 LLD</el-button></div>
                <el-table :data="full.lld_documents" border size="small">
                  <el-table-column label="版本" width="80"><template #default="{ row }">v{{ row.version }}</template></el-table-column>
                  <el-table-column label="标题" min-width="200"><template #default="{ row }">{{ row.title || '(未命名)' }}</template></el-table-column>
                  <el-table-column label="内容预览" min-width="300"><template #default="{ row }"><div class="text-preview">{{ (row.content || '').slice(0, 80) || '(空)' }}</div></template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button v-if="canUseDatasetAction('lld', 'update')" link type="primary" @click="openItemEditor('lld', $index)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('lld', 'delete')" link type="danger" @click="deleteCollectionItem('lld', $index)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 数据字典 -->
              <el-tab-pane label="数据字典" name="dictionary">
                <div class="toolbar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <div style="display: flex; gap: 8px;">
                    <el-button v-if="canUseDatasetAction('dict', 'create')" size="small" @click="openItemEditor('dict', -1)">新增字段</el-button>
                    <el-button v-if="canUseDatasetFeature('dataset_dict_extract')" size="small" type="success" @click="extractDictFromDDL">从 DDL 提取字段</el-button>
                    <el-button v-if="canUseDatasetFeature('dataset_dict_extract')" size="small" type="primary" :loading="pgDictLoading" @click="extractDictFromPg">从 PG 提取 fields</el-button>
                    <el-button v-if="canUseDatasetAction('dict', 'delete')" size="small" type="danger" plain @click="clearDictionary">清空字段</el-button>
                  </div>
                  <el-input v-model="tabPagination.dictionary.search" placeholder="搜索表名 / 字段 / 语义名..." size="small" clearable style="width: 220px;" @input="tabPagination.dictionary.page = 1" />
                </div>
                <el-table :data="pagedDict.rows" border size="small">
                  <el-table-column label="表名" min-width="160"><template #default="{ row }">{{ row.table_name }}</template></el-table-column>
                  <el-table-column label="字段" min-width="140"><template #default="{ row }">{{ row.column_name }}</template></el-table-column>
                  <el-table-column label="JSONB Key" min-width="120"><template #default="{ row }">{{ row.jsonb_key || '-' }}</template></el-table-column>
                  <el-table-column label="语义名" min-width="140"><template #default="{ row }">{{ row.semantic_name || '-' }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ row }">
                      <el-button v-if="canUseDatasetAction('dict', 'update')" link type="primary" @click="openItemEditor('dict', row._rawIndex)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('dict', 'delete')" link type="danger" @click="deleteCollectionItem('dict', row._rawIndex)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div style="margin-top: 10px; display: flex; justify-content: flex-end;">
                  <el-pagination
                    v-model:current-page="tabPagination.dictionary.page"
                    v-model:page-size="tabPagination.dictionary.pageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="pagedDict.total"
                    layout="total, sizes, prev, pager, next, jumper"
                    size="small"
                  />
                </div>
              </el-tab-pane>

              <!-- DDL + 表关联 (保留原始交互方式，已有 Drawer) -->
              <el-tab-pane label="DDL + 表关联" name="schema">
                <div class="toolbar">
                  <el-button v-if="canUseDatasetFeature('dataset_source_table')" size="small" @click="openSourceTableDialog">从数据源拉表</el-button>
                  <el-button v-if="canUseDatasetFeature('dataset_schema_create')" size="small" @click="addSchema">新增DDL</el-button>
                  <el-button v-if="canUseDatasetAction('relation', 'create')" size="small" @click="openItemEditor('relation', -1)">新增关联</el-button>
                </div>
                <div class="section-title">表清单和 DDL</div>
                <el-table :data="full.schema_definition" border size="small">
                  <el-table-column label="来源" width="140"><template #default="{ row }"><el-tag effect="plain" size="small">{{ sourceNameById(row.source_id) }}</el-tag></template></el-table-column>
                  <el-table-column label="表名" width="200"><template #default="{ row }"><span class="schema-name-cell">{{ row.table_name || '未命名表' }}</span></template></el-table-column>
                  <el-table-column label="DDL 预览" min-width="300"><template #default="{ row }"><div class="ddl-preview-line">{{ ddlPreview(row.ddl_sql) }}</div></template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ row, $index }">
                      <el-button v-if="canUseDatasetFeature('dataset_schema_update')" link type="primary" @click="openSchemaEditor(row, $index)">编辑</el-button>
                      <el-button v-if="canUseDatasetFeature('dataset_schema_delete')" link type="danger" @click="removeSchema($index)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="section-title">表关联</div>
                <el-table :data="full.table_relations" border size="small">
                  <el-table-column label="左表"><template #default="{ row }">{{ row.left_table }}</template></el-table-column>
                  <el-table-column label="左键"><template #default="{ row }">{{ row.left_key }}</template></el-table-column>
                  <el-table-column label="右表"><template #default="{ row }">{{ row.right_table }}</template></el-table-column>
                  <el-table-column label="右键"><template #default="{ row }">{{ row.right_key }}</template></el-table-column>
                  <el-table-column label="类型" width="100"><template #default="{ row }">{{ row.relation_type }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button v-if="canUseDatasetAction('relation', 'update')" link type="primary" @click="openItemEditor('relation', $index)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('relation', 'delete')" link type="danger" @click="deleteCollectionItem('relation', $index)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- Golden SQL -->
              <el-tab-pane label="Golden SQL" name="golden">
                <div class="toolbar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <div><el-button v-if="canUseDatasetAction('golden', 'create')" size="small" @click="openItemEditor('golden', -1)">新增训练实例</el-button></div>
                  <el-input v-model="tabPagination.golden.search" placeholder="搜索问题 / SQL / Intent..." size="small" clearable style="width: 220px;" @input="tabPagination.golden.page = 1" />
                </div>
                <el-table :data="pagedGoldenSql.rows" border size="small">
                  <el-table-column label="Intent" width="100"><template #default="{ row }">{{ row.intent_type }}</template></el-table-column>
                  <el-table-column label="问题" min-width="260"><template #default="{ row }">{{ row.question || '(空)' }}</template></el-table-column>
                  <el-table-column label="SQL 预览" min-width="280"><template #default="{ row }"><div class="ddl-preview-line">{{ (row.sql_text || '').slice(0, 100) || '(空)' }}</div></template></el-table-column>
                  <el-table-column label="分数" width="70"><template #default="{ row }">{{ row.quality_score }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ row }">
                      <el-button v-if="canUseDatasetAction('golden', 'update')" link type="primary" @click="openItemEditor('golden', row._rawIndex)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('golden', 'delete')" link type="danger" @click="deleteCollectionItem('golden', row._rawIndex)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div style="margin-top: 10px; display: flex; justify-content: flex-end;">
                  <el-pagination
                    v-model:current-page="tabPagination.golden.page"
                    v-model:page-size="tabPagination.golden.pageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="pagedGoldenSql.total"
                    layout="total, sizes, prev, pager, next, jumper"
                    size="small"
                  />
                </div>
              </el-tab-pane>

              <!-- Agent 提示片段 -->
              <el-tab-pane label="Agent 提示片段" name="prompts">
                <div class="toolbar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <div><el-button v-if="canUseDatasetAction('prompt', 'create')" size="small" @click="openItemEditor('prompt', -1)">新增片段</el-button></div>
                  <el-input v-model="tabPagination.prompts.search" placeholder="搜索 Key / 内容..." size="small" clearable style="width: 220px;" @input="tabPagination.prompts.page = 1" />
                </div>
                <el-table :data="pagedPrompts.rows" border size="small">
                  <el-table-column label="Agent" width="90"><template #default="{ row }">Agent{{ row.agent_no }}</template></el-table-column>
                  <el-table-column label="Key" width="150"><template #default="{ row }">{{ row.prompt_key }}</template></el-table-column>
                  <el-table-column label="内容预览" min-width="300"><template #default="{ row }"><div class="text-preview">{{ (row.prompt_content || '').slice(0, 120) || '(空)' }}</div></template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ row }">
                      <el-button v-if="canUseDatasetAction('prompt', 'update')" link type="primary" @click="openItemEditor('prompt', row._rawIndex)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('prompt', 'delete')" link type="danger" @click="deleteCollectionItem('prompt', row._rawIndex)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div style="margin-top: 10px; display: flex; justify-content: flex-end;">
                  <el-pagination
                    v-model:current-page="tabPagination.prompts.page"
                    v-model:page-size="tabPagination.prompts.pageSize"
                    :page-sizes="[10, 20, 50, 100]"
                    :total="pagedPrompts.total"
                    layout="total, sizes, prev, pager, next, jumper"
                    size="small"
                  />
                </div>
              </el-tab-pane>

              <!-- 外部配置 -->
              <el-tab-pane label="飞书/外部配置" name="external">
                <div v-if="canUseDatasetAction('extcfg', 'create')" class="toolbar"><el-button size="small" @click="openItemEditor('extcfg', -1)">新增配置</el-button></div>
                <el-table :data="full.external_configs" border size="small">
                  <el-table-column label="类型" width="140"><template #default="{ row }">{{ row.config_type }}</template></el-table-column>
                  <el-table-column label="Key" width="200"><template #default="{ row }">{{ row.config_key }}</template></el-table-column>
                  <el-table-column label="配置预览" min-width="300"><template #default="{ row }"><div class="text-preview">{{ jsonString(row.config_value).slice(0, 100) }}</div></template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button v-if="canUseDatasetAction('extcfg', 'update')" link type="primary" @click="openItemEditor('extcfg', $index)">编辑</el-button>
                      <el-button v-if="canUseDatasetAction('extcfg', 'delete')" link type="danger" @click="deleteCollectionItem('extcfg', $index)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 数据转换 -->
              <el-tab-pane label="数据转换" name="transforms">
                <div class="toolbar">
                  <el-button
                    v-if="isFeatureEnabled('dataset_transform_edit') && selectedCanEdit"
                    size="small"
                    type="primary"
                    @click="openTransformEditor()"
                  >新增转换任务</el-button>
                  <el-button size="small" @click="loadTransforms" :loading="transformLoading">刷新</el-button>
                </div>
                <el-table :data="transforms" border size="small" v-loading="transformLoading">
                  <el-table-column label="任务名称" min-width="160">
                    <template #default="{ row }">{{ row.name }}</template>
                  </el-table-column>
                  <el-table-column label="源表 → 目标" min-width="220">
                    <template #default="{ row }">
                      <div>{{ row.source_table }} →</div>
                      <div><el-tag size="small" effect="plain">{{ row.target_type }}</el-tag> {{ row.target_name }}</div>
                    </template>
                  </el-table-column>
                  <el-table-column label="自动执行" width="90">
                    <template #default="{ row }">{{ row.auto_run_on_sync ? '是' : '否' }}</template>
                  </el-table-column>
                  <el-table-column label="状态" width="140">
                    <template #default="{ row }">
                      <div v-if="row.last_run_status">
                        <el-tag :type="row.last_run_status === 'success' ? 'success' : 'danger'" size="small" effect="light">{{ row.last_run_status }}</el-tag>
                        <div class="text-muted" style="font-size: 11px;">{{ formatTime(row.last_run_at) }}</div>
                      </div>
                      <span v-else class="text-muted">尚未执行</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="180" fixed="right">
                    <template #default="{ row }">
                      <el-button link type="primary" size="small" :loading="transformRunLoading[row.id]" @click="handleRunTransform(row)">执行</el-button>
                      <el-button v-if="isFeatureEnabled('dataset_transform_edit') && selectedCanEdit" link type="primary" size="small" @click="openTransformEditor(row)">编辑</el-button>
                      <el-button v-if="isFeatureEnabled('dataset_transform_edit') && selectedCanEdit" link type="danger" size="small" @click="handleDeleteTransform(row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <!-- ========== 通用编辑弹窗 ========== -->
    <el-dialog v-model="itemEditorVisible" :title="itemEditorTitle" width="680px" destroy-on-close top="6vh">
      <!-- 常见问题编辑 -->
      <el-form v-if="itemEditorType === 'question'" label-width="80px">
        <el-form-item label="问题"><el-input v-model="itemDraft.question_text" placeholder="输入常见问题文本" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="itemDraft.sort_order" :min="1" :max="9999" /></el-form-item>
      </el-form>

      <el-form v-if="itemEditorType === 'regression'" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="题型">
              <el-select v-model="itemDraft.case_type" style="width:100%">
                <el-option value="detail" label="明细题" />
                <el-option value="summary" label="汇总题" />
                <el-option value="trend" label="趋势题" />
                <el-option value="confirmation" label="口径确认题" />
                <el-option value="cross_dataset" label="跨数据集题" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="排序"><el-input-number v-model="itemDraft.sort_order" :min="1" :max="9999" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="问题"><el-input v-model="itemDraft.question_text" placeholder="输入标准回归题" /></el-form-item>
        <el-form-item label="预期焦点">
          <el-input v-model="itemDraft.expected_focus" type="textarea" :rows="4" resize="vertical" placeholder="例如：应命中商用事业部数据集；应先触发组织口径确认；结果应包含月度趋势。" />
        </el-form-item>
        <el-form-item label="执行预期">
          <el-select v-model="itemDraft.expected_intent" style="width:100%">
            <el-option value="direct_execute" label="直接执行" />
            <el-option value="generate_sql" label="生成 SQL" />
            <el-option value="requires_confirmation" label="需要确认" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 同义词编辑 -->
      <el-form v-if="itemEditorType === 'synonym'" label-width="80px">
        <el-form-item label="同义词"><el-input v-model="itemDraft.synonym" /></el-form-item>
        <el-form-item label="归一词"><el-input v-model="itemDraft.normalized_synonym" /></el-form-item>
        <el-form-item label="权重"><el-input-number v-model="itemDraft.weight" :min="1" :max="10" /></el-form-item>
      </el-form>

      <!-- LLD 编辑 -->
      <el-form v-if="itemEditorType === 'lld'" label-width="80px">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="版本"><el-input-number v-model="itemDraft.version" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="16"><el-form-item label="标题"><el-input v-model="itemDraft.title" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="内容">
          <el-input v-model="itemDraft.content" type="textarea" :rows="18" resize="vertical" placeholder="业务逻辑、红线、隔离规则..." class="mono-textarea" />
        </el-form-item>
      </el-form>

      <!-- 数据字典编辑 -->
      <el-form v-if="itemEditorType === 'dict'" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="表名"><el-input v-model="itemDraft.table_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="字段名"><el-input v-model="itemDraft.column_name" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="JSONB Key"><el-input v-model="itemDraft.jsonb_key" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="语义名"><el-input v-model="itemDraft.semantic_name" /></el-form-item></el-col>
        </el-row>
      </el-form>

      <!-- 表关联编辑 -->
      <el-form v-if="itemEditorType === 'relation'" label-width="80px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="左表"><el-input v-model="itemDraft.left_table" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="左键"><el-input v-model="itemDraft.left_key" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="右表"><el-input v-model="itemDraft.right_table" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="右键"><el-input v-model="itemDraft.right_key" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="关联类型"><el-input v-model="itemDraft.relation_type" placeholder="inner / left / right" /></el-form-item>
      </el-form>

      <!-- Golden SQL 编辑 -->
      <el-form v-if="itemEditorType === 'golden'" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="Intent"><el-input v-model="itemDraft.intent_type" placeholder="detail / summary" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="质量分"><el-input-number v-model="itemDraft.quality_score" :min="0" :max="100" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="自然语言问题"><el-input v-model="itemDraft.question" /></el-form-item>
        <el-form-item label="标准 SQL">
          <el-input v-model="itemDraft.sql_text" type="textarea" :rows="14" resize="vertical" placeholder="标准 PostgreSQL SQL" class="mono-textarea" />
        </el-form-item>
      </el-form>

      <!-- Agent 提示词编辑 -->
      <el-form v-if="itemEditorType === 'prompt'" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="Agent">
              <el-select v-model="itemDraft.agent_no" style="width:100%">
                <el-option :value="1" label="Agent1" /><el-option :value="2" label="Agent2" />
                <el-option :value="3" label="Agent3" /><el-option :value="4" label="Agent4" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="16"><el-form-item label="Key"><el-input v-model="itemDraft.prompt_key" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="Prompt 内容">
          <el-input v-model="itemDraft.prompt_content" type="textarea" :rows="16" resize="vertical" placeholder="在这里编辑完整的提示词内容..." class="mono-textarea" />
        </el-form-item>
      </el-form>

      <!-- 外部配置编辑 -->
      <el-form v-if="itemEditorType === 'extcfg'" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="10"><el-form-item label="类型"><el-input v-model="itemDraft.config_type" /></el-form-item></el-col>
          <el-col :span="14"><el-form-item label="Key"><el-input v-model="itemDraft.config_key" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="配置 JSON">
          <el-input v-model="itemDraftJson" type="textarea" :rows="14" resize="vertical" class="mono-textarea" placeholder='{"key": "value"}' />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="itemEditorVisible = false">取消</el-button>
        <el-button v-if="canSaveItemEditor" type="primary" @click="saveItemEditor">确认保存</el-button>
      </template>
    </el-dialog>

    <!-- 大段提示词生成数据集 -->
    <el-dialog
      v-model="promptDatasetVisible"
      title="根据提示词生成新数据集"
      width="1120px"
      class="prompt-dataset-dialog"
      destroy-on-close
      top="3vh"
      :close-on-click-modal="!promptDatasetLoading"
    >
      <div class="prompt-generate-shell">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="把 DDL、fields 字段字典、LLD、Agent2/Agent4 提示词、示例 SQL 粘贴进来，系统会生成一套新的数据集书架内容。"
        />
        <div v-if="promptDatasetLoading || promptDatasetStatus" class="prompt-progress-panel">
          <div class="prompt-progress-head">
            <div>
              <strong>{{ promptDatasetStageTitle }}</strong>
              <span>{{ promptDatasetStatus }}</span>
            </div>
            <em>{{ promptDatasetElapsedText }}</em>
          </div>
          <el-progress :percentage="promptDatasetProgress" :status="promptDatasetProgress === 100 ? 'success' : undefined" />
          <div class="prompt-stage-strip">
            <div
              v-for="(step, index) in PROMPT_DATASET_STEPS"
              :key="step"
              class="prompt-stage"
              :class="{ active: index === promptDatasetStepIndex, done: index < promptDatasetStepIndex }"
            >
              <span>{{ index + 1 }}</span>
              <strong>{{ step }}</strong>
            </div>
          </div>
          <div class="prompt-progress-note">
            AI 正在阅读大段文档并生成 DDL、字段字典、Golden SQL 和 Agent Prompt，复杂提示词通常需要 1-5 分钟。页面有耗时和阶段反馈，失败后会给出具体原因和建议。
          </div>
        </div>
        <el-form label-width="112px" class="prompt-generate-form">
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="绑定数据源">
                <el-select v-model="promptDatasetForm.source_id" clearable style="width:100%">
                  <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="参考样式">
                <el-select v-model="promptDatasetForm.style_dataset_id" clearable placeholder="可选：参考当前某个数据集的书架风格" style="width:100%">
                  <el-option v-for="item in datasets" :key="item.id" :label="item.dataset_name" :value="item.id" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="8"><el-form-item label="名称覆盖"><el-input v-model="promptDatasetForm.dataset_name" placeholder="可空，AI 自动推断" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="编码覆盖"><el-input v-model="promptDatasetForm.dataset_code" placeholder="可空，AI 自动推断" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="业务域覆盖"><el-input v-model="promptDatasetForm.business_domain" placeholder="可空，AI 自动推断" /></el-form-item></el-col>
          </el-row>
          <el-form-item label="大段提示词">
            <el-input
              v-model="promptDatasetForm.doc_text"
              type="textarea"
              :rows="16"
              resize="vertical"
              class="mono-textarea"
              placeholder="粘贴 DDL、字段字典、业务口径、报告要求、Agent 提示词、示例 SQL 等内容..."
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button v-if="!promptDatasetLoading" @click="promptDatasetVisible = false">取消</el-button>
        <el-button v-else plain type="warning" @click="cancelPromptDatasetGeneration">停止生成</el-button>
        <el-button type="primary" :loading="promptDatasetLoading" @click="generateDatasetFromPrompt">
          生成并保存新数据集
        </el-button>
      </template>
    </el-dialog>

    <!-- 从数据源拉表 dialog -->
    <el-dialog v-model="sourceDialogVisible" title="从数据源拉表进数据集" width="72%">
      <div class="toolbar-col" style="margin-bottom:10px">
        <el-select v-model="sourceDialogSourceId" placeholder="选择数据源" style="width:320px">
          <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
        </el-select>
        <el-button v-if="canUseDatasetFeature('dataset_source_table')" type="primary" @click="loadSourceTables">加载表清单</el-button>
      </div>
      <el-table :data="sourceTables" border @selection-change="onSourceTableSelection">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="full_table_name" label="表名" min-width="260" />
        <el-table-column prop="column_count" label="字段数" width="100" />
        <el-table-column label="DDL预览" min-width="280">
          <template #default="{ row }"><el-input :model-value="row.ddl_sql" type="textarea" :rows="2" readonly /></template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="sourceDialogVisible = false">取消</el-button>
        <el-button v-if="canUseDatasetFeature('dataset_source_table')" type="primary" @click="appendSelectedSourceTables">
          加入当前数据集{{ selectedSourceTables.length > 0 ? ` (${selectedSourceTables.length} 张表)` : '' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- DDL 编辑 drawer -->
    <el-drawer v-model="schemaEditorVisible" size="72%" destroy-on-close :with-header="false">
      <div class="schema-editor-shell">
        <div class="schema-editor-header">
          <div>
            <div class="panel-title">{{ schemaEditorIndex === -1 ? '新增 DDL' : '编辑 DDL' }}</div>
            <div class="schema-editor-subtitle">独立维护表定义，宽敞编辑不拥挤</div>
          </div>
          <div class="header-actions">
            <el-button @click="schemaEditorVisible = false">关闭</el-button>
            <el-button v-if="canUseDatasetFeature('dataset_schema_update')" type="primary" @click="saveSchemaEditor">保存 DDL</el-button>
          </div>
        </div>
        <el-form label-width="110px" class="schema-editor-form">
          <el-row :gutter="14">
            <el-col :span="8">
              <el-form-item label="来源">
                <el-select v-model="schemaEditor.source_id" clearable placeholder="请选择来源">
                  <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8"><el-form-item label="表名"><el-input v-model="schemaEditor.table_name" placeholder="例如 angel_group_data" /></el-form-item></el-col>
            <el-col :span="8"><el-form-item label="描述"><el-input v-model="schemaEditor.description" placeholder="说明这张表的用途" /></el-form-item></el-col>
          </el-row>
          <el-form-item label="DDL 正文">
            <el-input v-model="schemaEditor.ddl_sql" type="textarea" :rows="24" resize="vertical" class="mono-textarea" placeholder="在这里编辑完整 DDL，支持大段文本" />
          </el-form-item>
        </el-form>
      </div>
    </el-drawer>

    <!-- 数据转换编辑弹窗 -->
    <el-dialog v-model="transformDialogVisible" :title="isTransformEdit ? '编辑转换任务' : '新增转换任务'" width="780px" destroy-on-close top="5vh">
      <el-form label-width="110px" :disabled="!selectedCanEdit">
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="任务名称" required>
              <el-input v-model="transformForm.name" placeholder="例如：电商事业部视图" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="源表" required>
              <el-input v-model="transformForm.source_table" placeholder="例如：feishu_tbldianshang" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="目标类型">
              <el-select v-model="transformForm.target_type" style="width: 100%">
                <el-option label="视图 VIEW" value="view" />
                <el-option label="表 TABLE" value="table" />
                <el-option label="物化视图 MATERIALIZED VIEW" value="materialized_view" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标名称" required>
              <el-input v-model="transformForm.target_name" placeholder="例如：v_feishu_tbldianshang" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="转换 SQL" required>
          <div style="margin-bottom: 6px;">
            <el-button size="small" @click="applyEcommerceTemplate">套用电商事业部模板</el-button>
            <el-button size="small" :loading="transformTestLoading" @click="handleTestTransformSql">测试 SQL</el-button>
            <span class="muted-text" style="margin-left: 8px;">只允许单条 SELECT 或 WITH 语句，可用 <code v-pre>{{source_table}}</code> 占位符</span>
          </div>
          <el-input v-model="transformForm.transform_sql" type="textarea" :rows="14" resize="vertical" placeholder="输入 SELECT 语句..." />
        </el-form-item>
        <el-row :gutter="14">
          <el-col :span="8">
            <el-form-item label="自动执行">
              <el-switch v-model="transformForm.auto_run_on_sync" active-text="源表同步后自动执行" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="启用状态">
              <el-switch v-model="transformForm.is_active" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="绑定同步任务">
              <el-input v-model="transformForm.sync_dependency" placeholder="可选：飞书同步配置名称/ID" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="closeTransformEditor">取消</el-button>
        <el-button type="primary" :loading="transformLoading" @click="saveTransform">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createBookshelfDataset, deleteBookshelfDataset, getBookshelfDatasetFull,
  extractBookshelfDictionaryFromPg, generateBookshelfDatasetFromPrompt, getBookshelfDatasets, getDataSources, getSourceTables,
  saveBookshelfDatasetFull, updateBookshelfDataset,
  getDatasetTransforms, createDatasetTransform, updateDatasetTransform, deleteDatasetTransform,
  runDatasetTransform, testDatasetTransformSql
} from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'
import {
  dedupeGoldenSqlSamples,
  extractSqlSamplesFromPrompts,
  mergeAutofillCollection,
} from '../utils/datasetAutofillPromptMining.js'

// ========== 基础状态 ==========
const datasets = ref([])
const dataSources = ref([])
const listFilterSourceId = ref('')
const listStatusFilter = ref('active')
const searchKeyword = ref('')
const selectedDatasetId = ref(null)
const activeTab = ref('common_questions')
const isDirty = ref(false)
const newDatasetSourceId = ref(null)
const qualitySummary = ref(null)
const pgDictLoading = ref(false)
const promptDatasetVisible = ref(false)
const promptDatasetLoading = ref(false)
const promptDatasetStatus = ref('')
const promptDatasetStepIndex = ref(-1)
const promptDatasetProgress = ref(0)
const promptDatasetElapsed = ref(0)
let promptDatasetTimer = null
let promptDatasetAbortController = null
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()

const PROMPT_DATASET_STEPS = ['准备输入', 'AI 生成', '校验质量', '创建数据集', '保存书架']
const promptDatasetStageTitle = computed(() => {
  if (promptDatasetStepIndex.value < 0) return '等待开始'
  return PROMPT_DATASET_STEPS[promptDatasetStepIndex.value] || '处理中'
})
const promptDatasetElapsedText = computed(() => {
  if (!promptDatasetElapsed.value) return '尚未开始'
  const minutes = Math.floor(promptDatasetElapsed.value / 60)
  const seconds = promptDatasetElapsed.value % 60
  return `已用时 ${minutes}:${String(seconds).padStart(2, '0')}`
})

const datasetForm = reactive({ dataset_code: '', dataset_name: '', business_domain: '', source_id: null, description: '', is_active: true })
const promptDatasetForm = reactive({
  source_id: null,
  style_dataset_id: null,
  dataset_name: '',
  dataset_code: '',
  business_domain: '',
  doc_text: '',
})
const full = reactive({
  common_questions: [], regression_cases: [], synonyms: [], lld_documents: [], data_dictionary: [],
  schema_definition: [], table_relations: [], golden_sql_samples: [],
  agent_prompts: [], external_configs: []
})

const transforms = ref([])
const transformDialogVisible = ref(false)
const transformEditId = ref(null)
const transformLoading = ref(false)
const transformRunLoading = ref({})
const transformTestLoading = ref(false)
const transformForm = reactive({
  name: '',
  source_table: '',
  target_type: 'view',
  target_name: '',
  transform_sql: '',
  is_active: true,
  auto_run_on_sync: false,
  sync_dependency: ''
})
const isTransformEdit = computed(() => Boolean(transformEditId.value))

const selectedDataset = computed(() => datasets.value.find(item => Number(item.id) === Number(selectedDatasetId.value)) || null)
const selectedCanEdit = computed(() => Boolean(selectedDataset.value?.can_edit))
const selectedCanDelete = computed(() => Boolean(selectedDataset.value?.can_delete))
const selectedDatasetScopeHit = computed(() => Boolean(selectedDataset.value?.dataset_scope_hit || selectedCanEdit.value))
const selectedDatasetReadonly = computed(() => Boolean(selectedDataset.value?.dataset_readonly || (selectedDatasetId.value && !selectedCanEdit.value)))
const datasetItemActionFeatureKeys = [
  'dataset_question_create', 'dataset_question_update', 'dataset_question_delete',
  'dataset_regression_create', 'dataset_regression_update', 'dataset_regression_delete',
  'dataset_synonym_create', 'dataset_synonym_update', 'dataset_synonym_delete',
  'dataset_lld_create', 'dataset_lld_update', 'dataset_lld_delete',
  'dataset_dict_create', 'dataset_dict_update', 'dataset_dict_delete',
  'dataset_schema_create', 'dataset_schema_update', 'dataset_schema_delete',
  'dataset_relation_create', 'dataset_relation_update', 'dataset_relation_delete',
  'dataset_golden_create', 'dataset_golden_update', 'dataset_golden_delete',
  'dataset_prompt_create', 'dataset_prompt_update', 'dataset_prompt_delete',
  'dataset_extcfg_create', 'dataset_extcfg_update', 'dataset_extcfg_delete',
]
const datasetShelfFeatureKeys = [
  'dataset_save',
  'dataset_prompt_generate',
  'dataset_autofill',
  'dataset_dict_extract',
  'dataset_source_table',
  ...datasetItemActionFeatureKeys,
]
const canViewDatasetShelfDetails = computed(() => Boolean(
  selectedCanEdit.value || datasetShelfFeatureKeys.some(key => isFeatureEnabled(key))
))
const readonlyAlertTitle = computed(() => (
  canViewDatasetShelfDetails.value
    ? '当前数据集为只读状态，仅可查看，不能编辑。'
    : '当前账号仅可查看数据集基础信息，书架维护内容已隐藏。'
))
const canUseDatasetFeature = (key) => Boolean(selectedCanEdit.value && isFeatureEnabled(key))
const datasetItemActionFeatureMap = {
  question: { create: 'dataset_question_create', update: 'dataset_question_update', delete: 'dataset_question_delete' },
  regression: { create: 'dataset_regression_create', update: 'dataset_regression_update', delete: 'dataset_regression_delete' },
  synonym: { create: 'dataset_synonym_create', update: 'dataset_synonym_update', delete: 'dataset_synonym_delete' },
  lld: { create: 'dataset_lld_create', update: 'dataset_lld_update', delete: 'dataset_lld_delete' },
  dict: { create: 'dataset_dict_create', update: 'dataset_dict_update', delete: 'dataset_dict_delete' },
  relation: { create: 'dataset_relation_create', update: 'dataset_relation_update', delete: 'dataset_relation_delete' },
  golden: { create: 'dataset_golden_create', update: 'dataset_golden_update', delete: 'dataset_golden_delete' },
  prompt: { create: 'dataset_prompt_create', update: 'dataset_prompt_update', delete: 'dataset_prompt_delete' },
  extcfg: { create: 'dataset_extcfg_create', update: 'dataset_extcfg_update', delete: 'dataset_extcfg_delete' },
}
const datasetActionFeatureKey = (type, action) => datasetItemActionFeatureMap[type]?.[action] || ''
const canUseDatasetAction = (type, action) => {
  const key = datasetActionFeatureKey(type, action)
  if (type === 'question') {
    return Boolean(selectedDatasetScopeHit.value && isFeatureEnabled(key))
  }
  return canUseDatasetFeature(key)
}
const canModifyCommonQuestions = computed(() => selectedDatasetScopeHit.value && (
  isFeatureEnabled('dataset_question_create')
  || isFeatureEnabled('dataset_question_update')
  || isFeatureEnabled('dataset_question_delete')
))
const canSaveShelfContent = computed(() => selectedDatasetScopeHit.value && (
  isFeatureEnabled('dataset_save') || canModifyCommonQuestions.value
))
const warnReadonly = () => {
  ElMessage.warning(selectedDatasetReadonly.value ? '当前数据集未命中你的员工组织范围，仅可查看。' : '当前账号没有该数据集的编辑权限。')
}
const ensureSelectedCanEdit = () => {
  if (selectedCanEdit.value) return true
  warnReadonly()
  return false
}
const markDirty = () => {
  if (!canSaveShelfContent.value) return
  isDirty.value = true
}
const deleteCollectionItem = async (type, index) => {
  const key = COLLECTIONS[type]
  if (!key || !Array.isArray(full[key])) return
  const removed = full[key].splice(index, 1)
  markDirty()
  // 常见问题支持部分保存；其他类型需具备完整 dataset_save 权限才可自动保存
  const canAutoSave = canUseDatasetFeature('dataset_save') || type === 'question'
  if (!canAutoSave) {
    ElMessage.info('已删除，请记得点击「保存书架内容」后生效')
    return
  }
  const ok = await saveFull()
  if (!ok) {
    full[key].splice(index, 0, ...removed)
  }
}
const qualityAlertType = computed(() => {
  if (!qualitySummary.value) return 'info'
  return qualitySummary.value.level === 'healthy' ? 'success' : qualitySummary.value.level === 'warning' ? 'warning' : 'error'
})
const qualityCheckTagType = (status) => (status === 'healthy' ? 'success' : status === 'warning' ? 'warning' : 'danger')
const isSyybDataset = computed(() => {
  const text = [datasetForm.dataset_name, datasetForm.dataset_code, datasetForm.business_domain].filter(Boolean).join(' ')
  return /商用事业部|安吉尔商用|angel_business/i.test(text)
})
const selectedDatasetName = computed(() => datasetForm.dataset_name || selectedDataset.value?.dataset_name || '当前数据集')

const SYYB_DEFAULT_DDL = `CREATE TABLE angel_group_data (
  id BIGINT,
  fields JSONB
);`

const createSyybTemplate = (sourceId) => ({
  common_questions: [
    { question_text: '商用事业部当前年整体达成率是多少？', sort_order: 10, is_active: true },
    { question_text: '东部分公司当前年达成率和剩余任务是多少？', sort_order: 20, is_active: true },
    { question_text: '哪些代表处达成率最低？', sort_order: 30, is_active: true },
    { question_text: '各业务部当前年开单金额排名如何？', sort_order: 40, is_active: true },
  ],
  regression_cases: [
    {
      case_type: 'summary',
      question_text: '商用事业部当前年整体达成率是多少？',
      expected_focus: '应命中商用事业部数据集，并输出事业部层级汇总达成率。',
      expected_intent: 'generate_sql',
      sort_order: 10,
      is_active: true,
    },
    {
      case_type: 'trend',
      question_text: '东部分公司今年任务和开单差距大吗？',
      expected_focus: '应保留东部分公司过滤意图，并给出剩余任务金额判断。',
      expected_intent: 'generate_sql',
      sort_order: 20,
      is_active: true,
    },
    {
      case_type: 'confirmation',
      question_text: '分公司和代表处分别怎么看业绩？',
      expected_focus: '应触发层级口径确认，避免把下级明细汇总进上级。',
      expected_intent: 'requires_confirmation',
      sort_order: 30,
      is_active: true,
    },
  ],
  synonyms: [
    { synonym: '商用事业部', normalized_synonym: '商用事业部', weight: 10 },
    { synonym: '安吉尔商用', normalized_synonym: '商用事业部', weight: 9 },
    { synonym: '东部分公司', normalized_synonym: '东部分公司', weight: 8 },
    { synonym: '销售业绩', normalized_synonym: '销售业绩', weight: 7 },
  ],
  lld_documents: [
    {
      version: 1,
      title: '商用事业部飞书销售表问数规则',
      content: '核心约束：数据来自 angel_group_data，业务字段位于 fields(JSONB)，年份口径固定为 2026。统计分公司、代表处、业务部等上级层级时，必须排除下级明细行，避免重复累计。金额字段统一先清洗非数字字符后再转 NUMERIC。',
      redline_rules: ['仅允许只读SQL', '必须按2026过滤', '必须执行层级隔离', '默认LIMIT 100'],
      is_active: true,
    },
  ],
  data_dictionary: [
    {
      table_name: 'angel_group_data',
      column_name: 'fields',
      jsonb_key: '事业部',
      semantic_name: '事业部',
      data_type: 'text',
      enum_mapping: {},
      extraction_rule: "CASE WHEN jsonb_typeof(fields->'事业部')='array' THEN fields->'事业部'->0->>'text' ELSE fields->>'事业部' END",
      is_active: true,
    },
    {
      table_name: 'angel_group_data',
      column_name: 'fields',
      jsonb_key: '分公司',
      semantic_name: '分公司',
      data_type: 'text',
      enum_mapping: {},
      extraction_rule: "CASE WHEN jsonb_typeof(fields->'分公司')='array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END",
      is_active: true,
    },
    {
      table_name: 'angel_group_data',
      column_name: 'fields',
      jsonb_key: '代表处',
      semantic_name: '代表处',
      data_type: 'text',
      enum_mapping: {},
      extraction_rule: "CASE WHEN jsonb_typeof(fields->'代表处')='array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END",
      is_active: true,
    },
    {
      table_name: 'angel_group_data',
      column_name: 'fields',
      jsonb_key: '业务代表',
      semantic_name: '业务代表',
      data_type: 'text',
      enum_mapping: {},
      extraction_rule: "CASE WHEN jsonb_typeof(fields->'业务代表')='array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END",
      is_active: true,
    },
    {
      table_name: 'angel_group_data',
      column_name: 'fields',
      jsonb_key: '当前年',
      semantic_name: '当前年',
      data_type: 'text',
      enum_mapping: {},
      extraction_rule: "CASE WHEN jsonb_typeof(fields->'当前年')='array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END",
      is_active: true,
    },
    {
      table_name: 'angel_group_data',
      column_name: 'fields',
      jsonb_key: '总任务（金额）',
      semantic_name: '总任务金额',
      data_type: 'numeric',
      enum_mapping: {},
      extraction_rule: "COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务（金额）')='array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END,'[^0-9.-]','','g'),''),'0')::NUMERIC",
      is_active: true,
    },
    {
      table_name: 'angel_group_data',
      column_name: 'fields',
      jsonb_key: '年度开单金额',
      semantic_name: '年度开单金额',
      data_type: 'numeric',
      enum_mapping: {},
      extraction_rule: "COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'年度开单金额')='array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END,'[^0-9.-]','','g'),''),'0')::NUMERIC",
      is_active: true,
    },
  ],
  schema_definition: [
    {
      table_name: 'angel_group_data',
      ddl_sql: SYYB_DEFAULT_DDL,
      description: '飞书多维表格落库主表，业务字段位于 fields(JSONB)。',
      source_id: sourceId,
      is_active: true,
    },
  ],
  table_relations: [],
  golden_sql_samples: [
    {
      intent_type: 'summary',
      question: '商用事业部当前年整体达成率是多少？',
      sql_text: `WITH 字段提取 AS (
  SELECT
    CASE WHEN jsonb_typeof(fields->'当前年')='array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年,
    CASE WHEN jsonb_typeof(fields->'分公司')='array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END AS 分公司,
    CASE WHEN jsonb_typeof(fields->'代表处')='array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END AS 代表处,
    CASE WHEN jsonb_typeof(fields->'业务代表')='array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END AS 业务代表,
    COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务（金额）')='array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 任务金额,
    COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'年度开单金额')='array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 开单金额
  FROM angel_group_data
), 事业部汇总 AS (
  SELECT 任务金额, 开单金额
  FROM 字段提取
  WHERE 当前年='2026'
    AND 分公司 IS NOT NULL AND 分公司<>''
    AND (代表处 IS NULL OR 代表处='')
    AND (业务代表 IS NULL OR 业务代表='')
)
SELECT
  SUM(任务金额) AS 总任务金额,
  SUM(开单金额) AS 年度开单金额,
  CASE WHEN SUM(任务金额)>0 THEN ROUND(SUM(开单金额)/SUM(任务金额)*100,2) ELSE 0 END AS 达成率,
  ROUND(SUM(任务金额)-SUM(开单金额),2) AS 剩余任务金额
FROM 事业部汇总
LIMIT 100`,
      tags: ['商用事业部', '达成率', '汇总'],
      quality_score: 95,
      is_active: true,
    },
    {
      intent_type: 'detail',
      question: '东部分公司当前年达成率和剩余任务是多少？',
      sql_text: `WITH 字段提取 AS (
  SELECT
    CASE WHEN jsonb_typeof(fields->'当前年')='array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年,
    CASE WHEN jsonb_typeof(fields->'分公司')='array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END AS 分公司,
    CASE WHEN jsonb_typeof(fields->'代表处')='array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END AS 代表处,
    CASE WHEN jsonb_typeof(fields->'业务代表')='array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END AS 业务代表,
    COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务（金额）')='array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 任务金额,
    COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'年度开单金额')='array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 开单金额
  FROM angel_group_data
)
SELECT
  '东部分公司' AS 节点名称,
  SUM(任务金额) AS 总任务金额,
  SUM(开单金额) AS 年度开单金额,
  CASE WHEN SUM(任务金额)>0 THEN ROUND(SUM(开单金额)/SUM(任务金额)*100,2) ELSE 0 END AS 达成率,
  ROUND(SUM(任务金额)-SUM(开单金额),2) AS 剩余任务金额
FROM 字段提取
WHERE 当前年='2026'
  AND 分公司='东部分公司'
  AND (代表处 IS NULL OR 代表处='')
  AND (业务代表 IS NULL OR 业务代表='')
LIMIT 100`,
      tags: ['东部分公司', '分公司', '达成率'],
      quality_score: 92,
      is_active: true,
    },
    {
      intent_type: 'ranking',
      question: '哪些代表处达成率最低？',
      sql_text: `WITH 字段提取 AS (
  SELECT
    CASE WHEN jsonb_typeof(fields->'当前年')='array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年,
    CASE WHEN jsonb_typeof(fields->'分公司')='array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END AS 分公司,
    CASE WHEN jsonb_typeof(fields->'代表处')='array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END AS 代表处,
    CASE WHEN jsonb_typeof(fields->'业务代表')='array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END AS 业务代表,
    COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务（金额）')='array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 任务金额,
    COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'年度开单金额')='array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 开单金额
  FROM angel_group_data
), 代表处汇总 AS (
  SELECT 分公司, 代表处, SUM(任务金额) AS 总任务金额, SUM(开单金额) AS 年度开单金额
  FROM 字段提取
  WHERE 当前年='2026'
    AND 代表处 IS NOT NULL AND 代表处<>''
    AND (业务代表 IS NULL OR 业务代表='')
  GROUP BY 分公司, 代表处
)
SELECT
  分公司,
  代表处,
  总任务金额,
  年度开单金额,
  CASE WHEN 总任务金额>0 THEN ROUND(年度开单金额/总任务金额*100,2) ELSE 0 END AS 达成率
FROM 代表处汇总
ORDER BY 达成率 ASC, 总任务金额 DESC
LIMIT 100`,
      tags: ['代表处', '排行', '低达成率'],
      quality_score: 90,
      is_active: true,
    },
  ],
  agent_prompts: [
    {
      agent_no: 1,
      prompt_key: 'default',
      prompt_content: '你是 Agent1（语义路由与口径守卫）。识别商用事业部问题对应的数据集与统计口径；涉及分公司、代表处、业务部、业务代表等层级时，优先检查是否存在统计歧义，必要时先确认口径。所有当前年相关问题统一按 2026 处理。',
      is_active: true,
    },
    {
      agent_no: 2,
      prompt_key: 'default',
      prompt_content: '你是 Agent2（SQL 生成专家），仅允许输出 PostgreSQL 只读 SQL。表为 angel_group_data，业务字段位于 fields(JSONB)。金额字段必须清洗为 NUMERIC，年份固定过滤 2026，统计上级层级时必须排除下级明细行。',
      is_active: true,
    },
    {
      agent_no: 3,
      prompt_key: 'default',
      prompt_content: '你是 Agent3（SQL 复核官）。复核 SQL 是否只读、安全、可执行，是否正确使用 JSONB 提取、金额清洗、2026 年过滤、层级隔离和 LIMIT 100；若不满足，直接修正并返回 final_sql。',
      is_active: true,
    },
    {
      agent_no: 4,
      prompt_key: 'default',
      prompt_content: '你是 Agent4（业务解读官），面向商用事业部管理层输出结论。先给出整体达成、风险和动作建议，再按事业部、条线、分公司或代表处分层展开，避免空话。',
      is_active: true,
    },
  ],
  external_configs: [
    {
      config_type: 'dataset_meta',
      config_key: 'sql_generation_profile',
      config_value: {
        year_fixed: '2026',
        main_table: 'angel_group_data',
        db_type: 'postgresql',
        jsonb_column: 'fields',
        readonly: true,
      },
      is_active: true,
    },
  ],
})

const mergeCollection = (collectionName, items, keyFn, options = {}) => {
  mergeAutofillCollection(full[collectionName], items, keyFn, options)
}

const quoteIdent = (name) => `"${String(name || '').replace(/"/g, '""')}"`
const quoteTable = (name) => String(name || '').split('.').filter(Boolean).map(quoteIdent).join('.')
const compactName = (value, fallback = '当前数据集') => String(value || fallback).trim() || fallback
const semanticNameOf = (columnName) => {
  const raw = String(columnName || '').trim()
  const lower = raw.toLowerCase()
  const compound = [
    [/(order|deal|sale).*(no|code|number)$/, '订单编号'],
    [/(order|deal|sale).*(amount|money|amt|price)$/, '订单金额'],
    [/(order|deal|sale).*(count|qty|quantity)$/, '订单数量'],
    [/(order|deal|sale).*(status|state)$/, '订单状态'],
    [/(order|deal|sale).*(date|day)$/, '订单日期'],
    [/(region|area|province|city).*name$/, '区域名称'],
    [/(dept|department).*name$/, '部门名称'],
    [/(customer|client).*name$/, '客户名称'],
    [/(product|sku).*name$/, '产品名称'],
    [/(employee|staff|sales).*name$/, '员工名称'],
    [/(company|org|organization).*name$/, '组织名称'],
  ].find(([pattern]) => pattern.test(lower))
  if (compound) return compound[1]
  const mapped = [
    [/^(id|.*_id)$/, '编号'],
    [/(name|title|label|名称|姓名)$/, '名称'],
    [/(code|编码|编号)$/, '编码'],
    [/(date|day|日期)$/, '日期'],
    [/(time|created_at|updated_at|时间)$/, '时间'],
    [/(amount|money|amt|price|金额|价格|费用)$/, '金额'],
    [/(count|qty|quantity|数量)$/, '数量'],
    [/(rate|ratio|percent|比例|率)$/, '比例'],
    [/(status|state|状态)$/, '状态'],
    [/(type|category|分类|类型)$/, '类型'],
    [/(dept|department|部门)$/, '部门'],
    [/(org|organization|company|公司|组织)$/, '组织'],
    [/(region|area|province|city|区域|省|市)$/, '区域'],
  ].find(([pattern]) => pattern.test(lower) || pattern.test(raw))
  if (mapped) return mapped[1]
  return raw
    .replace(/^fields[._-]?/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim() || raw || '字段'
}
const parseDdlColumns = (schema) => {
  const ddl = String(schema?.ddl_sql || '')
  const tableName = compactName(schema?.table_name, 'unknown_table')
  const columns = []
  const colRegex = /^\s*["`']?([\w\u4e00-\u9fa5]+)["`']?\s+([a-zA-Z][\w]*(?:\s*\([^)]*\))?)/gm
  let match
  while ((match = colRegex.exec(ddl)) !== null) {
    const colName = match[1]
    const lower = colName.toLowerCase()
    if (['constraint', 'primary', 'unique', 'index', 'check', 'foreign', 'create', 'alter', 'table', 'key'].includes(lower)) continue
    columns.push({
      table_name: tableName,
      column_name: colName,
      jsonb_key: '',
      semantic_name: semanticNameOf(colName),
      data_type: match[2] || 'text',
      enum_mapping: {},
      extraction_rule: '',
      is_active: true,
    })
  }
  return columns
}
const isNumericType = (type) => /int|numeric|decimal|double|float|real|money|number/i.test(String(type || ''))
const isTextLikeType = (type) => /char|text|varchar|uuid|jsonb?|enum/i.test(String(type || ''))
const buildSelectList = (columns) => {
  const selected = (columns || []).slice(0, 8)
  if (selected.length === 0) return '*'
  return selected.map(col => `${quoteIdent(col.column_name)} AS ${quoteIdent(col.semantic_name || col.column_name)}`).join(',\n  ')
}
const truncateText = (value, max = 3600) => {
  const text = String(value || '').trim()
  return text.length > max ? `${text.slice(0, max)}\n...已截断，完整 DDL 以数据集书架为准。` : text
}
const buildPromptDdlContext = (schemas) => schemas
  .map(item => `表：${item.table_name}\n${truncateText(item.ddl_sql, 2200)}`)
  .join('\n\n')
const buildPromptDictionaryContext = (items) => (items || [])
  .slice(0, 80)
  .map(item => `- ${item.table_name}.${item.column_name}：${item.semantic_name || item.column_name}，类型=${item.data_type || 'unknown'}${item.jsonb_key ? `，JSON key=${item.jsonb_key}` : ''}`)
  .join('\n')
const buildAgent1Prompt = ({ datasetName, domain, promptTableNames }) => `你是 Agent1（语义路由与口径守卫）。
当前数据集：「${datasetName}」
业务域：「${domain}」
可用表：${promptTableNames}

职责：
1. 判断用户问题是否应命中当前数据集。
2. 从问题中提取统计对象、指标、时间范围、筛选条件、排序/TopN/对比意图。
3. 用户说“这个、那个、继续下钻、换成上月”等省略表达时，优先沿用上一轮数据集和口径。
4. 如果实体、指标、时间或字段口径不清，先追问；不要让 Agent2 猜字段或猜业务规则。
5. 不得虚构 DDL、数据字典、LLD 中不存在的字段。`
const buildAgent2Prompt = ({ datasetName, domain, schemas, dictionaryForBuild, promptTableNames }) => `你是 Agent2（SQL 生成专家），你的输出质量直接决定问数是否可信。
当前数据集：「${datasetName}」
业务域：「${domain}」
可用表：${promptTableNames}

硬性规则：
1. 只生成 PostgreSQL 只读 SQL，禁止 INSERT、UPDATE、DELETE、TRUNCATE、DROP、ALTER、CREATE。
2. 只能使用下方 DDL 和数据字典中出现的表、字段、JSON key；字段不存在时不要猜，必须要求补充口径。
3. SQL 必须能独立执行；表名、字段名需要正确引用；聚合查询必须保证 GROUP BY 合法。
4. 明细查询默认 LIMIT 100；Top/排名查询默认 LIMIT 20；除非用户明确要求更多。
5. 输出列使用中文别名，让 Agent4 可以直接写报告。
6. 金额、数量、比例等指标必须按字段类型谨慎处理：数值字段可直接聚合；文本金额必须先清洗再转 numeric；无法确认类型时先给保守 SQL 或追问。
7. 用户要求对比时，要同时返回所有对比对象，不得只返回其中一个。
8. 用户要求下钻时，要先返回上一级摘要，再返回下一层明细；不能用明细直接替代管理层级结论。
9. 如果涉及时间但数据集中没有明确时间字段，必须说明无法按时间过滤或要求用户补充时间字段。
10. 如果查询意图与当前 DDL 不匹配，返回需要澄清的原因，不要硬造 SQL。

DDL 上下文：
${buildPromptDdlContext(schemas)}

字段语义：
${buildPromptDictionaryContext(dictionaryForBuild) || '暂无字段字典，请优先依据 DDL 字段名谨慎推断。'}`
const buildAgent3Prompt = ({ datasetName }) => `你是 Agent3（SQL 复核官）。
当前数据集：「${datasetName}」

复核重点：
1. SQL 是否只读、安全。
2. 表名、字段名、JSON key 是否来自当前数据集 DDL/字典。
3. 聚合、GROUP BY、ORDER BY、SELECT DISTINCT 是否符合 PostgreSQL 语法。
4. 明细查询是否有限制返回行数。
5. 对比场景是否遗漏用户要求的任一对象。
6. 下钻场景是否保留管理层级，不直接跳到过细明细。

发现问题时，优先修正 SQL；无法修正时明确指出缺少哪个字段或口径。`
const buildAgent4Prompt = ({ datasetName, domain }) => `你是 Agent4（报告生成与业务解读官）。
当前数据集：「${datasetName}」
业务域：「${domain}」

报告规则：
1. 必须基于 SQL 结果说话，不得编造查询结果之外的数字、排名、原因或建议。
2. 开头先回答用户问题，用 1-3 句话给出核心结论；不要把字段逐项堆成流水账。
3. 对比问题必须同时呈现各对象核心指标，并明确差异、领先/落后、风险点。
4. 下钻问题必须先说上层概览，再说下层贡献或拖累，不要只给长名单。
5. 输出结构优先采用：核心结论、关键指标对比、风险/异常、建议动作。
6. 如果结果为空，要说明可能原因：筛选条件未命中、字段口径缺失、时间范围不匹配或数据未同步。
7. 当查询结果字段不足以支撑判断时，明确说“当前结果不足以判断”，并建议补充字段或追问。`
const buildGenericAutofillTemplate = () => {
  const datasetName = compactName(datasetForm.dataset_name)
  const domain = compactName(datasetForm.business_domain, '未分类业务域')
  const schemas = full.schema_definition.filter(item => String(item.table_name || '').trim() && String(item.ddl_sql || '').trim())
  const dictionary = schemas.flatMap(parseDdlColumns)
  const dictionaryForBuild = [...full.data_dictionary, ...dictionary]
  const promptSqlSamples = extractSqlSamplesFromPrompts(full.agent_prompts, datasetName)
  const firstSchema = schemas[0]
  const firstTable = quoteTable(firstSchema?.table_name)
  const firstColumns = dictionaryForBuild.filter(item => item.table_name === firstSchema?.table_name)
  const numericCol = firstColumns.find(item => isNumericType(item.data_type))
  const dimensionCol = firstColumns.find(item => isTextLikeType(item.data_type) && !/id|编号|编码/i.test(`${item.column_name}${item.semantic_name}`))
  const hasJsonbFields = firstColumns.some(item => item.column_name === 'fields' && /jsonb?/i.test(item.data_type))
  const goldenSql = [...promptSqlSamples]
  if (firstTable) {
    goldenSql.push({
      intent_type: 'summary',
      question: `${datasetName}一共有多少条记录？`,
      sql_text: `SELECT COUNT(*) AS "记录数"\nFROM ${firstTable};`,
      tags: [datasetName, '汇总'],
      quality_score: 82,
    })
    goldenSql.push({
      intent_type: 'detail',
      question: `${datasetName}最近有哪些明细数据？`,
      sql_text: `SELECT\n  ${buildSelectList(firstColumns)}\nFROM ${firstTable}\nLIMIT 20;`,
      tags: [datasetName, '明细'],
      quality_score: 80,
    })
    if (dimensionCol) {
      goldenSql.push({
        intent_type: 'aggregation',
        question: `${datasetName}按${dimensionCol.semantic_name}分布如何？`,
        sql_text: `SELECT\n  ${quoteIdent(dimensionCol.column_name)} AS ${quoteIdent(dimensionCol.semantic_name)},\n  COUNT(*) AS "记录数"\nFROM ${firstTable}\nGROUP BY ${quoteIdent(dimensionCol.column_name)}\nORDER BY "记录数" DESC\nLIMIT 20;`,
        tags: [datasetName, dimensionCol.semantic_name],
        quality_score: 82,
      })
    }
    if (numericCol) {
      goldenSql.push({
        intent_type: 'metric_summary',
        question: `${datasetName}${numericCol.semantic_name}合计是多少？`,
        sql_text: `SELECT SUM(${quoteIdent(numericCol.column_name)}) AS ${quoteIdent(`${numericCol.semantic_name}合计`)}\nFROM ${firstTable};`,
        tags: [datasetName, numericCol.semantic_name],
        quality_score: 82,
      })
    }
    if (dimensionCol && numericCol) {
      goldenSql.push({
        intent_type: 'topn',
        question: `${datasetName}按${dimensionCol.semantic_name}看${numericCol.semantic_name}排名如何？`,
        sql_text: `SELECT\n  ${quoteIdent(dimensionCol.column_name)} AS ${quoteIdent(dimensionCol.semantic_name)},\n  SUM(${quoteIdent(numericCol.column_name)}) AS ${quoteIdent(`${numericCol.semantic_name}合计`)}\nFROM ${firstTable}\nGROUP BY ${quoteIdent(dimensionCol.column_name)}\nORDER BY ${quoteIdent(`${numericCol.semantic_name}合计`)} DESC\nLIMIT 20;`,
        tags: [datasetName, dimensionCol.semantic_name, numericCol.semantic_name],
        quality_score: 84,
      })
    }
    if (hasJsonbFields) {
      goldenSql.push({
        intent_type: 'schema_probe',
        question: `${datasetName}JSON 字段里有哪些 key？`,
        sql_text: `SELECT key AS "字段名", COUNT(*) AS "出现次数"\nFROM ${firstTable}, LATERAL jsonb_object_keys(fields) AS key\nGROUP BY key\nORDER BY "出现次数" DESC\nLIMIT 50;`,
        tags: [datasetName, 'JSONB'],
        quality_score: 80,
      })
    }
    while (goldenSql.length < 3) {
      goldenSql.push({
        intent_type: 'detail',
        question: `${datasetName}样例数据${goldenSql.length + 1}怎么看？`,
        sql_text: `SELECT\n  ${buildSelectList(firstColumns)}\nFROM ${firstTable}\nLIMIT 20 OFFSET ${(goldenSql.length - 1) * 20};`,
        tags: [datasetName, '样例'],
        quality_score: 78,
      })
    }
  }
  const promptQuestions = promptSqlSamples
    .filter(item => !/^.+样例 SQL \d+$/.test(item.question || ''))
    .slice(0, 3)
  const promptTableNames = schemas.map(item => item.table_name).join('、') || '已维护 DDL 的表'
  return {
    __meta: {
      prompt_sql_count: promptSqlSamples.length,
    },
    common_questions: [
      { question_text: `${datasetName}一共有多少条记录？`, sort_order: 10, is_active: true },
      { question_text: `${datasetName}最近有哪些明细数据？`, sort_order: 20, is_active: true },
      ...(dimensionCol ? [{ question_text: `${datasetName}按${dimensionCol.semantic_name}分布如何？`, sort_order: 30, is_active: true }] : []),
      ...(numericCol ? [{ question_text: `${datasetName}${numericCol.semantic_name}合计是多少？`, sort_order: 40, is_active: true }] : []),
      ...(dimensionCol && numericCol ? [{ question_text: `${datasetName}按${dimensionCol.semantic_name}看${numericCol.semantic_name}排名如何？`, sort_order: 50, is_active: true }] : []),
      ...promptQuestions.map((item, index) => ({ question_text: item.question, sort_order: 60 + index * 10, is_active: true })),
    ],
    regression_cases: [
      { case_type: 'summary', question_text: `${datasetName}一共有多少条记录？`, expected_focus: '应命中当前数据集，并返回总记录数。', expected_intent: 'generate_sql', sort_order: 10, is_active: true },
      { case_type: 'detail', question_text: `${datasetName}最近有哪些明细数据？`, expected_focus: '应基于当前 DDL 返回明细列表，并限制返回行数。', expected_intent: 'generate_sql', sort_order: 20, is_active: true },
      ...(dimensionCol ? [{ case_type: 'aggregation', question_text: `${datasetName}按${dimensionCol.semantic_name}分布如何？`, expected_focus: `应按${dimensionCol.semantic_name}聚合统计。`, expected_intent: 'generate_sql', sort_order: 30, is_active: true }] : []),
      ...promptQuestions.map((item, index) => ({
        case_type: 'prompt_example',
        question_text: item.question,
        expected_focus: '应优先参考已维护 Agent2/Agent4 中的样例 SQL 和业务逻辑。',
        expected_intent: 'generate_sql',
        sort_order: 40 + index * 10,
        is_active: true,
      })),
    ],
    synonyms: [
      { synonym: datasetName, normalized_synonym: datasetName, weight: 10 },
      ...(datasetForm.dataset_code ? [{ synonym: datasetForm.dataset_code, normalized_synonym: datasetName, weight: 8 }] : []),
      ...(datasetForm.business_domain ? [{ synonym: datasetForm.business_domain, normalized_synonym: datasetName, weight: 6 }] : []),
    ],
    lld_documents: [{
      version: full.lld_documents.length + 1,
      title: `${datasetName}智能问数基础口径`,
      content: `# ${datasetName}智能问数基础口径\n\n## 业务域\n${domain}\n\n## 数据范围\n当前数据集基于已维护 DDL 自动生成基础问数配置，涉及表：${promptTableNames}。\n\n## 字段口径\n字段语义优先使用数据字典；字典缺失时只能依据 DDL 字段名进行谨慎推断，不得编造未出现在 DDL 或业务描述中的字段。\n\n## SQL 红线\n只允许生成只读 SQL；必须使用当前数据集维护的表结构和字段；聚合、排序、筛选条件需要与用户问题一致；无法判断业务口径时先追问。`,
      redline_rules: ['只读 SQL', '不得编造字段', '口径不清先追问', '结果必须限制返回行数'],
      is_active: true,
    }],
    data_dictionary: dictionary,
    golden_sql_samples: dedupeGoldenSqlSamples(goldenSql).slice(0, 12),
    agent_prompts: [
      { agent_no: 1, prompt_key: 'default', prompt_content: buildAgent1Prompt({ datasetName, domain, promptTableNames }), is_active: true },
      { agent_no: 2, prompt_key: 'default', prompt_content: buildAgent2Prompt({ datasetName, domain, schemas, dictionaryForBuild, promptTableNames }), is_active: true },
      { agent_no: 3, prompt_key: 'default', prompt_content: buildAgent3Prompt({ datasetName }), is_active: true },
      { agent_no: 4, prompt_key: 'default', prompt_content: buildAgent4Prompt({ datasetName, domain }), is_active: true },
    ],
    external_configs: [{
      config_type: 'dataset_meta',
      config_key: 'sql_generation_profile',
      config_value: { db_type: 'postgresql', readonly: true, tables: schemas.map(item => item.table_name) },
      is_active: true,
    }],
  }
}

const autofillSelectedDataset = async () => {
  if (!selectedDatasetId.value) return
  if (!selectedCanEdit.value) { warnReadonly(); return }
  const hasUsableDdl = full.schema_definition.some(item => String(item.table_name || '').trim() && String(item.ddl_sql || '').trim())
  const sourceId = datasetForm.source_id || newDatasetSourceId.value || dataSources.value[0]?.id || null
  if (!isSyybDataset.value && !hasUsableDdl) {
    ElMessage.warning(`请先为「${selectedDatasetName.value}」维护至少一张表的 DDL，再执行智能补齐。`)
    return
  }
  if (isSyybDataset.value && !sourceId) {
    ElMessage.warning('请先为当前数据集选择一个数据源。')
    return
  }
  try {
    await ElMessageBox.confirm(`将根据「${selectedDatasetName.value}」当前已维护的 DDL 和基础信息，重点补齐字段字典与 4 个 Agent Prompt（尤其 Agent2 SQL 生成、Agent4 报告解读），并补充少量常见问题和 Golden SQL 样例。确认继续？`, '智能补齐数据集', {
      type: 'info',
      confirmButtonText: '开始补齐',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  const template = isSyybDataset.value ? createSyybTemplate(sourceId) : buildGenericAutofillTemplate()
  if (!isSyybDataset.value && template.data_dictionary.length === 0 && full.data_dictionary.length === 0) {
    ElMessage.warning('当前 DDL 暂未解析出字段，请检查 DDL 是否包含标准列定义。')
    return
  }
  if (isSyybDataset.value) {
    if (!datasetForm.dataset_name) datasetForm.dataset_name = '商用事业部'
    if (!datasetForm.dataset_code) datasetForm.dataset_code = 'angel_business_2026'
    if (!datasetForm.business_domain) datasetForm.business_domain = '安吉尔商用事业部销售业绩分析'
    if (!datasetForm.description) datasetForm.description = '商用事业部（飞书多维表格）四 Agent 模板'
    if (!datasetForm.source_id) datasetForm.source_id = sourceId
  } else if (!datasetForm.description) {
    datasetForm.description = `${selectedDatasetName.value}智能问数数据集`
  }

  mergeCollection('common_questions', template.common_questions, item => item.question_text)
  mergeCollection('regression_cases', template.regression_cases, item => `${item.case_type}|${item.question_text}`)
  mergeCollection('synonyms', template.synonyms, item => item.synonym)
  mergeCollection('lld_documents', template.lld_documents, item => `${item.version}|${item.title}`)
  mergeCollection('data_dictionary', template.data_dictionary, item => `${item.table_name}|${item.column_name}|${item.jsonb_key}`, { preserveExisting: true })
  mergeCollection('schema_definition', template.schema_definition, item => item.table_name)
  mergeCollection('golden_sql_samples', template.golden_sql_samples, item => item.question, { preserveExisting: true })
  mergeCollection('agent_prompts', template.agent_prompts, item => `${item.agent_no}|${item.prompt_key}`, { preservePromptContent: true })
  mergeCollection('external_configs', template.external_configs, item => `${item.config_type}|${item.config_key}`)

  activeTab.value = 'prompts'
  markDirty()
  if (!isSyybDataset.value && template.__meta?.prompt_sql_count) {
    ElMessage.success(`已从 Agent2/Agent4 提取 ${template.__meta.prompt_sql_count} 条样例 SQL，并保留原有 Prompt 内容。`)
  }
  await saveFull()
}

// ========== 左侧:搜索+筛选 ==========
const datasetStatusCounts = computed(() => {
  const active = datasets.value.filter(item => item.is_active !== false).length
  const inactive = datasets.value.filter(item => item.is_active === false).length
  return { all: datasets.value.length, active, inactive }
})

const filteredDatasets = computed(() => {
  let list = datasets.value
  if (listStatusFilter.value === 'active') list = list.filter(i => i.is_active !== false)
  if (listStatusFilter.value === 'inactive') list = list.filter(i => i.is_active === false)
  if (listFilterSourceId.value) list = list.filter(i => Number(i.source_id) === Number(listFilterSourceId.value))
  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter(i => (i.dataset_name || '').toLowerCase().includes(kw) || (i.dataset_code || '').toLowerCase().includes(kw))
  }
  return list
})

const sourceNameById = (id) => dataSources.value.find(x => Number(x.id) === Number(id))?.name || '未设置'

// ========== 各 Tab 列表的分页与关键字搜索 ==========
const tabPagination = reactive({
  common_questions: { page: 1, pageSize: 10, search: '' },
  regression_cases: { page: 1, pageSize: 10, search: '' },
  synonyms: { page: 1, pageSize: 20, search: '' },
  lld: { page: 1, pageSize: 10, search: '' },
  dictionary: { page: 1, pageSize: 20, search: '' },
  golden: { page: 1, pageSize: 10, search: '' },
  prompts: { page: 1, pageSize: 10, search: '' },
})

const getPagedCollection = (key, searchFields = []) => {
  const col = (full[key] || []).map((item, idx) => ({ ...item, _rawIndex: idx }))
  const conf = tabPagination[key === 'golden_sql_samples' ? 'golden' : (key === 'data_dictionary' ? 'dictionary' : (key === 'agent_prompts' ? 'prompts' : key))] || { page: 1, pageSize: 10, search: '' }
  const kw = (conf.search || '').trim().toLowerCase()
  let filtered = col
  if (kw && searchFields.length) {
    filtered = col.filter(item => searchFields.some(field => String(item[field] || '').toLowerCase().includes(kw)))
  }
  const total = filtered.length
  const start = (conf.page - 1) * conf.pageSize
  const rows = filtered.slice(start, start + conf.pageSize)
  return { rows, total }
}

const pagedSynonyms = computed(() => getPagedCollection('synonyms', ['synonym', 'normalized_synonym']))
const pagedGoldenSql = computed(() => getPagedCollection('golden_sql_samples', ['question', 'sql_text', 'intent_type']))
const pagedQuestions = computed(() => getPagedCollection('common_questions', ['question_text']))
const pagedRegression = computed(() => getPagedCollection('regression_cases', ['question_text', 'expected_focus', 'case_type']))
const pagedDict = computed(() => getPagedCollection('data_dictionary', ['table_name', 'column_name', 'semantic_name', 'jsonb_key']))
const pagedPrompts = computed(() => getPagedCollection('agent_prompts', ['prompt_key', 'prompt_content']))

// ========== 通用弹窗编辑器 ==========
const itemEditorVisible = ref(false)
const itemEditorType = ref('')
const itemEditorIndex = ref(-1)
const itemDraft = reactive({})
const itemDraftJson = ref('{}')

const EDITOR_TITLES = {
  question: '编辑常见问题', regression: '编辑标准题集', synonym: '编辑路由词/别名', lld: '编辑 LLD 文档',
  dict: '编辑数据字典', relation: '编辑表关联', golden: '编辑 Golden SQL',
  prompt: '编辑 Agent 提示片段', extcfg: '编辑外部配置'
}
const COLLECTIONS = {
  question: 'common_questions', regression: 'regression_cases', synonym: 'synonyms', lld: 'lld_documents',
  dict: 'data_dictionary', relation: 'table_relations', golden: 'golden_sql_samples',
  prompt: 'agent_prompts', extcfg: 'external_configs'
}
const FULL_COLLECTION_KEYS = [
  'common_questions',
  'regression_cases',
  'synonyms',
  'lld_documents',
  'data_dictionary',
  'schema_definition',
  'table_relations',
  'golden_sql_samples',
  'agent_prompts',
  'external_configs',
]
const DEFAULTS = {
  question: () => ({ question_text: '', sort_order: (full.common_questions.length + 1) * 10, is_active: true }),
  regression: () => ({
    case_type: 'summary',
    question_text: '',
    expected_focus: '',
    expected_intent: 'generate_sql',
    sort_order: (full.regression_cases.length + 1) * 10,
    is_active: true,
  }),
  synonym: () => ({ synonym: '', normalized_synonym: '', weight: 1 }),
  lld: () => ({ version: full.lld_documents.length + 1, title: '', content: '' }),
  dict: () => ({ table_name: '', column_name: '', jsonb_key: '', semantic_name: '', data_type: 'text' }),
  relation: () => ({ left_table: '', left_key: '', right_table: '', right_key: '', relation_type: 'inner' }),
  golden: () => ({ intent_type: 'detail', question: '', sql_text: '', quality_score: 80 }),
  prompt: () => ({ agent_no: 1, prompt_key: 'default', prompt_content: '' }),
  extcfg: () => ({ config_type: 'feishu_sync', config_key: `config_${Date.now()}`, config_value: {} })
}

const itemEditorTitle = computed(() => {
  const prefix = itemEditorIndex.value === -1 ? '新增' : '编辑'
  return (EDITOR_TITLES[itemEditorType.value] || '编辑').replace('编辑', prefix)
})
const canSaveItemEditor = computed(() => canUseDatasetAction(
  itemEditorType.value,
  itemEditorIndex.value === -1 ? 'create' : 'update'
))

const openItemEditor = (type, index) => {
  if (!canUseDatasetAction(type, index === -1 ? 'create' : 'update')) {
    warnReadonly()
    return
  }
  itemEditorType.value = type
  itemEditorIndex.value = index
  const col = full[COLLECTIONS[type]]
  const source = index >= 0 ? col[index] : DEFAULTS[type]()
  Object.keys(itemDraft).forEach(k => delete itemDraft[k])
  Object.assign(itemDraft, JSON.parse(JSON.stringify(source)))
  if (type === 'extcfg') itemDraftJson.value = jsonString(itemDraft.config_value)
  itemEditorVisible.value = true
}

const saveItemEditor = () => {
  if (!canSaveItemEditor.value) {
    warnReadonly()
    return
  }
  const type = itemEditorType.value
  const col = full[COLLECTIONS[type]]
  if (type === 'extcfg') {
    try { itemDraft.config_value = JSON.parse(itemDraftJson.value || '{}') } catch { ElMessage.warning('JSON 格式错误'); return }
  }
  const copy = JSON.parse(JSON.stringify(itemDraft))
  if (itemEditorIndex.value >= 0) col[itemEditorIndex.value] = copy
  else col.push(copy)
  itemEditorVisible.value = false
  markDirty()
}

// ========== 从 DDL 提取数据字典 ==========
const extractDictFromDDL = () => {
  if (!canUseDatasetFeature('dataset_dict_extract')) { warnReadonly(); return }
  if (full.schema_definition.length === 0) { ElMessage.warning('请先在 DDL 标签页中添加表定义'); return }
  let added = 0
  full.schema_definition.forEach(schema => {
    const ddl = schema.ddl_sql || ''
    const colRegex = /^\s+["']?(\w+)["']?\s+([\w()]+)/gm
    let match
    while ((match = colRegex.exec(ddl)) !== null) {
      const colName = match[1].toLowerCase()
      if (['constraint', 'primary', 'unique', 'index', 'check', 'foreign', 'create', 'alter', 'table'].includes(colName)) continue
      const exists = full.data_dictionary.some(d => d.table_name === schema.table_name && d.column_name === colName)
      if (!exists) {
        full.data_dictionary.push({ table_name: schema.table_name, column_name: colName, jsonb_key: '', semantic_name: '', data_type: match[2] || 'text' })
        added++
      }
    }
  })
  if (added > 0) { ElMessage.success(`已从 DDL 提取 ${added} 个新字段`); markDirty() }
  else ElMessage.info('DDL 中没有发现新的字段可提取，或字段已存在')
}

const mergeDictionaryItems = (items = []) => {
  let added = 0
  let updated = 0
  items.forEach(item => {
    const tableName = String(item.table_name || '').trim()
    const columnName = String(item.column_name || '').trim()
    const jsonbKey = String(item.jsonb_key || '').trim()
    if (!tableName || !columnName) return
    const key = `${tableName}|${columnName}|${jsonbKey}`
    const index = full.data_dictionary.findIndex(d => `${d.table_name || ''}|${d.column_name || ''}|${d.jsonb_key || ''}` === key)
    const next = {
      table_name: tableName,
      column_name: columnName,
      jsonb_key: jsonbKey,
      semantic_name: item.semantic_name || jsonbKey || columnName,
      data_type: item.data_type || '字符串',
      enum_mapping: item.enum_mapping || {},
      extraction_rule: item.extraction_rule || '',
      is_active: item.is_active !== false,
    }
    if (index >= 0) {
      full.data_dictionary[index] = { ...full.data_dictionary[index], ...next }
      updated++
    } else {
      full.data_dictionary.push(next)
      added++
    }
  })
  return { added, updated }
}

const extractDictFromPg = async () => {
  if (!canUseDatasetFeature('dataset_dict_extract')) { warnReadonly(); return }
  if (!selectedDatasetId.value) { ElMessage.warning('请先选择数据集'); return }
  const schema = full.schema_definition.find(item => String(item.table_name || '').trim()) || {}
  const tableName = String(schema.table_name || '').trim()
  if (!tableName) { ElMessage.warning('请先在 DDL + 表关联中维护来源表，或先从数据源拉表'); return }
  pgDictLoading.value = true
  try {
    const res = await extractBookshelfDictionaryFromPg(selectedDatasetId.value, {
      source_id: datasetForm.source_id,
      table_name: tableName,
      jsonb_column: 'fields',
      sample_limit: 5000,
    })
    const { added, updated } = mergeDictionaryItems(res.items || [])
    if (added || updated) {
      markDirty()
      ElMessage.success(`已从 PostgreSQL 提取字段：新增 ${added} 条，更新 ${updated} 条，JSONB Key ${res.jsonb_key_count || 0} 个`)
    } else {
      ElMessage.info('PostgreSQL 未发现新的字段，或字段已是最新')
    }
  } finally {
    pgDictLoading.value = false
  }
}

const clearDictionary = async () => {
  if (!canUseDatasetAction('dict', 'delete')) { warnReadonly(); return }
  if (!full.data_dictionary.length) { ElMessage.info('当前数据字典已经是空的'); return }
  await ElMessageBox.confirm('确认清空当前数据字典？清空后需要点击“保存书架内容”才会写入后端。', '清空数据字典', { type: 'warning' })
  full.data_dictionary = []
  markDirty()
  ElMessage.success('已清空当前数据字典，请保存书架内容')
}

// ========== 数据加载/保存 ==========
const applyDataset = (d) => {
  datasetForm.dataset_code = d?.dataset_code || ''; datasetForm.dataset_name = d?.dataset_name || ''
  datasetForm.business_domain = d?.business_domain || ''; datasetForm.source_id = d?.source_id || null
  datasetForm.description = d?.description || ''; datasetForm.is_active = d?.is_active !== false
}
const resetFull = () => { FULL_COLLECTION_KEYS.forEach(key => { full[key] = [] }); qualitySummary.value = null }

const loadDatasets = async () => { datasets.value = (await getBookshelfDatasets({ include_inactive: 1 })).datasets || [] }
const loadDataSources = async () => {
  dataSources.value = (await getDataSources()).databases || []
  if (!newDatasetSourceId.value && dataSources.value.length > 0) newDatasetSourceId.value = dataSources.value[0].id
}

const selectDataset = async (dataset) => {
  selectedDatasetId.value = dataset.id
  applyDataset(dataset)
  const r = await getBookshelfDatasetFull(dataset.id)
  if (r.dataset) {
    const idx = datasets.value.findIndex(item => Number(item.id) === Number(dataset.id))
    if (idx >= 0) datasets.value[idx] = { ...datasets.value[idx], ...r.dataset }
    applyDataset(r.dataset)
  }
  FULL_COLLECTION_KEYS.forEach(key => { full[key] = r[key] || [] })
  qualitySummary.value = r.quality_summary || null
  isDirty.value = false
  await loadTransforms()
}

const onSelectDataset = async (item) => {
  if (isDirty.value) {
    try { await ElMessageBox.confirm('当前有未保存的修改，切换后将丢失。确认切换？', '提示', { type: 'warning' }) }
    catch { return }
  }
  await selectDataset(item)
}

const createDataset = async () => {
  const r = await createBookshelfDataset({ dataset_code: `dataset_${Date.now()}`, dataset_name: '新数据集', business_domain: '未分类', source_id: newDatasetSourceId.value || undefined, description: '' })
  await loadDatasets()
  const t = datasets.value.find(i => i.id === r.dataset?.id)
  if (t) await selectDataset(t)
}

const removeDataset = async () => {
  if (!selectedDatasetId.value) return
  if (!selectedCanDelete.value) { warnReadonly(); return }
  await ElMessageBox.confirm('确认删除当前数据集吗？', '删除确认', { type: 'warning' })
  await deleteBookshelfDataset(selectedDatasetId.value)
  ElMessage.success('数据集已删除'); selectedDatasetId.value = null; resetFull(); isDirty.value = false; await loadDatasets()
}

const saveFull = async () => {
  if (!selectedDatasetId.value) return
  if (!canSaveShelfContent.value) { warnReadonly(); return false }
  const hasFullSave = canUseDatasetFeature('dataset_save')
  const payload = hasFullSave
    ? {}
    : { __partial: true, common_questions: full.common_questions }
  if (hasFullSave) {
    FULL_COLLECTION_KEYS.forEach(key => { payload[key] = full[key] })
  }
  try {
    if (hasFullSave) {
      await updateBookshelfDataset(selectedDatasetId.value, { ...datasetForm })
    }
    await saveBookshelfDatasetFull(selectedDatasetId.value, payload)
    ElMessage.success('书架内容已保存'); isDirty.value = false
    await loadDatasets()
    const currentDataset = datasets.value.find(item => Number(item.id) === Number(selectedDatasetId.value))
    if (currentDataset) {
      if ((listStatusFilter.value === 'active' && currentDataset.is_active === false)
        || (listStatusFilter.value === 'inactive' && currentDataset.is_active !== false)) {
        listStatusFilter.value = 'active'
      }
      await selectDataset(currentDataset)
    }
    return true
  } catch (err) {
    const details = err?.response?.data?.details
    if (Array.isArray(details) && details.length) {
      ElMessageBox.alert(details.join('<br/>'), '保存前校验未通过', {
        confirmButtonText: '知道了',
        dangerouslyUseHTMLString: true,
        type: 'warning',
      })
      return false
    }
    ElMessage.error(err?.response?.data?.error || err?.message || '保存失败')
    return false
  }
}

// ========== 大段提示词生成新数据集 ==========
const resetPromptDatasetForm = () => {
  promptDatasetForm.source_id = datasetForm.source_id || newDatasetSourceId.value || dataSources.value[0]?.id || null
  promptDatasetForm.style_dataset_id = selectedDatasetId.value || null
  promptDatasetForm.dataset_name = ''
  promptDatasetForm.dataset_code = ''
  promptDatasetForm.business_domain = ''
  promptDatasetForm.doc_text = ''
  resetPromptDatasetProgress()
}

const openPromptDatasetDialog = () => {
  if (!isFeatureEnabled('dataset_prompt_generate')) return
  resetPromptDatasetForm()
  promptDatasetVisible.value = true
}

const resetPromptDatasetProgress = () => {
  if (promptDatasetTimer) window.clearInterval(promptDatasetTimer)
  promptDatasetTimer = null
  promptDatasetStatus.value = ''
  promptDatasetStepIndex.value = -1
  promptDatasetProgress.value = 0
  promptDatasetElapsed.value = 0
}

const startPromptDatasetTimer = () => {
  if (promptDatasetTimer) window.clearInterval(promptDatasetTimer)
  const startedAt = Date.now()
  promptDatasetElapsed.value = 1
  promptDatasetTimer = window.setInterval(() => {
    promptDatasetElapsed.value = Math.max(1, Math.floor((Date.now() - startedAt) / 1000))
    if (promptDatasetLoading.value && promptDatasetProgress.value < 88) {
      promptDatasetProgress.value = Math.min(88, promptDatasetProgress.value + (promptDatasetElapsed.value > 90 ? 1 : 2))
    }
  }, 1000)
}

const setPromptDatasetStage = (index, status, progress = null) => {
  promptDatasetStepIndex.value = index
  promptDatasetStatus.value = status
  if (progress !== null) promptDatasetProgress.value = Math.max(promptDatasetProgress.value, progress)
}

const cancelPromptDatasetGeneration = () => {
  if (promptDatasetAbortController) {
    promptDatasetAbortController.abort()
    setPromptDatasetStage(promptDatasetStepIndex.value, '已停止本次生成请求，可以修改提示词后重新生成。', promptDatasetProgress.value)
  }
}

const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const promptDatasetFailureLines = (err, createdDatasetId) => {
  const status = err?.response?.status
  const data = err?.response?.data || {}
  const url = err?.config?.url || '/api/bookshelves/datasets/generate-from-prompt'
  const message = data.error || err?.message || '未知错误'
  if (err?.code === 'ERR_CANCELED' || message === 'canceled') {
    return [
      '失败位置：前端主动取消请求',
      '详细报错：本次生成已停止，后端请求不再等待前端响应。',
      '建议：缩短提示词、补充关键 DDL/字段字典后重新生成；如果后端仍在跑旧请求，稍等一会儿再试。',
      '建议改代码位置：frontend/src/views/DatasetManagement.vue 的 cancelPromptDatasetGeneration；后端入口 backend/controllers/bookshelf.py。',
    ]
  }
  const lines = [
    `失败位置：${url}${status ? `（HTTP ${status}）` : ''}`,
    `详细报错：${message}`,
  ]
  if (Array.isArray(data.details) && data.details.length) {
    lines.push(`校验未通过：${data.details.join('；')}`)
  }
  if (createdDatasetId) {
    lines.push(`当前状态：数据集基础信息已创建，ID=${createdDatasetId}，书架内容保存失败；页面会切到这个数据集，方便你继续补齐。`)
  }
  if (status === 404 && url.includes('generate-from-prompt')) {
    lines.push('建议：后端没有加载“提示词生成数据集”接口，重启 backend/app.py 后再试。')
    lines.push('代码位置：backend/controllers/bookshelf.py 的 generate-from-prompt 路由、backend/app.py 蓝图注册。')
  } else if (status === 404 && url.includes('/bookshelves/datasets')) {
    lines.push('建议：这是“创建数据集”接口 404。请强刷页面，确认浏览器请求的是 /api/bookshelves/datasets；前端已自动用显式 /api 路径重试一次。')
    lines.push('代码位置：frontend/src/api/index.js 的 createBookshelfDataset；backend/controllers/bookshelf.py 的 POST /api/bookshelves/datasets。')
  } else if (status === 400) {
    lines.push('建议：补充更完整的 DDL、字段字典、LLD、示例 SQL，或先选择一个绑定数据源。')
    lines.push('代码位置：backend/controllers/bookshelf.py 的参数校验和 _validate_full_payload。')
  } else if (status >= 500) {
    lines.push('建议：优先检查默认 AI 模型/API Key、模型超时、返回 JSON 是否完整，以及 /full 保存时的字段格式。')
    lines.push('代码位置：backend/dataset_copilot/payload_generator.py、backend/controllers/bookshelf.py。')
  } else {
    lines.push('建议：打开“系统控制台 -> 日志管理”，筛选“报错”或搜索 generate-from-prompt 查看后端记录。')
  }
  return lines
}

const uniqueDatasetCode = (code) => {
  const base = String(code || `dataset_${Date.now()}`)
    .trim()
    .replace(/[^A-Za-z0-9_]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 80) || `dataset_${Date.now()}`
  const exists = datasets.value.some(item => String(item.dataset_code || '').toLowerCase() === base.toLowerCase())
  return exists ? `${base}_${Date.now().toString().slice(-6)}` : base
}

const buildGeneratedFullPayload = (generatedPayload, sourceId = null) => {
  const payload = {}
  FULL_COLLECTION_KEYS.forEach(key => { payload[key] = Array.isArray(generatedPayload?.[key]) ? generatedPayload[key] : [] })
  if (sourceId) {
    payload.schema_definition = payload.schema_definition.map(item => ({ ...item, source_id: sourceId }))
  }
  if (generatedPayload?.report_config && typeof generatedPayload.report_config === 'object') {
    payload.report_config = generatedPayload.report_config
  }
  return payload
}

const generateDatasetFromPrompt = async () => {
  if (!isFeatureEnabled('dataset_prompt_generate')) return
  const docText = String(promptDatasetForm.doc_text || '').trim()
  if (docText.length < 80) {
    ElMessage.warning('请粘贴更完整的提示词、DDL、字段字典或业务口径，至少 80 字。')
    return
  }
  const sourceId = promptDatasetForm.source_id || newDatasetSourceId.value || dataSources.value[0]?.id || null
  if (!sourceId) {
    ElMessage.warning('请先选择或配置一个数据源。')
    return
  }

  promptDatasetLoading.value = true
  startPromptDatasetTimer()
  setPromptDatasetStage(0, '正在检查输入、数据源和参考样式...', 8)
  let createdDatasetId = null
  try {
    promptDatasetAbortController = new AbortController()
    setPromptDatasetStage(1, '正在请求后端 AI 生成接口。大段提示词会比较慢，请稍等...', 18)
    const generated = await generateBookshelfDatasetFromPrompt({
      doc_text: docText,
      source_id: sourceId,
      style_dataset_id: promptDatasetForm.style_dataset_id || undefined,
      dataset_name: promptDatasetForm.dataset_name || undefined,
      dataset_code: promptDatasetForm.dataset_code || undefined,
      business_domain: promptDatasetForm.business_domain || undefined,
    }, {
      signal: promptDatasetAbortController.signal,
    })
    setPromptDatasetStage(2, 'AI 已返回，正在检查 LLD、DDL、字段字典、Golden SQL 和 Agent Prompt 是否完整...', 76)
    const validationErrors = generated.validation_errors || []
    if (validationErrors.length) {
      setPromptDatasetStage(2, '生成结果未达到保存标准，请按弹窗提示补充底稿后重试。', 76)
      await ElMessageBox.alert(validationErrors.join('<br/>'), '生成结果还不完整', {
        confirmButtonText: '知道了',
        dangerouslyUseHTMLString: true,
        type: 'warning',
      })
      return
    }

    const meta = generated.dataset_meta || {}
    const createPayload = {
      dataset_code: uniqueDatasetCode(meta.dataset_code || promptDatasetForm.dataset_code),
      dataset_name: meta.dataset_name || promptDatasetForm.dataset_name || 'AI生成数据集',
      business_domain: meta.business_domain || promptDatasetForm.business_domain || meta.dataset_name || 'AI生成数据集',
      source_id: sourceId,
      description: meta.description || `由大段提示词自动生成：${meta.dataset_name || promptDatasetForm.dataset_name || 'AI生成数据集'}`,
    }
    setPromptDatasetStage(3, `正在创建数据集：${createPayload.dataset_name}`, 84)
    const created = await createBookshelfDataset(createPayload)
    createdDatasetId = created.dataset?.id
    if (!createdDatasetId) throw new Error('数据集创建成功但未返回 ID')

    setPromptDatasetStage(4, '正在保存书架内容：LLD、DDL、字段字典、Golden SQL、Agent Prompt...', 92)
    await saveBookshelfDatasetFull(createdDatasetId, buildGeneratedFullPayload(generated.payload || {}, sourceId))
    setPromptDatasetStage(4, '保存完成，正在刷新数据集列表...', 100)
    promptDatasetVisible.value = false
    ElMessage.success(`已生成并保存「${createPayload.dataset_name}」`)
    await loadDatasets()
    const target = datasets.value.find(item => Number(item.id) === Number(createdDatasetId))
    if (target) await selectDataset(target)
  } catch (err) {
    const details = err?.response?.data?.details
    if (Array.isArray(details) && details.length) {
      const isGenerateError = String(err?.config?.url || '').includes('generate-from-prompt')
      setPromptDatasetStage(Math.max(promptDatasetStepIndex.value, 0), isGenerateError ? 'AI 生成失败，已整理原因和建议。' : '保存前校验未通过，已整理原因和建议。', promptDatasetProgress.value)
      await ElMessageBox.alert(details.map(line => `<p>${escapeHtml(line)}</p>`).join(''), isGenerateError ? 'AI 生成失败' : '保存前校验未通过', {
        confirmButtonText: '知道了',
        dangerouslyUseHTMLString: true,
        type: isGenerateError ? 'error' : 'warning',
      })
    } else if (err?.response?.status === 404 && err?.response?.data?.error === 'API not found') {
      setPromptDatasetStage(Math.max(promptDatasetStepIndex.value, 0), '接口 404，已整理原因和建议。', promptDatasetProgress.value)
      await ElMessageBox.alert(
        promptDatasetFailureLines(err, createdDatasetId).map(line => `<p>${escapeHtml(line)}</p>`).join(''),
        '接口未找到',
        { confirmButtonText: '知道了', dangerouslyUseHTMLString: true, type: 'error' },
      )
    } else {
      setPromptDatasetStage(Math.max(promptDatasetStepIndex.value, 0), '处理失败，已整理原因和建议。', promptDatasetProgress.value)
      await ElMessageBox.alert(
        promptDatasetFailureLines(err, createdDatasetId).map(line => `<p>${escapeHtml(line)}</p>`).join(''),
        '生成数据集失败',
        { confirmButtonText: '知道了', dangerouslyUseHTMLString: true, type: 'error' },
      )
    }
    if (createdDatasetId) {
      await loadDatasets()
      const target = datasets.value.find(item => Number(item.id) === Number(createdDatasetId))
      if (target) await selectDataset(target)
    }
  } finally {
    promptDatasetLoading.value = false
    promptDatasetAbortController = null
    if (promptDatasetTimer) window.clearInterval(promptDatasetTimer)
    promptDatasetTimer = null
  }
}

// ========== 从数据源拉表 ==========
const sourceDialogVisible = ref(false); const sourceDialogSourceId = ref(null)
const sourceTables = ref([]); const selectedSourceTables = ref([])

const openSourceTableDialog = () => {
  if (!canUseDatasetFeature('dataset_source_table')) { warnReadonly(); return }
  sourceDialogVisible.value = true; sourceDialogSourceId.value = datasetForm.source_id || dataSources.value[0]?.id || null; sourceTables.value = []; selectedSourceTables.value = []
}
const loadSourceTables = async () => { if (!sourceDialogSourceId.value) { ElMessage.warning('请先选择数据源'); return }; sourceTables.value = (await getSourceTables(sourceDialogSourceId.value)).tables || [] }
const onSourceTableSelection = (rows) => { selectedSourceTables.value = rows || [] }
const appendSelectedSourceTables = () => {
  if (!canUseDatasetFeature('dataset_source_table')) { warnReadonly(); return }
  if (selectedSourceTables.value.length === 0) { ElMessage.warning('请先勾选表'); return }
  let added = 0
  selectedSourceTables.value.forEach(t => {
    if (full.schema_definition.some(x => x.table_name === t.full_table_name)) return
    full.schema_definition.push({ table_name: t.full_table_name, ddl_sql: t.ddl_sql || '', description: '', source_id: sourceDialogSourceId.value }); added++
  })
  sourceDialogVisible.value = false; ElMessage.success(`已加入 ${added} 张表`); if (added > 0) markDirty()
}

// ========== DDL Drawer ==========
const schemaEditorVisible = ref(false); const schemaEditorIndex = ref(-1)
const schemaEditor = reactive({ table_name: '', ddl_sql: '', description: '', source_id: null })
const resetSchemaEditor = () => { schemaEditor.table_name = ''; schemaEditor.ddl_sql = ''; schemaEditor.description = ''; schemaEditor.source_id = null }
const openSchemaEditor = (row = null, index = -1) => {
  if (!canUseDatasetFeature(index === -1 ? 'dataset_schema_create' : 'dataset_schema_update')) { warnReadonly(); return }
  schemaEditorIndex.value = index
  if (row) { schemaEditor.table_name = row.table_name || ''; schemaEditor.ddl_sql = row.ddl_sql || ''; schemaEditor.description = row.description || ''; schemaEditor.source_id = row.source_id || null }
  else resetSchemaEditor()
  schemaEditorVisible.value = true
}
const saveSchemaEditor = () => {
  if (!canUseDatasetFeature(schemaEditorIndex.value === -1 ? 'dataset_schema_create' : 'dataset_schema_update')) { warnReadonly(); return }
  if (!schemaEditor.table_name.trim()) { ElMessage.warning('请填写表名'); return }
  const item = { table_name: schemaEditor.table_name.trim(), ddl_sql: schemaEditor.ddl_sql || '', description: schemaEditor.description || '', source_id: schemaEditor.source_id || null }
  if (schemaEditorIndex.value >= 0) full.schema_definition[schemaEditorIndex.value] = item
  else full.schema_definition.push(item)
  schemaEditorVisible.value = false; resetSchemaEditor(); markDirty()
}
const removeSchema = (i) => {
  if (!canUseDatasetFeature('dataset_schema_delete')) { warnReadonly(); return }
  full.schema_definition.splice(i, 1); markDirty()
}
const addSchema = () => openSchemaEditor()

// ========== 数据转换 ==========
const loadTransforms = async () => {
  if (!selectedDatasetId.value) {
    transforms.value = []
    return
  }
  transformLoading.value = true
  try {
    const r = await getDatasetTransforms(selectedDatasetId.value)
    transforms.value = r.transforms || []
  } catch (error) {
    transforms.value = []
  } finally {
    transformLoading.value = false
  }
}
const resetTransformForm = () => {
  Object.assign(transformForm, {
    name: '',
    source_table: '',
    target_type: 'view',
    target_name: '',
    transform_sql: '',
    is_active: true,
    auto_run_on_sync: false,
    sync_dependency: ''
  })
}
const openTransformEditor = (row = null) => {
  if (!ensureSelectedCanEdit()) return
  transformEditId.value = row ? row.id : null
  resetTransformForm()
  if (row) {
    Object.assign(transformForm, {
      name: row.name || '',
      source_table: row.source_table || '',
      target_type: row.target_type || 'view',
      target_name: row.target_name || '',
      transform_sql: row.transform_sql || '',
      is_active: row.is_active !== false,
      auto_run_on_sync: row.auto_run_on_sync === true,
      sync_dependency: row.sync_dependency || ''
    })
  }
  transformDialogVisible.value = true
}
const closeTransformEditor = () => {
  transformDialogVisible.value = false
  transformEditId.value = null
  resetTransformForm()
}
const saveTransform = async () => {
  if (!ensureSelectedCanEdit()) return
  if (!transformForm.name.trim()) { ElMessage.warning('请输入任务名称'); return }
  if (!transformForm.source_table.trim()) { ElMessage.warning('请输入源表名'); return }
  if (!transformForm.target_name.trim()) { ElMessage.warning('请输入目标名称'); return }
  if (!transformForm.transform_sql.trim()) { ElMessage.warning('请输入转换 SQL'); return }
  transformLoading.value = true
  try {
    const payload = {
      name: transformForm.name.trim(),
      source_table: transformForm.source_table.trim(),
      target_type: transformForm.target_type,
      target_name: transformForm.target_name.trim(),
      transform_sql: transformForm.transform_sql.trim(),
      is_active: transformForm.is_active,
      auto_run_on_sync: transformForm.auto_run_on_sync,
      sync_dependency: transformForm.sync_dependency.trim()
    }
    if (transformEditId.value) {
      await updateDatasetTransform(transformEditId.value, payload)
      ElMessage.success('转换任务更新成功')
    } else {
      await createDatasetTransform(selectedDatasetId.value, payload)
      ElMessage.success('转换任务创建成功')
    }
    closeTransformEditor()
    await loadTransforms()
  } finally {
    transformLoading.value = false
  }
}
const handleDeleteTransform = async (row) => {
  if (!ensureSelectedCanEdit()) return
  try {
    await ElMessageBox.confirm(`确认删除转换任务 "${row.name}" 吗？`, '删除确认', { type: 'warning' })
    await deleteDatasetTransform(row.id)
    ElMessage.success('转换任务已删除')
    await loadTransforms()
  } catch (error) {
    if (error !== 'cancel') {
      // ElMessage.error 已由 api 拦截器处理
    }
  }
}
const handleRunTransform = async (row) => {
  transformRunLoading.value = { ...transformRunLoading.value, [row.id]: true }
  try {
    const r = await runDatasetTransform(row.id)
    ElMessage.success(r.message || '执行成功')
    await loadTransforms()
  } finally {
    transformRunLoading.value = { ...transformRunLoading.value, [row.id]: false }
  }
}
const handleTestTransformSql = async () => {
  if (!transformForm.transform_sql.trim()) { ElMessage.warning('请输入转换 SQL'); return }
  transformTestLoading.value = true
  try {
    const r = await testDatasetTransformSql({
      target_type: transformForm.target_type,
      target_name: transformForm.target_name || 'test_target',
      source_table: transformForm.source_table,
      transform_sql: transformForm.transform_sql.trim()
    })
    if (r.success) ElMessage.success(r.message || '测试成功')
    else ElMessage.error(r.error || '测试失败')
  } finally {
    transformTestLoading.value = false
  }
}
const applyEcommerceTemplate = () => {
  transformForm.source_table = 'feishu_tbldianshang'
  transformForm.target_name = 'v_feishu_tbldianshang'
  transformForm.target_type = 'view'
  transformForm.transform_sql = `SELECT
  id,
  record_id,
  fields->>'状态' AS 审批状态,
  fields->>'编号' AS 编号,
  fields->>'经营主体' AS 集团,
  fields->>'事业部' AS 事业部,
  NULLIF(fields->>'业务部','') AS 业务部,
  NULLIF(fields->>'业务承接角色','') AS 细分业务,
  fields->>'层级级别' AS 层级级别,
  fields->>'任务承接人' AS 负责人,
  fields->>'任务维护人' AS 上级负责人,
  NULLIF(trim(fields->>'总任务（金额）'),'')::numeric AS 年度目标营收,
  NULLIF(trim(fields->>'年度开单金额'),'')::numeric AS 年度开单金额,
  NULLIF(trim(fields->>'总任务达成率'),'')::numeric AS 总任务达成率,
  NULLIF(trim(fields->>'当前月份任务达成率'),'')::numeric AS 当前月份任务达成率,
  NULLIF(trim(fields->>'截止当前目标阈值达成率'),'')::numeric AS 截止当前目标阈值达成率,
  NULLIF(trim(fields->>'本月开单金额'),'')::numeric AS 本月开单金额,
  NULLIF(trim(fields->>'本月当前目标阈值'),'')::numeric AS 本月当前目标阈值,
  NULLIF(trim(fields->>'年度阈值/开单差额（万）'),'')::numeric AS 年度阈值开单差额万,
  NULLIF(trim(fields->>'月度阈值/开单差额（万）'),'')::numeric AS 月度阈值开单差额万,
  NULLIF(trim(fields->>'总金额转换（以万为单位）'),'')::numeric AS 总金额转换万,
  NULLIF(trim(fields->>'年度开单金额转换（以万为单位）'),'')::numeric AS 年度开单金额转换万,
  fields->>'链接字段(勿删)' AS 组织路径,
  fields->>'当前年' AS 当前年,
  fields->>'当前月' AS 当前月,
  NULLIF(trim(fields->>'2601'),'')::numeric AS q1目标,
  NULLIF(trim(fields->>'2602'),'')::numeric AS q2目标,
  NULLIF(trim(fields->>'2603'),'')::numeric AS q3目标,
  NULLIF(trim(fields->>'2604'),'')::numeric AS q4目标
FROM {{source_table}}
WHERE fields IS NOT NULL AND fields <> '{}'::jsonb
  AND NULLIF(fields->>'编号','') IS NOT NULL`
}
const formatTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { hour12: false })
}

// ========== 工具函数 ==========
const ddlPreview = (t) => { const n = String(t || '').replace(/\s+/g, ' ').trim(); return n ? (n.length > 120 ? n.slice(0, 120) + '...' : n) : '暂无 DDL' }
const jsonString = (v) => { try { return JSON.stringify(v || {}, null, 2) } catch { return '{}' } }

onMounted(async () => {
  await loadFeatureFlags()
  await Promise.all([loadDatasets(), loadDataSources()])
  if (datasets.value.length > 0) await selectDataset(datasets.value[0])
  else resetFull()
})

onUnmounted(() => {
  if (promptDatasetAbortController) promptDatasetAbortController.abort()
  if (promptDatasetTimer) window.clearInterval(promptDatasetTimer)
})
</script>

<style scoped>
.dataset-page { min-height: calc(100vh - 150px); }
.glass-card { border: 1px solid var(--border, #E5E7EB); background: var(--bg-card, #fff); border-radius: var(--radius-card, 12px); box-shadow: var(--shadow-xs); }
.sidebar-card { min-height: calc(100vh - 150px); }
.panel-title { font-size: 18px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; color: var(--text-title, #111827); }
.header-row { display: flex; align-items: center; justify-content: space-between; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.compact-actions { gap: 6px; }
.toolbar-col { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.dataset-status-filter { width: 100%; }
.dataset-status-filter :deep(.el-radio-button) { flex: 1; }
.dataset-status-filter :deep(.el-radio-button__inner) { width: 100%; padding-left: 8px; padding-right: 8px; }
.dataset-tile { padding: 12px 14px; border-radius: var(--radius-card, 12px); margin-bottom: 8px; border: 1px solid var(--border, #E5E7EB); background: var(--bg-card, #fff); cursor: pointer; transition: all var(--duration-normal, 220ms) var(--ease-out); }
.dataset-tile:hover { border-color: var(--border-hover, #D1D5DB); box-shadow: var(--shadow-sm); transform: translateY(-1px); }
.dataset-tile.active { border-color: var(--color-primary, #E61F24); background: var(--color-primary-light, #FEF2F2); box-shadow: var(--shadow-md); }
.dataset-tile.inactive { background: #F8F9FA; }
.dataset-tile.readonly { background: #FFFBEB; }
.dataset-tile-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.dataset-tile-tags { display: flex; gap: 5px; flex-wrap: wrap; justify-content: flex-end; }
.dataset-tile-title { font-weight: 700; font-size: 14px; color: var(--text-title, #111827); }
.dataset-tile.inactive .dataset-tile-title { color: var(--text-body, #6B7280); }
.dataset-tile-meta { margin-top: 3px; font-size: 11px; color: var(--text-muted, #9CA3AF); }
.dataset-tile-sub { margin-top: 4px; font-size: 11px; color: var(--text-muted, #9CA3AF); }
.readonly-alert { margin-bottom: 12px; }
.readonly-summary-card { border: 1px solid #E5E7EB; border-radius: 8px; padding: 18px; background: #F8F9FA; }
.readonly-summary-title { font-size: 16px; font-weight: 700; color: var(--text-title, #111827); }
.readonly-summary-desc { margin-top: 6px; color: var(--text-muted, #9CA3AF); font-size: 13px; }
.readonly-summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }
.readonly-summary-grid div { border: 1px solid #E5E7EB; border-radius: 8px; background: #fff; padding: 12px; min-width: 0; }
.readonly-summary-grid span { display: block; font-size: 12px; color: var(--text-muted, #9CA3AF); margin-bottom: 6px; }
.readonly-summary-grid strong { display: block; font-size: 14px; color: var(--text-title, #111827); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.base-form { margin-bottom: 10px; }
.quality-alert { margin-bottom: 14px; }
.quality-overview { display: flex; flex-direction: column; gap: 10px; padding-top: 4px; }
.quality-checks { display: flex; flex-wrap: wrap; gap: 8px; }
.quality-gaps { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-body, #6B7280); line-height: 1.6; }
.toolbar { margin-bottom: 10px; display: flex; gap: 8px; }
.section-title { margin: 18px 0 10px; font-weight: 700; font-size: 14px; color: var(--text-title, #111827); }
.muted-text { color: var(--text-muted, #9CA3AF); font-size: 12px; line-height: 1.5; }
.text-preview { font-size: 12px; color: var(--text-body, #6B7280); line-height: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 400px; }
.schema-name-cell { font-weight: 600; color: var(--text-title, #111827); }
.ddl-preview-line { font-family: 'JetBrains Mono', Consolas, Monaco, monospace; font-size: 12px; line-height: 1.4; color: var(--text-body, #6B7280); word-break: break-word; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 500px; }
.schema-editor-shell { display: flex; flex-direction: column; gap: 18px; height: 100%; }
.schema-editor-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.schema-editor-subtitle { margin-top: 6px; color: var(--text-muted, #9CA3AF); font-size: 13px; }
.schema-editor-form { flex: 1; }
:global(.prompt-dataset-dialog) {
  max-width: calc(100vw - 48px);
}
:global(.prompt-dataset-dialog .el-dialog__body) {
  max-height: calc(100vh - 170px);
  overflow: auto;
  padding-top: 18px;
}
.prompt-generate-shell { display: flex; flex-direction: column; gap: 14px; }
.prompt-generate-form {
  margin-top: 2px;
  padding: 16px 16px 2px;
  border: 1px solid #F8F9FA;
  border-radius: 10px;
  background: #F8F9FA;
}
.prompt-progress-panel {
  border: 1px solid #FEF2F2;
  background: linear-gradient(180deg, #F8F9FA 0%, #FEF2F2 100%);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}
.prompt-progress-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.prompt-progress-head strong {
  display: block;
  color: #111827;
  font-size: 14px;
}
.prompt-progress-head span {
  display: block;
  margin-top: 4px;
  color: #6B7280;
  font-size: 13px;
  line-height: 1.5;
}
.prompt-progress-head em {
  flex: 0 0 auto;
  color: #E61F24;
  font-style: normal;
  font-weight: 600;
}
.prompt-stage-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}
.prompt-stage {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 7px 9px;
  border: 1px solid #F3F4F6;
  border-radius: 8px;
  color: #6B7280;
  background: rgba(255, 255, 255, 0.72);
}
.prompt-stage span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  color: #6B7280;
  background: #F3F4F6;
  font-size: 12px;
  font-weight: 800;
  flex-shrink: 0;
}
.prompt-stage strong {
  min-width: 0;
  font-size: 13px;
  line-height: 1.25;
}
.prompt-stage.done,
.prompt-stage.active {
  border-color: #FEF2F2;
  color: #E61F24;
  background: #ECFDF5;
}
.prompt-stage.done span,
.prompt-stage.active span {
  color: #fff;
  background: #E61F24;
}
.prompt-stage.active {
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
}
.prompt-progress-note {
  margin-top: 10px;
  color: #6B7280;
  font-size: 12px;
  line-height: 1.6;
}
.mono-textarea :deep(textarea) { font-family: 'JetBrains Mono', Consolas, Monaco, monospace; font-size: 13px; line-height: 1.6; }
@media (max-width: 900px) {
  .prompt-stage-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
