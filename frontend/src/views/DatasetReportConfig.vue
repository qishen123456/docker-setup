<template>
  <div class="report-config-page" v-loading="loading">
    <div class="rc-header">
      <h2>报告配置管理</h2>
      <p class="rc-desc">为每个数据集配置独立的报告渲染规则：列映射、指标定义、信号灯规则、报告结构。</p>
    </div>

    <!-- Dataset Selector -->
    <div class="rc-selector">
      <el-select v-model="selectedDatasetId" placeholder="选择数据集" style="width: 320px" filterable @change="loadConfig">
        <el-option v-for="ds in datasets" :key="ds.id" :label="ds.name || ds.dataset_code" :value="ds.id" />
      </el-select>
      <el-button v-if="selectedDatasetId" :icon="Refresh" circle @click="loadConfig(selectedDatasetId)" />
    </div>

    <template v-if="selectedDatasetId">
      <el-tabs v-model="activeTab" type="border-card" class="rc-tabs">
        <!-- Tab 1: Visual Editor -->
        <el-tab-pane label="可视化编辑" name="visual">
          <el-form :model="configForm" label-width="120px" class="rc-form">
            <el-divider content-position="left">列映射</el-divider>
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="节点名称列"><el-input v-model="configForm.nameColumn" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="上级名称列"><el-input v-model="configForm.parentColumn" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="条线列"><el-input v-model="configForm.trackColumn" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="层级列"><el-input v-model="configForm.levelColumn" /></el-form-item></el-col>
            </el-row>

            <el-divider content-position="left">报告标题</el-divider>
            <el-form-item label="标题"><el-input v-model="configForm.reportTitle" /></el-form-item>

            <el-divider content-position="left">指标定义</el-divider>
            <div v-for="(m, i) in configForm.metrics" :key="i" class="rc-metric-row">
              <el-input v-model="m.key" placeholder="key" style="width:100px" />
              <el-input v-model="m.label" placeholder="显示名" style="width:120px" />
              <el-input v-model="m.column" placeholder="数据列名" style="width:140px" />
              <el-select v-model="m.format" style="width:100px">
                <el-option label="金额" value="amount" />
                <el-option label="百分比" value="percent" />
                <el-option label="数字" value="number" />
                <el-option label="文本" value="text" />
              </el-select>
              <el-button text type="danger" @click="configForm.metrics.splice(i, 1)">删除</el-button>
            </div>
            <el-button text type="primary" @click="configForm.metrics.push({ key: '', label: '', column: '', format: 'amount' })">+ 添加指标</el-button>

            <el-divider content-position="left">信号灯规则</el-divider>
            <div v-for="(r, i) in configForm.signalRules" :key="i" class="rc-signal-row">
              <el-select v-model="r.key" style="width:100px" placeholder="指标key">
                <el-option v-for="m in configForm.metrics" :key="m.key" :label="m.label || m.key" :value="m.key" />
              </el-select>
              <el-select v-model="r.op" style="width:70px">
                <el-option label=">=" value=">=" />
                <el-option label="<" value="<" />
                <el-option label="<=" value="<=" />
                <el-option label=">" value=">" />
                <el-option label="==" value="==" />
              </el-select>
              <el-input-number v-model="r.value" :step="5" style="width:100px" />
              <el-select v-model="r.tone" style="width:90px">
                <el-option label="🟢 绿" value="good" />
                <el-option label="🟡 黄" value="warn" />
                <el-option label="🔴 红" value="danger" />
              </el-select>
              <el-input v-model="r.label" placeholder="标签" style="width:80px" />
              <el-button text type="danger" @click="configForm.signalRules.splice(i, 1)">删除</el-button>
            </div>
            <el-button text type="primary" @click="configForm.signalRules.push({ key: '', op: '>=', value: 0, tone: 'good', label: '' })">+ 添加规则</el-button>

            <el-divider content-position="left">风险阈值</el-divider>
            <el-form-item label="风险阈值 (%)"><el-input-number v-model="configForm.riskThreshold" :min="0" :max="100" /></el-form-item>

            <el-divider content-position="left">报告章节</el-divider>
            <el-checkbox-group v-model="configForm.sections">
              <el-checkbox label="core">核心指标</el-checkbox>
              <el-checkbox label="group">分组分析</el-checkbox>
              <el-checkbox label="risk">风险预警</el-checkbox>
              <el-checkbox label="strategy">策略建议</el-checkbox>
            </el-checkbox-group>
          </el-form>
        </el-tab-pane>

        <!-- Tab 2: JSON Editor -->
        <el-tab-pane label="JSON 编辑" name="json">
          <el-input
            v-model="jsonText"
            type="textarea"
            :autosize="{ minRows: 20, maxRows: 40 }"
            class="rc-json-editor"
          />
          <el-button style="margin-top:8px" @click="parseJson">解析 JSON → 可视化</el-button>
        </el-tab-pane>
      </el-tabs>

      <!-- Actions -->
      <div class="rc-actions">
        <el-button @click="loadDefaultConfig">加载默认模板</el-button>
        <el-popconfirm title="确认删除此数据集的报告配置？" @confirm="deleteConfig">
          <template #reference><el-button type="danger" plain>删除配置</el-button></template>
        </el-popconfirm>
        <div class="rc-actions-spacer"></div>
        <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getReportConfig, upsertReportConfig, deleteReportConfig, getDefaultReportConfig } from '../api/index.js'
import axios from 'axios'

const loading = ref(false)
const saving = ref(false)
const datasets = ref([])
const selectedDatasetId = ref(null)
const activeTab = ref('visual')
const jsonText = ref('')

const configForm = ref({
  nameColumn: '', parentColumn: '', trackColumn: '', levelColumn: '',
  reportTitle: '', riskThreshold: 80,
  metrics: [], signalRules: [], sections: ['core', 'group', 'risk', 'strategy'],
  levels: [], trackValues: {}
})

const loadDatasets = async () => {
  try {
    const r = await axios.get('/api/bookshelf/datasets')
    datasets.value = r.data?.datasets || r.data || []
  } catch { datasets.value = [] }
}

const loadConfig = async (dsId) => {
  if (!dsId) return
  loading.value = true
  try {
    const r = await getReportConfig(dsId)
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
  } catch (e) { ElMessage.error('JSON 格式错误: ' + e.message) }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await upsertReportConfig(selectedDatasetId.value, configForm.value)
    ElMessage.success('配置已保存')
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const deleteConfig = async () => {
  try {
    await deleteReportConfig(selectedDatasetId.value)
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
.report-config-page { max-width: 860px; margin: 0 auto; padding: 8px 0 32px; }
.rc-header h2 { font-size: 18px; font-weight: 700; color: #1d2129; margin-bottom: 4px; }
.rc-desc { font-size: 13px; color: #86909c; margin-bottom: 16px; }
.rc-selector { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.rc-tabs { border-radius: 12px; }
.rc-form { padding: 12px 0; }
.rc-metric-row, .rc-signal-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.rc-json-editor :deep(textarea) { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; }
.rc-actions { display: flex; align-items: center; gap: 8px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #e5e6eb; }
.rc-actions-spacer { flex: 1; }
</style>
