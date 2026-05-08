<template>
  <div class="agent-page">
    <div class="admin-page-head agent-head">
      <div>
        <div class="admin-kicker">AGENT ORCHESTRATION</div>
        <h2>AGENT 管理</h2>
        <p>维护路由、SQL 生成、复核和业务解读四个核心角色的提示词与知识片段。</p>
      </div>
      <div class="agent-head-metrics">
        <span>{{ agents.length }} 个 Agent</span>
        <span>{{ form.knowledge_base.length }} 条知识片段</span>
      </div>
    </div>

    <div class="agent-workbench">
      <section class="agent-rail">
        <div class="agent-rail-head">
          <div>
            <div class="agent-rail-kicker">CONTROL ROLES</div>
            <div class="panel-title">四个中枢 AGENT</div>
          </div>
        </div>
          <div
            v-for="item in agents"
            :key="item.agent_no"
            class="agent-card"
            :class="{ active: selectedAgentNo === item.agent_no }"
            @click="selectAgent(item)"
          >
            <div class="agent-card-no">0{{ item.agent_no }}</div>
            <div class="agent-card-copy">
              <div class="agent-card-title">{{ item.name }}</div>
              <div class="agent-card-desc">{{ item.role_summary }}</div>
            </div>
          </div>
      </section>

      <section class="agent-editor">
        <div class="agent-editor-head">
          <div>
            <div class="agent-editor-kicker">PROMPT WORKSPACE</div>
            <div class="panel-title">{{ form.name || 'AGENT详情' }}</div>
          </div>
          <el-button v-if="isFeatureEnabled('agent_config_edit')" type="primary" @click="saveAgent">保存配置</el-button>
        </div>

          <el-empty v-if="!selectedAgentNo" description="请选择一个 Agent" />
          <template v-else>
            <div class="agent-form-grid">
              <label class="agent-field agent-field-name">
                <span>Agent 名称</span>
                <el-input v-model="form.name" />
              </label>
              <label class="agent-field">
                <span>职责说明</span>
                <el-input v-model="form.role_summary" type="textarea" :rows="3" />
              </label>
              <label class="agent-field agent-field-prompt">
                <span>系统提示词</span>
                <el-input v-model="form.system_prompt" type="textarea" :rows="9" class="prompt-input" />
              </label>
            </div>

            <div class="knowledge-head">
              <div>
                <div class="subheading">知识片段</div>
                <div class="knowledge-desc">用于给当前 Agent 补充稳定规则和业务约束。</div>
              </div>
              <el-button v-if="isFeatureEnabled('agent_config_edit')" size="small" @click="addKnowledge">新增知识片段</el-button>
            </div>

            <div v-for="(item, index) in form.knowledge_base" :key="index" class="knowledge-item">
              <span class="knowledge-index">{{ index + 1 }}</span>
              <el-input v-model="form.knowledge_base[index]" type="textarea" :rows="2" />
              <el-button v-if="isFeatureEnabled('agent_config_edit')" link type="danger" @click="form.knowledge_base.splice(index, 1)">删除</el-button>
            </div>
          </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAgents, updateAgent } from '../api/index.js'
import { useFeatureFlags } from '../state/featureFlags.js'

const agents = ref([])
const selectedAgentNo = ref(null)
const { isFeatureEnabled, loadFeatureFlags } = useFeatureFlags()
const form = reactive({
  name: '',
  role_summary: '',
  system_prompt: '',
  knowledge_base: []
})

const applyAgent = (agent) => {
  selectedAgentNo.value = agent.agent_no
  form.name = agent.name || ''
  form.role_summary = agent.role_summary || ''
  form.system_prompt = agent.system_prompt || ''
  form.knowledge_base = Array.isArray(agent.knowledge_base) ? [...agent.knowledge_base] : []
}

const loadAgents = async () => {
  const result = await getAgents()
  agents.value = result.agents || []
  if (!selectedAgentNo.value && agents.value.length > 0) {
    applyAgent(agents.value[0])
  }
}

const selectAgent = (agent) => {
  applyAgent(agent)
}

const addKnowledge = () => {
  form.knowledge_base.push('')
}

const saveAgent = async () => {
  if (!selectedAgentNo.value) return
  await updateAgent(selectedAgentNo.value, {
    name: form.name,
    role_summary: form.role_summary,
    system_prompt: form.system_prompt,
    knowledge_base: form.knowledge_base
  })
  ElMessage.success('AGENT 配置已保存')
  await loadAgents()
}

onMounted(() => {
  loadFeatureFlags()
  loadAgents()
})
</script>

<style scoped>
.agent-page {
  min-height: calc(100vh - 150px);
}

.agent-head {
  margin-bottom: 14px;
  border-radius: 18px;
}

.agent-head-metrics {
  display: flex;
  gap: 8px;
  color: var(--text-body, #4e5969);
  font-size: 13px;
}

.agent-head-metrics span {
  padding: 8px 12px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 999px;
  background: #f5fbfa;
  color: #0b625d;
  font-weight: 750;
}

.agent-workbench {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.panel-title {
  font-size: 17px;
  font-weight: 900;
  color: #101828;
}

.agent-rail,
.agent-editor {
  border: 1px solid rgba(18, 48, 79, 0.08);
  border-radius: 20px;
  background:
    radial-gradient(circle at 100% 0%, rgba(15, 118, 110, 0.08), transparent 30%),
    rgba(255, 255, 255, 0.86);
  box-shadow: 0 10px 26px rgba(18, 48, 79, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.82);
  overflow: hidden;
}

.agent-rail {
  padding: 16px;
}

.agent-rail-head,
.agent-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.agent-rail-head {
  margin-bottom: 14px;
}

.agent-rail-kicker,
.agent-editor-kicker {
  margin-bottom: 4px;
  color: #0f766e;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.12em;
}

.agent-card {
  display: flex;
  gap: 12px;
  padding: 13px;
  margin-bottom: 10px;
  border-radius: 16px;
  cursor: pointer;
  border: 1px solid rgba(18, 48, 79, 0.08);
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  transition: all var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
}

.agent-card:hover {
  border-color: rgba(15, 118, 110, 0.2);
  box-shadow: 0 10px 22px rgba(18, 48, 79, 0.07);
  transform: translateY(-1px);
}

.agent-card.active {
  border-color: rgba(15, 118, 110, 0.28);
  background:
    radial-gradient(circle at 100% 0%, rgba(15, 118, 110, 0.12), transparent 28%),
    linear-gradient(135deg, #e8f6f4 0%, #ffffff 100%);
  box-shadow: 0 12px 26px rgba(15, 118, 110, 0.12), inset 4px 0 0 #0f766e;
}

.agent-card-no {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #0b625d;
  font-size: 12px;
  font-weight: 900;
  background: #e8f6f4;
  border: 1px solid rgba(15, 118, 110, 0.14);
}

.agent-card-copy {
  min-width: 0;
  flex: 1;
}

.agent-card-title {
  font-weight: 850;
  margin-bottom: 5px;
  color: #101828;
}

.agent-card-desc {
  font-size: 12px;
  color: #667085;
  line-height: 1.6;
}

.agent-editor {
  padding: 18px 20px;
}

.agent-editor-head {
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(18, 48, 79, 0.08);
}

.agent-form-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 14px;
}

.agent-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #1f3349;
  font-size: 13px;
  font-weight: 800;
}

.agent-field-prompt {
  grid-column: 1 / -1;
}

.prompt-input :deep(textarea) {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Microsoft YaHei UI', monospace;
  line-height: 1.65;
}

.knowledge-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 18px 0 12px;
  padding-top: 14px;
  border-top: 1px solid rgba(18, 48, 79, 0.08);
}

.subheading {
  font-size: 15px;
  font-weight: 900;
  color: #101828;
}

.knowledge-desc {
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
}

.knowledge-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
  padding: 10px;
  border: 1px solid rgba(18, 48, 79, 0.06);
  border-radius: 14px;
  background: #ffffff;
}

.knowledge-index {
  width: 26px;
  height: 26px;
  margin-top: 4px;
  border-radius: 999px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #0b625d;
  font-size: 11px;
  font-weight: 900;
  background: #e8f6f4;
}

@media (max-width: 1180px) {
  .agent-workbench {
    grid-template-columns: 1fr;
  }

  .agent-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
