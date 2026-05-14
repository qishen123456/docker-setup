<template>
  <div class="rbac-page">
    <header class="rbac-head">
      <div>
        <div class="rbac-kicker">权限治理</div>
        <h2>角色权限与用户分组</h2>
        <p>统一维护角色、功能权限、数据集资源权限、用户分组和停用控制。</p>
      </div>
      <div class="rbac-head-actions">
        <button type="button" class="rbac-ghost" :disabled="loading" @click="loadAll">刷新</button>
        <button type="button" class="rbac-primary" @click="createRole">新建角色</button>
        <button type="button" class="rbac-primary muted" @click="createGroup">新建分组</button>
      </div>
    </header>

    <section class="rbac-metrics">
      <div><span>角色</span><strong>{{ roles.length }}</strong></div>
      <div><span>用户</span><strong>{{ users.length }}</strong></div>
      <div><span>分组</span><strong>{{ groups.length }}</strong></div>
      <div><span>停用用户</span><strong>{{ disabledCount }}</strong></div>
    </section>

    <main class="rbac-layout" v-loading="loading">
      <aside class="rbac-left">
        <div class="rbac-search">
          <input v-model.trim="keyword" placeholder="搜索角色、用户、分组、数据集" />
          <select v-model="userStatusFilter">
            <option value="all">全部状态</option>
            <option value="enabled">正常</option>
            <option value="disabled">停用</option>
          </select>
        </div>

        <div class="rbac-list-section">
          <div class="rbac-section-title">角色列表</div>
          <button
            v-for="role in filteredRoles"
            :key="role.id"
            type="button"
            class="rbac-list-item"
            :class="{ active: activeType === 'role' && activeId === role.id }"
            @click="selectItem('role', role.id)"
          >
            <span>
              <b>{{ role.name }}</b>
              <small>{{ role.builtin ? '内置角色' : role.code }}</small>
            </span>
            <em>{{ role.function_permissions?.length || 0 }} 功能</em>
          </button>
        </div>

        <div class="rbac-list-section">
          <div class="rbac-section-title with-action">
            <span>用户列表</span>
            <button type="button" @click="bulkDialogVisible = true">批量</button>
          </div>
          <button
            v-for="user in filteredUsers"
            :key="user.id"
            type="button"
            class="rbac-list-item"
            :class="{ active: activeType === 'user' && activeId === user.id, disabled: !user.enabled }"
            @click="selectItem('user', user.id)"
          >
            <label class="rbac-check" @click.stop>
              <input type="checkbox" :checked="selectedUserIds.includes(user.id)" @change="toggleSelectedUser(user.id, $event.target.checked)" />
            </label>
            <span>
              <b>{{ user.name || user.account }}</b>
              <small>{{ user.account || '-' }} · {{ user.enabled ? '正常' : '停用' }}</small>
            </span>
            <em>{{ user.role === 'admin' ? '管理员' : '普通用户' }}</em>
          </button>
        </div>

        <div class="rbac-list-section">
          <div class="rbac-section-title">分组列表</div>
          <button
            v-for="group in filteredGroups"
            :key="group.id"
            type="button"
            class="rbac-list-item"
            :class="{ active: activeType === 'group' && activeId === group.id }"
            @click="selectItem('group', group.id)"
          >
            <span>
              <b>{{ group.name }}</b>
              <small>{{ groupPath(group) }}</small>
            </span>
            <em>{{ group.user_ids?.length || 0 }} 人</em>
          </button>
        </div>

        <div class="rbac-list-section">
          <div class="rbac-section-title">资源视角</div>
          <button
            v-for="dataset in filteredDatasets"
            :key="dataset.id"
            type="button"
            class="rbac-list-item"
            :class="{ active: activeType === 'resource' && Number(activeId) === Number(dataset.id) }"
            @click="selectItem('resource', dataset.id)"
          >
            <span>
              <b>{{ dataset.dataset_name }}</b>
              <small>{{ dataset.business_domain || dataset.dataset_code }}</small>
            </span>
          </button>
        </div>
      </aside>

      <section class="rbac-detail">
        <template v-if="activeType === 'role' && activeRole">
          <div class="detail-head">
            <div>
              <span class="detail-badge">{{ activeRole.builtin ? '内置角色' : '自定义角色' }}</span>
              <h3>{{ activeRole.name }}</h3>
              <p>{{ activeRole.description || '角色是功能权限和资源权限的集合容器。' }}</p>
            </div>
            <div class="detail-actions">
              <button v-if="!activeRole.locked" class="rbac-danger" @click="removeRole(activeRole)">删除角色</button>
              <button class="rbac-primary" :disabled="activeRole.id === 'super_admin'" @click="saveRole(activeRole)">保存角色</button>
            </div>
          </div>

          <div class="detail-grid">
            <section class="detail-card">
              <h4>基础信息</h4>
              <label>角色名称<input v-model.trim="activeRole.name" :disabled="activeRole.builtin" /></label>
              <label>角色编码<input v-model.trim="activeRole.code" :disabled="activeRole.builtin" /></label>
              <label>说明<textarea v-model.trim="activeRole.description" rows="3" /></label>
            </section>

            <section class="detail-card wide">
              <div class="detail-card-title">
                <h4>权限配置 · 功能操作权限</h4>
                <span v-if="activeRole.id === 'super_admin'" class="readonly-tip">超管角色受保护，默认拥有全部权限，不可编辑</span>
              </div>
              <div class="feature-groups">
                <div v-for="group in featureGroups" :key="group.name" class="feature-group">
                  <div class="feature-group-title">{{ group.name }}</div>
                  <label v-for="feature in group.items" :key="feature.key" class="permission-pill">
                    <input
                      type="checkbox"
                      :disabled="activeRole.id === 'super_admin'"
                      :checked="activeRole.function_permissions?.includes(feature.key)"
                      @change="toggleRoleFunction(activeRole, feature.key, $event.target.checked)"
                    />
                    <span>{{ feature.label }}</span>
                  </label>
                </div>
              </div>
            </section>

            <section class="detail-card wide">
              <div class="detail-card-title">
                <h4>权限配置 · 数据集资源权限</h4>
                <span v-if="activeRole.id === 'super_admin'" class="readonly-tip">超管默认拥有所有数据集管理权限</span>
              </div>
              <div class="resource-table">
                <div class="resource-row head"><span>数据集</span><span>权限</span></div>
                <div v-for="dataset in datasets" :key="dataset.id" class="resource-row">
                  <span>{{ dataset.dataset_name }}</span>
                  <select
                    :disabled="activeRole.id === 'super_admin'"
                    :value="getRoleResourceLevel(activeRole, dataset.id)"
                    @change="setRoleResourceLevel(activeRole, dataset.id, $event.target.value)"
                  >
                    <option v-for="level in resourceLevels" :key="level.value" :value="level.value">{{ level.label }}</option>
                  </select>
                </div>
              </div>
            </section>

            <section class="detail-card wide">
              <h4>授权对象</h4>
              <div class="auth-object-grid">
                <div><b>{{ roleDirectUsers(activeRole.id).length }}</b><span>直接用户</span></div>
                <div><b>{{ roleGroups(activeRole.id).length }}</b><span>继承分组</span></div>
              </div>
              <div class="mini-tags">
                <span v-for="item in roleDirectUsers(activeRole.id)" :key="item.id">{{ item.name || item.account }}</span>
                <span v-for="item in roleGroups(activeRole.id)" :key="item.id">分组：{{ item.name }}</span>
              </div>
            </section>
          </div>
        </template>

        <template v-else-if="activeType === 'group' && activeGroup">
          <div class="detail-head">
            <div>
              <span class="detail-badge">用户分组</span>
              <h3>{{ activeGroup.name }}</h3>
              <p>分组角色会被组内用户自动继承；子分组用户同时继承上级分组角色。</p>
            </div>
            <div class="detail-actions">
              <button class="rbac-danger" @click="removeGroup(activeGroup)">删除分组</button>
              <button class="rbac-primary" @click="saveGroup(activeGroup)">保存分组</button>
            </div>
          </div>
          <div class="detail-grid">
            <section class="detail-card">
              <h4>基础信息</h4>
              <label>分组名称<input v-model.trim="activeGroup.name" /></label>
              <label>上级分组
                <select v-model="activeGroup.parent_id">
                  <option value="">无上级</option>
                  <option v-for="group in groups.filter(item => item.id !== activeGroup.id)" :key="group.id" :value="group.id">{{ group.name }}</option>
                </select>
              </label>
              <label>说明<textarea v-model.trim="activeGroup.description" rows="3" /></label>
            </section>
            <section class="detail-card">
              <h4>分配角色</h4>
              <label v-for="role in assignableRoles" :key="role.id" class="permission-pill block">
                <input type="checkbox" :checked="activeGroup.role_ids?.includes(role.id)" @change="toggleGroupRole(activeGroup, role.id, $event.target.checked)" />
                <span>{{ role.name }}</span>
              </label>
            </section>
            <section class="detail-card wide">
              <h4>批量添加/移除用户</h4>
              <div class="user-pick-grid">
                <label v-for="user in users" :key="user.id" class="permission-pill">
                  <input type="checkbox" :checked="activeGroup.user_ids?.includes(user.id)" @change="toggleGroupUser(activeGroup, user.id, $event.target.checked)" />
                  <span>{{ user.name || user.account }}</span>
                </label>
              </div>
            </section>
          </div>
        </template>

        <template v-else-if="activeType === 'user' && activeUser">
          <div class="detail-head">
            <div>
              <span class="detail-badge" :class="{ danger: !activeUser.enabled }">{{ activeUser.enabled ? '正常用户' : '停用用户' }}</span>
              <h3>{{ activeUser.name || activeUser.account }}</h3>
              <p>最终权限 = 直接角色权限 + 所属分组继承角色权限；资源冲突按最高权限优先。</p>
            </div>
            <div class="detail-actions">
              <button class="rbac-ghost" :disabled="activeUser.role === 'super_admin'" @click="toggleUserEnabled(activeUser)">
                {{ activeUser.enabled ? '停用用户' : '启用用户' }}
              </button>
              <button class="rbac-primary" :disabled="activeUser.role === 'super_admin'" @click="saveUser(activeUser)">保存用户</button>
            </div>
          </div>
          <div class="detail-grid">
            <section class="detail-card">
              <h4>基础信息</h4>
              <label>姓名<input v-model.trim="activeUser.name" /></label>
              <label>账号<input v-model.trim="activeUser.account" /></label>
              <label>固定角色
                <select v-model="activeUser.role">
                  <option value="admin">管理员</option>
                  <option value="user">普通用户</option>
                </select>
              </label>
            </section>
            <section class="detail-card">
              <h4>直接分配角色</h4>
              <label v-for="role in assignableRoles" :key="role.id" class="permission-pill block">
                <input type="checkbox" :checked="activeUser.role_ids?.includes(role.id)" @change="toggleUserRole(activeUser, role.id, $event.target.checked)" />
                <span>{{ role.name }}</span>
              </label>
            </section>
            <section class="detail-card wide">
              <h4>用户视角 · 权限来源</h4>
              <div class="source-list">
                <div v-for="source in selectedUserPermission?.role_sources || []" :key="`${source.role_id}-${source.source_type}-${source.source_id}`">
                  <b>{{ source.role_name }}</b>
                  <span>{{ source.source_type === 'direct' ? '直接分配' : source.source_type === 'group' ? `分组继承：${source.source_name}` : source.source_name }}</span>
                </div>
              </div>
              <div class="permission-columns">
                <div>
                  <h5>可访问功能</h5>
                  <span v-for="item in selectedUserPermission?.function_permissions || []" :key="item.key" class="mini-chip">{{ item.label }}</span>
                </div>
                <div>
                  <h5>可访问数据集</h5>
                  <span v-for="item in selectedUserPermission?.resource_permissions || []" :key="item.dataset_id" class="mini-chip">
                    {{ item.dataset_name }} · {{ item.level_label }}
                  </span>
                </div>
              </div>
            </section>
          </div>
        </template>

        <template v-else-if="activeType === 'resource' && activeDataset">
          <div class="detail-head">
            <div>
              <span class="detail-badge">数据集/资源视角</span>
              <h3>{{ activeDataset.dataset_name }}</h3>
              <p>查看该数据集下哪些用户、分组、角色拥有访问权限。</p>
            </div>
          </div>
          <div class="detail-grid">
            <section class="detail-card wide">
              <h4>拥有权限的角色</h4>
              <div class="source-list">
                <div v-for="item in activeResourceAccess?.roles || []" :key="item.role.id"><b>{{ item.role.name }}</b><span>{{ item.level_label }}</span></div>
              </div>
            </section>
            <section class="detail-card wide">
              <h4>拥有权限的分组</h4>
              <div class="source-list">
                <div v-for="item in activeResourceAccess?.groups || []" :key="item.group.id"><b>{{ item.group.name }}</b><span>{{ item.level_label }} · {{ item.roles.map(r => r.name).join(' / ') }}</span></div>
              </div>
            </section>
            <section class="detail-card wide">
              <h4>拥有权限的用户</h4>
              <div class="source-list">
                <div v-for="item in activeResourceAccess?.users || []" :key="item.user.id"><b>{{ item.user.name || item.user.account }}</b><span>{{ item.level_label }}</span></div>
              </div>
            </section>
          </div>
        </template>

        <div v-else class="rbac-empty">请选择左侧角色、用户、分组或数据集查看详情。</div>
      </section>
    </main>

    <el-dialog v-model="bulkDialogVisible" title="批量授权" width="520px">
      <div class="bulk-panel">
        <p>已选择 {{ selectedUserIds.length }} 个用户。</p>
        <label>选择角色
          <select v-model="bulkRoleId">
            <option value="">请选择</option>
            <option v-for="role in assignableRoles" :key="role.id" :value="role.id">{{ role.name }}</option>
          </select>
        </label>
        <div class="bulk-actions">
          <button class="rbac-primary" @click="bulkAssign('add_roles')">批量分配</button>
          <button class="rbac-ghost" @click="bulkAssign('remove_roles')">批量取消</button>
          <button class="rbac-ghost" @click="bulkSetEnabled(true)">批量启用</button>
          <button class="rbac-danger" @click="bulkSetEnabled(false)">批量停用</button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  bulkUpdateRbacUsers,
  createRbacGroup,
  createRbacRole,
  deleteRbacGroup,
  deleteRbacRole,
  getRbacDatasetAccess,
  getRbacOverview,
  updateRbacGroup,
  updateRbacRole,
  updateRbacUser,
} from '../api/index.js'

const loading = ref(false)
const roles = ref([])
const users = ref([])
const groups = ref([])
const features = ref([])
const datasets = ref([])
const resourceLevels = ref([])
const userPermissions = ref([])
const keyword = ref('')
const userStatusFilter = ref('all')
const activeType = ref('role')
const activeId = ref('')
const selectedUserIds = ref([])
const bulkDialogVisible = ref(false)
const bulkRoleId = ref('')
const activeResourceAccess = ref(null)

const clone = (value) => JSON.parse(JSON.stringify(value || null))
const norm = (value) => String(value || '').toLowerCase()
const match = (value) => !keyword.value || norm(value).includes(norm(keyword.value))

const disabledCount = computed(() => users.value.filter(item => !item.enabled).length)
const assignableRoles = computed(() => roles.value.filter(item => item.id !== 'super_admin'))
const activeRole = computed(() => roles.value.find(item => item.id === activeId.value))
const activeUser = computed(() => users.value.find(item => item.id === activeId.value))
const activeGroup = computed(() => groups.value.find(item => item.id === activeId.value))
const activeDataset = computed(() => datasets.value.find(item => Number(item.id) === Number(activeId.value)))
const selectedUserPermission = computed(() => userPermissions.value.find(item => item.user?.id === activeId.value))

const filteredRoles = computed(() => roles.value.filter(item => match(`${item.name} ${item.code} ${item.description}`)))
const filteredGroups = computed(() => groups.value.filter(item => match(`${item.name} ${item.description}`)))
const filteredDatasets = computed(() => datasets.value.filter(item => match(`${item.dataset_name} ${item.business_domain} ${item.dataset_code}`)))
const filteredUsers = computed(() => users.value
  .filter(item => userStatusFilter.value === 'all' || (userStatusFilter.value === 'enabled' ? item.enabled : !item.enabled))
  .filter(item => match(`${item.name} ${item.account} ${item.department} ${item.position}`)))

const featureGroups = computed(() => {
  const map = new Map()
  features.value.forEach((item) => {
    const key = item.module_label || item.category || '其他'
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(item)
  })
  return Array.from(map.entries()).map(([name, items]) => ({ name, items }))
})

const loadAll = async () => {
  loading.value = true
  try {
    const data = await getRbacOverview()
    roles.value = clone(data.roles) || []
    users.value = clone(data.users) || []
    groups.value = clone(data.groups) || []
    features.value = clone(data.features) || []
    datasets.value = clone(data.datasets) || []
    resourceLevels.value = clone(data.resource_levels) || []
    userPermissions.value = clone(data.user_permissions) || []
    if (!activeId.value && roles.value.length) {
      activeType.value = 'role'
      activeId.value = roles.value[0].id
    }
  } finally {
    loading.value = false
  }
}

const selectItem = async (type, id) => {
  activeType.value = type
  activeId.value = String(id)
  activeResourceAccess.value = null
  if (type === 'resource') {
    try {
      const res = await getRbacDatasetAccess(id)
      activeResourceAccess.value = res.data
    } catch (error) {
      ElMessage.error(error?.response?.data?.error || error.message || '资源权限视图加载失败')
    }
  }
}

const createRole = async () => {
  const role = { name: '新角色', code: `custom_${Date.now()}`, function_permissions: [], resource_permissions: {} }
  const res = await createRbacRole(role)
  roles.value = clone(res.roles) || roles.value
  activeType.value = 'role'
  activeId.value = res.role.id
  ElMessage.success('角色已创建')
}

const saveRole = async (role) => {
  const res = await updateRbacRole(role.id, role)
  roles.value = clone(res.roles) || roles.value
  ElMessage.success('角色已保存')
  await loadAll()
}

const removeRole = async (role) => {
  await ElMessageBox.confirm(`确认删除角色「${role.name}」？`, '删除角色', { type: 'warning' })
  const res = await deleteRbacRole(role.id)
  roles.value = clone(res.roles) || []
  activeId.value = roles.value[0]?.id || ''
  ElMessage.success('角色已删除')
}

const createGroup = async () => {
  const res = await createRbacGroup({ name: '新用户分组', role_ids: [], user_ids: [] })
  groups.value = clone(res.groups) || groups.value
  activeType.value = 'group'
  activeId.value = res.group.id
  ElMessage.success('分组已创建')
}

const saveGroup = async (group) => {
  const res = await updateRbacGroup(group.id, group)
  groups.value = clone(res.groups) || groups.value
  ElMessage.success('分组已保存')
  await loadAll()
}

const removeGroup = async (group) => {
  await ElMessageBox.confirm(`确认删除分组「${group.name}」？`, '删除分组', { type: 'warning' })
  const res = await deleteRbacGroup(group.id)
  groups.value = clone(res.groups) || []
  activeId.value = groups.value[0]?.id || ''
  ElMessage.success('分组已删除')
}

const saveUser = async (user) => {
  const res = await updateRbacUser(user.id, user)
  users.value = clone(res.users) || users.value
  ElMessage.success('用户授权已保存')
  await loadAll()
}

const toggleUserEnabled = async (user) => {
  await updateRbacUser(user.id, { enabled: !user.enabled })
  ElMessage.success(user.enabled ? '用户已停用' : '用户已启用')
  await loadAll()
}

const toggleSet = (target, key, checked) => {
  const next = new Set(target || [])
  if (checked) next.add(key)
  else next.delete(key)
  return Array.from(next)
}

const toggleRoleFunction = (role, key, checked) => {
  role.function_permissions = toggleSet(role.function_permissions, key, checked)
}

const getRoleResourceLevel = (role, datasetId) => role.resource_permissions?.[String(datasetId)] || 'none'
const setRoleResourceLevel = (role, datasetId, level) => {
  role.resource_permissions = role.resource_permissions || {}
  if (level === 'none') delete role.resource_permissions[String(datasetId)]
  else role.resource_permissions[String(datasetId)] = level
}

const toggleGroupRole = (group, roleId, checked) => {
  group.role_ids = toggleSet(group.role_ids, roleId, checked)
}
const toggleGroupUser = (group, userId, checked) => {
  group.user_ids = toggleSet(group.user_ids, userId, checked)
}
const toggleUserRole = (user, roleId, checked) => {
  user.role_ids = toggleSet(user.role_ids, roleId, checked)
}
const toggleSelectedUser = (userId, checked) => {
  selectedUserIds.value = toggleSet(selectedUserIds.value, userId, checked)
}

const roleDirectUsers = (roleId) => users.value.filter(item => item.role === roleId || (item.role_ids || []).includes(roleId))
const roleGroups = (roleId) => groups.value.filter(item => (item.role_ids || []).includes(roleId))

const groupPath = (group) => {
  const parent = groups.value.find(item => item.id === group.parent_id)
  return parent ? `${parent.name} / ${group.name}` : '一级分组'
}

const bulkAssign = async (action) => {
  if (!selectedUserIds.value.length || !bulkRoleId.value) return ElMessage.warning('请选择用户和角色')
  await bulkUpdateRbacUsers({ user_ids: selectedUserIds.value, action, role_ids: [bulkRoleId.value] })
  bulkDialogVisible.value = false
  ElMessage.success(action === 'remove_roles' ? '已批量取消授权' : '已批量分配角色')
  await loadAll()
}

const bulkSetEnabled = async (enabled) => {
  if (!selectedUserIds.value.length) return ElMessage.warning('请选择用户')
  await bulkUpdateRbacUsers({ user_ids: selectedUserIds.value, action: 'set_enabled', enabled })
  bulkDialogVisible.value = false
  ElMessage.success(enabled ? '已批量启用' : '已批量停用')
  await loadAll()
}

watch(activeId, async () => {
  if (activeType.value === 'resource' && activeId.value) {
    const res = await getRbacDatasetAccess(activeId.value)
    activeResourceAccess.value = res.data
  }
})

onMounted(loadAll)
</script>

<style scoped>
.rbac-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #1d2129;
}

.rbac-head,
.rbac-metrics > div,
.rbac-left,
.rbac-detail,
.detail-card {
  background: #fff;
  border: 1px solid #e5e6eb;
  box-shadow: none;
}

.rbac-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 10px;
}

.rbac-kicker {
  color: #4e5969;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .06em;
}

.rbac-head h2,
.detail-head h3 {
  margin: 5px 0;
}

.rbac-head h2 {
  font-size: 24px;
}

.rbac-head p,
.detail-head p {
  margin: 0;
  color: #86909c;
  font-size: 13px;
}

.rbac-head-actions,
.detail-actions,
.bulk-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

button {
  border: 0;
  cursor: pointer;
  font-weight: 800;
}

.rbac-primary,
.rbac-ghost,
.rbac-danger {
  min-height: 32px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 13px;
}

.rbac-primary {
  background: #165dff;
  color: #fff;
}

.rbac-primary.muted {
  background: #344054;
}

.rbac-ghost {
  background: #f7f8fa;
  color: #4e5969;
  border: 1px solid #e5e6eb;
}

.rbac-danger {
  background: #fff;
  color: #d93026;
  border: 1px solid #f1b8b2;
}

.rbac-primary:disabled,
.rbac-ghost:disabled,
.rbac-danger:disabled {
  opacity: .55;
  cursor: not-allowed;
}

.rbac-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.rbac-metrics > div {
  padding: 12px 14px;
  border-radius: 8px;
  min-height: 70px;
}

.rbac-metrics span,
.rbac-section-title,
.detail-badge {
  color: #86909c;
  font-size: 12px;
  font-weight: 900;
}

.rbac-metrics strong {
  display: block;
  margin-top: 6px;
  font-size: 24px;
  line-height: 1;
}

.rbac-layout {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 12px;
  min-height: 680px;
}

.rbac-left,
.rbac-detail {
  border-radius: 10px;
}

.rbac-left {
  padding: 12px;
  overflow: auto;
  max-height: calc(100vh - 214px);
}

.rbac-search {
  display: grid;
  grid-template-columns: 1fr 96px;
  gap: 8px;
  margin-bottom: 12px;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  padding: 8px 10px;
  background: #fff;
  color: #1d2129;
  outline: none;
  font-size: 13px;
}

.rbac-list-section {
  margin-bottom: 14px;
}

.rbac-section-title {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.rbac-section-title button {
  color: #165dff;
  background: transparent;
}

.rbac-list-item {
  width: 100%;
  min-height: 48px;
  margin-bottom: 6px;
  padding: 9px 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: space-between;
  text-align: left;
  border-radius: 8px;
  border: 1px solid transparent;
  background: #fafbfc;
  color: #1d2129;
}

.rbac-list-item.active {
  background: #f0f6ff;
  border-color: #b8d4ff;
  outline: none;
}

.rbac-list-item:hover {
  background: #f4f7fb;
  border-color: #d8dee8;
}

.rbac-list-item.active:hover {
  background: #eaf3ff;
  border-color: #96c0ff;
}

.rbac-list-item.disabled {
  opacity: .62;
}

.rbac-list-item span {
  min-width: 0;
  flex: 1;
}

.rbac-list-item b,
.rbac-list-item small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rbac-list-item small,
.rbac-list-item em {
  color: #86909c;
  font-style: normal;
  font-size: 11px;
}

.rbac-check {
  width: 16px;
  flex: 0 0 16px;
}

.rbac-detail {
  padding: 16px;
  overflow: auto;
  max-height: calc(100vh - 214px);
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f0f1f3;
}

.detail-badge {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 6px;
  background: #f0f6ff;
  color: #165dff;
}

.detail-badge.danger {
  background: #fff1f0;
  color: #d93026;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.detail-card {
  padding: 14px;
  border-radius: 8px;
}

.detail-card.wide {
  grid-column: 1 / -1;
}

.detail-card h4,
.detail-card h5 {
  margin: 0 0 10px;
}

.detail-card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.detail-card-title h4 {
  margin: 0;
}

.readonly-tip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 6px;
  background: #f7f8fa;
  border: 1px solid #e5e6eb;
  color: #86909c;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.detail-card label {
  display: block;
  margin-bottom: 10px;
  color: #4e5969;
  font-size: 12px;
  font-weight: 800;
}

.detail-card label input,
.detail-card label select,
.detail-card label textarea {
  margin-top: 6px;
}

.feature-groups {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
}

.feature-group {
  padding: 10px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fbfcfe;
}

.feature-group-title {
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #edf0f5;
  font-size: 12px;
  font-weight: 900;
  color: #1d2129;
}

.permission-pill {
  display: inline-flex !important;
  align-items: center;
  gap: 6px;
  width: auto !important;
  margin: 0 6px 6px 0 !important;
  padding: 6px 8px;
  border-radius: 6px;
  background: #fff;
  border: 1px solid #e5e6eb;
  color: #4e5969 !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 1.35;
}

.feature-group .permission-pill {
  display: flex !important;
  width: 100% !important;
  min-height: 30px;
  margin: 0 !important;
  padding: 5px 2px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #4e5969 !important;
}

.feature-group .permission-pill + .permission-pill {
  margin-top: 4px !important;
}

.feature-group .permission-pill:hover {
  background: #f2f6fb;
}

.feature-group .permission-pill:has(input:checked) {
  color: #165dff !important;
  background: #eef5ff;
}

.feature-group .permission-pill:has(input:disabled) {
  cursor: not-allowed;
  opacity: .58;
}

.permission-pill input,
.rbac-check input {
  width: auto;
  flex: 0 0 auto;
  margin: 0;
  accent-color: #165dff;
}

.permission-pill span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.permission-pill.block {
  display: flex !important;
  width: 100% !important;
  min-height: 34px;
  border-radius: 6px;
  justify-content: flex-start;
}

.resource-table {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  overflow: hidden;
}

.resource-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 160px;
  gap: 12px;
  align-items: center;
  padding: 9px 10px;
  border-top: 1px solid #f1f3f7;
  font-size: 13px;
}

.resource-row.head {
  border-top: 0;
  background: #f7f8fa;
  color: #86909c;
  font-weight: 900;
}

.auth-object-grid,
.permission-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.auth-object-grid > div {
  padding: 12px;
  border-radius: 8px;
  background: #fafbfc;
  border: 1px solid #edf0f5;
}

.auth-object-grid b {
  display: block;
  font-size: 22px;
}

.mini-tags,
.source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.mini-tags span,
.mini-chip {
  display: inline-flex;
  align-self: flex-start;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f0f6ff;
  color: #2f5fb3;
  font-size: 12px;
  font-weight: 700;
}

.source-list > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 10px;
  border-radius: 6px;
  background: #fafbfc;
  border: 1px solid #edf0f5;
}

.source-list span {
  color: #86909c;
}

.user-pick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 6px;
}

.user-pick-grid .permission-pill {
  display: flex !important;
  width: 100% !important;
  min-height: 34px;
  margin: 0 !important;
  justify-content: flex-start;
}

.rbac-empty {
  padding: 80px 20px;
  text-align: center;
  color: #86909c;
}

.bulk-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

@media (max-width: 1100px) {
  .rbac-layout,
  .detail-grid,
  .feature-groups,
  .user-pick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
