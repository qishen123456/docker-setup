<template>
  <div class="sa-user-message">
    <div class="sa-user-bubble">{{ content }}</div>
    <div class="sa-user-avatar">{{ userName[0] }}</div>
  </div>
</template>

<script setup>
defineProps({
  content: {
    type: String,
    default: ''
  },
  userName: {
    type: String,
    default: '用户'
  }
})
</script>

<style scoped>
.sa-user-message {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  justify-content: flex-end;
  margin: 14px 0;
}

.sa-user-avatar {
  width: 26px;
  height: 26px;
  background: #86909c;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
}

.sa-user-bubble {
  max-width: 70%;
  padding: 11px 15px;
  background: #165dff;
  color: #ffffff;
  border-radius: 12px 12px 2px 12px;
  font-size: 13px;
  line-height: 1.58;
  word-break: break-word;
  box-shadow: 0 8px 18px rgba(22, 93, 255, 0.16);
}
</style>
