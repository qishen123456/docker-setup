<template>
  <div class="console-page">
    <section class="console-hero">
      <div class="hero-copy">
        <span class="hero-kicker">{{ activeHero.kicker }}</span>
        <h1>系统控制台</h1>
        <p>{{ activeHero.description }}</p>
      </div>
      <div class="hero-actions">
        <el-button plain @click="toggleAdminFloat">{{ adminFloatEnabled ? '关闭悬浮入口' : '开启悬浮入口' }}</el-button>
        <template v-if="activeConsoleTab === 'permissions'">
          <el-button plain :loading="loading" @click="loadFlags">刷新</el-button>
          <el-button plain type="warning" :loading="resetting" @click="handleReset">恢复默认</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
        </template>
        <template v-else-if="activeConsoleTab === 'data'">
          <el-button plain :loading="dataPermissionLoading" @click="loadDataPermissions">刷新数据集权限</el-button>
          <el-button type="primary" :loading="dataPermissionSaving" @click="saveDataPermissionRules">保存数据集权限</el-button>
        </template>
        <template v-else>
          <el-button plain :loading="logLoading" @click="loadLogData">刷新日志</el-button>
          <el-button plain type="danger" :loading="logClearing" @click="handleClearLogs">清理查询日期内日志</el-button>
        </template>
      </div>
    </section>

    <section class="console-tabs">
      <button type="button" :class="{ active: activeConsoleTab === 'permissions' }" @click="activeConsoleTab = 'permissions'">功能权限控制</button>
      <button type="button" :class="{ active: activeConsoleTab === 'data' }" @click="activeConsoleTab = 'data'; ensureDataPermissionsLoaded()">数据集权限控制</button>
      <button type="button" :class="{ active: activeConsoleTab === 'logs' }" @click="activeConsoleTab = 'logs'; ensureLogsLoaded()">日志管理</button>
    </section>

    <section class="console-command-layout" :class="{ 'is-data-tab': activeConsoleTab === 'data' }">
      <main class="console-command-main">
    <template v-if="activeConsoleTab === 'permissions' || activeConsoleTab === 'data'">
    <section v-if="activeConsoleTab === 'permissions'" class="summary-strip">
      <div><strong>{{ navigationItems.length }}</strong><span>导航项</span></div>
      <div><strong>{{ buttonItems.length }}</strong><span>按钮项</span></div>
      <div><strong>{{ enabledButtonCount }}</strong><span>已开放按钮</span></div>
      <div><strong>{{ highRiskCount }}</strong><span>高风险项</span></div>
    </section>

    <el-skeleton v-if="loading && !featureList.length" :rows="8" animated />

    <template v-else-if="activeConsoleTab === 'data'">
      <section class="summary-strip data-summary-strip">
        <div><strong>{{ dataPermissionRows.length }}</strong><span>数据集</span></div>
        <div><strong>{{ orgScopedDatasetCount }}</strong><span>组织树控制</span></div>
        <div><strong>{{ dataPermissionTreeTypes.length }}</strong><span>组织树类型</span></div>
        <div><strong>{{ employeesWithOrgCount }}</strong><span>已授权员工</span></div>
      </section>

      <section class="data-permission-card" v-loading="dataPermissionLoading">
        <div class="data-permission-toolbar">
          <div>
            <span class="card-kicker">数据集权限控制</span>
            <h2>数据集绑定组织树与行级过滤</h2>
            <p>角色只控制功能板块；数据集按组织树和组织节点控制可见范围，员工在账号页选择组织节点后自动生效。</p>
          </div>
        </div>
        <el-table :data="dataPermissionRows" border stripe class="data-permission-table">
          <el-table-column label="数据集" min-width="190">
            <template #default="{ row }">
              <strong>{{ row.dataset_name }}</strong>
              <small>{{ row.business_domain || row.dataset_code }}</small>
            </template>
          </el-table-column>
          <el-table-column label="模式" width="108">
            <template #default="{ row }">
              <el-tag :type="dataModeTagType(row.rule.mode)" effect="plain">{{ dataModeLabel(row.rule.mode) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="组织树" min-width="220">
            <template #default="{ row }">
              <div class="dataset-scope-tags">
                <el-tag v-for="item in dataRuleTreeLabels(row.rule)" :key="item" size="small">{{ item }}</el-tag>
                <span v-if="!dataRuleTreeLabels(row.rule).length" class="muted-text">未绑定</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="授权组织" min-width="260">
            <template #default="{ row }">
              <div class="dataset-scope-tags">
                <el-tag v-for="item in dataRuleOrgLabels(row.rule).slice(0, 4)" :key="item" size="small" type="success">{{ item }}</el-tag>
                <el-tag v-if="dataRuleOrgLabels(row.rule).length > 4" size="small">+{{ dataRuleOrgLabels(row.rule).length - 4 }}</el-tag>
                <span v-if="!dataRuleOrgLabels(row.rule).length" class="muted-text">未选择</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="命中员工" width="118">
            <template #default="{ row }">
              <div class="scope-summary">
                <strong>{{ scopedEmployeeCount(row.rule) }}</strong>
                <span>人</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.rule.note || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="96" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDataRuleEditor(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <template v-else>
      <section class="permission-card">
        <header class="card-head">
          <div>
            <span class="card-kicker">导航权限</span>
            <h2>左侧导航栏</h2>
            <p>只控制左侧菜单入口是否显示，不影响页面里的按钮。</p>
          </div>
          <em>{{ navigationEnabledCount }}/{{ navigationItems.length }} 开放</em>
        </header>
        <div class="matrix-table">
          <div class="matrix-row matrix-head">
            <div class="feature-col">功能项</div>
            <label v-for="role in roles" :key="role.value" class="role-head" :class="{ checked: isRoleAllChecked(navigationItems, role.value) }">
              <input type="checkbox" :checked="isRoleAllChecked(navigationItems, role.value)" @change="toggleRoleAll(navigationItems, role.value, $event.target.checked)" />
              <span class="check-box"></span>
              <span class="role-name">{{ role.label }}</span>
              <small>全选</small>
            </label>
          </div>
          <div v-for="item in navigationItems" :key="item.key" class="matrix-row">
            <div class="feature-col">
              <strong>{{ item.label }}</strong>
              <small>{{ item.description }}</small>
            </div>
            <label
              v-for="role in roles"
              :key="role.value"
              class="permission-check"
              :class="{ checked: hasRole(item, role.value), disabled: isFixedPermission(item, role.value) }"
            >
              <input
                type="checkbox"
                :checked="hasRole(item, role.value)"
                :disabled="isFixedPermission(item, role.value)"
                @change="setRole(item, role.value, $event.target.checked)"
              />
              <span class="check-box"></span>
            </label>
          </div>
        </div>
      </section>

      <section class="module-section">
        <div class="module-title">
          <div>
            <span class="card-kicker">按钮权限</span>
            <h2>按导航模块归属</h2>
          </div>
          <em>按钮只放在自己所属页面或全局区域中。</em>
        </div>

        <section
          v-for="group in buttonGroups"
          :key="group.module"
          class="module-card"
          :class="{ 'is-open': isModuleOpen(group.module) }"
        >
          <button class="module-card-head" type="button" @click="toggleModule(group.module)">
            <div class="module-head-copy">
              <span class="module-scope">{{ group.scopeLabel }}</span>
              <strong>{{ group.label }}</strong>
              <small>{{ group.description }}</small>
            </div>
            <div class="module-head-stats">
              <span>{{ group.enabledCount }}/{{ group.items.length }} 开放</span>
              <i>{{ group.riskCount }} 个高风险</i>
            </div>
          </button>

          <div v-show="isModuleOpen(group.module)" class="matrix-table compact">
            <div class="matrix-row matrix-head">
              <div class="feature-col">功能项</div>
              <label v-for="role in roles" :key="role.value" class="role-head" :class="{ checked: isRoleAllChecked(group.items, role.value) }">
                <input type="checkbox" :checked="isRoleAllChecked(group.items, role.value)" @change="toggleRoleAll(group.items, role.value, $event.target.checked)" />
                <span class="check-box"></span>
                <span class="role-name">{{ role.label }}</span>
                <small>全选</small>
              </label>
            </div>
            <div v-for="item in group.items" :key="item.key" class="matrix-row" :class="{ 'is-risk': item.risk === 'high' }">
              <div class="feature-col">
                <strong>{{ item.label }}</strong>
                <b v-if="item.risk === 'high'">高风险</b>
                <small>{{ item.description }}</small>
              </div>
              <label
                v-for="role in roles"
                :key="role.value"
                class="permission-check"
                :class="{ checked: hasRole(item, role.value), disabled: isFixedPermission(item, role.value) }"
              >
                <input
                  type="checkbox"
                  :checked="hasRole(item, role.value)"
                  :disabled="isFixedPermission(item, role.value)"
                  @change="setRole(item, role.value, $event.target.checked)"
                />
                <span class="check-box"></span>
              </label>
            </div>
          </div>
        </section>
      </section>
    </template>
    </template>

    <template v-else>
      <section class="summary-strip log-summary-strip">
        <div><strong>{{ logStats.last_24h || 0 }}</strong><span>24小时记录</span></div>
        <div><strong>{{ logStats.errors_7d || 0 }}</strong><span>7天报错</span></div>
        <div><strong>{{ logStats.low_confidence_7d || 0 }}</strong><span>7天低置信</span></div>
        <div><strong>{{ totalLogs }}</strong><span>当前筛选</span></div>
      </section>

      <section class="log-card">
        <div class="log-toolbar">
          <el-select v-model="logFilters.category" placeholder="日志类型" clearable style="width:180px" @change="loadLogs">
            <el-option label="全部" value="" />
            <el-option label="登录访问" value="auth" />
            <el-option label="接口访问" value="access" />
            <el-option label="报错" value="error" />
            <el-option label="低置信问答" value="low_confidence" />
            <el-option label="问答记录" value="qa_all" />
            <el-option label="数据集生成" value="dataset_generation" />
          </el-select>
          <el-select v-model="logFilters.level" placeholder="级别" clearable style="width:130px" @change="loadLogs">
            <el-option label="info" value="info" />
            <el-option label="warning" value="warning" />
            <el-option label="error" value="error" />
          </el-select>
          <el-date-picker
            v-model="logFilters.date_range"
            type="daterange"
            unlink-panels
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 280px"
          />
          <el-input v-model="logFilters.keyword" clearable placeholder="搜索用户、路径、问题、SQL、答案..." @keyup.enter="loadLogs" />
          <el-button type="primary" :loading="logLoading" @click="loadLogs">查询</el-button>
          <el-button plain :loading="logExporting" @click="exportFilteredLogs">导出</el-button>
        </div>

        <el-table :data="logs" border stripe v-loading="logLoading" class="log-table">
          <el-table-column prop="created_at" label="时间" width="178">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="类型" width="112">
            <template #default="{ row }"><el-tag :type="categoryTagType(row.category)" effect="plain">{{ categoryLabel(row.category) }}</el-tag></template>
          </el-table-column>
          <el-table-column label="级别" width="92">
            <template #default="{ row }"><el-tag :type="levelTagType(row.level)" effect="plain">{{ row.level }}</el-tag></template>
          </el-table-column>
          <el-table-column label="事件名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ eventName(row) }}</template>
          </el-table-column>
          <el-table-column label="用户" width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.user_name || row.username || '-' }}</template>
          </el-table-column>
          <el-table-column label="发生了什么" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">{{ whatHappened(row) }}</template>
          </el-table-column>
          <el-table-column label="建议" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">{{ actionSuggestion(row) }}</template>
          </el-table-column>
          <el-table-column label="置信度" width="110">
            <template #default="{ row }">{{ confidenceLabel(row.confidence) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openLogDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="log-pager">
          <span>共 {{ totalLogs }} 条</span>
          <el-pagination
            layout="prev, pager, next, sizes"
            :total="totalLogs"
            :current-page="logPage"
            :page-size="logPageSize"
            :page-sizes="[50, 100, 200]"
            @current-change="onLogPageChange"
            @size-change="onLogPageSizeChange"
          />
        </div>
      </section>

      <el-drawer v-model="logDetailVisible" size="64%" title="日志详情" destroy-on-close>
        <div v-if="selectedLog" class="log-detail">
          <div class="detail-grid">
            <div><span>类型</span><strong>{{ categoryLabel(selectedLog.category) }}</strong></div>
            <div><span>级别</span><strong>{{ selectedLog.level }}</strong></div>
            <div><span>用户</span><strong>{{ selectedLog.user_name || selectedLog.username || '-' }}</strong></div>
            <div><span>耗时</span><strong>{{ selectedLog.duration_ms ? `${selectedLog.duration_ms}ms` : '-' }}</strong></div>
          </div>
          <section class="detail-section detail-highlight">
            <h3>事件名称</h3>
            <p>{{ eventName(selectedLog) }}</p>
          </section>
          <section class="detail-section">
            <h3>发生了什么</h3>
            <p>{{ whatHappened(selectedLog) }}</p>
          </section>
          <section class="detail-section">
            <h3>建议怎么处理</h3>
            <p>{{ actionSuggestion(selectedLog) }}</p>
          </section>
          <section class="detail-section">
            <h3>建议检查的代码位置</h3>
            <pre>{{ codeHint(selectedLog) }}</pre>
          </section>
          <section v-if="selectedLog.request_path" class="detail-section">
            <h3>请求路径</h3>
            <pre>{{ selectedLog.request_method || '' }} {{ selectedLog.request_path }}</pre>
          </section>
          <section v-if="selectedLog.question" class="detail-section">
            <h3>问题</h3>
            <p>{{ selectedLog.question }}</p>
          </section>
          <section v-if="selectedLog.error_message" class="detail-section">
            <h3>错误</h3>
            <pre>{{ selectedLog.error_message }}</pre>
          </section>
          <section v-if="selectedLog.sql_text" class="detail-section">
            <h3>SQL</h3>
            <pre>{{ selectedLog.sql_text }}</pre>
          </section>
          <section v-if="selectedLog.answer_text" class="detail-section">
            <h3>答案</h3>
            <pre>{{ selectedLog.answer_text }}</pre>
          </section>
          <section class="detail-section">
            <h3>思考过程</h3>
            <el-timeline v-if="thinkingRows(selectedLog).length">
              <el-timeline-item v-for="(item, index) in thinkingRows(selectedLog)" :key="index" :timestamp="item.time || ''" :type="timelineType(item.status)">
                <strong>{{ item.stage || item.agent || '执行节点' }}</strong>
                <p v-if="item.detail">{{ item.detail }}</p>
                <p v-if="item.reasoning">{{ item.reasoning }}</p>
                <p v-if="item.stream">{{ item.stream }}</p>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无思考过程记录" :image-size="60" />
          </section>
          <section class="detail-section">
            <h3>原始详情</h3>
            <pre>{{ prettyJson({ confidence: selectedLog.confidence, details: selectedLog.details }) }}</pre>
          </section>
        </div>
      </el-drawer>
    </template>
      </main>

    </section>

    <el-dialog v-model="dataRuleDialog.visible" title="编辑数据集权限" width="720px" destroy-on-close>
      <el-form v-if="dataRuleForm" label-position="top" class="data-rule-form">
        <div class="data-rule-dataset">
          <span>数据集</span>
          <strong>{{ dataRuleForm.dataset_name }}</strong>
          <small>{{ dataRuleForm.business_domain || dataRuleForm.dataset_code }}</small>
        </div>
        <el-form-item label="权限模式">
          <el-radio-group v-model="dataRuleForm.rule.mode">
            <el-radio-button label="public">公开</el-radio-button>
            <el-radio-button label="org_tree">按组织树控制</el-radio-button>
            <el-radio-button label="disabled">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="组织树类型">
          <el-select
            v-model="dataRuleForm.rule.tree_type_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            clearable
            :disabled="dataRuleForm.rule.mode !== 'org_tree'"
            placeholder="可选择多棵组织树"
            @change="onDataRuleTreeChange(dataRuleForm)"
          >
            <el-option v-for="item in dataPermissionTreeTypes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="授权组织">
          <el-tree-select
            v-model="dataRuleForm.rule.organization_node_ids"
            :data="datasetOrganizationOptions(dataRuleForm.rule.tree_type_ids)"
            multiple
            collapse-tags
            collapse-tags-tooltip
            check-strictly
            filterable
            node-key="id"
            :props="{ label: 'label', value: 'id', children: 'children' }"
            :disabled="dataRuleForm.rule.mode !== 'org_tree' || !(dataRuleForm.rule.tree_type_ids || []).length"
            placeholder="选择具体组织节点"
          >
            <template #header>
              <div class="tree-select-panel-actions compact-actions" @click.stop>
                <el-button size="small" @click="selectDataRuleCurrentTree(dataRuleForm)">全选当前树</el-button>
                <el-button size="small" @click="completeDataRuleChildren(dataRuleForm)">补齐含下级</el-button>
                <el-button size="small" @click="clearDataRuleOrganizations(dataRuleForm)">全部清空</el-button>
              </div>
            </template>
          </el-tree-select>
        </el-form-item>
        <el-form-item label="兜底指定员工">
          <el-select
            v-model="dataRuleForm.rule.allowed_employee_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            :disabled="dataRuleForm.rule.mode !== 'org_tree'"
            placeholder="可选，额外放行员工"
          >
            <el-option
              v-for="item in enabledDataPermissionEmployees"
              :key="item.id"
              :label="employeeOptionLabel(item)"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dataRuleForm.rule.note" placeholder="权限说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dataRuleDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="applyDataRuleEditor">应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  clearSystemLogs,
  getAdminFeatureFlags,
  getDataPermissions,
  getSystemLogDetail,
  getSystemLogs,
  getSystemLogStats,
  resetAdminFeatureFlags,
  saveDataPermissions,
  saveAdminFeatureFlags,
} from '../api/index.js'

const roles = [
  { value: 'super_admin', label: '超管' },
  { value: 'admin', label: '管理员' },
  { value: 'user', label: '普通用户' }
]
const roleOrder = roles.map((item) => item.value)
const FEATURE_FLAGS_UPDATED_EVENT = 'smartask-feature-flags-updated'
const ADMIN_CONSOLE_FLOAT_HIDDEN_KEY = 'smartask_admin_console_float_hidden'
const ADMIN_CONSOLE_FLOAT_TOGGLE_EVENT = 'smartask-admin-console-float-toggle'

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const features = ref({})
const openModules = ref(['organization_tree_management', 'employee_permissions', 'runtime_migration'])
const activeConsoleTab = ref('permissions')
const dataPermissionLoading = ref(false)
const dataPermissionSaving = ref(false)
const dataPermissionRows = ref([])
const dataRuleDialog = ref({ visible: false })
const dataRuleForm = ref(null)
const dataPermissionEmployees = ref([])
const dataPermissionOrganizationTrees = ref({ tree_types: [], nodes: [], trees: {} })
const logs = ref([])
const logStats = ref({})
const totalLogs = ref(0)
const logLoading = ref(false)
const logClearing = ref(false)
const logExporting = ref(false)
const logPage = ref(1)
const logPageSize = ref(100)
const logDetailVisible = ref(false)
const selectedLog = ref(null)
const adminFloatEnabled = ref(false)
const allFetchedLogs = ref([])
const logFilters = ref({
  category: '',
  level: '',
  keyword: '',
  date_range: [],
})

const activeHero = computed(() => {
  if (activeConsoleTab.value === 'logs') {
    return {
      kicker: '日志审计',
      description: '集中查看登录访问、接口报错和低置信度问答，保留问题、思考过程、SQL 与答案。'
    }
  }
  if (activeConsoleTab.value === 'data') {
    return {
      kicker: '数据集权限控制',
      description: '按数据集绑定组织树和组织节点，员工在账号页选择组织节点后自动获得对应数据范围。'
    }
  }
  return {
    kicker: '功能权限控制',
    description: '按角色勾选左侧导航和页面按钮权限；数据范围不在这里配置。'
  }
})

const featureList = computed(() =>
  Object.entries(features.value || {})
    .map(([key, value]) => {
      value.key = key
      value.label = value.label || key
      value.description = value.description || ''
      value.module = value.module || (value.kind === 'navigation' ? 'navigation' : 'other')
      value.module_label = value.module_label || value.category || '其他'
      value.kind = value.kind || 'button'
      value.order = Number(value.order || 999)
      value.roles = Array.isArray(value.roles) ? value.roles : []
      value.enabled = value.roles.length > 0 && Boolean(value.enabled)
      value.risk = value.risk || ''
      return value
    })
    .sort((a, b) => a.order - b.order)
)

const navigationItems = computed(() => featureList.value.filter((item) => item.kind === 'navigation'))
const buttonItems = computed(() => featureList.value.filter((item) => item.kind !== 'navigation'))
const navigationEnabledCount = computed(() => navigationItems.value.filter((item) => item.enabled).length)
const enabledButtonCount = computed(() => buttonItems.value.filter((item) => item.enabled).length)
const highRiskCount = computed(() => buttonItems.value.filter((item) => item.risk === 'high').length)
const orgScopedDatasetCount = computed(() => dataPermissionRows.value.filter((item) => item.rule?.mode === 'org_tree').length)
const enabledDataPermissionEmployees = computed(() => dataPermissionEmployees.value.filter((item) => item.enabled !== false))
const dataPermissionTreeTypes = computed(() => dataPermissionOrganizationTrees.value?.tree_types || [])
const employeesWithOrgCount = computed(() => dataPermissionEmployees.value.filter((item) => (item.organization_node_ids || []).length > 0).length)
const dataPermissionNodeById = computed(() => new Map((dataPermissionOrganizationTrees.value?.nodes || []).map((node) => [node.id, node])))
const moduleInfoMap = computed(() => {
  const map = new Map()
  for (const item of navigationItems.value) {
    map.set(item.key, {
      order: item.order,
      label: item.label,
      description: item.description,
      scopeLabel: '左侧导航模块'
    })
  }
  map.set('global_shell', {
    order: 5,
    label: '全局操作',
    description: '右上角账号菜单、左侧历史区等不属于单个页面的公共按钮。',
    scopeLabel: '全局区域'
  })
  return map
})

const buttonGroups = computed(() => {
  const grouped = new Map()
  for (const item of buttonItems.value) {
    if (!grouped.has(item.module)) {
      grouped.set(item.module, { module: item.module, items: [] })
    }
    grouped.get(item.module).items.push(item)
  }
  return Array.from(grouped.values())
    .map((group) => {
      const info = moduleInfoMap.value.get(group.module) || {}
      const firstItem = group.items[0] || {}
      return {
        ...group,
        label: info.label || firstItem.module_label || '其他模块',
        description: info.description || `归属于 ${firstItem.module_label || '其他模块'} 的页面按钮。`,
        scopeLabel: info.scopeLabel || '页面模块',
        order: Number(info.order || Math.min(...group.items.map((item) => item.order || 999))),
        items: group.items.sort((a, b) => a.order - b.order),
        enabledCount: group.items.filter((item) => item.enabled).length,
        riskCount: group.items.filter((item) => item.risk === 'high').length
      }
    })
    .sort((a, b) => a.order - b.order)
})

const isModuleOpen = (module) => openModules.value.includes(module)
const toggleModule = (module) => {
  openModules.value = isModuleOpen(module)
    ? openModules.value.filter((item) => item !== module)
    : [...openModules.value, module]
}

const hasRole = (item, role) => Array.isArray(item.roles) && item.roles.includes(role)
const isFixedPermission = (item, role) => item.key === 'admin_console' && role === 'super_admin'

const setRole = (item, role, checked) => {
  if (isFixedPermission(item, role)) return
  const next = new Set(item.roles || [])
  if (checked) next.add(role)
  else next.delete(role)
  item.roles = roleOrder.filter((value) => next.has(value))
  item.enabled = item.roles.length > 0
}

const editableItems = (items, role) => items.filter((item) => !isFixedPermission(item, role))

const isRoleAllChecked = (items, role) => {
  const list = editableItems(items, role)
  return list.length > 0 && list.every((item) => hasRole(item, role))
}

const toggleRoleAll = (items, role, checked) => {
  editableItems(items, role).forEach((item) => setRole(item, role, checked))
}

const loadFlags = async () => {
  loading.value = true
  try {
    const res = await getAdminFeatureFlags()
    features.value = structuredClone(res?.data?.features || {})
  } catch (error) {
    showRequestError(error, '控制台配置加载失败')
  } finally {
    loading.value = false
  }
}

const buildPayload = () => {
  const payload = {}
  for (const item of featureList.value) {
    payload[item.key] = {
      enabled: item.roles.length > 0,
      roles: item.roles,
      experimental: item.experimental
    }
  }
  return payload
}

const handleSave = async () => {
  if (!featureList.value.length) {
    ElMessage.warning('暂无可保存的权限配置，请先刷新控制台')
    return
  }
  saving.value = true
  try {
    const res = await saveAdminFeatureFlags(buildPayload())
    features.value = structuredClone(res?.data?.features || {})
    window.dispatchEvent(new CustomEvent(FEATURE_FLAGS_UPDATED_EVENT, { detail: { source: 'admin-console', at: Date.now() } }))
    ElMessage.success('控制台配置已保存')
  } catch (error) {
    showRequestError(error, '控制台配置保存失败')
  } finally {
    saving.value = false
  }
}

const handleReset = async () => {
  await ElMessageBox.confirm('将恢复系统默认权限矩阵，当前自定义勾选会被覆盖。确认继续吗？', '恢复默认', {
    type: 'warning',
    confirmButtonText: '恢复默认',
    cancelButtonText: '取消'
  })
  resetting.value = true
  try {
    const res = await resetAdminFeatureFlags()
    features.value = structuredClone(res?.data?.features || {})
    window.dispatchEvent(new CustomEvent(FEATURE_FLAGS_UPDATED_EVENT, { detail: { source: 'admin-console-reset', at: Date.now() } }))
    ElMessage.success('已恢复默认权限矩阵')
  } catch (error) {
    showRequestError(error, '恢复默认权限失败')
  } finally {
    resetting.value = false
  }
}

const showRequestError = (error, fallback) => {
  const message = error?.response?.data?.error || error?.message || fallback
  ElMessage.error(message)
}

const clonePlain = (value) => JSON.parse(JSON.stringify(value ?? null))
const uniqueList = (items = []) => Array.from(new Set((items || []).filter(Boolean)))
const mapDatasetTreeOptions = (items = []) => items.map((node) => ({
  id: node.id,
  label: `${node.name}（${node.code}）`,
  children: mapDatasetTreeOptions(node.children || []),
}))
const selectedTreeTypeIds = (rule = {}) => Array.isArray(rule.tree_type_ids)
  ? rule.tree_type_ids
  : (rule.tree_type_id ? [rule.tree_type_id] : [])
const treeTypeName = (id) => dataPermissionTreeTypes.value.find(item => item.id === id)?.name || id
const dataRuleTreeLabels = (rule = {}) => selectedTreeTypeIds(rule).map(treeTypeName).filter(Boolean)
const dataRuleOrgLabels = (rule = {}) => (rule.organization_node_ids || [])
  .map(id => dataPermissionNodeById.value.get(id))
  .filter(Boolean)
  .map(node => `${node.name}（${node.code}）`)
const dataModeLabel = (mode) => ({ public: '公开', org_tree: '组织树', disabled: '停用', restricted: '组织树' }[mode] || '公开')
const dataModeTagType = (mode) => ({ public: 'success', org_tree: 'primary', disabled: 'danger', restricted: 'primary' }[mode] || 'info')
const datasetOrganizationOptions = (treeTypeIds = []) => {
  const ids = Array.isArray(treeTypeIds) ? treeTypeIds : (treeTypeIds ? [treeTypeIds] : [])
  if (!ids.length) return []
  return ids.map((treeTypeId) => {
    const tree = dataPermissionTreeTypes.value.find(item => item.id === treeTypeId)
    return {
      id: `tree:${treeTypeId}`,
      label: tree?.name || treeTypeId,
      disabled: true,
      children: mapDatasetTreeOptions((dataPermissionOrganizationTrees.value?.trees || {})[treeTypeId] || []),
    }
  })
}
const expandDataPermissionNodeIds = (ids = [], treeTypeId = '') => {
  const selected = new Set((ids || []).filter(id => dataPermissionNodeById.value.has(id)))
  if (!selected.size && !treeTypeId) return []
  const result = []
  ;(dataPermissionOrganizationTrees.value?.nodes || []).forEach((node) => {
    if (treeTypeId && node.tree_type_id !== treeTypeId) return
    const pathIds = Array.isArray(node.path_ids) ? node.path_ids : [node.id]
    if ((selected.size && (selected.has(node.id) || pathIds.some(id => selected.has(id)))) || (!selected.size && treeTypeId)) {
      result.push(node.id)
    }
  })
  return uniqueList(result)
}
const organizationCodesFromDataNodeIds = (ids = [], treeTypeId = '') => expandDataPermissionNodeIds(ids, treeTypeId)
  .map(id => dataPermissionNodeById.value.get(id)?.code)
  .filter(Boolean)
const onDataRuleTreeChange = (row) => {
  row.rule.tree_type_id = selectedTreeTypeIds(row.rule)[0] || ''
  row.rule.organization_node_ids = []
  row.rule.organization_codes = []
}
const currentTreeTypeIdFromDataRule = (rule = {}) => {
  const selectedNode = (rule.organization_node_ids || [])
    .map(id => dataPermissionNodeById.value.get(id))
    .find(Boolean)
  if (selectedNode?.tree_type_id) return selectedNode.tree_type_id
  const ids = selectedTreeTypeIds(rule)
  return ids.length === 1 ? ids[0] : ''
}
const selectDataRuleCurrentTree = (row) => {
  const treeTypeId = currentTreeTypeIdFromDataRule(row.rule)
  if (row.rule.mode !== 'org_tree' || !treeTypeId) {
    ElMessage.warning('请先选择一个组织树类型，或在下方点选该组织树里的任意节点')
    return
  }
  const otherTreeNodeIds = (row.rule.organization_node_ids || []).filter((id) => dataPermissionNodeById.value.get(id)?.tree_type_id !== treeTypeId)
  row.rule.organization_node_ids = uniqueList([...otherTreeNodeIds, ...expandDataPermissionNodeIds([], treeTypeId)])
  row.rule.organization_codes = organizationCodesFromDataNodeIds(row.rule.organization_node_ids)
}
const completeDataRuleChildren = (row) => {
  if (!(row.rule.organization_node_ids || []).length) {
    ElMessage.warning('请先选择一个或多个组织节点')
    return
  }
  row.rule.organization_node_ids = expandDataPermissionNodeIds(row.rule.organization_node_ids)
  row.rule.organization_codes = organizationCodesFromDataNodeIds(row.rule.organization_node_ids)
}
const clearDataRuleOrganizations = (row) => {
  row.rule.organization_node_ids = []
  row.rule.organization_codes = []
}

const normalizeRule = (dataset, rule = {}) => ({
  dataset_id: Number(dataset.id || rule.dataset_id || 0),
  mode: ['public', 'org_tree', 'disabled', 'restricted'].includes(rule.mode) ? (rule.mode === 'restricted' ? 'org_tree' : rule.mode) : 'public',
  tree_type_id: (Array.isArray(rule.tree_type_ids) ? rule.tree_type_ids[0] : rule.tree_type_id) || '',
  tree_type_ids: Array.isArray(rule.tree_type_ids)
    ? rule.tree_type_ids
    : (rule.tree_type_id ? [rule.tree_type_id] : []),
  organization_node_ids: Array.isArray(rule.organization_node_ids) ? rule.organization_node_ids : [],
  organization_codes: Array.isArray(rule.organization_codes) ? rule.organization_codes : [],
  allowed_roles: Array.isArray(rule.allowed_roles) ? rule.allowed_roles : [],
  allowed_departments: Array.isArray(rule.allowed_departments) ? rule.allowed_departments : [],
  allowed_positions: Array.isArray(rule.allowed_positions) ? rule.allowed_positions : [],
  allowed_employee_ids: Array.isArray(rule.allowed_employee_ids) ? rule.allowed_employee_ids : [],
  allowed_union_ids: Array.isArray(rule.allowed_union_ids) ? rule.allowed_union_ids : [],
  scope: {
    organization_field: rule.scope?.organization_field || '组织编码',
    organization_values: Array.isArray(rule.scope?.organization_values) ? rule.scope.organization_values : [],
    company_field: rule.scope?.company_field || '',
    company_values: Array.isArray(rule.scope?.company_values) ? rule.scope.company_values : [],
    row_filter_note: rule.scope?.row_filter_note || '',
  },
  note: rule.note || '',
})

const openDataRuleEditor = (row) => {
  dataRuleForm.value = clonePlain({
    ...row,
    rule: normalizeRule(row, row.rule),
  })
  dataRuleDialog.value.visible = true
}

const applyDataRuleEditor = () => {
  if (!dataRuleForm.value) return
  const edited = clonePlain(dataRuleForm.value)
  edited.rule = normalizeRule(edited, edited.rule)
  edited.rule.tree_type_id = selectedTreeTypeIds(edited.rule)[0] || ''
  edited.rule.organization_codes = organizationCodesFromDataNodeIds(edited.rule.organization_node_ids)
  edited.rule.scope.organization_field = '组织编码'
  dataPermissionRows.value = dataPermissionRows.value.map((row) => (
    row.id === edited.id ? { ...row, rule: edited.rule } : row
  ))
  dataRuleDialog.value.visible = false
  ElMessage.success('已应用，记得点击顶部保存数据集权限')
}

const loadDataPermissions = async () => {
  dataPermissionLoading.value = true
  try {
    const res = await getDataPermissions()
    const datasets = Array.isArray(res?.datasets) ? res.datasets : []
    const rules = res?.rules || {}
    dataPermissionEmployees.value = Array.isArray(res?.employees) ? res.employees : []
    dataPermissionOrganizationTrees.value = res?.organization_trees || { tree_types: [], nodes: [], trees: {} }
    dataPermissionRows.value = datasets.map((dataset) => ({
      ...dataset,
      rule: normalizeRule(dataset, rules[String(dataset.id)] || {}),
    }))
  } catch (error) {
    showRequestError(error, '数据集权限加载失败')
  } finally {
    dataPermissionLoading.value = false
  }
}

const ensureDataPermissionsLoaded = () => {
  if (!dataPermissionRows.value.length) loadDataPermissions()
}

const saveDataPermissionRules = async () => {
  dataPermissionSaving.value = true
  try {
    const rules = {}
    dataPermissionRows.value.forEach((row) => {
      const rule = normalizeRule(row, row.rule)
      rule.tree_type_id = selectedTreeTypeIds(rule)[0] || ''
      rule.organization_codes = organizationCodesFromDataNodeIds(rule.organization_node_ids)
      rule.scope.organization_field = '组织编码'
      rules[String(row.id)] = rule
    })
    const res = await saveDataPermissions(rules)
    const savedRules = res?.rules || rules
    dataPermissionRows.value = dataPermissionRows.value.map((row) => ({
      ...row,
      rule: normalizeRule(row, savedRules[String(row.id)] || row.rule),
    }))
    ElMessage.success('数据集权限已保存')
  } catch (error) {
    showRequestError(error, '数据集权限保存失败')
  } finally {
    dataPermissionSaving.value = false
  }
}

const employeeOptionLabel = (item) => {
  const parts = [item.name || item.account || item.id]
  if (item.department) parts.push(item.department)
  if (item.position) parts.push(item.position)
  return parts.join(' / ')
}

const scopedEmployeeCount = (rule) => {
  if (!selectedTreeTypeIds(rule).length || !(rule?.organization_node_ids || []).length) return 0
  const ruleNodeIds = new Set(expandDataPermissionNodeIds(rule.organization_node_ids))
  return enabledDataPermissionEmployees.value.filter((employee) => (
    expandDataPermissionNodeIds(employee.organization_node_ids || []).some(nodeId => ruleNodeIds.has(nodeId))
  )).length
}

const syncAdminFloatState = () => {
  adminFloatEnabled.value = sessionStorage.getItem(ADMIN_CONSOLE_FLOAT_HIDDEN_KEY) === '0'
}

const toggleAdminFloat = () => {
  const nextVisible = !adminFloatEnabled.value
  adminFloatEnabled.value = nextVisible
  sessionStorage.setItem(ADMIN_CONSOLE_FLOAT_HIDDEN_KEY, nextVisible ? '0' : '1')
  window.dispatchEvent(new CustomEvent(ADMIN_CONSOLE_FLOAT_TOGGLE_EVENT, { detail: { visible: nextVisible } }))
  ElMessage.success(nextVisible ? '已开启悬浮控制台入口' : '已关闭悬浮控制台入口')
}

const normalizeLogDate = (value) => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

const filterLogsByDateRange = (items) => {
  const range = Array.isArray(logFilters.value.date_range) ? logFilters.value.date_range : []
  if (range.length !== 2 || !range[0] || !range[1]) return items
  const start = normalizeLogDate(`${range[0]}T00:00:00`)
  const end = normalizeLogDate(`${range[1]}T23:59:59`)
  if (!start || !end) return items
  return items.filter((item) => {
    const current = normalizeLogDate(item?.created_at)
    return current && current >= start && current <= end
  })
}

const refreshLogTable = () => {
  const filtered = filterLogsByDateRange(allFetchedLogs.value)
  totalLogs.value = filtered.length
  const start = (logPage.value - 1) * logPageSize.value
  logs.value = filtered.slice(start, start + logPageSize.value)
}

const loadLogStats = async () => {
  try {
    const res = await getSystemLogStats()
    logStats.value = res?.stats || {}
  } catch (error) {
    showRequestError(error, '日志统计加载失败')
  }
}

const loadLogs = async () => {
  logLoading.value = true
  logPage.value = 1
  try {
    const res = await getSystemLogs({
      category: logFilters.value.category || undefined,
      level: logFilters.value.level || undefined,
      keyword: logFilters.value.keyword || undefined,
      limit: 5000,
      offset: 0,
    })
    allFetchedLogs.value = Array.isArray(res?.logs) ? res.logs : []
    refreshLogTable()
  } catch (error) {
    showRequestError(error, '系统日志加载失败')
  } finally {
    logLoading.value = false
  }
}

const exportFilteredLogs = async () => {
  logExporting.value = true
  try {
    const filtered = filterLogsByDateRange(allFetchedLogs.value)
    if (!filtered.length) {
      ElMessage.warning('当前筛选结果为空，暂无可导出的日志')
      return
    }
    const header = ['时间', '类型', '级别', '事件名称', '用户', '发生了什么', '建议', '请求路径', '问题', 'SQL', '答案', '错误']
    const escapeCell = (value) => `"${String(value ?? '').replace(/"/g, '""').replace(/\r?\n/g, ' ')}"`
    const rows = filtered.map((row) => ([
      formatTime(row.created_at),
      categoryLabel(row.category),
      row.level || '',
      eventName(row),
      row.user_name || row.username || '',
      whatHappened(row),
      actionSuggestion(row),
      row.request_path || '',
      row.question || '',
      row.sql_text || '',
      row.answer_text || '',
      row.error_message || '',
    ].map(escapeCell).join(',')))
    const csv = ['\ufeff' + header.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `system-logs-${Date.now()}.csv`
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success(`已导出 ${filtered.length} 条日志`)
  } finally {
    logExporting.value = false
  }
}

const loadLogData = async () => {
  logLoading.value = true
  try {
    await Promise.all([loadLogStats(), loadLogs()])
  } finally {
    logLoading.value = false
  }
}

const ensureLogsLoaded = () => {
  if (!logs.value.length) loadLogData()
}

const onLogPageChange = (page) => {
  logPage.value = page
  refreshLogTable()
}

const onLogPageSizeChange = (size) => {
  logPageSize.value = size
  logPage.value = 1
  refreshLogTable()
}

const openLogDetail = async (row) => {
  selectedLog.value = row
  logDetailVisible.value = true
  try {
    const res = await getSystemLogDetail(row.id)
    selectedLog.value = res?.log || row
  } catch (error) {
    showRequestError(error, '日志详情加载失败')
  }
}

const handleClearLogs = async () => {
  const range = Array.isArray(logFilters.value.date_range) ? logFilters.value.date_range : []
  const beforeDate = range[1] || ''
  if (!beforeDate) {
    ElMessage.warning('请先选择查询日期范围')
    return
  }
  const categoryText = logFilters.value.category ? `，日志类型为「${categoryLabel(logFilters.value.category)}」` : ''
  await ElMessageBox.confirm(`将清理 ${beforeDate} 及之前${categoryText}的系统日志。确认继续吗？`, '清理系统日志', {
    type: 'warning',
    confirmButtonText: '清理',
    cancelButtonText: '取消',
  })
  logClearing.value = true
  try {
    const res = await clearSystemLogs({
      category: logFilters.value.category,
      before_date: beforeDate,
    })
    ElMessage.success(`已清理 ${res?.deleted || 0} 条日志`)
    await loadLogData()
  } catch (error) {
    showRequestError(error, '清理系统日志失败')
  } finally {
    logClearing.value = false
  }
}

const categoryLabel = (category) => ({
  auth: '登录访问',
  access: '接口访问',
  error: '报错',
  low_confidence: '低置信',
  qa: '问答',
  dataset_generation: '数据集生成',
}[category] || category || '-')

const categoryTagType = (category) => ({
  auth: 'success',
  access: 'info',
  error: 'danger',
  low_confidence: 'warning',
  qa: 'primary',
  dataset_generation: 'warning',
}[category] || 'info')

const levelTagType = (level) => ({
  info: 'info',
  warning: 'warning',
  error: 'danger',
}[level] || 'info')

const eventTypeLabel = (eventType) => ({
  api_access: '接口访问',
  http_error: '接口报错',
  password_login_success: '密码登录成功',
  password_login_failed: '密码登录失败',
  admin_login_success: '管理员登录成功',
  admin_login_failed: '管理员登录失败',
  feishu_login_success: '飞书登录成功',
  feishu_login_failed: '飞书登录失败',
  logout: '退出登录',
  smart_chat_completed: '问答完成',
  smart_chat_low_confidence: '低置信问答',
  smart_chat_failed: '问答报错',
  dataset_generate_from_prompt_started: '开始提示词生成数据集',
  dataset_generate_from_prompt_completed: '提示词生成数据集完成',
  dataset_generate_from_prompt_failed: 'AI 生成数据集失败',
  dataset_generate_from_prompt_error: '提示词生成接口异常',
}[eventType] || eventType || '-')

const eventDetails = (row) => (row && typeof row.details === 'object' && row.details ? row.details : {})

const eventName = (row) => eventDetails(row).event_name || row?.title || eventTypeLabel(row?.event_type)

const whatHappened = (row) => (
  eventDetails(row).what_happened
  || row?.question
  || row?.error_message
  || row?.request_path
  || row?.title
  || '-'
)

const actionSuggestion = (row) => {
  const details = eventDetails(row)
  if (details.suggested_action) return details.suggested_action
  if (row?.category === 'low_confidence') return '建议把这条问题补进回归题集或 Golden SQL，并检查字段字典、同义词和 Agent2 SQL 生成提示词。'
  if (row?.category === 'error') return '建议先看详细错误和请求路径，再到对应 controller 搜索接口路径定位代码。'
  if (row?.category === 'auth') return '建议核对登录账号、角色和权限矩阵配置。'
  return '无需处理；这是正常访问记录。'
}

const codeHint = (row) => {
  const details = eventDetails(row)
  if (details.code_hint) return details.code_hint
  if (row?.request_path?.includes('/smart-chat')) return 'backend/controllers/smart_chat.py；backend/four_agent_ask.py；frontend/src/views/SmartAsk.vue。'
  if (row?.request_path?.includes('/bookshelves')) return 'backend/controllers/bookshelf.py；frontend/src/views/DatasetManagement.vue。'
  if (row?.request_path?.includes('/admin/system-logs')) return 'backend/controllers/system_logs.py；backend/system_log_store.py；frontend/src/views/AdminConsole.vue。'
  return 'backend/controllers/*.py 中搜索请求路径；frontend/src/api/index.js 中搜索对应 API 方法。'
}

const confidenceLabel = (confidence) => {
  const route = confidence?.route
  const result = confidence?.result
  const parts = []
  if (route?.score !== undefined) parts.push(`路由${route.score}`)
  if (result?.score !== undefined) parts.push(`结果${result.score}`)
  return parts.join(' / ') || '-'
}

const formatTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}

const thinkingRows = (item) => Array.isArray(item?.thinking_process) ? item.thinking_process : []
const timelineType = (status) => status === 'error' ? 'danger' : status === 'warning' ? 'warning' : status === 'success' ? 'success' : 'primary'
const prettyJson = (value) => {
  try { return JSON.stringify(value || {}, null, 2) } catch { return String(value || '') }
}

onMounted(() => {
  syncAdminFloatState()
  loadFlags()
})
</script>

<style scoped>
.console-page {
  min-height: 100%;
  padding: 24px 28px 36px;
  color: #1f2937;
  background:
    radial-gradient(circle at 8% 6%, rgba(24, 144, 255, 0.12), transparent 28%),
    linear-gradient(135deg, #f6f9ff 0%, #f4f7fb 54%, #edf4ff 100%);
}

.console-page > * {
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
}

.console-hero,
.summary-strip,
.permission-card,
.module-card {
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
}

.console-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px;
}

.hero-kicker,
.card-kicker {
  display: inline-flex;
  margin-bottom: 5px;
  color: #1677ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
}

.console-hero h1,
.card-head h2,
.module-title h2 {
  margin: 0;
  color: #0f172a;
  font-size: 22px;
  line-height: 1.25;
}

.console-hero h1 {
  font-size: 30px;
  letter-spacing: -0.02em;
}

.console-hero p,
.card-head p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
}

.hero-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.summary-strip div {
  padding: 13px 16px;
  border: 1px solid rgba(203, 213, 225, 0.76);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.summary-strip strong {
  display: block;
  color: #0f766e;
  font-size: 21px;
  line-height: 1.1;
}

.summary-strip span {
  color: #64748b;
  font-size: 12px;
}

.console-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
  padding: 8px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
}

.console-tabs button {
  min-width: 0;
  height: 42px;
  border: 0;
  border-radius: 10px;
  color: #475569;
  background: transparent;
  font-weight: 800;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.console-tabs button.active {
  color: #ffffff;
  background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
  box-shadow: 0 10px 20px rgba(15, 118, 110, 0.22);
}

.console-command-layout {
  display: block;
  margin-top: 16px;
}

.console-command-main {
  min-width: 0;
}

.console-command-main > .summary-strip:first-child,
.console-command-main > .log-summary-strip:first-child {
  margin-top: 0;
}

.permission-card {
  margin-top: 16px;
  overflow: hidden;
}

.card-head,
.module-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid #edf2f7;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.card-head em,
.module-title em,
.module-head-stats i,
.module-head-stats span {
  color: #64748b;
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
}

.matrix-table {
  padding: 10px 14px 14px;
}

.matrix-row {
  display: grid;
  grid-template-columns: minmax(340px, 1fr) 112px 112px 112px;
  align-items: center;
  min-height: 48px;
  border-bottom: 1px solid #eef2f7;
}

.matrix-row:last-child {
  border-bottom: 0;
}

.matrix-head {
  min-height: 40px;
  margin-bottom: 4px;
  border: 0;
  border-radius: 10px;
  background: #f4f7fb;
  color: #475569;
}

.feature-col {
  min-width: 0;
  padding: 8px 12px;
}

.feature-col strong {
  display: inline-flex;
  align-items: center;
  color: #0f172a;
  font-size: 14px;
  font-weight: 800;
}

.feature-col small {
  display: block;
  margin-top: 3px;
  color: #718096;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feature-col b {
  margin-left: 8px;
  padding: 2px 7px;
  border-radius: 999px;
  color: #dc2626;
  background: #fee2e2;
  font-size: 11px;
}

.role-head,
.permission-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.role-head {
  gap: 5px;
  color: #334155;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  position: relative;
}

.role-name {
  min-width: 34px;
  text-align: left;
}

.role-head small {
  padding: 1px 6px;
  border-radius: 999px;
  color: #64748b;
  background: #eef2f7;
  font-weight: 700;
}

.role-head.checked small {
  color: #0f766e;
  background: #dff7f1;
}

.role-head input,
.permission-check input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.check-box {
  width: 17px;
  height: 17px;
  border: 1px solid #cbd5e1;
  border-radius: 5px;
  background: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.role-head.checked .check-box,
.permission-check.checked .check-box {
  border-color: #0f766e;
  background: #0f766e;
  box-shadow: inset 0 0 0 3px #0f766e;
}

.role-head.checked .check-box::after,
.permission-check.checked .check-box::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 8px;
  height: 4px;
  border-left: 2px solid #fff;
  border-bottom: 2px solid #fff;
  transform: translate(-50%, -70%) rotate(-45deg);
}

.permission-check {
  position: relative;
  min-height: 34px;
  cursor: pointer;
}

.permission-check .check-box,
.role-head .check-box {
  position: relative;
  flex-shrink: 0;
}

.permission-check.disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.is-risk {
  background: linear-gradient(90deg, rgba(254, 242, 242, 0.78), transparent 52%);
}

.module-section {
  margin-top: 18px;
}

.module-title {
  padding: 0 2px 12px;
  border-bottom: 0;
  background: transparent;
}

.module-card {
  margin-bottom: 12px;
  overflow: hidden;
}

.module-card-head {
  width: 100%;
  min-height: 64px;
  padding: 0 18px;
  border: 0;
  border-bottom: 1px solid transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  color: inherit;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  user-select: none;
  text-align: left;
}

.module-card-head::before {
  content: '';
  width: 8px;
  height: 8px;
  border-right: 2px solid #64748b;
  border-bottom: 2px solid #64748b;
  flex-shrink: 0;
  transform: rotate(-45deg);
  transition: transform 0.18s ease;
}

.module-card.is-open .module-card-head::before {
  transform: rotate(45deg);
}

.module-head-copy {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 4px 10px;
}

.module-card-head strong {
  color: #0f172a;
  font-size: 15px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.module-head-copy small {
  grid-column: 1 / -1;
  color: #7b8798;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.module-scope {
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  color: #165dff;
  background: #edf4ff;
  font-size: 11px;
  font-weight: 800;
}

.module-head-stats {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.module-card.is-open .module-card-head {
  border-bottom: 1px solid #edf2f7;
}

.compact {
  padding-top: 6px;
}

.log-summary-strip strong {
  color: #7c3aed;
}

.data-summary-strip strong {
  color: #0f766e;
}

.data-permission-card {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.data-permission-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 2px 2px 14px;
}

.data-permission-toolbar h2 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.data-permission-toolbar p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
}

.data-permission-table small,
.data-permission-table strong {
  display: block;
}

.data-permission-table small {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
}

.data-permission-table :deep(.el-table__cell) {
  vertical-align: top;
}

.data-permission-table :deep(.el-select),
.data-permission-table :deep(.el-input) {
  width: 100%;
}

.scope-fields {
  display: grid;
  grid-template-columns: minmax(88px, 0.8fr) minmax(130px, 1.2fr);
  gap: 8px;
}

.dataset-org-scope {
  display: grid;
  gap: 8px;
}

.log-card {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.log-toolbar {
  display: grid;
  grid-template-columns: auto auto auto minmax(240px, 1fr) auto auto;
  gap: 10px;
  margin-bottom: 12px;
}

.log-table {
  width: 100%;
}

.log-pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 12px;
  color: #64748b;
  font-size: 12px;
}

.log-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.detail-grid div {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.detail-grid span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.detail-grid strong {
  display: block;
  margin-top: 4px;
  color: #0f172a;
  font-size: 14px;
}

.detail-section {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}

.detail-highlight {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.detail-section h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 15px;
}

.detail-section p {
  margin: 0 0 6px;
  color: #334155;
  line-height: 1.6;
}

.detail-section pre {
  max-height: 360px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  border-radius: 8px;
  color: #1e293b;
  background: #f8fafc;
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.console-page {
  background: #f5f7fb;
}

.console-page > * {
  max-width: 1280px;
}

.console-hero {
  padding: 18px 22px;
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(246, 250, 255, 0.96)),
    radial-gradient(circle at 0 0, rgba(22, 93, 255, 0.1), transparent 34%);
}

.console-hero h1 {
  font-size: 26px;
}

.summary-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-strip div {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
}

.summary-strip strong {
  display: inline;
  font-size: 19px;
}

.permission-card,
.module-card {
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.matrix-table {
  padding: 8px 14px 12px;
}

.matrix-row {
  grid-template-columns: minmax(360px, 1fr) 136px 136px 136px;
  min-height: 50px;
}

.matrix-head {
  position: sticky;
  top: 0;
  z-index: 2;
  margin-bottom: 2px;
  background: #eef4ff;
}

.feature-col {
  padding: 9px 12px;
}

.feature-col strong {
  font-size: 13px;
  line-height: 1.35;
}

.feature-col small {
  margin-top: 2px;
  font-size: 11px;
  color: #7b8798;
  white-space: normal;
  line-height: 1.45;
}

.role-head {
  width: fit-content;
  min-width: 96px;
  height: 28px;
  margin: 0 auto;
  padding: 0 8px;
  border: 1px solid #d8e3f5;
  border-radius: 999px;
  background: #fff;
}

.role-head.checked {
  border-color: rgba(15, 118, 110, 0.24);
  background: #eefaf7;
}

.role-head small {
  padding: 0;
  background: transparent;
  color: #7b8798;
}

.permission-check {
  width: 100%;
}

.module-card-head {
  min-height: 58px;
  background: #fff;
}

.module-head-stats span {
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
}

.module-head-stats i {
  min-width: 74px;
  text-align: right;
}

.scope-summary {
  display: flex;
  align-items: baseline;
  gap: 8px;
  color: #64748b;
}

.scope-summary strong {
  color: #0f766e;
  font-size: 18px;
}

@media (max-width: 900px) {
  .console-page {
    padding: 14px;
  }

  .console-hero {
    flex-direction: column;
    align-items: stretch;
  }

  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .log-toolbar {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .matrix-row {
    grid-template-columns: minmax(220px, 1fr) 86px 86px 86px;
  }
}
</style>

<style>
.tree-select-panel-actions {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) repeat(4, auto);
  gap: 6px;
  padding: 8px;
  border-bottom: 1px solid #eef2f7;
  background: #f8fafc;
}

.tree-select-panel-actions.compact-actions {
  grid-template-columns: repeat(3, auto);
  justify-content: start;
}

.tree-select-panel-actions .el-button {
  margin-left: 0;
}

@media (max-width: 720px) {
  .tree-select-panel-actions,
  .tree-select-panel-actions.compact-actions {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
