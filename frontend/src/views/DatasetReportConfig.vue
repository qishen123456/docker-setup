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
            <el-button size="small" @click="loadDefaultConfig">加载默认模板</el-button>
            <el-button size="small" type="primary" :loading="saving" @click="saveConfig">保存</el-button>
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
                  <el-button text type="primary" size="small" @click="addMetric">+ 添加</el-button>
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
                        <el-button text type="danger" size="small" @click="configForm.metrics.splice($index, 1)">×</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>

              <!-- Signal Rules Card -->
              <div class="rc-card rc-card-wide">
                <div class="rc-card-title">
                  信号灯规则
                  <el-button text type="primary" size="small" @click="addSignalRule">+ 添加</el-button>
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
                        <el-button text type="danger" size="small" @click="configForm.signalRules.splice($index, 1)">×</el-button>
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
              <el-button size="small" @click="parseJson">应用 JSON → 可视化</el-button>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- Bottom bar -->
        <div class="rc-bottom-bar">
          <el-popconfirm v-if="hasConfig" title="确认删除此数据集的报告配置？" @confirm="deleteConfig">
            <template #reference><el-button type="danger" plain size="small">删除配置</el-button></template>
          </el-popconfirm>
          <div class="rc-spacer"></div>
          <el-button size="small" @click="loadDefaultConfig">重置为默认</el-button>
          <el-button type="primary" size="small" :loading="saving" @click="saveConfig">保存配置</el-button>
        </div>
      </main>

      <!-- Empty State -->
      <main class="rc-main rc-main-empty" v-else>
        <div class="rc-empty-hint">
          <el-icon :size="40" color="#c9cdd4"><Grid /></el-icon>
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
import axios from 'axios'

const loading = ref(false)
const saving = ref(false)
const datasets = ref([])
const selectedDatasetId = ref(null)
const activeTab = ref('visual')
const jsonText = ref('')
const hasConfig = ref(false)

const configForm = ref({
  nameColumn: '', parentColumn: '', trackColumn: '', levelColumn: '',
  reportTitle: '', riskThreshold: 80,
  metrics: [], signalRules: [], sections: ['core', 'group', 'risk', 'strategy'],
  levels: [], trackValues: {}
})

const selectedDatasetName = computed(() => {
  const ds = datasets.value.find(d => d.id === selectedDatasetId.value)
  return ds ? (ds.dataset_name || ds.dataset_code || `数据集#${ds.id}`) : ''
})

const addMetric = () => configForm.value.metrics.push({ key: '', label: '', column: '', format: 'amount' })
const addSignalRule = () => configForm.value.signalRules.push({ key: '', op: '>=', value: 0, tone: 'good', label: '' })

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
    })
    jsonText.value = JSON.stringify(configForm.value, null, 2)
  } finally { loading.value = false }
}

const loadDefaultConfig = async () => {
  try {
    const r = await getDefaultReportConfig()
    const cfg = r.config || {}
    Object.assign(configForm.value, cfg)
    jsonText.value = JSON.stringify(configForm.value, null, 2)
    ElMessage.success('已加载默认模板')
  } catch { ElMessage.error('加载默认模板失败') }
}

const parseJson = () => {
  try {
    const parsed = JSON.parse(jsonText.value)
    Object.assign(configForm.value, parsed)
    ElMessage.success('JSON 已解析')
    activeTab.value = 'visual'
  } catch (e) { ElMessage.error('JSON 格式错误: ' + e.message) }
}

const saveConfig = async () => {
  saving.value = true
  try {
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

onMounted(loadDatasets)
</script>

<style scoped>
.rc-page { height: 100%; display: flex; flex-direction: column; }

.rc-layout {
  flex: 1; display: flex; min-height: 0;
  background: #f7f8fa;
  border-radius: 12px; overflow: hidden;
  border: 1px solid rgba(229,230,235,0.6);
}

/* LEFT SIDEBAR */
.rc-sidebar {
  width: 240px; min-width: 240px;
  background: #fff;
  border-right: 1px solid rgba(229,230,235,0.6);
  display: flex; flex-direction: column;
}
.rc-sidebar-title {
  padding: 14px 16px 10px;
  font-size: 13px; font-weight: 700; color: #1d2129;
  border-bottom: 1px solid rgba(229,230,235,0.5);
}
.rc-sidebar-scroll {
  flex: 1; overflow-y: auto; padding: 8px;
}
.rc-ds-item {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-radius: 10px;
  cursor: pointer; transition: all 0.15s ease;
  margin-bottom: 2px;
}
.rc-ds-item:hover { background: rgba(22,93,255,0.04); }
.rc-ds-item.is-active {
  background: rgba(22,93,255,0.08);
  box-shadow: inset 3px 0 0 #165dff;
}
.rc-ds-icon { font-size: 16px; color: #86909c; flex-shrink: 0; }
.rc-ds-meta { flex: 1; min-width: 0; }
.rc-ds-name { font-size: 13px; font-weight: 500; color: #1d2129; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc-ds-code { font-size: 10px; color: #86909c; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rc-ds-badge {
  font-size: 10px; font-weight: 600; color: #00b42a; background: #e8ffea;
  padding: 1px 6px; border-radius: 999px; flex-shrink: 0;
}
.rc-ds-empty { text-align: center; padding: 24px 0; color: #86909c; font-size: 13px; }

/* RIGHT MAIN */
.rc-main {
  flex: 1; overflow-y: auto; padding: 20px 28px;
}
.rc-main-empty {
  display: flex; align-items: center; justify-content: center;
}
.rc-empty-hint { text-align: center; color: #86909c; }
.rc-empty-hint p { margin-top: 12px; font-size: 14px; }

.rc-main-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.rc-main-title {
  font-size: 16px; font-weight: 700; color: #1d2129;
  display: flex; align-items: center; gap: 8px;
}
.rc-main-actions { display: flex; gap: 8px; }

.rc-tabs { margin-bottom: 12px; }

/* Form Grid */
.rc-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.rc-card {
  background: #fff; border-radius: 12px;
  border: 1px solid rgba(229,230,235,0.6);
  overflow: hidden;
}
.rc-card-wide { grid-column: 1 / -1; }
.rc-card-title {
  padding: 10px 16px; font-size: 13px; font-weight: 700; color: #1d2129;
  background: #fafbfc; border-bottom: 1px solid rgba(229,230,235,0.5);
  display: flex; align-items: center; justify-content: space-between;
}
.rc-card-body { padding: 14px 16px; }

.rc-field-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
}
.rc-field label {
  display: block; font-size: 11px; font-weight: 600; color: #4e5969;
  margin-bottom: 4px;
}

.rc-json-editor :deep(textarea) {
  font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px;
}
.rc-json-actions { margin-top: 8px; }

.rc-bottom-bar {
  display: flex; align-items: center; gap: 8px;
  padding-top: 12px; border-top: 1px solid rgba(229,230,235,0.5);
}
.rc-spacer { flex: 1; }
</style>
