<template>
  <span class="sa-typewriter-line">
    <span>{{ visibleText }}</span>
    <span v-if="isTyping" class="sa-typewriter-cursor"></span>
  </span>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  text: {
    type: String,
    default: '',
  },
  speed: {
    type: Number,
    default: 18,
  },
})

const visibleText = ref('')
const isTyping = ref(false)
let timer = null

const clearTyping = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

watch(
  () => props.text,
  (text) => {
    clearTyping()
    const target = String(text || '').trim()
    if (!target) {
      visibleText.value = ''
      isTyping.value = false
      return
    }

    if (!target.startsWith(visibleText.value)) {
      visibleText.value = ''
    }

    isTyping.value = true
    let cursor = visibleText.value.length
    timer = setInterval(() => {
      cursor += 1
      visibleText.value = target.slice(0, cursor)
      if (cursor >= target.length) {
        clearTyping()
        isTyping.value = false
      }
    }, Math.max(8, Number(props.speed) || 18))
  },
  { immediate: true }
)

onBeforeUnmount(clearTyping)
</script>

<style scoped>
.sa-typewriter-line {
  display: inline;
  word-break: break-word;
}

.sa-typewriter-cursor {
  display: inline-flex;
  width: 7px;
  height: 1em;
  margin-left: 3px;
  border-right: 2px solid currentColor;
  vertical-align: -0.12em;
  animation: saTypewriterBlink 0.85s steps(1, end) infinite;
}

@keyframes saTypewriterBlink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}
</style>
