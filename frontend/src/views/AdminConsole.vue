<template>
  <div class="console-page">
    <section class="console-hero">
      <div class="hero-copy">
        <span class="hero-kicker">权限矩阵</span>
        <h1>系统控制台</h1>
        <p>按身份勾选左侧导航和页面按钮权限。勾选即代表该身份可见，取消即隐藏。</p>
      </div>
      <div class="hero-actions">
        <el-button plain :loading="loading" @click="loadFlags">刷新</el-button>
        <el-button plain type="warning" :loading="resetting" @click="handleReset">恢复默认</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
      </div>
    </section>

    <section class="summary-strip">
      <div><strong>{{ navigationItems.length }}</strong><span>导航项</span></div>
      <div><strong>{{ buttonItems.length }}</strong><span>按钮项</span></div>
      <div><strong>{{ enabledButtonCount }}</strong><span>已开放按钮</span></div>
      <div><strong>{{ highRiskCount }}</strong><span>高风险项</span></div>
    </section>

    <el-skeleton v-if="loading && !featureList.length" :rows="8" animated />

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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdminFeatureFlags, resetAdminFeatureFlags, saveAdminFeatureFlags } from '../api/index.js'

const roles = [
  { value: 'super_admin', label: '超管' },
  { value: 'admin', label: '管理员' },
  { value: 'user', label: '普通用户' }
]
const roleOrder = roles.map((item) => item.value)
const FEATURE_FLAGS_UPDATED_EVENT = 'smartask-feature-flags-updated'

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const features = ref({})
const openModules = ref(['runtime_migration', 'employee_permissions'])

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

onMounted(loadFlags)
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
  max-width: 1080px;
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
  grid-template-columns: repeat(4, 150px);
  justify-content: start;
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

  .matrix-row {
    grid-template-columns: minmax(220px, 1fr) 86px 86px 86px;
  }
}
</style>
