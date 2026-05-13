<template>
  <div class="permission-page admin-workspace">
    <div class="admin-page-head permission-head">
      <div>
        <div class="admin-kicker">ACCESS GOVERNANCE</div>
        <h2>员工权限配置</h2>
        <p>维护账号、角色与飞书免登映射。新员工默认密码为 12345678。</p>
      </div>
      <button v-if="isFeatureEnabled('employee_permission_edit')" class="save-button" type="button" :disabled="loading || saving" @click="saveAll">
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
    </div>

    <section class="permission-metrics">
      <div>
        <span>员工账号</span>
        <strong>{{ employees.length }}</strong>
      </div>
      <div>
        <span>管理员</span>
        <strong>{{ adminCount }}</strong>
      </div>
      <div>
        <span>普通用户</span>
        <strong>{{ userCount }}</strong>
      </div>
      <div>
        <span>待重置密码</span>
        <strong>{{ resetCount }}</strong>
      </div>
    </section>

    <section class="permission-card">
      <div class="permission-toolbar">
        <div>
          <h3>账号与角色</h3>
          <p>登录账号用于密码登录；飞书 UnionID 用于免登匹配。</p>
        </div>
        <button v-if="isFeatureEnabled('employee_permission_edit')" class="add-button" type="button" @click="addEmployee">新增员工</button>
      </div>

      <div class="permission-table">
        <div class="permission-row permission-row-head">
          <span>员工名称</span>
          <span>登录账号</span>
          <span>飞书 UnionID</span>
          <span>部门</span>
          <span>岗位</span>
          <span>角色</span>
          <span>状态</span>
          <span>密码操作</span>
          <span>操作</span>
        </div>

        <div v-if="!employees.length" class="permission-empty">
          暂无员工权限配置。新增员工后，默认密码为 12345678。
        </div>

        <div v-for="(item, index) in employees" :key="item.id" class="permission-row">
          <input v-model.trim="item.name" placeholder="例如：张三" />
          <input v-model.trim="item.account" placeholder="例如：zhangsan" />
          <input v-model.trim="item.union_id" placeholder="飞书 union_id" @input="item.identifier = item.union_id" />
          <input v-model.trim="item.department" placeholder="例如：东部分公司" />
          <input v-model.trim="item.position" placeholder="例如：总经理" />
          <select v-model="item.role">
            <option value="admin">管理员</option>
            <option value="user">普通用户</option>
          </select>
          <select v-model="item.enabled">
            <option :value="true">启用</option>
            <option :value="false">停用</option>
          </select>
          <div class="password-cell">
            <span class="password-status" :class="{ 'is-reset': item.reset_password }">
              {{ item.reset_password ? '保存后重置' : '已设置' }}
            </span>
            <button v-if="isFeatureEnabled('employee_password_reset')" class="reset-button" type="button" @click="resetPassword(item)">重置密码</button>
          </div>
          <div class="row-actions">
            <button v-if="isFeatureEnabled('employee_delete')" class="delete-button" type="button" @click="removeEmployee(index)">删除</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getEmployeePermissions, saveEmployeePermissions } from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'

const employees = ref([])
const loading = ref(false)
const saving = ref(false)
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const adminCount = computed(() => employees.value.filter((item) => item.role === 'admin').length)
const userCount = computed(() => employees.value.filter((item) => item.role === 'user').length)
const resetCount = computed(() => employees.value.filter((item) => item.reset_password).length)

const uid = () => `emp_${Date.now()}_${Math.random().toString(16).slice(2)}`

const load = async () => {
  loading.value = true
  try {
    const data = await getEmployeePermissions()
    employees.value = Array.isArray(data?.employees) ? data.employees : []
  } finally {
    loading.value = false
  }
}

const addEmployee = () => {
  employees.value.unshift({
    id: uid(),
    name: '',
    account: '',
    identifier: '',
    union_id: '',
    department: '',
    position: '',
    role: 'user',
    enabled: true,
    note: '',
    reset_password: true
  })
}

const resetPassword = (item) => {
  item.reset_password = true
  ElMessage.info('点击“保存配置”后，该员工密码将重置为 12345678')
}

const removeEmployee = (index) => {
  employees.value.splice(index, 1)
}

const saveAll = async () => {
  saving.value = true
  try {
    const payload = employees.value.map((item) => ({
      ...item,
      identifier: item.union_id || item.identifier || '',
    }))
    const data = await saveEmployeePermissions(payload)
    employees.value = Array.isArray(data?.employees) ? data.employees : employees.value
    ElMessage.success('员工权限配置已保存')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadFeatureFlags()
  load()
})
</script>

<style scoped>
.permission-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.permission-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  min-height: auto;
  padding: 22px 24px;
  border-radius: 22px;
  background:
    radial-gradient(circle at 100% 0%, rgba(22, 93, 255, 0.08), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.save-button,
.add-button,
.reset-button,
.delete-button {
  border: 0;
  border-radius: 999px;
  font-weight: 800;
  cursor: pointer;
}

.save-button {
  height: 38px;
  padding: 0 18px;
  background: linear-gradient(135deg, #165dff, #0f766e);
  color: #fff;
  box-shadow: 0 12px 24px rgba(22, 93, 255, 0.18);
}

.save-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.permission-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.permission-metrics > div {
  min-height: 82px;
  padding: 16px 18px;
  border-radius: 18px;
  background: #fff;
  border: 1px solid rgba(18, 48, 79, 0.07);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.035);
}

.permission-metrics span {
  color: #86909c;
  font-size: 12px;
  font-weight: 800;
}

.permission-metrics strong {
  display: block;
  margin-top: 8px;
  color: #1d2129;
  font-size: 26px;
  line-height: 1;
  letter-spacing: -0.04em;
}

.permission-card {
  border: 1px solid rgba(18, 48, 79, 0.08);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.04);
}

.permission-toolbar p {
  margin: 6px 0 0;
  color: #86909c;
  font-size: 12px;
  line-height: 1.6;
}

.permission-card {
  overflow: hidden;
}

.permission-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid #f0f1f3;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%);
}

.permission-toolbar h3 {
  margin: 0;
  color: #1d2129;
  font-size: 18px;
}

.add-button {
  height: 36px;
  padding: 0 16px;
  background: #e8f6f4;
  color: #0b625d;
}

.permission-table {
  padding: 8px 20px 18px;
  overflow-x: auto;
}

.permission-row {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(130px, 1fr) minmax(190px, 1.25fr) minmax(130px, 1fr) minmax(120px, 0.9fr) 110px 86px 200px 68px;
  gap: 12px;
  align-items: center;
  min-width: 1420px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f6f8;
}

.permission-row-head {
  color: #86909c;
  font-size: 12px;
  font-weight: 900;
  padding-top: 12px;
  padding-bottom: 8px;
}

.permission-row input,
.permission-row select {
  height: 36px;
  padding: 0 12px;
  border: 1px solid #e5e6eb;
  border-radius: 12px;
  background: #fff;
  color: #1d2129;
  outline: none;
  font-size: 14px;
}

.permission-row input:focus,
.permission-row select:focus {
  border-color: #3370ff;
  box-shadow: 0 0 0 3px rgba(51, 112, 255, 0.1);
}

.password-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.password-status {
  height: 28px;
  min-width: 72px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #f2f3f5;
  color: #86909c;
  font-size: 12px;
  font-weight: 800;
}

.password-status.is-reset {
  background: #fff7e8;
  color: #b76e00;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.reset-button,
.delete-button {
  height: 30px;
  padding: 0 12px;
}

.reset-button {
  background: #eef4ff;
  color: #165dff;
}

.delete-button {
  background: #fff1f2;
  color: #c52b35;
}

.permission-empty {
  padding: 34px 0;
  text-align: center;
  color: #86909c;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .permission-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .permission-summary {
    grid-template-columns: 1fr;
  }

  .permission-row {
    grid-template-columns: 1fr;
    min-width: 0;
    padding: 14px 0;
  }

  .permission-row-head {
    display: none;
  }
}
</style>
