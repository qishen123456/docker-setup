<template>
  <div class="agent-page">
    <el-row :gutter="18">
      <el-col :span="7">
        <el-card class="glass-card">
          <template #header>
            <div class="panel-title">四个中枢 AGENT</div>
          </template>
          <div
            v-for="item in agents"
            :key="item.agent_no"
            class="agent-card"
            :class="{ active: selectedAgentNo === item.agent_no }"
            @click="selectAgent(item)"
          >
            <div class="agent-card-title">{{ item.name }}</div>
            <div class="agent-card-desc">{{ item.role_summary }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="17">
        <el-card class="glass-card">
          <template #header>
            <div class="header-row">
              <div class="panel-title">{{ form.name || 'AGENT详情' }}</div>
              <el-button type="primary" @click="saveAgent">保存配置</el-button>
            </div>
          </template>

          <el-empty v-if="!selectedAgentNo" description="请选择一个 Agent" />
          <template v-else>
            <el-form label-width="110px">
              <el-form-item label="Agent名称">
                <el-input v-model="form.name" />
              </el-form-item>
              <el-form-item label="职责说明">
                <el-input v-model="form.role_summary" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="系统提示词">
                <el-input v-model="form.system_prompt" type="textarea" :rows="10" />
              </el-form-item>
            </el-form>

            <div class="knowledge-head">
              <div class="subheading">知识片段</div>
              <el-button size="small" @click="addKnowledge">新增知识片段</el-button>
            </div>

            <div v-for="(item, index) in form.knowledge_base" :key="index" class="knowledge-item">
              <el-input v-model="form.knowledge_base[index]" type="textarea" :rows="2" />
              <el-button link type="danger" @click="form.knowledge_base.splice(index, 1)">删除</el-button>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAgents, updateAgent } from '../api/index.js'

const agents = ref([])
const selectedAgentNo = ref(null)
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

onMounted(loadAgents)
</script>

<style scoped>
.agent-page {
  min-height: calc(100vh - 150px);
}

.glass-card {
  border: 1px solid var(--border, #e5e6eb);
  background: var(--bg-card, #ffffff);
  border-radius: var(--radius-card, 12px);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(0,0,0,0.04));
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-title, #1d2129);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-card {
  padding: 16px;
  margin-bottom: 12px;
  border-radius: var(--radius-card, 12px);
  cursor: pointer;
  border: 1px solid var(--border, #e5e6eb);
  background: var(--bg-card, #fff);
  transition: all var(--duration-normal, 220ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1));
}

.agent-card:hover {
  border-color: var(--border-hover, #c9cdd4);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
  transform: translateY(-1px);
}

.agent-card.active {
  border-color: var(--color-primary, #3370ff);
  background: var(--color-primary-light, #f0f5ff);
  box-shadow: var(--shadow-md, 0 2px 4px rgba(0,0,0,0.03));
}

.agent-card-title {
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--text-title, #1d2129);
}

.agent-card-desc {
  font-size: 13px;
  color: var(--text-muted, #86909c);
  line-height: 1.6;
}

.knowledge-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px 0 12px;
}

.subheading {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-title, #1d2129);
}

.knowledge-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}
</style>
