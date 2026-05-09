import { computed, ref } from 'vue'
import { getFeatureFlags } from '../api/index.js'

const features = ref({})
const ready = ref(false)
let loadingPromise = null
let eventBound = false
let requestSeq = 0

const FEATURE_FLAGS_UPDATED_EVENT = 'smartask-feature-flags-updated'

export const loadFeatureFlags = async (force = false) => {
  if (loadingPromise && !force) return loadingPromise
  const seq = ++requestSeq
  const request = getFeatureFlags()
    .then((res) => {
      if (seq === requestSeq) {
        features.value = res?.data?.features || {}
        ready.value = true
      }
      return features.value
    })
    .catch(() => {
      if (seq === requestSeq) {
        features.value = {}
        ready.value = false
      }
      return features.value
    })
    .finally(() => {
      if (loadingPromise === request) {
        loadingPromise = null
      }
    })
  loadingPromise = request
  return loadingPromise
}

export const clearFeatureFlags = () => {
  features.value = {}
  ready.value = false
}

export const isFeatureEnabled = (key) => {
  if (!key) return true
  const feature = features.value?.[key]
  if (!ready.value || !feature) return true
  if (typeof feature.available === 'boolean') return feature.available
  return Boolean(feature.enabled)
}

const bindFeatureFlagEvent = () => {
  if (eventBound || typeof window === 'undefined') return
  eventBound = true
  window.addEventListener(FEATURE_FLAGS_UPDATED_EVENT, () => {
    loadFeatureFlags(true)
  })
}

bindFeatureFlagEvent()

export const useFeatureFlags = () => ({
  features,
  ready,
  loadFeatureFlags,
  clearFeatureFlags,
  isFeatureEnabled,
  enabledFeatures: computed(() => features.value),
})
