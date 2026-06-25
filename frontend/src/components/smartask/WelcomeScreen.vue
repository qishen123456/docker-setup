<template>
  <div class="sa-welcome">
    <div class="sa-welcome-head">
      <div class="sa-welcome-avatar">D</div>
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
  gap: 14px;
  padding: 12px 8px 6px;
  max-width: 760px;
}

.sa-welcome-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.sa-welcome-avatar {
  width: 34px;
  height: 34px;
  background: linear-gradient(180deg, #1A1A1A 0%, #1A1A1A 100%);
  color: #fff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
  box-shadow:
    0 8px 18px rgba(0, 0, 0, 0.1),
    inset 0 -2px 0 rgba(230, 31, 36, 0.55);
}

.sa-welcome-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sa-welcome-label {
  font-size: 10px;
  font-weight: 700;
  color: #E61F24;
  letter-spacing: 0.03em;
}

.sa-welcome-text {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  line-height: 1.5;
}

.sa-welcome-text::after {
  content: '|';
  margin-left: 2px;
  color: #E61F24;
  animation: sa-welcome-cursor-blink 1s step-end infinite;
}

.sa-quick-questions {
  margin-left: 46px;
  padding-top: 0;
}

.sa-quick-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.sa-quick-title {
  font-size: 11px;
  font-weight: 700;
  color: #9CA3AF;
  margin-bottom: 4px;
}

.sa-quick-tip {
  margin-bottom: 6px;
  font-size: 10px;
  color: #9CA3AF;
}

.sa-quick-refresh {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 32px;
  min-width: 82px;
  padding: 0 13px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #F8F9FA 100%);
  color: #1A1A1A;
  font-size: 11px;
  font-weight: 750;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.05);
  transition: border-color 0.16s ease, color 0.16s ease, background 0.16s ease, transform 0.16s ease, box-shadow 0.16s ease;
  white-space: nowrap;
}

.sa-quick-refresh:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(230, 31, 36, 0.22);
  background: #ffffff;
  color: #E61F24;
  box-shadow: 0 9px 18px rgba(0, 0, 0, 0.07);
}

.sa-quick-refresh:disabled {
  cursor: default;
  opacity: 0.72;
}

.sa-quick-refresh-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 15px;
  height: 15px;
  font-size: 14px;
  line-height: 1;
  transform-origin: center;
}

.sa-quick-refresh-icon.is-loading {
  animation: sa-quick-spin 0.8s linear infinite;
}

.sa-quick-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
}

.sa-quick-btn {
  text-align: left;
  min-height: 40px;
  padding: 10px 14px;
  background: linear-gradient(180deg, #ffffff 0%, #FFFFFF 100%);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  font-size: 11px;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.15s;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.035);
  line-height: 1.4;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sa-quick-btn:hover {
  background: linear-gradient(180deg, #ffffff 0%, #FEF2F2 100%);
  border-color: rgba(230, 31, 36, 0.22);
  color: #E61F24;
  transform: translateY(-1px);
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
  padding: 2px 7px;
  border-radius: 8px;
  background: rgba(230, 31, 36, 0.08);
  color: #E61F24;
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
  border: 1px dashed rgba(0, 0, 0, 0.12);
  border-radius: 12px;
  background: rgba(247, 248, 250, 0.72);
  color: #9CA3AF;
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
    font-size: 15px;
  }
}
</style>
