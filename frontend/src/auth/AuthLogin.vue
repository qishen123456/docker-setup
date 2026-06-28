<template>
  <main class="auth-login-page">
    <section class="auth-hero">
      <div class="auth-hero-mark">
        <img src="/angel-logowite.png" alt="ANGEL" class="auth-hero-logo" />
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
/* ===== 登录页：安吉尔品牌企业工作台感 ===== */
.auth-login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr minmax(380px, 480px);
  align-items: stretch;
  background: #F2EDE8;
}

/* ─── 左侧：品牌Hero面板 ─── */
.auth-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 64px 72px;
  background: rgba(26, 24, 22, 0.96);
  overflow: hidden;
}

/* 细腻纹理感背景 */
.auth-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(230, 31, 36, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.03) 0%, transparent 40%);
  pointer-events: none;
}

/* 右侧细线装饰 */
.auth-hero::after {
  content: '';
  position: absolute;
  right: 0;
  top: 15%;
  bottom: 15%;
  width: 1px;
  background: linear-gradient(to bottom, transparent, rgba(255,255,255,0.10), transparent);
}

.auth-hero-mark {
  position: relative;
  z-index: 1;
  width: auto;
  height: auto;
  background: none;
  box-shadow: none;
  border-radius: 0;
  padding: 0;
  display: block;
  overflow: visible;
}

.auth-hero-logo {
  width: 220px;
  height: auto;
  object-fit: contain;
  /* 白色版logo反显 */
  opacity: 0.95;
  display: block;
}

.auth-kicker {
  position: relative;
  z-index: 1;
  margin: 36px 0 16px;
  color: rgba(230, 31, 36, 0.85);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.auth-hero h1 {
  position: relative;
  z-index: 1;
  margin: 0;
  color: rgba(255, 255, 255, 0.95);
  font-size: clamp(28px, 3.5vw, 48px);
  line-height: 1.15;
  letter-spacing: -0.03em;
  font-weight: 800;
}

.auth-desc {
  position: relative;
  z-index: 1;
  max-width: 440px;
  margin: 20px 0 0;
  color: rgba(255, 255, 255, 0.45);
  font-size: 15px;
  line-height: 1.85;
}

.auth-capabilities {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 8px;
  margin-top: 36px;
  flex-wrap: wrap;
}

.auth-capabilities span {
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.10);
  color: rgba(255, 255, 255, 0.55);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
}

/* ─── 右侧：登录卡 ─── */
.login-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 52px 44px;
  background: #FDFAF7;
  border-left: 1px solid rgba(0, 0, 0, 0.06);
}

.login-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 2px;
}

.login-kicker {
  margin: 0 0 10px;
  color: rgba(26, 24, 22, 0.35);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.login-card h2 {
  margin: 0 0 28px;
  color: #1A1816;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.025em;
}

.login-badge {
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(26, 24, 22, 0.06);
  color: rgba(26, 24, 22, 0.45);
  font-size: 10px;
  font-weight: 800;
  white-space: nowrap;
  letter-spacing: 0.02em;
}

/* ─── 表单 ─── */
.login-form {
  display: grid;
  gap: 16px;
}

.login-form label {
  display: grid;
  gap: 7px;
  color: rgba(26, 24, 22, 0.5);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.login-form input {
  width: 100%;
  height: 46px;
  padding: 0 14px;
  border: 1px solid #DDD8D1;
  border-radius: 10px;
  outline: none;
  color: #1A1816;
  font-size: 14px;
  background: #FFFFFF;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
  font-family: inherit;
}

.login-form input:focus {
  border-color: rgba(26, 24, 22, 0.45);
  box-shadow: 0 0 0 3px rgba(26, 24, 22, 0.07);
}

.password-control {
  position: relative;
}

.password-control input {
  padding-right: 48px;
}

.password-control input[type="password"] {
  font-size: 20px;
  letter-spacing: 0.08em;
}

.password-control input::placeholder {
  font-size: 13px;
  letter-spacing: 0;
}

.password-eye {
  position: absolute;
  right: 8px;
  top: 50%;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 8px;
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
  color: rgba(26, 24, 22, 0.6);
  background: rgba(26, 24, 22, 0.06);
}

.password-eye .el-icon {
  font-size: 16px;
}

/* ─── 主登录按钮 ─── */
.primary-login,
.feishu-login {
  width: 100%;
  height: 46px;
  border: 0;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s ease;
}

.primary-login {
  margin-top: 6px;
  background: rgba(26, 24, 22, 0.92);
  color: #fff;
  letter-spacing: 0.02em;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.14);
}

.primary-login:hover:not(:disabled) {
  background: rgba(10, 10, 10, 0.98);
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}

.primary-login:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

/* 飞书登录按钮 */
.feishu-login {
  background: #FFFFFF;
  color: #374151;
  border: 1px solid #DDD8D1;
  letter-spacing: 0.01em;
}

.feishu-login:hover:not(:disabled) {
  background: #F5F0EB;
  border-color: #C8C0B7;
  color: #1A1816;
}

.primary-login:disabled,
.feishu-login:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

/* ─── 分隔线 ─── */
.login-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  color: #C8C0B7;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.login-divider::before,
.login-divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: #E8E3DC;
}

/* ─── 底部提示 ─── */
.login-tip {
  margin: 18px 0 0;
  color: #B0A89E;
  font-size: 11.5px;
  line-height: 1.7;
}

/* ─── 响应式 ─── */
@media (max-width: 860px) {
  .auth-login-page {
    grid-template-columns: 1fr;
  }

  .auth-hero {
    padding: 48px 32px 40px;
    min-height: 280px;
  }

  .auth-hero-logo {
    width: 160px;
  }

  .auth-hero h1 {
    font-size: 28px;
  }

  .login-card {
    padding: 36px 28px;
  }
}
</style>
