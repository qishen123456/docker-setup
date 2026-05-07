<template>
  <div class="permission-page admin-workspace">
    <div class="admin-page-head permission-head">
      <div>
        <div class="admin-kicker">ACCESS GOVERNANCE</div>
        <h2>员工权限配置</h2>
        <p>维护员工登录账号、默认密码、飞书身份映射与系统角色。新增员工默认密码为 12345678。</p>
      </div>
      <button class="save-button" type="button" :disabled="loading || saving" @click="saveAll">
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
    </div>

    <section class="permission-card">
      <div class="permission-toolbar">
        <div>
          <h3>账号与角色</h3>
          <p>登录账号用于账号密码登录；飞书 UnionID 用于飞书免登身份匹配。</p>
        </div>
        <button class="add-button" type="button" @click="addEmployee">新增员工</button>
      </div>

      <div class="permission-table">
        <div class="permission-row permission-row-head">
          <span>员工名称</span>
          <span>登录账号</span>
          <span>飞书 UnionID</span>
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
          <input v-model.trim="item.identifier" placeholder="可选，用于飞书免登" />
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
            <button class="reset-button" type="button" @click="resetPassword(item)">重置密码</button>
          </div>
          <div class="row-actions">
            <button class="delete-button" type="button" @click="removeEmployee(index)">删除</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getEmployeePermissions, saveEmployeePermissions } from '../api/index.js'

const employees = ref([])
const loading = ref(false)
const saving = ref(false)

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
    const data = await saveEmployeePermissions(employees.value)
    employees.value = Array.isArray(data?.employees) ? data.employees : employees.value
    ElMessage.success('员工权限配置已保存')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.permission-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.permission-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
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
  height: 36px;
  padding: 0 16px;
  background: #165dff;
  color: #fff;
}

.save-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.permission-card {
  border: 1px solid rgba(18, 48, 79, 0.08);
  border-radius: 18px;
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
  padding: 18px;
  border-bottom: 1px solid #f0f1f3;
}

.permission-toolbar h3 {
  margin: 0;
  color: #1d2129;
  font-size: 18px;
}

.add-button {
  height: 34px;
  padding: 0 14px;
  background: #e8f6f4;
  color: #0b625d;
}

.permission-table {
  padding: 12px 18px 18px;
}

.permission-row {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) minmax(150px, 1fr) minmax(190px, 1.25fr) 120px 88px 220px 68px;
  gap: 12px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f5f6f8;
}

.permission-row-head {
  color: #86909c;
  font-size: 12px;
  font-weight: 900;
}

.permission-row input,
.permission-row select {
  height: 38px;
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
  height: 30px;
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
  height: 32px;
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
  .permission-summary {
    grid-template-columns: 1fr;
  }

  .permission-row {
    grid-template-columns: 1fr;
    padding: 14px 0;
  }

  .permission-row-head {
    display: none;
  }
}
</style>
