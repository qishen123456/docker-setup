<template>
  <div class="sa-welcome">
    <div class="sa-welcome-head">
      <div class="sa-welcome-avatar">
        <svg class="sa-welcome-avatar-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
          <defs>
            <linearGradient id="aiAura" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#F51F19" />
              <stop offset="100%" stop-color="#FFA07A" />
            </linearGradient>
            <linearGradient id="innerBg" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#FFFFFF" />
              <stop offset="100%" stop-color="#F8FAFC" />
            </linearGradient>
          </defs>
          <circle cx="50" cy="50" r="45" stroke="url(#aiAura)" stroke-width="2.5" />
          <circle cx="50" cy="50" r="40" fill="url(#innerBg)" />
          <circle cx="50" cy="50" r="32" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="2 2" />
          <path d="M50 31 L25 73 L37 73 L50 52 L63 73 L75 73 Z" fill="#F51F19" />
        </svg>
      </div>
      <div class="sa-welcome-copy">
        <div class="sa-welcome-label">安吉尔经营分析顾问</div>
        <div class="sa-welcome-text">{{ displayText }}</div>
      </div>
    </div>

    <div class="sa-quick-questions">
      <div class="sa-quick-head">
        <div>
          <div class="sa-quick-title">常用问题</div>
          <div class="sa-quick-tip">点击问题将带入所属数据集口径，你可以修改后再发送。</div>
        </div>
        <button v-if="allowRefreshQuestions" class="sa-quick-refresh" :disabled="commonQuestionsLoading" @click="$emit('refresh-questions')">
          <el-icon class="sa-quick-refresh-icon" :class="{ 'is-loading': commonQuestionsLoading }">
            <RefreshRight />
          </el-icon>
          <span>{{ commonQuestionsLoading ? '刷新中' : '换一批' }}</span>
        </button>
      </div>
      <div v-if="commonQuestions.length" class="sa-quick-list">
        <button 
          v-for="(q, i) in commonQuestions" 
          :key="q.id || `${q.dataset_id || 'auto'}-${q.question_text || q}-${i}`" 
          class="sa-quick-btn"
          :disabled="!allowQuickAsk"
          @click="$emit('quick-ask', q)"
        >
          <span class="sa-quick-dataset">{{ q.dataset_tag || q.dataset_name || '自动' }}</span>
          <span class="sa-quick-question">{{ q.question_text || q }}</span>
        </button>
      </div>
      <div v-else class="sa-quick-empty">
        {{ commonQuestionsLoading ? '正在加载推荐问题...' : '暂无可用常用问题，请先在数据资产管理中为数据集维护问题池。' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RefreshRight } from '@element-plus/icons-vue'

const props = defineProps({
  welcomeText: {
    type: String,
    default: 'hi，我是你的经营分析顾问，今天有什么我可以帮助你的吗？'
  },
  commonQuestions: {
    type: Array,
    default: () => []
  },
  commonQuestionsLoading: {
    type: Boolean,
    default: false
  },
  allowQuickAsk: {
    type: Boolean,
    default: true
  },
  allowRefreshQuestions: {
    type: Boolean,
    default: true
  }
})

defineEmits(['quick-ask', 'refresh-questions'])

const displayText = ref('')
const currentIndex = ref(0)

const typeWriter = () => {
  if (currentIndex.value < props.welcomeText.length) {
    displayText.value += props.welcomeText[currentIndex.value]
    currentIndex.value++
    setTimeout(typeWriter, 30) // 火山引擎规格：每字30ms
  }
}

onMounted(() => {
  typeWriter()
})
</script>

<style scoped>
.sa-welcome {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px 0 4px;
  max-width: 960px;
  width: 100%;
}

.sa-welcome-head {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.sa-welcome-avatar {
  position: relative;
  width: 44px;
  height: 44px;
  margin-top: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  overflow: visible;
  padding: 0;
  background: transparent;
  border: 0;
  box-shadow: none;
}

.sa-welcome-avatar::before {
  content: none;
}

.sa-welcome-avatar::after {
  content: '';
  position: absolute;
  right: 1px;
  bottom: 1px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #10B981;
  box-shadow:
    0 0 0 3px #FFFFFF,
    0 4px 9px rgba(16, 185, 129, 0.2);
}

.sa-welcome-avatar-img {
  display: none;
}

.sa-welcome-avatar-svg {
  width: 44px;
  height: 44px;
  display: block;
}

.sa-welcome-copy {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.sa-welcome-label {
  display: inline-flex;
  align-self: flex-start;
  padding: 0;
  border-radius: 0;
  background: transparent;
  color: #E61F24;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0;
}

.sa-welcome-text {
  max-width: 100%;
  font-size: 18px;
  font-weight: 720;
  color: #1F2937;
  line-height: 1.28;
  white-space: nowrap;
  text-wrap: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sa-welcome-text::after {
  content: '|';
  margin-left: 5px;
  color: rgba(230, 31, 36, 0.72);
  animation: sa-welcome-cursor-blink 1s step-end infinite;
}

.sa-quick-questions {
  margin-left: 0;
  padding-top: 0;
}

.sa-quick-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.sa-quick-title {
  font-size: 14px;
  font-weight: 800;
  color: rgba(17, 24, 39, 0.7);
  margin-bottom: 5px;
}

.sa-quick-tip {
  margin-bottom: 0;
  font-size: 12px;
  color: #8B95A1;
  line-height: 1.45;
}

.sa-quick-refresh {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  min-width: 88px;
  padding: 0 13px;
  border: 1px solid rgba(17, 24, 39, 0.09);
  border-radius: 12px;
  background: #FFFFFF;
  color: #111827;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
  transition: border-color 0.16s ease, color 0.16s ease, background 0.16s ease, transform 0.16s ease, box-shadow 0.16s ease;
  white-space: nowrap;
}

.sa-quick-refresh:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(230, 31, 36, 0.2);
  background: #ffffff;
  color: #111827;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
}

.sa-quick-refresh:disabled {
  cursor: default;
  opacity: 0.72;
}

.sa-quick-refresh-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 13px;
  height: 13px;
  font-size: 13px;
  line-height: 1;
  transform-origin: center;
}

.sa-quick-refresh-icon.is-loading {
  animation: sa-quick-spin 0.8s linear infinite;
}

.sa-quick-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 14px;
  width: 100%;
}

.sa-quick-btn {
  position: relative;
  text-align: left;
  min-height: 74px;
  padding: 14px 42px 14px 18px;
  background: #FFFFFF;
  border: 1px solid rgba(17, 24, 39, 0.07);
  border-radius: 14px;
  font-size: 11px;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.18s ease;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.045),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  line-height: 1.35;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sa-quick-btn::after {
  content: '›';
  position: absolute;
  right: 18px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(17, 24, 39, 0.38);
  font-size: 26px;
  font-weight: 300;
  line-height: 1;
}

.sa-quick-btn:hover {
  background: #FFFFFF;
  border-color: rgba(230, 31, 36, 0.14);
  color: #1A1A1A;
  transform: translateY(-2px);
  box-shadow:
    0 14px 30px rgba(15, 23, 42, 0.07),
    inset 0 1px 0 rgba(255, 255, 255, 0.94);
}

.sa-quick-btn:disabled {
  cursor: not-allowed;
  opacity: 0.58;
  transform: none;
}

.sa-quick-dataset {
  display: inline-flex;
  align-self: flex-start;
  max-width: 100%;
  padding: 3px 8px;
  border-radius: 999px;
  background: #FEE2E2;
  color: #991B1B;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-quick-question {
  display: block;
  color: #111827;
  font-size: 14px;
  font-weight: 760;
  line-height: 1.35;
}

.sa-quick-empty {
  padding: 14px 16px;
  border: 1px dashed rgba(17, 24, 39, 0.12);
  border-radius: 18px;
  background: rgba(247, 248, 250, 0.82);
  color: #6B7280;
  font-size: 11px;
  line-height: 1.5;
}

@keyframes sa-quick-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes sa-welcome-cursor-blink {
  0%, 45% {
    opacity: 1;
  }
  46%, 100% {
    opacity: 0;
  }
}

@media (max-width: 900px) {
  .sa-welcome {
    padding: 20px 16px 6px;
  }

  .sa-quick-questions {
    margin-left: 0;
  }

  .sa-quick-list {
    grid-template-columns: 1fr;
  }

  .sa-welcome-text {
    font-size: 17px;
    white-space: normal;
    text-wrap: balance;
  }
}
</style>
