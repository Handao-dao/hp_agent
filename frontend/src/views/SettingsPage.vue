<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useSettings } from '../composables/useSettings'

const {
  settings,
  loading,
  errorMessage,
  loadSettings,
  updateSettings,
} = useSettings()

const apiKey = ref('')
const baseUrl = ref('https://api.deepseek.com')
const timeout = ref(60)
const temperature = ref(0.2)
const savedMessage = ref('')

const modelId = computed(() => settings.value?.model_id || 'deepseek-v4-pro')

watch(settings, (value) => {
  if (!value) return
  baseUrl.value = value.base_url || 'https://api.deepseek.com'
  timeout.value = value.timeout || 60
  temperature.value = value.temperature ?? 0.2
}, { immediate: true })

async function handleSave() {
  savedMessage.value = ''
  try {
    await updateSettings({
      api_key: apiKey.value.trim(),
      base_url: baseUrl.value.trim() || 'https://api.deepseek.com',
      timeout: Number(timeout.value),
      temperature: Number(temperature.value),
    })
    apiKey.value = ''
    savedMessage.value = '设置已保存'
  } catch {
    savedMessage.value = ''
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<template>
  <div class="page-shell">
    <div class="settings-panel">
      <div class="page-header">
        <h2>设置</h2>
        <span
          class="status-pill"
          :class="{ ready: settings?.configured }"
        >
          {{ settings?.configured ? 'API Key 已配置' : '待配置' }}
        </span>
      </div>

      <div class="setting-section">
        <label class="field">
          <span>DeepSeek API Key</span>
          <input
            v-model="apiKey"
            type="password"
            placeholder="请输入你的 DeepSeek API Key"
            autocomplete="off"
          />
          <small v-if="settings?.api_key_masked">
            当前：{{ settings.api_key_masked }}（重新输入后会覆盖）
          </small>
        </label>

        <label class="field">
          <span>模型</span>
          <input
            :value="modelId"
            disabled
          />
        </label>

        <details class="advanced">
          <summary>高级设置</summary>
          <label class="field">
            <span>Base URL</span>
            <input v-model="baseUrl" />
          </label>
          <div class="field-grid">
            <label class="field">
              <span>超时（秒）</span>
              <input
                v-model.number="timeout"
                type="number"
                min="5"
                max="300"
              />
            </label>
            <label class="field">
              <span>Temperature</span>
              <input
                v-model.number="temperature"
                type="number"
                min="0"
                max="2"
                step="0.1"
              />
            </label>
          </div>
        </details>

        <button
          class="save-btn"
          :disabled="loading || !apiKey.trim()"
          @click="handleSave"
        >
          {{ loading ? '保存中...' : '保存设置' }}
        </button>

        <div
          v-if="savedMessage"
          class="success-message"
        >
          {{ savedMessage }}
        </div>
        <div
          v-if="errorMessage"
          class="error-message"
        >
          {{ errorMessage }}
        </div>
      </div>

      <div class="setting-section data-note">
        <h3>数据保存</h3>
        <p>API Key 设置、生词本和阅读历史会保存在后端本地数据目录中。Docker 部署时，该目录映射到项目的 backend/data，重启容器不会丢失数据。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-shell {
  flex: 1;
  padding: 32px 20px 60px;
}

.settings-panel {
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  padding: 28px 32px 36px;
  border-radius: 24px;
  background:
    radial-gradient(circle at 15% 10%, rgba(255, 255, 255, 0.26), transparent 18%),
    linear-gradient(135deg, #f3dfae 0%, #ead19a 45%, #dec184 100%);
  border: 1px solid rgba(98, 60, 24, 0.32);
  box-shadow:
    inset 0 0 42px rgba(84, 47, 15, 0.42),
    0 24px 70px rgba(0, 0, 0, 0.42);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(91, 57, 24, 0.22);
}

.page-header h2 {
  font-size: 22px;
  color: #3c2915;
}

.status-pill {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(180, 42, 42, 0.1);
  color: #8f1f1f;
  font-size: 13px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.status-pill.ready {
  background: rgba(55, 120, 71, 0.12);
  color: #2f6d3c;
}

.setting-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: #4a321b;
  font-size: 14px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.field input {
  height: 42px;
  padding: 0 12px;
  border: 1px solid rgba(98, 60, 24, 0.24);
  border-radius: 10px;
  background: rgba(255, 250, 236, 0.84);
  color: #2f2112;
  font: inherit;
  outline: none;
}

.field input:focus {
  border-color: #B8860B;
}

.field input:disabled {
  opacity: 0.65;
}

.field small {
  color: #7d654a;
}

.advanced {
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(111, 72, 28, 0.06);
}

.advanced summary {
  cursor: pointer;
  color: #5a3417;
  font-size: 14px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.advanced[open] {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.save-btn {
  align-self: flex-start;
  height: 42px;
  padding: 0 20px;
  border: none;
  border-radius: 10px;
  background: #5a3417;
  color: #fff2d5;
  font-weight: 600;
  cursor: pointer;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.success-message,
.error-message {
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.success-message {
  background: rgba(55, 120, 71, 0.12);
  color: #2f6d3c;
}

.error-message {
  background: rgba(180, 42, 42, 0.1);
  color: #8f1f1f;
}

.data-note {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid rgba(91, 57, 24, 0.18);
  color: #5c4a32;
  font-size: 14px;
  line-height: 1.7;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.data-note h3 {
  color: #3c2915;
  font-size: 16px;
}

@media (max-width: 640px) {
  .page-shell {
    padding: 16px 12px 40px;
  }

  .settings-panel {
    padding: 20px 16px 24px;
  }

  .field-grid {
    grid-template-columns: 1fr;
  }
}
</style>
