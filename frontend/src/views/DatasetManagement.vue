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
            <el-input v-model="searchKeyword" clearable placeholder="搜索数据集名称/编码..." size="small" />
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
              :class="{ active: selectedDatasetId === item.id }"
              @click="onSelectDataset(item)"
            >
              <div class="dataset-tile-title">{{ item.dataset_name || '未命名数据集' }}</div>
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
                数据集书架维护
                <el-tag v-if="isDirty" type="warning" size="small" effect="plain" style="margin-left:8px">有未保存修改</el-tag>
              </div>
              <div class="header-actions">
                <el-button type="danger" plain @click="removeDataset" :disabled="!selectedDatasetId">删除</el-button>
                <el-button type="primary" :disabled="!isDirty" @click="saveFull">保存书架内容</el-button>
              </div>
            </div>
          </template>

          <el-empty v-if="!selectedDatasetId" description="请选择一个数据集后开始维护。" />
          <template v-else>
            <el-form label-width="120px" class="base-form">
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
              v-if="qualitySummary"
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

            <el-tabs v-model="activeTab">
              <!-- 常见问题 -->
              <el-tab-pane label="常见问题" name="common_questions">
                <div class="toolbar"><el-button size="small" @click="openItemEditor('question', -1)">新增常见问题</el-button></div>
                <el-table :data="full.common_questions" border size="small">
                  <el-table-column label="问题" min-width="300"><template #default="{ row }">{{ row.question_text || '(空)' }}</template></el-table-column>
                  <el-table-column label="排序" width="80"><template #default="{ row }">{{ row.sort_order }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button link type="primary" @click="openItemEditor('question', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.common_questions.splice($index, 1); markDirty()">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="标准题集" name="regression_cases">
                <div class="toolbar"><el-button size="small" @click="openItemEditor('regression', -1)">新增回归题</el-button></div>
                <el-table :data="full.regression_cases" border size="small">
                  <el-table-column label="类型" width="110"><template #default="{ row }">{{ row.case_type }}</template></el-table-column>
                  <el-table-column label="问题" min-width="260"><template #default="{ row }">{{ row.question_text || '(空)' }}</template></el-table-column>
                  <el-table-column label="预期焦点" min-width="260"><template #default="{ row }">{{ row.expected_focus || '-' }}</template></el-table-column>
                  <el-table-column label="执行预期" width="120"><template #default="{ row }">{{ row.expected_intent || '-' }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button link type="primary" @click="openItemEditor('regression', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.regression_cases.splice($index, 1); markDirty()">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 路由词/别名 -->
              <el-tab-pane label="路由词/别名" name="synonyms">
                <div class="toolbar"><el-button size="small" @click="openItemEditor('synonym', -1)">新增路由词</el-button></div>
                <el-table :data="full.synonyms" border size="small">
                  <el-table-column label="同义词" min-width="180"><template #default="{ row }">{{ row.synonym }}</template></el-table-column>
                  <el-table-column label="归一词" min-width="180"><template #default="{ row }">{{ row.normalized_synonym }}</template></el-table-column>
                  <el-table-column label="权重" width="80"><template #default="{ row }">{{ row.weight }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button link type="primary" @click="openItemEditor('synonym', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.synonyms.splice($index, 1); markDirty()">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- LLD 文档 -->
              <el-tab-pane label="LLD 文档" name="lld">
                <div class="toolbar"><el-button size="small" @click="openItemEditor('lld', -1)">新增 LLD</el-button></div>
                <el-table :data="full.lld_documents" border size="small">
                  <el-table-column label="版本" width="80"><template #default="{ row }">v{{ row.version }}</template></el-table-column>
                  <el-table-column label="标题" min-width="200"><template #default="{ row }">{{ row.title || '(未命名)' }}</template></el-table-column>
                  <el-table-column label="内容预览" min-width="300"><template #default="{ row }"><div class="text-preview">{{ (row.content || '').slice(0, 80) || '(空)' }}</div></template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button link type="primary" @click="openItemEditor('lld', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.lld_documents.splice($index, 1); markDirty()">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 数据字典 -->
              <el-tab-pane label="数据字典" name="dictionary">
                <div class="toolbar">
                  <el-button size="small" @click="openItemEditor('dict', -1)">新增字段</el-button>
                  <el-button size="small" type="success" @click="extractDictFromDDL">从 DDL 提取字段</el-button>
                </div>
                <el-table :data="full.data_dictionary" border size="small">
                  <el-table-column label="表名" min-width="160"><template #default="{ row }">{{ row.table_name }}</template></el-table-column>
                  <el-table-column label="字段" min-width="140"><template #default="{ row }">{{ row.column_name }}</template></el-table-column>
                  <el-table-column label="JSONB Key" min-width="120"><template #default="{ row }">{{ row.jsonb_key || '-' }}</template></el-table-column>
                  <el-table-column label="语义名" min-width="140"><template #default="{ row }">{{ row.semantic_name || '-' }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button link type="primary" @click="openItemEditor('dict', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.data_dictionary.splice($index, 1); markDirty()">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- DDL + 表关联 (保留原始交互方式，已有 Drawer) -->
              <el-tab-pane label="DDL + 表关联" name="schema">
                <div class="toolbar">
                  <el-button size="small" @click="openSourceTableDialog">从数据源拉表</el-button>
                  <el-button size="small" @click="addSchema">新增DDL</el-button>
                  <el-button size="small" @click="openItemEditor('relation', -1)">新增关联</el-button>
                </div>
                <div class="section-title">表清单和 DDL</div>
                <el-table :data="full.schema_definition" border size="small">
                  <el-table-column label="来源" width="140"><template #default="{ row }"><el-tag effect="plain" size="small">{{ sourceNameById(row.source_id) }}</el-tag></template></el-table-column>
                  <el-table-column label="表名" width="200"><template #default="{ row }"><span class="schema-name-cell">{{ row.table_name || '未命名表' }}</span></template></el-table-column>
                  <el-table-column label="DDL 预览" min-width="300"><template #default="{ row }"><div class="ddl-preview-line">{{ ddlPreview(row.ddl_sql) }}</div></template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ row, $index }">
                      <el-button link type="primary" @click="openSchemaEditor(row, $index)">编辑</el-button>
                      <el-button link type="danger" @click="removeSchema($index)">删除</el-button>
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
                      <el-button link type="primary" @click="openItemEditor('relation', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.table_relations.splice($index, 1); markDirty()">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- Golden SQL -->
              <el-tab-pane label="Golden SQL" name="golden">
                <div class="toolbar"><el-button size="small" @click="openItemEditor('golden', -1)">新增训练实例</el-button></div>
                <el-table :data="full.golden_sql_samples" border size="small">
                  <el-table-column label="Intent" width="100"><template #default="{ row }">{{ row.intent_type }}</template></el-table-column>
                  <el-table-column label="问题" min-width="260"><template #default="{ row }">{{ row.question || '(空)' }}</template></el-table-column>
                  <el-table-column label="SQL 预览" min-width="280"><template #default="{ row }"><div class="ddl-preview-line">{{ (row.sql_text || '').slice(0, 100) || '(空)' }}</div></template></el-table-column>
                  <el-table-column label="分数" width="70"><template #default="{ row }">{{ row.quality_score }}</template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button link type="primary" @click="openItemEditor('golden', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.golden_sql_samples.splice($index, 1); markDirty()">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- Agent 提示片段 -->
              <el-tab-pane label="Agent 提示片段" name="prompts">
                <div class="toolbar"><el-button size="small" @click="openItemEditor('prompt', -1)">新增片段</el-button></div>
                <el-table :data="full.agent_prompts" border size="small">
                  <el-table-column label="Agent" width="90"><template #default="{ row }">Agent{{ row.agent_no }}</template></el-table-column>
                  <el-table-column label="Key" width="150"><template #default="{ row }">{{ row.prompt_key }}</template></el-table-column>
                  <el-table-column label="内容预览" min-width="300"><template #default="{ row }"><div class="text-preview">{{ (row.prompt_content || '').slice(0, 120) || '(空)' }}</div></template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button link type="primary" @click="openItemEditor('prompt', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.agent_prompts.splice($index, 1); markDirty()">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 外部配置 -->
              <el-tab-pane label="飞书/外部配置" name="external">
                <div class="toolbar"><el-button size="small" @click="openItemEditor('extcfg', -1)">新增配置</el-button></div>
                <el-table :data="full.external_configs" border size="small">
                  <el-table-column label="类型" width="140"><template #default="{ row }">{{ row.config_type }}</template></el-table-column>
                  <el-table-column label="Key" width="200"><template #default="{ row }">{{ row.config_key }}</template></el-table-column>
                  <el-table-column label="配置预览" min-width="300"><template #default="{ row }"><div class="text-preview">{{ jsonString(row.config_value).slice(0, 100) }}</div></template></el-table-column>
                  <el-table-column label="操作" width="130">
                    <template #default="{ $index }">
                      <el-button link type="primary" @click="openItemEditor('extcfg', $index)">编辑</el-button>
                      <el-button link type="danger" @click="full.external_configs.splice($index, 1); markDirty()">删除</el-button>
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
        <el-button type="primary" @click="saveItemEditor">确认保存</el-button>
      </template>
    </el-dialog>

    <!-- 从数据源拉表 dialog -->
    <el-dialog v-model="sourceDialogVisible" title="从数据源拉表进数据集" width="72%">
      <div class="toolbar-col" style="margin-bottom:10px">
        <el-select v-model="sourceDialogSourceId" placeholder="选择数据源" style="width:320px">
          <el-option v-for="source in dataSources" :key="source.id" :label="source.name" :value="source.id" />
        </el-select>
        <el-button type="primary" @click="loadSourceTables">加载表清单</el-button>
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
        <el-button type="primary" @click="appendSelectedSourceTables">
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
            <el-button type="primary" @click="saveSchemaEditor">保存 DDL</el-button>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createBookshelfDataset, deleteBookshelfDataset, getBookshelfDatasetFull,
  getBookshelfDatasets, getDataSources, getSourceTables,
  saveBookshelfDatasetFull, updateBookshelfDataset
} from '../api/index.js'

// ========== 基础状态 ==========
const datasets = ref([])
const dataSources = ref([])
const listFilterSourceId = ref('')
const searchKeyword = ref('')
const selectedDatasetId = ref(null)
const activeTab = ref('common_questions')
const isDirty = ref(false)
const newDatasetSourceId = ref(null)
const qualitySummary = ref(null)

const datasetForm = reactive({ dataset_code: '', dataset_name: '', business_domain: '', source_id: null, description: '', is_active: true })
const full = reactive({
  common_questions: [], regression_cases: [], synonyms: [], lld_documents: [], data_dictionary: [],
  schema_definition: [], table_relations: [], golden_sql_samples: [],
  agent_prompts: [], external_configs: []
})

const markDirty = () => { isDirty.value = true }
const qualityAlertType = computed(() => {
  if (!qualitySummary.value) return 'info'
  return qualitySummary.value.level === 'healthy' ? 'success' : qualitySummary.value.level === 'warning' ? 'warning' : 'error'
})
const qualityCheckTagType = (status) => (status === 'healthy' ? 'success' : status === 'warning' ? 'warning' : 'danger')

// ========== 左侧:搜索+筛选 ==========
const filteredDatasets = computed(() => {
  let list = datasets.value
  if (listFilterSourceId.value) list = list.filter(i => Number(i.source_id) === Number(listFilterSourceId.value))
  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter(i => (i.dataset_name || '').toLowerCase().includes(kw) || (i.dataset_code || '').toLowerCase().includes(kw))
  }
  return list
})

const sourceNameById = (id) => dataSources.value.find(x => Number(x.id) === Number(id))?.name || '未设置'

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

const openItemEditor = (type, index) => {
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

// ========== 数据加载/保存 ==========
const applyDataset = (d) => {
  datasetForm.dataset_code = d?.dataset_code || ''; datasetForm.dataset_name = d?.dataset_name || ''
  datasetForm.business_domain = d?.business_domain || ''; datasetForm.source_id = d?.source_id || null
  datasetForm.description = d?.description || ''; datasetForm.is_active = d?.is_active !== false
}
const resetFull = () => { Object.keys(full).forEach(k => { full[k] = [] }); qualitySummary.value = null }

const loadDatasets = async () => { datasets.value = (await getBookshelfDatasets()).datasets || [] }
const loadDataSources = async () => {
  dataSources.value = (await getDataSources()).databases || []
  if (!newDatasetSourceId.value && dataSources.value.length > 0) newDatasetSourceId.value = dataSources.value[0].id
}

const selectDataset = async (dataset) => {
  selectedDatasetId.value = dataset.id
  applyDataset(dataset)
  const r = await getBookshelfDatasetFull(dataset.id)
  Object.keys(COLLECTIONS).forEach(type => { full[COLLECTIONS[type]] = r[COLLECTIONS[type]] || [] })
  qualitySummary.value = r.quality_summary || null
  isDirty.value = false
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
  await ElMessageBox.confirm('确认删除当前数据集吗？', '删除确认', { type: 'warning' })
  await deleteBookshelfDataset(selectedDatasetId.value)
  ElMessage.success('数据集已删除'); selectedDatasetId.value = null; resetFull(); isDirty.value = false; await loadDatasets()
}

const saveFull = async () => {
  if (!selectedDatasetId.value) return
  const payload = {}; Object.keys(COLLECTIONS).forEach(type => { payload[COLLECTIONS[type]] = full[COLLECTIONS[type]] })
  try {
    await updateBookshelfDataset(selectedDatasetId.value, { ...datasetForm })
    await saveBookshelfDatasetFull(selectedDatasetId.value, payload)
    ElMessage.success('书架内容已保存'); isDirty.value = false
    await loadDatasets()
  } catch (err) {
    const details = err?.response?.data?.details
    if (Array.isArray(details) && details.length) {
      ElMessageBox.alert(details.join('<br/>'), '保存前校验未通过', {
        confirmButtonText: '知道了',
        dangerouslyUseHTMLString: true,
        type: 'warning',
      })
      return
    }
    ElMessage.error(err?.response?.data?.error || err?.message || '保存失败')
  }
}

// ========== 从数据源拉表 ==========
const sourceDialogVisible = ref(false); const sourceDialogSourceId = ref(null)
const sourceTables = ref([]); const selectedSourceTables = ref([])

const openSourceTableDialog = () => { sourceDialogVisible.value = true; sourceDialogSourceId.value = datasetForm.source_id || dataSources.value[0]?.id || null; sourceTables.value = []; selectedSourceTables.value = [] }
const loadSourceTables = async () => { if (!sourceDialogSourceId.value) { ElMessage.warning('请先选择数据源'); return }; sourceTables.value = (await getSourceTables(sourceDialogSourceId.value)).tables || [] }
const onSourceTableSelection = (rows) => { selectedSourceTables.value = rows || [] }
const appendSelectedSourceTables = () => {
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
  schemaEditorIndex.value = index
  if (row) { schemaEditor.table_name = row.table_name || ''; schemaEditor.ddl_sql = row.ddl_sql || ''; schemaEditor.description = row.description || ''; schemaEditor.source_id = row.source_id || null }
  else resetSchemaEditor()
  schemaEditorVisible.value = true
}
const saveSchemaEditor = () => {
  if (!schemaEditor.table_name.trim()) { ElMessage.warning('请填写表名'); return }
  const item = { table_name: schemaEditor.table_name.trim(), ddl_sql: schemaEditor.ddl_sql || '', description: schemaEditor.description || '', source_id: schemaEditor.source_id || null }
  if (schemaEditorIndex.value >= 0) full.schema_definition[schemaEditorIndex.value] = item
  else full.schema_definition.push(item)
  schemaEditorVisible.value = false; resetSchemaEditor(); markDirty()
}
const removeSchema = (i) => { full.schema_definition.splice(i, 1); markDirty() }
const addSchema = () => openSchemaEditor()

// ========== 工具函数 ==========
const ddlPreview = (t) => { const n = String(t || '').replace(/\s+/g, ' ').trim(); return n ? (n.length > 120 ? n.slice(0, 120) + '...' : n) : '暂无 DDL' }
const jsonString = (v) => { try { return JSON.stringify(v || {}, null, 2) } catch { return '{}' } }

onMounted(async () => {
  await Promise.all([loadDatasets(), loadDataSources()])
  if (datasets.value.length > 0) await selectDataset(datasets.value[0])
  else resetFull()
})
</script>

<style scoped>
.dataset-page { min-height: calc(100vh - 150px); }
.glass-card { border: 1px solid var(--border, #e5e6eb); background: var(--bg-card, #fff); border-radius: var(--radius-card, 12px); box-shadow: var(--shadow-xs); }
.sidebar-card { min-height: calc(100vh - 150px); }
.panel-title { font-size: 18px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; color: var(--text-title, #1d2129); }
.header-row { display: flex; align-items: center; justify-content: space-between; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.toolbar-col { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.dataset-tile { padding: 12px 14px; border-radius: var(--radius-card, 12px); margin-bottom: 8px; border: 1px solid var(--border, #e5e6eb); background: var(--bg-card, #fff); cursor: pointer; transition: all var(--duration-normal, 220ms) var(--ease-out); }
.dataset-tile:hover { border-color: var(--border-hover, #c9cdd4); box-shadow: var(--shadow-sm); transform: translateY(-1px); }
.dataset-tile.active { border-color: var(--color-primary, #3370ff); background: var(--color-primary-light, #f0f5ff); box-shadow: var(--shadow-md); }
.dataset-tile-title { font-weight: 700; font-size: 14px; color: var(--text-title, #1d2129); }
.dataset-tile-meta { margin-top: 3px; font-size: 11px; color: var(--text-muted, #86909c); }
.dataset-tile-sub { margin-top: 4px; font-size: 11px; color: var(--text-muted, #86909c); }
.base-form { margin-bottom: 10px; }
.quality-alert { margin-bottom: 14px; }
.quality-overview { display: flex; flex-direction: column; gap: 10px; padding-top: 4px; }
.quality-checks { display: flex; flex-wrap: wrap; gap: 8px; }
.quality-gaps { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-body, #4e5969); line-height: 1.6; }
.toolbar { margin-bottom: 10px; display: flex; gap: 8px; }
.section-title { margin: 18px 0 10px; font-weight: 700; font-size: 14px; color: var(--text-title, #1d2129); }
.text-preview { font-size: 12px; color: var(--text-body, #4e5969); line-height: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 400px; }
.schema-name-cell { font-weight: 600; color: var(--text-title, #1d2129); }
.ddl-preview-line { font-family: 'JetBrains Mono', Consolas, Monaco, monospace; font-size: 12px; line-height: 1.4; color: var(--text-body, #4e5969); word-break: break-word; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 500px; }
.schema-editor-shell { display: flex; flex-direction: column; gap: 18px; height: 100%; }
.schema-editor-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.schema-editor-subtitle { margin-top: 6px; color: var(--text-muted, #86909c); font-size: 13px; }
.schema-editor-form { flex: 1; }
.mono-textarea :deep(textarea) { font-family: 'JetBrains Mono', Consolas, Monaco, monospace; font-size: 13px; line-height: 1.6; }
</style>
