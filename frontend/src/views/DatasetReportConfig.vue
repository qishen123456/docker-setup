<template>
  <div class="rc-page" v-loading="loading">
    <div class="rc-layout">
      <!-- LEFT: Dataset List -->
      <aside class="rc-sidebar">
        <div class="rc-sidebar-title">数据集</div>
        <div class="rc-sidebar-scroll">
          <div
            v-for="ds in datasets" :key="ds.id"
            class="rc-ds-item"
            :class="{ 'is-active': selectedDatasetId === ds.id }"
            @click="selectDataset(ds.id)"
          >
            <el-icon class="rc-ds-icon"><Grid /></el-icon>
            <div class="rc-ds-meta">
              <div class="rc-ds-name">{{ ds.dataset_name || ds.dataset_code || `数据集#${ds.id}` }}</div>
              <div class="rc-ds-code">{{ ds.dataset_code || '' }}</div>
            </div>
            <span v-if="ds._hasConfig" class="rc-ds-badge">已配</span>
          </div>
          <div v-if="!datasets.length" class="rc-ds-empty">暂无数据集</div>
        </div>
      </aside>

      <!-- RIGHT: Config Editor -->
      <main class="rc-main" v-if="selectedDatasetId">
        <div class="rc-main-header">
          <div class="rc-main-title">
            {{ selectedDatasetName }}
            <el-tag v-if="hasConfig" type="success" size="small" effect="plain" round>已配置</el-tag>
            <el-tag v-else type="info" size="small" effect="plain" round>未配置</el-tag>
          </div>
          <div class="rc-main-actions">
            <el-button v-if="isFeatureEnabled('report_template_edit')" size="small" @click="loadDefaultConfig">加载默认模板</el-button>
            <el-button v-if="isFeatureEnabled('report_template_edit')" size="small" type="primary" :loading="saving" @click="saveConfig">保存</el-button>
          </div>
        </div>

        <el-tabs v-model="activeTab" class="rc-tabs">
          <!-- Visual Editor -->
          <el-tab-pane label="可视化编辑" name="visual">
            <div class="rc-form-grid">
              <!-- Column Mapping Card -->
              <div class="rc-card">
                <div class="rc-card-title">列映射</div>
                <div class="rc-card-body">
                  <div class="rc-help-text">这里是 SQL 结果的标准列名，不要求源表物理存在。Agent2 会按下方 SQL 输出契约把源字段投影成这些列。</div>
                  <div class="rc-field-grid">
                    <div class="rc-field">
                      <label>节点名称列</label>
                      <el-input v-model="configForm.nameColumn" size="small" placeholder="节点名称" />
                    </div>
                    <div class="rc-field">
                      <label>上级名称列</label>
                      <el-input v-model="configForm.parentColumn" size="small" placeholder="上级名称" />
                    </div>
                    <div class="rc-field">
                      <label>条线列</label>
                      <el-input v-model="configForm.trackColumn" size="small" placeholder="条线" />
                    </div>
                    <div class="rc-field">
                      <label>层级列</label>
                      <el-input v-model="configForm.levelColumn" size="small" placeholder="层级" />
                    </div>
                  </div>
                </div>
              </div>

              <div class="rc-card rc-card-wide">
                <div class="rc-card-title">源数据结构与报告意图</div>
                <div class="rc-card-body">
                  <div class="rc-field">
                    <label>业务背景 / Agent 参考口径</label>
                    <el-input v-model="configForm.businessContext" type="textarea" :rows="3" size="small" placeholder="例如：源数据没有父子字段，组织链路由 SQL 从分公司/代表处/业务代表字段生成。" />
                  </div>
                  <div class="rc-field" style="margin-top:12px">
                    <label>Agent4 写作口径</label>
                    <el-input v-model="configForm.agentReportGuidance" type="textarea" :rows="2" size="small" placeholder="例如：结构由系统生成，Agent4 只补洞察、风险解释和建议。" />
                  </div>
                </div>
              </div>

              <div class="rc-card rc-card-wide">
                <div class="rc-card-title">SQL 标准输出契约</div>
                <div class="rc-card-body">
                  <div class="rc-help-text">用于约束 Agent2：无论源表字段如何，最终 SQL 应输出这些报告标准列，前端再用 rows + 上级名称动态建树。</div>
                  <div class="rc-field-grid">
                    <div class="rc-field">
                      <label>必需结构列</label>
                      <el-input v-model="requiredColumnsText" size="small" placeholder="条线, 层级, 节点名称, 上级名称" />
                    </div>
                    <div class="rc-field">
                      <label>指标输出列</label>
                      <el-input v-model="metricColumnsText" size="small" placeholder="总任务金额, 年度开单金额, 达成率, 剩余任务金额" />
                    </div>
                  </div>
                  <div class="rc-field" style="margin-top:12px">
                    <label>SQL 投影规则</label>
                    <el-input v-model="sqlContractNotesText" type="textarea" :rows="5" size="small" placeholder="每行一条，例如：源表没有节点名称时，用 SELECT 别名生成。" />
                  </div>
                </div>
              </div>

              <div class="rc-card rc-card-wide">
                <div class="rc-card-title">意图策略</div>
                <div class="rc-card-body">
                  <div class="rc-help-text">按数据集独立配置排名、TopN、最高/最低、目标层级和默认排序指标。问数时只读取当前数据集策略，不影响其他数据集。</div>
                  <div class="rc-field-grid">
                    <div class="rc-field">
                      <label>排名意图</label>
                      <el-switch
                        v-model="rankingPolicy.enabled"
                        size="small"
                        active-text="启用"
                        inactive-text="停用"
                      />
                    </div>
                    <div class="rc-field">
                      <label>默认方向</label>
                      <el-select v-model="rankingPolicy.defaultDirection" size="small">
                        <el-option label="从高到低" value="desc" />
                        <el-option label="从低到高" value="asc" />
                      </el-select>
                    </div>
                    <div class="rc-field">
                      <label>默认 TopN</label>
                      <el-input-number v-model="rankingPolicy.defaultTopN" size="small" :min="1" :max="50" controls-position="right" />
                    </div>
                    <div class="rc-field">
                      <label>最大 TopN</label>
                      <el-input-number v-model="rankingPolicy.maxTopN" size="small" :min="1" :max="200" controls-position="right" />
                    </div>
                    <div class="rc-field">
                      <label>默认排序指标</label>
                      <el-select v-model="rankingPolicy.defaultMetricKey" size="small" filterable allow-create default-first-option placeholder="选择指标 Key">
                        <el-option v-for="metric in metricOptions" :key="metric.key" :label="metric.label" :value="metric.key" />
                      </el-select>
                    </div>
                    <div class="rc-field">
                      <label>输出模式</label>
                      <el-select v-model="rankingPolicy.outputMode" size="small">
                        <el-option label="只返回排名对象" value="topn_only" />
                        <el-option label="返回排名与上下文" value="topn_with_context" />
                      </el-select>
                    </div>
                  </div>
                  <div class="rc-field-grid" style="margin-top:12px">
                    <div class="rc-field">
                      <label>排名触发词</label>
                      <el-input v-model="rankingTriggersText" size="small" placeholder="排名,排行,Top,前,最高,最好" />
                    </div>
                    <div class="rc-field">
                      <label>低位/倒序触发词</label>
                      <el-input v-model="rankingNegativeTriggersText" size="small" placeholder="最低,最差,后,倒数,垫底" />
                    </div>
                  </div>
                  <div class="rc-field" style="margin-top:12px">
                    <label>目标层级别名</label>
                    <el-input
                      v-model="rankingAliasLinesText"
                      type="textarea"
                      :rows="4"
                      size="small"
                      placeholder="每行一个层级，例如：分公司=分公司,区域公司&#10;城市公司=城市公司,城市分公司"
                    />
                  </div>
                  <el-collapse class="rc-advanced-config">
                    <el-collapse-item title="高级 JSON" name="intent-json">
                      <el-input
                        v-model="intentPoliciesText"
                        type="textarea"
                        :rows="8"
                        size="small"
                        class="rc-json-editor"
                        @blur="applyIntentPoliciesText"
                      />
                    </el-collapse-item>
                  </el-collapse>
                  <div class="rc-help-text rc-help-text-bottom">
                    例如“消费者前三的分公司”会命中排名意图，目标层级取“分公司”，TopN 取 3，排序指标默认取上方选择的指标。
                  </div>
                </div>
              </div>

              <div class="rc-card rc-card-wide">
                <div class="rc-card-title">
                  分析维度 / 管理链路
                  <el-button v-if="isFeatureEnabled('report_template_edit')" text type="primary" size="small" @click="addAnalysisDimension">+ 添加</el-button>
                </div>
                <div class="rc-card-body">
                  <el-table :data="configForm.analysisDimensions" size="small" border stripe>
                    <el-table-column label="Key" width="130">
                      <template #default="{ row }"><el-input v-model="row.key" size="small" /></template>
                    </el-table-column>
                    <el-table-column label="显示名" width="140">
                      <template #default="{ row }"><el-input v-model="row.label" size="small" /></template>
                    </el-table-column>
                    <el-table-column label="链路" min-width="220">
                      <template #default="{ row }"><el-input :model-value="(row.path || []).join(' -> ')" size="small" @update:model-value="value => row.path = splitList(value, '->')" /></template>
                    </el-table-column>
                    <el-table-column label="源字段" min-width="180">
                      <template #default="{ row }"><el-input :model-value="(row.sourceFields || []).join(', ')" size="small" @update:model-value="value => row.sourceFields = splitList(value)" /></template>
                    </el-table-column>
                    <el-table-column label="用途" min-width="220">
                      <template #default="{ row }"><el-input v-model="row.purpose" size="small" /></template>
                    </el-table-column>
                    <el-table-column label="" width="50">
                      <template #default="{ $index }">
                        <el-button v-if="isFeatureEnabled('report_template_edit')" text type="danger" size="small" @click="configForm.analysisDimensions.splice($index, 1)">×</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>

              <!-- Report Title + Threshold Card -->
              <div class="rc-card">
                <div class="rc-card-title">报告设置</div>
                <div class="rc-card-body">
                  <div class="rc-field">
                    <label>报告标题</label>
                    <el-input v-model="configForm.reportTitle" size="small" placeholder="经营分析报告" />
                  </div>
                  <div class="rc-field" style="margin-top:12px">
                    <label>风险阈值 (%)</label>
                    <el-slider v-model="configForm.riskThreshold" :min="0" :max="100" :step="5" show-input size="small" />
                  </div>
                  <div class="rc-field" style="margin-top:12px">
                    <label>报告章节</label>
                    <el-checkbox-group v-model="configForm.sections" size="small">
                      <el-checkbox label="core">核心指标</el-checkbox>
                      <el-checkbox label="group">分组分析</el-checkbox>
                      <el-checkbox label="risk">风险预警</el-checkbox>
                      <el-checkbox label="strategy">策略建议</el-checkbox>
                    </el-checkbox-group>
                  </div>
                </div>
              </div>

              <!-- Metrics Card -->
              <div class="rc-card rc-card-wide">
                <div class="rc-card-title">
                  指标定义
                  <el-button v-if="isFeatureEnabled('report_template_edit')" text type="primary" size="small" @click="addMetric">+ 添加</el-button>
                </div>
                <div class="rc-card-body">
                  <el-table :data="configForm.metrics" size="small" border stripe>
                    <el-table-column label="Key" width="100">
                      <template #default="{ row }"><el-input v-model="row.key" size="small" /></template>
                    </el-table-column>
                    <el-table-column label="显示名" width="130">
                      <template #default="{ row }"><el-input v-model="row.label" size="small" /></template>
                    </el-table-column>
                    <el-table-column label="数据列名" min-width="140">
                      <template #default="{ row }"><el-input v-model="row.column" size="small" /></template>
                    </el-table-column>
                    <el-table-column label="格式" width="100">
                      <template #default="{ row }">
                        <el-select v-model="row.format" size="small">
                          <el-option label="金额" value="amount" />
                          <el-option label="百分比" value="percent" />
                          <el-option label="数字" value="number" />
                          <el-option label="文本" value="text" />
                        </el-select>
                      </template>
                    </el-table-column>
                    <el-table-column label="" width="50">
                      <template #default="{ $index }">
                        <el-button v-if="isFeatureEnabled('report_template_edit')" text type="danger" size="small" @click="configForm.metrics.splice($index, 1)">×</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>

              <!-- Signal Rules Card -->
              <div class="rc-card rc-card-wide">
                <div class="rc-card-title">
                  信号灯规则
                  <el-button v-if="isFeatureEnabled('report_template_edit')" text type="primary" size="small" @click="addSignalRule">+ 添加</el-button>
                </div>
                <div class="rc-card-body">
                  <el-table :data="configForm.signalRules" size="small" border stripe>
                    <el-table-column label="指标" width="100">
                      <template #default="{ row }">
                        <el-select v-model="row.key" size="small">
                          <el-option v-for="m in configForm.metrics" :key="m.key" :label="m.label||m.key" :value="m.key" />
                        </el-select>
                      </template>
                    </el-table-column>
                    <el-table-column label="运算" width="70">
                      <template #default="{ row }">
                        <el-select v-model="row.op" size="small">
                          <el-option label=">=" value=">=" /><el-option label="<" value="<" />
                          <el-option label="<=" value="<=" /><el-option label=">" value=">" />
                        </el-select>
                      </template>
                    </el-table-column>
                    <el-table-column label="阈值" width="90">
                      <template #default="{ row }"><el-input-number v-model="row.value" size="small" :step="5" controls-position="right" /></template>
                    </el-table-column>
                    <el-table-column label="信号" width="90">
                      <template #default="{ row }">
                        <el-select v-model="row.tone" size="small">
                          <el-option label="🟢 绿" value="good" /><el-option label="🟡 黄" value="warn" /><el-option label="🔴 红" value="danger" />
                        </el-select>
                      </template>
                    </el-table-column>
                    <el-table-column label="标签" width="80">
                      <template #default="{ row }"><el-input v-model="row.label" size="small" /></template>
                    </el-table-column>
                    <el-table-column label="" width="50">
                      <template #default="{ $index }">
                        <el-button v-if="isFeatureEnabled('report_template_edit')" text type="danger" size="small" @click="configForm.signalRules.splice($index, 1)">×</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- JSON Editor -->
          <el-tab-pane label="JSON 编辑器" name="json">
            <el-input
              v-model="jsonText"
              type="textarea"
              :autosize="{ minRows: 24, maxRows: 50 }"
              class="rc-json-editor"
            />
            <div class="rc-json-actions">
              <el-button v-if="isFeatureEnabled('report_template_edit')" size="small" @click="parseJson">应用 JSON → 可视化</el-button>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- Bottom bar -->
        <div class="rc-bottom-bar">
          <el-popconfirm v-if="hasConfig && isFeatureEnabled('report_template_delete')" title="确认删除此数据集的报告配置？" @confirm="deleteConfig">
            <template #reference><el-button type="danger" plain size="small">删除配置</el-button></template>
          </el-popconfirm>
          <div class="rc-spacer"></div>
          <el-button v-if="isFeatureEnabled('report_template_edit')" size="small" @click="loadDefaultConfig">重置为默认</el-button>
          <el-button v-if="isFeatureEnabled('report_template_edit')" type="primary" size="small" :loading="saving" @click="saveConfig">保存配置</el-button>
        </div>
      </main>

      <!-- Empty State -->
      <main class="rc-main rc-main-empty" v-else>
        <div class="rc-empty-hint">
          <el-icon :size="40" color="#D1D5DB"><Grid /></el-icon>
          <p>请在左侧选择一个数据集进行配置</p>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Grid, Refresh } from '@element-plus/icons-vue'
import { getReportConfig, upsertReportConfig, deleteReportConfig, getDefaultReportConfig } from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'
import axios from 'axios'

const loading = ref(false)
const saving = ref(false)
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const datasets = ref([])
const selectedDatasetId = ref(null)
const activeTab = ref('visual')
const jsonText = ref('')
const intentPoliciesText = ref('{}')
const hasConfig = ref(false)

const configForm = ref({
  nameColumn: '', parentColumn: '', trackColumn: '', levelColumn: '',
  reportTitle: '', riskThreshold: 80,
  metrics: [], signalRules: [], sections: ['core', 'group', 'risk', 'strategy'],
  levels: [], trackValues: {},
  businessContext: '', agentReportGuidance: '', sourceFields: {},
  sqlOutputContract: { requiredColumns: [], metricColumns: [], notes: [] },
  analysisDimensions: [],
  intentPolicies: {},
})

const defaultRankingPolicy = {
  enabled: true,
  triggers: ['排名', '排行', 'Top', '前', '后', '最高', '最低', '最好', '最差', '倒数', '垫底'],
  defaultTopN: 3,
  maxTopN: 20,
  defaultMetricKey: 'rate',
  defaultDirection: 'desc',
  negativeTriggers: ['最低', '最差', '后', '倒数', '垫底', '落后'],
  targetLevelAliases: {
    分公司: ['分公司'],
    代表处: ['代表处'],
    业务部: ['业务部', '行业部'],
    业务代表: ['业务代表', '业务员', '个人'],
    城市公司: ['城市公司', '城市分公司'],
  },
  outputMode: 'topn_only',
}

const splitList = (value, delimiter = ',') => String(value || '')
  .split(delimiter)
  .map(item => item.trim())
  .filter(Boolean)

const splitFlexibleList = (value) => String(value || '')
  .split(/[,，、\n]+/)
  .map(item => item.trim())
  .filter(Boolean)

const ensureRankingPolicy = () => {
  if (!configForm.value.intentPolicies || typeof configForm.value.intentPolicies !== 'object') {
    configForm.value.intentPolicies = {}
  }
  if (!configForm.value.intentPolicies.ranking || typeof configForm.value.intentPolicies.ranking !== 'object') {
    configForm.value.intentPolicies.ranking = {}
  }
  const policy = configForm.value.intentPolicies.ranking
  Object.entries(defaultRankingPolicy).forEach(([key, value]) => {
    if (key === 'targetLevelAliases') return
    if (policy[key] !== undefined) return
    policy[key] = Array.isArray(value) ? [...value] : value
  })
  if (!policy.targetLevelAliases || typeof policy.targetLevelAliases !== 'object') {
    policy.targetLevelAliases = {}
  }
  Object.entries(defaultRankingPolicy.targetLevelAliases).forEach(([level, aliases]) => {
    if (!policy.targetLevelAliases[level]) {
      policy.targetLevelAliases[level] = [...aliases]
    }
  })
  return policy
}

const requiredColumnsText = computed({
  get: () => (configForm.value.sqlOutputContract?.requiredColumns || []).join(', '),
  set: (value) => {
    configForm.value.sqlOutputContract = { ...(configForm.value.sqlOutputContract || {}), requiredColumns: splitList(value) }
  },
})

const metricColumnsText = computed({
  get: () => (configForm.value.sqlOutputContract?.metricColumns || []).join(', '),
  set: (value) => {
    configForm.value.sqlOutputContract = { ...(configForm.value.sqlOutputContract || {}), metricColumns: splitList(value) }
  },
})

const sqlContractNotesText = computed({
  get: () => (configForm.value.sqlOutputContract?.notes || []).join('\n'),
  set: (value) => {
    configForm.value.sqlOutputContract = { ...(configForm.value.sqlOutputContract || {}), notes: splitList(value, '\n') }
  },
})

const selectedDatasetName = computed(() => {
  const ds = datasets.value.find(d => d.id === selectedDatasetId.value)
  return ds ? (ds.dataset_name || ds.dataset_code || `数据集#${ds.id}`) : ''
})

const rankingPolicy = computed(() => ensureRankingPolicy())

const metricOptions = computed(() => (configForm.value.metrics || [])
  .filter(metric => metric && (metric.key || metric.label || metric.column))
  .map(metric => ({
    key: metric.key || metric.column || metric.label,
    label: `${metric.label || metric.key || metric.column}${metric.column ? ` · ${metric.column}` : ''}`,
  })))

const rankingTriggersText = computed({
  get: () => (ensureRankingPolicy().triggers || []).join(', '),
  set: (value) => { ensureRankingPolicy().triggers = splitFlexibleList(value) },
})

const rankingNegativeTriggersText = computed({
  get: () => (ensureRankingPolicy().negativeTriggers || []).join(', '),
  set: (value) => { ensureRankingPolicy().negativeTriggers = splitFlexibleList(value) },
})

const rankingAliasLinesText = computed({
  get: () => Object.entries(ensureRankingPolicy().targetLevelAliases || {})
    .map(([level, aliases]) => `${level}=${(aliases || []).join(',')}`)
    .join('\n'),
  set: (value) => {
    const aliases = {}
    String(value || '').split('\n').forEach(line => {
      const [level, aliasText = ''] = line.split('=')
      const normalizedLevel = String(level || '').trim()
      if (!normalizedLevel) return
      aliases[normalizedLevel] = splitFlexibleList(aliasText || normalizedLevel)
    })
    ensureRankingPolicy().targetLevelAliases = aliases
  },
})

const addMetric = () => configForm.value.metrics.push({ key: '', label: '', column: '', format: 'amount' })
const addSignalRule = () => configForm.value.signalRules.push({ key: '', op: '>=', value: 0, tone: 'good', label: '' })
const addAnalysisDimension = () => configForm.value.analysisDimensions.push({ key: '', label: '', path: [], sourceFields: [], purpose: '' })

const syncIntentPoliciesText = () => {
  ensureRankingPolicy()
  intentPoliciesText.value = JSON.stringify(configForm.value.intentPolicies || {}, null, 2)
}

const applyIntentPoliciesText = () => {
  try {
    configForm.value.intentPolicies = JSON.parse(intentPoliciesText.value || '{}')
    ensureRankingPolicy()
    return true
  } catch (e) {
    ElMessage.error('意图策略 JSON 格式错误: ' + e.message)
    syncIntentPoliciesText()
    return false
  }
}

const loadDatasets = async () => {
  try {
    const r = await axios.get('/api/bookshelves/datasets')
    datasets.value = (r.data?.datasets || r.data || []).map(ds => ({ ...ds, _hasConfig: false }))
    // Check which have configs
    for (const ds of datasets.value) {
      try {
        const cr = await getReportConfig(ds.id)
        ds._hasConfig = !!(cr.config)
      } catch { /* skip */ }
    }
  } catch { datasets.value = [] }
}

const selectDataset = (id) => {
  selectedDatasetId.value = id
  loadConfig(id)
}

const loadConfig = async (dsId) => {
  if (!dsId) return
  loading.value = true
  try {
    const r = await getReportConfig(dsId)
    hasConfig.value = !!(r.config)
    const cfg = r.config || r.default_config || {}
    Object.assign(configForm.value, {
      nameColumn: cfg.nameColumn || '',
      parentColumn: cfg.parentColumn || '',
      trackColumn: cfg.trackColumn || '',
      levelColumn: cfg.levelColumn || '',
      reportTitle: cfg.reportTitle || '',
      riskThreshold: cfg.riskThreshold ?? 80,
      metrics: cfg.metrics || [],
      signalRules: cfg.signalRules || [],
      sections: cfg.sections || ['core', 'group', 'risk', 'strategy'],
      levels: cfg.levels || [],
      trackValues: cfg.trackValues || {},
      businessContext: cfg.businessContext || '',
      agentReportGuidance: cfg.agentReportGuidance || '',
      sourceFields: cfg.sourceFields || {},
      sqlOutputContract: cfg.sqlOutputContract || { requiredColumns: [], metricColumns: [], notes: [] },
      analysisDimensions: cfg.analysisDimensions || [],
      intentPolicies: cfg.intentPolicies || {},
    })
    syncIntentPoliciesText()
    jsonText.value = JSON.stringify(configForm.value, null, 2)
  } finally { loading.value = false }
}

const loadDefaultConfig = async () => {
  try {
    const r = await getDefaultReportConfig()
    const cfg = r.config || {}
    Object.assign(configForm.value, cfg)
    syncIntentPoliciesText()
    jsonText.value = JSON.stringify(configForm.value, null, 2)
    ElMessage.success('已加载默认模板')
  } catch { ElMessage.error('加载默认模板失败') }
}

const parseJson = () => {
  try {
    const parsed = JSON.parse(jsonText.value)
    Object.assign(configForm.value, parsed)
    syncIntentPoliciesText()
    ElMessage.success('JSON 已解析')
    activeTab.value = 'visual'
  } catch (e) { ElMessage.error('JSON 格式错误: ' + e.message) }
}

const saveConfig = async () => {
  saving.value = true
  try {
    ensureRankingPolicy()
    syncIntentPoliciesText()
    if (!applyIntentPoliciesText()) return
    await upsertReportConfig(selectedDatasetId.value, configForm.value)
    hasConfig.value = true
    // Update sidebar badge
    const ds = datasets.value.find(d => d.id === selectedDatasetId.value)
    if (ds) ds._hasConfig = true
    ElMessage.success('配置已保存')
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const deleteConfig = async () => {
  try {
    await deleteReportConfig(selectedDatasetId.value)
    hasConfig.value = false
    const ds = datasets.value.find(d => d.id === selectedDatasetId.value)
    if (ds) ds._hasConfig = false
    ElMessage.success('配置已删除')
    loadConfig(selectedDatasetId.value)
  } catch { ElMessage.error('删除失败') }
}

watch(configForm, () => {
  if (activeTab.value === 'visual') {
    jsonText.value = JSON.stringify(configForm.value, null, 2)
  }
}, { deep: true })

onMounted(() => {
  loadFeatureFlags()
  loadDatasets()
})
</script>

<style scoped>
.rc-page { height: 100%; display: flex; flex-direction: column; }

.rc-layout {
  flex: 1; display: flex; min-height: 0;
  background: var(--bg-card, #fff);
  border-radius: var(--radius-card, 12px); overflow: hidden;
  border: 1px solid var(--border, #E5E7EB);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(0,0,0,0.04));
}

/* LEFT SIDEBAR */
.rc-sidebar {
  width: 240px; min-width: 240px;
  background: var(--bg-muted, #F3F4F6);
  border-right: 1px solid var(--border, #E5E7EB);
  display: flex; flex-direction: column;
}
.rc-sidebar-title {
  padding: 14px 16px 10px;
  font-size: 13px; font-weight: 600; color: var(--text-body, #6B7280);
  text-transform: uppercase; letter-spacing: 0.04em;
  border-bottom: 1px solid var(--border, #E5E7EB);
}
.rc-sidebar-scroll {
  flex: 1; overflow-y: auto; padding: 8px;
}
.rc-ds-item {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-radius: var(--radius-md, 8px);
  cursor: pointer; transition: all var(--duration-fast, 150ms) ease;
  margin-bottom: 2px;
}
.rc-ds-item:hover { background: rgba(230, 31, 36, 0.04); }
.rc-ds-item.is-active {
  background: var(--color-primary-light, #FEF2F2);
  box-shadow: inset 3px 0 0 var(--color-primary, #E61F24);
}
.rc-ds-icon { font-size: 16px; color: var(--text-muted, #9CA3AF); flex-shrink: 0; }
.rc-ds-meta { flex: 1; min-width: 0; }
.rc-ds-name { font-size: 13px; font-weight: 500; color: var(--text-title, #111827); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc-ds-code { font-size: 10px; color: var(--text-muted, #9CA3AF); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc-ds-badge {
  font-size: 10px; font-weight: 600; color: var(--success, #10B981); background: var(--success-bg, #ECFDF5);
  padding: 1px 6px; border-radius: var(--radius-pill, 999px); flex-shrink: 0;
}
.rc-ds-empty { text-align: center; padding: 24px 0; color: var(--text-muted, #9CA3AF); font-size: 13px; }

/* RIGHT MAIN */
.rc-main {
  flex: 1; overflow-y: auto; padding: 24px 32px;
  background: var(--bg-card, #fff);
}
.rc-main-empty {
  display: flex; align-items: center; justify-content: center;
}
.rc-empty-hint { text-align: center; color: var(--text-muted, #9CA3AF); }
.rc-empty-hint p { margin-top: 12px; font-size: 14px; }

.rc-main-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px;
}
.rc-main-title {
  font-size: 16px; font-weight: 700; color: var(--text-title, #111827);
  display: flex; align-items: center; gap: 8px;
}
.rc-main-actions { display: flex; gap: 8px; }

.rc-tabs { margin-bottom: 16px; }

/* Form Grid */
.rc-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.rc-card {
  background: var(--bg-card, #fff); border-radius: var(--radius-card, 12px);
  border: 1px solid var(--border, #E5E7EB);
  overflow: hidden;
  transition: box-shadow var(--duration-normal, 220ms) ease;
}
.rc-card:hover { box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04)); }
.rc-card-wide { grid-column: 1 / -1; }
.rc-card-title {
  padding: 12px 16px; font-size: 13px; font-weight: 600; color: var(--text-body, #6B7280);
  background: var(--gray-50, #F8F9FA); border-bottom: 1px solid var(--border-light, #F3F4F6);
  display: flex; align-items: center; justify-content: space-between;
}
.rc-card-body { padding: 16px; }
.rc-help-text {
  margin-bottom: 12px;
  color: var(--text-muted, #9CA3AF);
  font-size: 12px;
  line-height: 1.6;
}

.rc-field-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
.rc-field label {
  display: block; font-size: 11px; font-weight: 600; color: var(--text-body, #6B7280);
  margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.03em;
}

.rc-json-editor :deep(textarea) {
  font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px;
}
.rc-json-actions { margin-top: 10px; }

.rc-bottom-bar {
  display: flex; align-items: center; gap: 8px;
  padding-top: 16px; border-top: 1px solid var(--border, #E5E7EB);
}
.rc-spacer { flex: 1; }
</style>
