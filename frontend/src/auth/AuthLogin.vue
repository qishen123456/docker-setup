<template>
  <main class="auth-login-page">
    <section class="auth-hero">
      <div class="auth-hero-mark">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <p class="auth-kicker">DATA AGENT ACCESS</p>
      <h1>经营分析工作台</h1>
      <p class="auth-desc">登录后根据员工权限加载分析、配置与管理能力。</p>
      <div class="auth-capabilities">
        <span>统一身份</span>
        <span>角色隔离</span>
        <span>安全审计</span>
      </div>
    </section>

    <section class="login-card">
      <div class="login-card-head">
        <div>
          <p class="login-kicker">账号登录</p>
          <h2>欢迎回来</h2>
        </div>
        <span class="login-badge">权限控制已启用</span>
      </div>

      <form class="login-form" @submit.prevent="submitAdmin">
        <label>
          <span>登录账号</span>
          <input v-model.trim="form.username" type="text" autocomplete="username" placeholder="admin" />
        </label>
        <label>
          <span>登录密码</span>
          <input v-model="form.password" type="password" autocomplete="current-password" placeholder="请输入密码" />
        </label>
        <button class="primary-login" type="submit" :disabled="adminLoading">
          {{ adminLoading ? '登录中...' : '账号登录' }}
        </button>
      </form>

      <div class="login-divider"><span>或</span></div>

      <button class="feishu-login" type="button" :disabled="feishuLoading" @click="startFeishu">
        {{ feishuLoading ? '连接飞书中...' : '使用飞书组织身份登录' }}
      </button>

      <p class="login-tip">员工账号由超级管理员维护；新建员工默认密码为 12345678，登录后可自行修改。</p>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getFeishuLoginUrl, passwordLogin, setAuthToken } from '../api/index.js'

const emit = defineEmits(['authenticated'])

const form = ref({
  username: 'admin',
  password: ''
})
const adminLoading = ref(false)
const feishuLoading = ref(false)

const submitAdmin = async () => {
  if (adminLoading.value) return
  adminLoading.value = true
  try {
    const data = await passwordLogin(form.value)
    if (data?.success && data?.token) {
      setAuthToken(data.token)
      form.value.password = ''
      ElMessage.success('登录成功')
      emit('authenticated', data.user || null)
    }
  } catch {
    // interceptor already displays backend error
  } finally {
    adminLoading.value = false
  }
}

const startFeishu = async () => {
  if (feishuLoading.value) return
  feishuLoading.value = true
  try {
    const data = await getFeishuLoginUrl()
    if (data?.url) {
      window.location.href = data.url
      return
    }
    ElMessage.warning('飞书登录地址暂未生成，请检查后端飞书配置')
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '飞书登录入口不可用')
  } finally {
    feishuLoading.value = false
  }
}
</script>

<style scoped>
.auth-login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(360px, 1.1fr) minmax(360px, 480px);
  gap: 34px;
  align-items: center;
  padding: 56px;
  background:
    radial-gradient(circle at 12% 16%, rgba(15, 118, 110, 0.18), transparent 28%),
    radial-gradient(circle at 82% 10%, rgba(51, 112, 255, 0.18), transparent 26%),
    linear-gradient(135deg, #f4f8fb 0%, #eef5f3 48%, #f7f9fc 100%);
}

.auth-hero {
  max-width: 620px;
  padding: 38px;
}

.auth-hero-mark {
  width: 68px;
  height: 68px;
  border-radius: 24px;
  position: relative;
  background: linear-gradient(135deg, #122033, #0f766e);
  box-shadow: 0 22px 50px rgba(18, 48, 79, 0.22);
}

.auth-hero-mark span {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: #fff;
}

.auth-hero-mark span:nth-child(1) { left: 16px; top: 18px; background: #8fb8ff; }
.auth-hero-mark span:nth-child(2) { right: 16px; top: 28px; background: #75e0d3; }
.auth-hero-mark span:nth-child(3) { left: 28px; bottom: 14px; background: #ffd36f; }

.auth-kicker,
.login-kicker {
  margin: 24px 0 10px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.auth-hero h1 {
  margin: 0;
  color: #172033;
  font-size: clamp(36px, 5vw, 64px);
  line-height: 1.05;
  letter-spacing: -0.05em;
}

.auth-desc {
  max-width: 460px;
  margin: 20px 0 0;
  color: #5f6b7a;
  font-size: 17px;
  line-height: 1.8;
}

.auth-capabilities {
  display: flex;
  gap: 10px;
  margin-top: 28px;
  flex-wrap: wrap;
}

.auth-capabilities span {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(18, 48, 79, 0.08);
  color: #344054;
  font-size: 12px;
  font-weight: 800;
}

.login-card {
  padding: 30px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(18, 48, 79, 0.08);
  box-shadow: 0 28px 70px rgba(18, 48, 79, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(14px);
}

.login-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.login-card h2 {
  margin: 0 0 22px;
  color: #1d2129;
  font-size: 28px;
  letter-spacing: -0.03em;
}

.login-badge {
  padding: 7px 10px;
  border-radius: 999px;
  background: #e8f6f4;
  color: #0b625d;
  font-size: 11px;
  font-weight: 900;
  white-space: nowrap;
}

.login-form {
  display: grid;
  gap: 16px;
}

.login-form label {
  display: grid;
  gap: 8px;
  color: #4e5969;
  font-size: 13px;
  font-weight: 800;
}

.login-form input {
  height: 44px;
  padding: 0 14px;
  border: 1px solid #e5e6eb;
  border-radius: 14px;
  outline: none;
  color: #1d2129;
  font-size: 14px;
  background: #fff;
}

.login-form input:focus {
  border-color: #3370ff;
  box-shadow: 0 0 0 4px rgba(51, 112, 255, 0.1);
}

.primary-login,
.feishu-login {
  width: 100%;
  height: 44px;
  border: 0;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 900;
  cursor: pointer;
}

.primary-login {
  margin-top: 4px;
  background: linear-gradient(135deg, #165dff, #0f766e);
  color: #fff;
  box-shadow: 0 14px 26px rgba(22, 93, 255, 0.22);
}

.feishu-login {
  background: #eef4ff;
  color: #165dff;
  border: 1px solid rgba(22, 93, 255, 0.14);
}

.primary-login:disabled,
.feishu-login:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.login-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 22px 0;
  color: #98a2b3;
  font-size: 12px;
}

.login-divider::before,
.login-divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: #edf0f5;
}

.login-tip {
  margin: 14px 0 0;
  color: #86909c;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .auth-login-page {
    grid-template-columns: 1fr;
    padding: 24px;
  }

  .auth-hero {
    padding: 10px;
  }
}
</style>
