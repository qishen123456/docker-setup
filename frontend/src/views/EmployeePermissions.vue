<template>
  <div class="permission-page">
    <section class="page-head">
      <div>
        <p class="kicker">权限治理</p>
        <h1>账号与数据范围</h1>
        <p>维护员工账号、角色和组织树授权；功能权限统一到系统控制台配置。</p>
      </div>
      <div class="head-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
        <el-button v-if="isFeatureEnabled('employee_create')" type="primary" :icon="Plus" @click="openCreateUser">新增</el-button>
        <el-button v-if="isFeatureEnabled('employee_bulk_update')" :disabled="!selectedUserIds.length" @click="openBulkEdit">批量修改</el-button>
        <el-button v-if="isFeatureEnabled('employee_delete')" type="danger" plain :disabled="!selectedUserIds.length" @click="bulkDeleteUsers">删除</el-button>
      </div>
    </section>

    <section class="toolbar">
      <el-input v-model.trim="phoneKeyword" clearable placeholder="按电话号码 / 姓名 / UnionID 搜索" />
      <el-select v-model="roleFilter" placeholder="角色" clearable>
        <el-option label="普通用户" value="user" />
        <el-option label="业务管理员" value="business_admin" />
        <el-option label="管理员" value="admin" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态">
        <el-option label="全部状态" value="all" />
        <el-option label="正常" value="enabled" />
        <el-option label="停用" value="disabled" />
      </el-select>
    </section>

    <section class="user-table-card">
      <el-table
        v-loading="loading"
        :data="filteredUsers"
        row-key="id"
        size="small"
        border
        @selection-change="selectedUserIds = $event.map(item => item.id)"
      >
        <el-table-column v-if="canSeeField('employee_field_actions')" type="selection" width="38" />
        <el-table-column label="id" type="index" width="48" />
        <el-table-column v-if="canSeeField('employee_field_name')" label="姓名" min-width="92">
          <template #default="{ row }">{{ row.name || '-' }}</template>
        </el-table-column>
        <el-table-column v-if="canSeeField('employee_field_phone')" label="电话" min-width="116">
          <template #default="{ row }">{{ row.account || row.username || '-' }}</template>
        </el-table-column>
        <el-table-column v-if="canSeeField('employee_field_role')" label="角色" width="86">
          <template #default="{ row }">{{ roleLabel(row.role) }}</template>
        </el-table-column>
        <el-table-column v-if="canSeeField('employee_field_status')" label="状态" width="76" align="center">
          <template #default="{ row }">
            <el-switch
              class="status-switch"
              :model-value="row.enabled !== false"
              active-color="#E61F24"
              inactive-color="#D1D5DB"
              :disabled="!isFeatureEnabled('employee_status_update')"
              @change="toggleUserEnabled(row)"
            />
          </template>
        </el-table-column>
        <el-table-column v-if="canSeeField('employee_field_org')" label="组织" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ organizationSummary(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="canSeeField('employee_field_bookshelf')" label="飞书信息" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ feishuSummary(row) }}</template>
        </el-table-column>
        <el-table-column v-if="canSeeField('employee_field_actions')" label="操作" width="112">
          <template #default="{ row }">
            <el-button v-if="isFeatureEnabled('employee_update')" link type="primary" @click="openEditUser(row)">编辑</el-button>
            <el-button v-if="isFeatureEnabled('employee_delete')" link type="danger" @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="userDialog.visible"
      :title="userDialog.mode === 'create' ? '新增账号' : '编辑账号'"
      width="760px"
      class="compact-user-dialog"
      top="5vh"
    >
      <el-form label-position="top" class="user-form compact-user-form">
        <el-form-item label="姓名">
          <el-input v-model.trim="userForm.name" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model.trim="userForm.account" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role">
            <el-option label="普通用户" value="user" />
            <el-option label="业务管理员" value="business_admin" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="组织">
          <el-tree-select
            v-model="userForm.organization_node_ids"
            :data="organizationTreeOptions"
            multiple
            collapse-tags
            collapse-tags-tooltip
            check-strictly
            node-key="id"
            :props="{ label: 'label', value: 'id', children: 'children' }"
            placeholder="从组织树中多选节点"
          >
            <template #header>
              <div class="tree-select-panel-actions" @click.stop>
                <el-button size="small" @click="selectCurrentTreeOrganizations(userForm)">全选当前树</el-button>
                <el-button size="small" @click="completeSelectedChildren(userForm)">补齐含下级</el-button>
                <el-button size="small" @click="clearOrganizations(userForm)">全部清空</el-button>
              </div>
            </template>
          </el-tree-select>
        </el-form-item>
        <el-form-item v-if="userDialog.mode === 'create'" label="初始密码">
          <el-input v-model.trim="userForm.password" placeholder="默认 12345678" />
        </el-form-item>
        <div class="form-section-title">飞书 / OA 信息</div>
        <el-form-item label="飞书 unionid">
          <el-input v-model.trim="userForm.union_id" />
        </el-form-item>
        <el-form-item label="企业邮箱">
          <el-input v-model.trim="userForm.email" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model.trim="userForm.mobile" />
        </el-form-item>
        <el-form-item label="飞书部门">
          <el-input v-model.trim="userForm.department" />
        </el-form-item>
        <el-form-item label="职务">
          <el-input v-model.trim="userForm.position" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model.trim="userForm.job_number" />
        </el-form-item>
        <el-form-item label="OA 账号">
          <el-input v-model.trim="userForm.oa_account" />
        </el-form-item>
        <el-form-item label="直属上级">
          <el-input v-model.trim="userForm.manager" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer-actions">
          <el-button
            v-if="userDialog.mode === 'edit' && isFeatureEnabled('employee_password_reset')"
            type="warning"
            plain
            :loading="passwordResetting"
            @click="resetUserPassword"
          >
            重置密码
          </el-button>
          <span v-else></span>
          <div class="dialog-footer-main">
            <el-button @click="userDialog.visible = false">取消</el-button>
            <el-button v-if="canSaveUserDialog" type="primary" :loading="saving" @click="saveUserDialog">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="bulkDialogVisible" title="批量修改账号" width="620px">
      <el-form label-position="top">
        <el-form-item label="角色">
          <el-select v-model="bulkForm.role" clearable placeholder="不修改角色">
            <el-option label="普通用户" value="user" />
            <el-option label="业务管理员" value="business_admin" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="组织">
          <el-tree-select
            v-model="bulkForm.organization_node_ids"
            :data="organizationTreeOptions"
            multiple
            collapse-tags
            collapse-tags-tooltip
            check-strictly
            node-key="id"
            :props="{ label: 'label', value: 'id', children: 'children' }"
            placeholder="不选择则不修改组织"
          >
            <template #header>
              <div class="tree-select-panel-actions" @click.stop>
                <el-button size="small" @click="selectCurrentTreeOrganizations(bulkForm)">全选当前树</el-button>
                <el-button size="small" @click="completeSelectedChildren(bulkForm)">补齐含下级</el-button>
                <el-button size="small" @click="clearOrganizations(bulkForm)">全部清空</el-button>
              </div>
            </template>
          </el-tree-select>
        </el-form-item>
        <el-form-item label="账号状态">
          <el-radio-group v-model="bulkForm.enabledMode">
            <el-radio-button value="skip">不修改</el-radio-button>
            <el-radio-button value="enabled">启用</el-radio-button>
            <el-radio-button value="disabled">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bulkDialogVisible = false">取消</el-button>
        <el-button v-if="isFeatureEnabled('employee_bulk_update')" type="primary" :loading="saving" @click="submitBulkEdit">应用到 {{ selectedUserIds.length }} 人</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import {
  bulkUpdateRbacUsers,
  createRbacUser,
  getRbacOverview,
  resetRbacUserPassword,
  updateRbacUser,
} from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'

const loading = ref(false)
const saving = ref(false)
const passwordResetting = ref(false)
const phoneKeyword = ref('')
const roleFilter = ref('')
const statusFilter = ref('all')
const users = ref([])
const orgTrees = ref({ tree_types: [], nodes: [], trees: {} })
const selectedUserIds = ref([])
const bulkDialogVisible = ref(false)
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const employeeFieldKeys = [
  'employee_field_name',
  'employee_field_phone',
  'employee_field_role',
  'employee_field_status',
  'employee_field_org',
  'employee_field_org_code',
  'employee_field_bookshelf',
  'employee_field_actions',
]
const fieldAccess = computed(() => employeeFieldKeys.reduce((map, key) => {
  map[key] = isFeatureEnabled(key)
  return map
}, {}))
const canSeeField = (key) => Boolean(fieldAccess.value[key])

const userDialog = reactive({ visible: false, mode: 'create' })
const userForm = reactive({
  id: '',
  name: '',
  account: '',
  role: 'user',
  organization_node_ids: [],
  organization_codes: [],
  union_id: '',
  email: '',
  enterprise_email: '',
  mobile: '',
  department: '',
  position: '',
  job_number: '',
  employee_no: '',
  oa_account: '',
  manager: '',
  password: '',
})
const bulkForm = reactive({
  role: '',
  organization_node_ids: [],
  enabledMode: 'skip',
})

const clone = (value) => JSON.parse(JSON.stringify(value ?? null))
const nodeById = computed(() => {
  const map = new Map()
  ;(orgTrees.value.nodes || []).forEach(node => map.set(node.id, node))
  return map
})
const organizationTreeOptions = computed(() => (orgTrees.value.tree_types || []).map(tree => ({
  id: `tree:${tree.id}`,
  label: tree.name,
  disabled: true,
  children: mapTreeOptions((orgTrees.value.trees || {})[tree.id] || []),
})))
const filteredUsers = computed(() => users.value.filter((user) => {
  const text = `${user.account || ''} ${user.username || ''} ${user.name || ''} ${user.union_id || ''} ${user.email || ''} ${user.mobile || ''} ${user.job_number || ''} ${user.oa_account || ''}`.toLowerCase()
  const keyword = phoneKeyword.value.toLowerCase()
  const matchKeyword = !keyword || text.includes(keyword)
  const matchRole = !roleFilter.value || user.role === roleFilter.value
  const matchStatus = statusFilter.value === 'all' || (statusFilter.value === 'enabled' ? user.enabled : !user.enabled)
  return matchKeyword && matchRole && matchStatus
}))
const canSaveUserDialog = computed(() => isFeatureEnabled(
  userDialog.mode === 'create' ? 'employee_create' : 'employee_update'
))
const mapTreeOptions = (items = []) => items.map(node => ({
  id: node.id,
  label: `${node.name}（${node.code}）`,
  children: mapTreeOptions(node.children || []),
}))
const fixedRoleValues = ['admin', 'business_admin', 'user']
const roleLabel = (role) => ({ admin: '管理员', business_admin: '业务管理员', user: '普通用户', super_admin: '超级管理员' }[role] || role || '普通用户')
const uniqueList = (items = []) => Array.from(new Set((items || []).filter(Boolean)))
const expandNodeIds = (ids = [], treeTypeId = '') => {
  const selected = new Set((ids || []).filter(id => nodeById.value.has(id)))
  if (!selected.size && !treeTypeId) return []
  const result = []
  ;(orgTrees.value.nodes || []).forEach((node) => {
    if (treeTypeId && node.tree_type_id !== treeTypeId) return
    const pathIds = Array.isArray(node.path_ids) ? node.path_ids : [node.id]
    if ((selected.size && (selected.has(node.id) || pathIds.some(id => selected.has(id)))) || (!selected.size && treeTypeId)) {
      result.push(node.id)
    }
  })
  return uniqueList(result)
}
const organizationCodesFromNodeIds = (ids = []) => expandNodeIds(ids)
  .map(id => nodeById.value.get(id)?.code)
  .filter(Boolean)
const organizationDisplayNodes = (row = {}) => (row.organization_node_ids || [])
  .map(id => nodeById.value.get(id))
  .filter(Boolean)
  .concat((row.organization_node_ids || []).length ? [] : (row.organization_codes || []).map(code => ({ id: `code:${code}`, name: code, code })))
const organizationSummary = (row = {}) => {
  const nodes = organizationDisplayNodes(row)
  if (!nodes.length) return '未授权'
  const first = nodes[0]
  const label = canSeeField('employee_field_org_code') && first.code
    ? `${first.name}（${first.code}）`
    : `${first.name}`
  return nodes.length > 1 ? `${label} +${nodes.length - 1}` : label
}
const feishuSummary = (row = {}) => row.union_id || row.email || row.enterprise_email || row.department || row.position || '-'
const currentTreeTypeIdFromSelection = (target) => {
  const selectedNode = (target.organization_node_ids || [])
    .map(id => nodeById.value.get(id))
    .find(Boolean)
  if (selectedNode?.tree_type_id) return selectedNode.tree_type_id
  const treeTypes = orgTrees.value.tree_types || []
  return treeTypes.length === 1 ? treeTypes[0].id : ''
}
const selectCurrentTreeOrganizations = (target) => {
  const treeTypeId = currentTreeTypeIdFromSelection(target)
  if (!treeTypeId) {
    ElMessage.warning('请先在下方点选该组织树里的任意节点')
    return
  }
  target.organization_node_ids = expandNodeIds([], treeTypeId)
}
const completeSelectedChildren = (target) => {
  if (!(target.organization_node_ids || []).length) {
    ElMessage.warning('请先选择一个或多个组织节点')
    return
  }
  target.organization_node_ids = expandNodeIds(target.organization_node_ids)
}
const clearOrganizations = (target) => {
  target.organization_node_ids = []
}

const applyOverview = (data) => {
  users.value = clone(data.users) || []
  orgTrees.value = clone(data.organization_trees) || { tree_types: [], nodes: [], trees: {} }
}

const loadAll = async () => {
  loading.value = true
  try {
    const res = await getRbacOverview()
    applyOverview(res)
  } finally {
    loading.value = false
  }
}

const resetUserForm = (user = {}) => {
  Object.assign(userForm, {
    id: user.id || '',
    name: user.name || '',
    account: user.account || user.username || '',
    role: fixedRoleValues.includes(user.role) ? user.role : 'user',
    organization_node_ids: clone(user.organization_node_ids) || [],
    organization_codes: clone(user.organization_codes) || [],
    union_id: user.union_id || '',
    email: user.email || user.enterprise_email || '',
    enterprise_email: user.enterprise_email || user.email || '',
    mobile: user.mobile || user.account || '',
    department: user.department || '',
    position: user.position || '',
    job_number: user.job_number || user.employee_no || '',
    employee_no: user.employee_no || user.job_number || '',
    oa_account: user.oa_account || '',
    manager: user.manager || '',
    password: '',
  })
}

const openCreateUser = () => {
  if (!isFeatureEnabled('employee_create')) return
  resetUserForm()
  userDialog.mode = 'create'
  userDialog.visible = true
}

const openEditUser = (user) => {
  if (!isFeatureEnabled('employee_update')) return
  resetUserForm(user)
  userDialog.mode = 'edit'
  userDialog.visible = true
}

const saveUserDialog = async () => {
  if (!canSaveUserDialog.value) return
  if (!userForm.account.trim()) {
    ElMessage.warning('请填写电话')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...clone(userForm),
      enterprise_email: userForm.email,
      employee_no: userForm.job_number,
      organization_codes: organizationCodesFromNodeIds(userForm.organization_node_ids),
    }
    const res = userDialog.mode === 'create'
      ? await createRbacUser(payload)
      : await updateRbacUser(userForm.id, payload)
    users.value = clone(res.users) || users.value
    userDialog.visible = false
    ElMessage.success(userDialog.mode === 'create' ? '账号已新增' : '账号已保存')
  } finally {
    saving.value = false
  }
}

const resetUserPassword = async () => {
  if (!isFeatureEnabled('employee_password_reset')) return
  if (!userForm.id || passwordResetting.value) return
  const targetName = userForm.name || userForm.account || '该账号'
  await ElMessageBox.confirm(
    `确认将「${targetName}」的登录密码重置为默认密码 12345678？`,
    '重置密码',
    {
      type: 'warning',
      confirmButtonText: '确认重置',
      cancelButtonText: '取消',
    }
  )
  passwordResetting.value = true
  try {
    const res = await resetRbacUserPassword(userForm.id)
    users.value = clone(res.users) || users.value
    ElMessage.success(`密码已重置为 ${res.default_password || '12345678'}`)
  } finally {
    passwordResetting.value = false
  }
}

const toggleUserEnabled = async (user) => {
  if (!isFeatureEnabled('employee_status_update')) return
  const res = await updateRbacUser(user.id, { enabled: !user.enabled })
  users.value = clone(res.users) || users.value
}

const deleteUser = async (user) => {
  if (!isFeatureEnabled('employee_delete')) return
  await ElMessageBox.confirm(`确认删除账号「${user.name || user.account}」？`, '删除账号', { type: 'warning' })
  const res = await bulkUpdateRbacUsers({ user_ids: [user.id], action: 'delete' })
  users.value = clone(res.users) || users.value
  ElMessage.success('账号已删除')
}

const openBulkEdit = () => {
  if (!isFeatureEnabled('employee_bulk_update')) return
  Object.assign(bulkForm, { role: '', organization_node_ids: [], enabledMode: 'skip' })
  bulkDialogVisible.value = true
}

const submitBulkEdit = async () => {
  if (!isFeatureEnabled('employee_bulk_update')) return
  if (!selectedUserIds.value.length) return
  saving.value = true
  try {
    let latest = null
    if (bulkForm.role) {
      latest = await bulkUpdateRbacUsers({ user_ids: selectedUserIds.value, action: 'set_role', role: bulkForm.role })
    }
    if (bulkForm.organization_node_ids.length) {
      latest = await bulkUpdateRbacUsers({
        user_ids: selectedUserIds.value,
        action: 'set_organizations',
        organization_node_ids: bulkForm.organization_node_ids,
        organization_codes: organizationCodesFromNodeIds(bulkForm.organization_node_ids),
      })
    }
    if (bulkForm.enabledMode !== 'skip') {
      latest = await bulkUpdateRbacUsers({
        user_ids: selectedUserIds.value,
        action: 'set_enabled',
        enabled: bulkForm.enabledMode === 'enabled',
      })
    }
    if (latest?.users) users.value = clone(latest.users)
    bulkDialogVisible.value = false
    ElMessage.success('批量修改已完成')
  } finally {
    saving.value = false
  }
}

const bulkDeleteUsers = async () => {
  if (!isFeatureEnabled('employee_delete')) return
  if (!selectedUserIds.value.length) return
  await ElMessageBox.confirm(`确认删除 ${selectedUserIds.value.length} 个账号？`, '批量删除', { type: 'warning' })
  const res = await bulkUpdateRbacUsers({ user_ids: selectedUserIds.value, action: 'delete' })
  users.value = clone(res.users) || users.value
  selectedUserIds.value = []
  ElMessage.success('批量删除已完成')
}

onMounted(() => {
  loadFeatureFlags()
  loadAll()
})
</script>

<style scoped>
.permission-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 13px;
}

.page-head,
.toolbar,
.user-table-card {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.04);
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 20px;
}

.kicker {
  margin: 0 0 8px;
  color: #E61F24;
  font-size: 12px;
  font-weight: 800;
}

.page-head h1 {
  margin: 0;
  color: #111827;
  font-size: 24px;
}

.page-head p,
.muted {
  margin: 6px 0 0;
  color: #6B7280;
  font-size: 12px;
}

.head-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 150px 130px;
  gap: 10px;
  padding: 12px;
}

.user-table-card {
  padding: 10px;
  overflow: hidden;
}

:deep(.el-table .el-table__row) {
  height: 48px;
}

.org-codes {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.user-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.compact-user-form :deep(.el-form-item:nth-child(4)),
.compact-user-form .form-section-title {
  grid-column: 1 / -1;
}

.user-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.compact-user-form :deep(.el-form-item__label) {
  margin-bottom: 4px;
  line-height: 18px;
  font-size: 12px;
}

.compact-user-form :deep(.el-input__wrapper),
.compact-user-form :deep(.el-select__wrapper),
.compact-user-form :deep(.el-tree-select__wrapper) {
  min-height: 34px;
}

:deep(.compact-user-dialog .el-dialog) {
  margin-bottom: 0;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

:deep(.compact-user-dialog .el-dialog__header) {
  padding: 18px 20px 12px;
}

:deep(.compact-user-dialog .el-dialog__body) {
  flex: 1;
  overflow-y: auto;
  padding: 14px 20px 8px;
}

:deep(.compact-user-dialog .el-dialog__footer) {
  padding: 10px 20px 16px;
  border-top: 1px solid #F3F4F6;
}

.dialog-footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dialog-footer-main {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.form-section-title {
  margin: 2px 0 8px;
  padding-top: 10px;
  border-top: 1px solid #F3F4F6;
  font-weight: 700;
  font-size: 13px;
  color: #111827;
}

:deep(.el-table) {
  font-size: 12px;
}

:deep(.el-table .cell) {
  padding: 0 6px;
  line-height: 1.35;
}

:deep(.el-button.is-link) {
  padding: 2px 3px;
  font-size: 12px;
}

:deep(.status-switch.el-switch) {
  --el-switch-on-color: #E61F24;
  --el-switch-off-color: #D1D5DB;
  height: 24px;
}

:deep(.status-switch .el-switch__core) {
  min-width: 46px;
  height: 24px;
  border-radius: 999px;
}

:deep(.status-switch .el-switch__action) {
  width: 20px;
  height: 20px;
}

@media (max-width: 1100px) {
  .toolbar,
  .user-form {
    grid-template-columns: 1fr;
  }

  .page-head {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>

<style>
.tree-select-panel-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, auto));
  justify-content: start;
  gap: 6px;
  padding: 8px;
  border-bottom: 1px solid #F3F4F6;
  background: #F8F9FA;
}

.tree-select-panel-actions .el-button {
  margin-left: 0;
}

@media (max-width: 720px) {
  .tree-select-panel-actions {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
