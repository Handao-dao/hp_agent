import { computed, ref } from 'vue'
import { fetchSettings, saveSettings } from '../api/settings'

const settings = ref(null)
const loading = ref(false)
const errorMessage = ref('')

export function useSettings() {
  const isConfigured = computed(() => Boolean(settings.value?.configured))

  async function loadSettings() {
    loading.value = true
    errorMessage.value = ''
    try {
      settings.value = await fetchSettings()
    } catch (error) {
      errorMessage.value = error.message || '设置加载失败'
    } finally {
      loading.value = false
    }
  }

  async function updateSettings(payload) {
    loading.value = true
    errorMessage.value = ''
    try {
      settings.value = await saveSettings(payload)
      return settings.value
    } catch (error) {
      errorMessage.value = error.message || '设置保存失败'
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    settings,
    loading,
    errorMessage,
    isConfigured,
    loadSettings,
    updateSettings,
  }
}
