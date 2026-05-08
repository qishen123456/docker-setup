import { computed, ref } from 'vue'
import { getFeatureFlags } from '../api/index.js'

const features = ref({})
const ready = ref(false)
let loadingPromise = null

export const loadFeatureFlags = async (force = false) => {
  if (loadingPromise && !force) return loadingPromise
  loadingPromise = getFeatureFlags()
    .then((res) => {
      features.value = res?.data?.features || {}
      ready.value = true
      return features.value
    })
    .catch(() => {
      features.value = {}
      ready.value = false
      return features.value
    })
    .finally(() => {
      loadingPromise = null
    })
  return loadingPromise
}

export const isFeatureEnabled = (key) => {
  if (!key) return true
  const feature = features.value?.[key]
  if (!ready.value || !feature) return true
  return Boolean(feature.available ?? feature.enabled)
}

export const useFeatureFlags = () => ({
  features,
  ready,
  loadFeatureFlags,
  isFeatureEnabled,
  enabledFeatures: computed(() => features.value),
})
