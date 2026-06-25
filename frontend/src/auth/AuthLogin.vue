<template>
  <main class="auth-login-page">
    <section class="auth-hero">
      <div class="auth-hero-mark">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <p class="auth-kicker">ANGEL INTELLIGENCE</p>
      <h1>安吉尔智能问数</h1>
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
          <input v-model.trim="form.username" type="text" autocomplete="username" placeholder="18576614568" />
        </label>
        <label>
          <span>登录密码</span>
          <div class="password-control">
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="请输入密码"
            />
            <button
              class="password-eye"
              type="button"
              :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              @click="showPassword = !showPassword"
            >
              <el-icon><component :is="showPassword ? Hide : View" /></el-icon>
            </button>
          </div>
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
import { Hide, View } from '@element-plus/icons-vue'
import { getFeishuLoginUrl, passwordLogin, setAuthToken } from '../api/index.js'

const emit = defineEmits(['authenticated'])

const form = ref({
  username: '18576614568',
  password: ''
})
const adminLoading = ref(false)
const feishuLoading = ref(false)
const showPassword = ref(false)

const submitAdmin = async () => {
  if (adminLoading.value) return
  adminLoading.value = true
  try {
    const data = await passwordLogin(form.value)
    if (data?.success && data?.token) {
      setAuthToken(data.token)
      form.value.password = ''
      ElMessage({
        message: '登录成功',
        type: 'success',
        duration: 1800,
        customClass: 'app-toast-modern',
      })
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
    radial-gradient(circle at 88% 12%, rgba(230, 31, 36, 0.04), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #f8f9fa 48%, #f3f4f6 100%);
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
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  box-shadow: 0 22px 50px rgba(0, 0, 0, 0.08);
  display: grid;
  place-items: center;
}

.auth-hero-mark::before {
  content: '';
  width: 38px;
  height: 42px;
  background: #E61F24;
  clip-path: polygon(50% 0%, 70% 100%, 30% 100%);
}

.auth-hero-mark span {
  display: none;
}

.auth-kicker,
.login-kicker {
  margin: 24px 0 10px;
  color: #E61F24;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.auth-hero h1 {
  margin: 0;
  color: #111827;
  font-size: clamp(36px, 5vw, 64px);
  line-height: 1.05;
  letter-spacing: -0.05em;
}

.auth-desc {
  max-width: 460px;
  margin: 20px 0 0;
  color: #6B7280;
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
  border: 1px solid rgba(0, 0, 0, 0.06);
  color: #374151;
  font-size: 12px;
  font-weight: 800;
}

.login-card {
  padding: 30px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #E5E7EB;
  box-shadow: 0 28px 70px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.8);
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
  color: #111827;
  font-size: 28px;
  letter-spacing: -0.03em;
}

.login-badge {
  padding: 7px 10px;
  border-radius: 999px;
  background: #FEF2F2;
  color: #E61F24;
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
  color: #6B7280;
  font-size: 13px;
  font-weight: 800;
}

.login-form input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  outline: none;
  color: #1d2129;
  font-size: 14px;
  background: #fff;
}

.password-control {
  position: relative;
}

.password-control input {
  padding-right: 48px;
}

.password-control input[type="password"] {
  font-size: 21px;
}

.password-control input::placeholder {
  font-size: 14px;
}

.password-eye {
  position: absolute;
  right: 7px;
  top: 50%;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #9CA3AF;
  background: transparent;
  cursor: pointer;
  transition: all 0.18s ease;
  transform: translateY(-50%);
}

.password-eye:hover {
  color: #E61F24;
  background: #FEF2F2;
}

.password-eye .el-icon {
  font-size: 17px;
}

.login-form input:focus {
  border-color: #E61F24;
  box-shadow: 0 0 0 4px rgba(230, 31, 36, 0.12);
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
  background: #1A1A1A;
  color: #fff;
  box-shadow: 0 14px 26px rgba(0, 0, 0, 0.12);
}

.primary-login:hover {
  background: #000000;
}

.feishu-login {
  background: #FFFFFF;
  color: #374151;
  border: 1px solid #E5E7EB;
}

.feishu-login:hover {
  background: #F3F4F6;
  border-color: #D1D5DB;
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
  color: #9CA3AF;
  font-size: 12px;
}

.login-divider::before,
.login-divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: #E5E7EB;
}

.login-tip {
  margin: 14px 0 0;
  color: #9CA3AF;
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
