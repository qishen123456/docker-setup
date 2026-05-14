<template>
  <div class="sa-welcome">
    <div class="sa-welcome-head">
      <div class="sa-welcome-avatar">DA</div>
      <div class="sa-welcome-copy">
        <div class="sa-welcome-label">经营分析顾问</div>
        <div class="sa-welcome-text">{{ displayText }}</div>
      </div>
    </div>

    <div class="sa-quick-questions">
      <div class="sa-quick-head">
        <div>
          <div class="sa-quick-title">常用问题</div>
          <div class="sa-quick-tip">点击问题将带入所属数据集口径，你可以修改后再发送。</div>
        </div>
        <button class="sa-quick-refresh" :disabled="commonQuestionsLoading" @click="$emit('refresh-questions')">
          <span class="sa-quick-refresh-icon" :class="{ 'is-loading': commonQuestionsLoading }">↻</span>
          <span>{{ commonQuestionsLoading ? '刷新中' : '换一批' }}</span>
        </button>
      </div>
      <div v-if="commonQuestions.length" class="sa-quick-list">
        <button 
          v-for="(q, i) in commonQuestions" 
          :key="q.id || `${q.dataset_id || 'auto'}-${q.question_text || q}-${i}`" 
          class="sa-quick-btn"
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
  gap: 22px;
  padding: 28px 10px 14px;
  max-width: 800px;
}

.sa-welcome-head {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.sa-welcome-avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(180deg, #3a74ff 0%, #165dff 100%);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 10px 22px rgba(22, 93, 255, 0.14);
}

.sa-welcome-copy {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.sa-welcome-label {
  font-size: 11px;
  font-weight: 700;
  color: #165dff;
  letter-spacing: 0.03em;
}

.sa-welcome-text {
  font-size: 18px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1.65;
}

.sa-welcome-text::after {
  content: '|';
  margin-left: 2px;
  color: #165dff;
  animation: sa-welcome-cursor-blink 1s step-end infinite;
}

.sa-quick-questions {
  margin-left: 56px;
  padding-top: 0;
}

.sa-quick-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 10px;
}

.sa-quick-title {
  font-size: 11px;
  font-weight: 700;
  color: #86909c;
  margin-bottom: 6px;
}

.sa-quick-tip {
  margin-bottom: 10px;
  font-size: 11px;
  color: #a0a7b4;
}

.sa-quick-refresh {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(22, 93, 255, 0.16);
  border-radius: 999px;
  background: #fff;
  color: #165dff;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.sa-quick-refresh:hover:not(:disabled) {
  border-color: rgba(22, 93, 255, 0.32);
  background: #f7fbff;
}

.sa-quick-refresh:disabled {
  cursor: default;
  opacity: 0.72;
}

.sa-quick-refresh-icon {
  display: inline-flex;
  font-size: 14px;
  line-height: 1;
}

.sa-quick-refresh-icon.is-loading {
  animation: sa-quick-spin 0.8s linear infinite;
}

.sa-quick-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 14px;
}

.sa-quick-btn {
  text-align: left;
  min-height: 44px;
  padding: 12px 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
  border: 1px solid rgba(29, 33, 41, 0.08);
  border-radius: 14px;
  font-size: 12px;
  color: #4e5969;
  cursor: pointer;
  transition: all 0.15s;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035);
  line-height: 1.45;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sa-quick-btn:hover {
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  border-color: rgba(22, 93, 255, 0.22);
  color: #165dff;
  transform: translateY(-1px);
}

.sa-quick-dataset {
  display: inline-flex;
  align-self: flex-start;
  max-width: 100%;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(22, 93, 255, 0.08);
  color: #165dff;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sa-quick-question {
  display: block;
  color: inherit;
}

.sa-quick-empty {
  padding: 14px 16px;
  border: 1px dashed rgba(29, 33, 41, 0.12);
  border-radius: 12px;
  background: rgba(247, 248, 250, 0.72);
  color: #86909c;
  font-size: 12px;
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
  .sa-quick-questions {
    margin-left: 0;
  }

  .sa-quick-list {
    grid-template-columns: 1fr;
  }

  .sa-welcome-text {
    font-size: 16px;
  }
}
</style>
