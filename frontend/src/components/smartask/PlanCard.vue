<template>
  <div v-if="steps.length" class="sa-plan-card">
    <div class="sa-plan-badge">执行计划</div>
    <p class="sa-plan-intro">{{ introText }}</p>

    <div class="sa-steps">
      <div v-for="step in steps" :key="step.index" class="sa-step">
        <div class="sa-step-number">{{ String(step.index).padStart(2, '0') }}</div>
        <div class="sa-step-main">
          <div class="sa-step-content">{{ step.title }}</div>
          <div v-for="(substep, subIndex) in step.substeps" :key="subIndex" class="sa-step-sub">
            {{ substep }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  route: {
    type: [String, Object],
    default: null
  }
})

const planText = computed(() => {
  const route = props.route
  if (!route) return ''

  const text = typeof route === 'string' ? route : (route.route_desc || JSON.stringify(route))
  return text
})

const introText = computed(() => {
  const lines = planText.value.split('\n').map(line => line.trim()).filter(Boolean)
  const intro = lines.find(line => !/^(步骤\s*\d+|[0-9]+[\.、]|\d+\.\d+)/.test(line))
  return intro || '好的，根据你的问题，我制定了以下执行计划：'
})

const steps = computed(() => {
  const lines = planText.value.split('\n').map(line => line.trim()).filter(Boolean)
  const list = []
  let current = null

  lines.forEach((line) => {
    if (/^(步骤\s*\d+|[0-9]+[\.、])/.test(line)) {
      const cleaned = line.replace(/^(步骤\s*\d+[:：]?|[0-9]+[\.、]\s*)/, '').trim()
      current = {
        index: list.length + 1,
        title: cleaned || `步骤 ${list.length + 1}`,
        substeps: [],
      }
      list.push(current)
      return
    }

    if (/^\d+\.\d+/.test(line) && current) {
      current.substeps.push(line.replace(/^\d+\.\d+\s*/, '').trim())
    }
  })

  return list
})
</script>

<style scoped>
.sa-plan-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  padding: 2px 0 3px;
}

.sa-plan-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  height: 24px;
  padding: 0 10px;
  border-radius: 8px;
  background: #FEF2F2;
  color: #E61F24;
  font-size: 11px;
  font-weight: 700;
}

.sa-plan-intro {
  margin: 0;
  font-size: 14px;
  color: #111827;
  line-height: 1.72;
  font-weight: 500;
}

.sa-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sa-step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.sa-step-number {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: linear-gradient(180deg, #FEF2F2 0%, #FEF2F2 100%);
  color: #E61F24;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sa-step-main {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-top: 2px;
}

.sa-step-content {
  font-size: 13px;
  color: #111827;
  line-height: 1.65;
}

.sa-step-sub {
  font-size: 12px;
  color: #9CA3AF;
  line-height: 1.62;
}
</style>
