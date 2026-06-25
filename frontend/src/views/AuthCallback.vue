<template>
  <section class="auth-callback-page">
    <div class="auth-callback-card">
      <div class="auth-callback-mark"></div>
      <h1>{{ message }}</h1>
      <p>正在为你进入智能问数工作台...</p>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { setAuthToken } from '../api/index.js'

const route = useRoute()
const message = ref('飞书登录处理中')

onMounted(() => {
  const token = String(route.query.token || '').trim()
  if (token) {
    setAuthToken(token)
    message.value = '飞书登录成功'
    ElMessage.success('飞书登录成功')
    window.setTimeout(() => {
      window.location.replace('/smart-ask')
    }, 300)
  } else {
    message.value = '未收到登录凭证'
    ElMessage.warning('未收到飞书登录凭证，请重新登录')
    window.setTimeout(() => {
      window.location.replace('/smart-ask')
    }, 300)
  }
})
</script>

<style scoped>
.auth-callback-page {
  min-height: 100%;
  display: grid;
  place-items: center;
  background: #F8F9FA;
}

.auth-callback-card {
  width: min(420px, calc(100vw - 48px));
  padding: 34px;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.auth-callback-mark {
  width: 42px;
  height: 42px;
  margin: 0 auto 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #E61F24, #9CA3AF);
}

.auth-callback-card h1 {
  margin: 0 0 8px;
  color: #111827;
  font-size: 20px;
}

.auth-callback-card p {
  margin: 0;
  color: #9CA3AF;
  font-size: 13px;
}
</style>
