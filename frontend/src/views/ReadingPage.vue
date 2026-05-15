<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useReadingStream } from '../composables/useReadingStream'
import { formatAnnotatedText } from '../utils/formatText'
import { fetchMasteredWords } from '../api/vocabulary'

const LEVEL_LABELS = { beginner: '初级', intermediate: '中级', advanced: '高级' }

const inputText = ref('')
const masteredWords = ref(new Set())
const level = ref(localStorage.getItem('hp_level') || 'intermediate')

watch(level, (val) => localStorage.setItem('hp_level', val))

const {
  annotatedText,
  vocabulary,
  isProcessing,
  progress,
  errorMessage,
  startProcessStream
} = useReadingStream()

const formattedHtml = computed(() => {
  return formatAnnotatedText(annotatedText.value, masteredWords.value)
})

onMounted(async () => {
  masteredWords.value = await fetchMasteredWords()
})

const handleSubmit = async () => {
  const text = inputText.value.trim()

  if (!text || isProcessing.value) {
    return
  }

  inputText.value = ''

  await startProcessStream(text, level.value)

  await nextTick()
}

const handleKeydown = (event) => {
  // Enter 发送，Shift + Enter 换行
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <div class="page-shell">
    <!-- 外层容器：负责渲染羊皮纸背景和内阴影 -->
    <div class="parchment-container">
      <!-- 顶部状态区 -->
      <div class="status-bar">
        <div class="status-title">
          HP 阅读助手
        </div>

        <div class="level-selector">
          <button
            v-for="(label, key) in LEVEL_LABELS"
            :key="key"
            class="level-btn"
            :class="{ active: level === key }"
            :disabled="isProcessing"
            @click="level = key"
          >
            {{ label }}
          </button>
        </div>

        <div
          v-if="isProcessing"
          class="status-progress"
        >
          正在处理：{{ progress.current }} / {{ progress.total }}
        </div>

        <div
          v-else-if="annotatedText"
          class="status-progress"
        >
          处理完成
        </div>

        <div
          v-else
          class="status-progress"
        >
          输入文本后开始阅读
        </div>
      </div>

      <!-- 错误提示 -->
      <div
        v-if="errorMessage"
        class="error-message"
      >
        {{ errorMessage }}
      </div>

      <!-- 阅读主体区：居中对齐，限制最大宽度以保证阅读视线不疲劳 -->
      <div class="reading-scroll-area">
        <div
          v-if="formattedHtml"
          class="reading-content"
          v-html="formattedHtml"
        ></div>

        <div
          v-else
          class="empty-state"
        >
          <p>在下方输入一段英文文本。</p>
          <p>系统会流式返回翻译标注后的阅读内容。</p>
        </div>
      </div>
    </div>

    <!-- 底部输入区：类似 GPT 对话输入框 -->
    <div class="input-wrapper">
      <div class="input-panel">
        <textarea
          v-model="inputText"
          class="text-input"
          placeholder="请输入需要翻译和标注的英文文本，按 Enter 开始处理，Shift + Enter 换行"
          rows="2"
          :disabled="isProcessing"
          @keydown="handleKeydown"
        ></textarea>

        <button
          class="send-button"
          :disabled="isProcessing || !inputText.trim()"
          @click="handleSubmit"
        >
          {{ isProcessing ? '处理中' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@font-face {
  font-family: 'Bookerly';
  src: url('/fonts/Bookerly.ttf') format('truetype');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'Bookerly';
  src: url('/fonts/Bookerly-Bold.ttf') format('truetype');
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}

.page-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 32px 20px 120px;
}

/* 外层羊皮纸容器 */
.parchment-container {
  width: 100%;
  max-width: 980px;
  min-height: calc(100vh - 180px);
  margin: 0 auto;
  border-radius: 24px;
  background:
    radial-gradient(circle at 15% 10%, rgba(255, 255, 255, 0.26), transparent 18%),
    radial-gradient(circle at 85% 20%, rgba(120, 74, 34, 0.12), transparent 20%),
    linear-gradient(135deg, #f3dfae 0%, #ead19a 45%, #dec184 100%);
  box-shadow:
    inset 0 0 42px rgba(84, 47, 15, 0.42),
    0 24px 70px rgba(0, 0, 0, 0.42);
  border: 1px solid rgba(98, 60, 24, 0.32);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 顶部状态栏 */
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 28px;
  border-bottom: 1px solid rgba(91, 57, 24, 0.22);
  background: rgba(111, 72, 28, 0.08);
}

.status-title {
  font-size: 20px;
  font-weight: 700;
  color: #3c2915;
  letter-spacing: 0.04em;
}

.status-progress {
  font-size: 14px;
  color: #6c4b24;
}

/* 水平选择器 */
.level-selector {
  display: flex;
  gap: 2px;
  background: rgba(111, 72, 28, 0.08);
  border-radius: 10px;
  padding: 3px;
}

.level-btn {
  padding: 4px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #6c4b24;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.level-btn:hover:not(:disabled) {
  background: rgba(111, 72, 28, 0.12);
}

.level-btn.active {
  background: #5a3417;
  color: #fff2d5;
}

.level-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 错误提示 */
.error-message {
  margin: 16px 28px 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(180, 42, 42, 0.12);
  color: #8f1f1f;
  font-size: 14px;
}

/* 阅读区滚动容器 */
.reading-scroll-area {
  flex: 1;
  padding: 34px 24px 46px;
  overflow-y: auto;
}

/* 阅读正文 */
.reading-content {
  max-width: 760px;
  margin: 0 auto;
  font-family: 'Bookerly', Georgia, 'Times New Roman', serif;
  font-size: 18px;
  line-height: 2;
  color: #2f2112;
  word-break: break-word;
}

/* 保证段落间距留白 */
:deep(.reading-content p) {
  margin-bottom: 1.5em;
  text-align: justify;
}

/* 空状态 */
.empty-state {
  max-width: 760px;
  margin: 120px auto 0;
  text-align: center;
  color: rgba(64, 42, 18, 0.68);
  font-size: 16px;
  line-height: 1.8;
}

/* 底部输入区 */
.input-wrapper {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 18px 20px 24px;
  background: linear-gradient(
    to top,
    rgba(18, 12, 7, 0.96),
    rgba(18, 12, 7, 0.72),
    transparent
  );
  box-sizing: border-box;
}

.input-panel {
  max-width: 980px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 12px;
  border-radius: 22px;
  background: rgba(255, 244, 213, 0.94);
  border: 1px solid rgba(120, 77, 32, 0.38);
  box-shadow: 0 12px 34px rgba(0, 0, 0, 0.34);
}

.text-input {
  flex: 1;
  resize: none;
  min-height: 48px;
  max-height: 160px;
  padding: 12px 14px;
  border: none;
  outline: none;
  border-radius: 14px;
  background: rgba(255, 250, 236, 0.88);
  color: #2f2112;
  font-size: 15px;
  line-height: 1.6;
  font-family: inherit;
}

.text-input:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.send-button {
  min-width: 82px;
  height: 48px;
  padding: 0 18px;
  border: none;
  border-radius: 14px;
  background: #5a3417;
  color: #fff2d5;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.18s ease;
}

.send-button:hover:not(:disabled) {
  background: #6e411d;
  transform: translateY(-1px);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 小屏适配 */
@media (max-width: 640px) {
  .page-shell {
    padding: 16px 12px 116px;
  }

  .parchment-container {
    min-height: calc(100vh - 150px);
    border-radius: 18px;
  }

  .status-bar {
    padding: 14px 18px;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .level-selector {
    align-self: stretch;
  }

  .level-btn {
    flex: 1;
    text-align: center;
  }

  .reading-scroll-area {
    padding: 24px 16px 36px;
  }

  .reading-content {
    font-size: 16px;
    line-height: 1.9;
  }

  .input-panel {
    border-radius: 18px;
  }

  .send-button {
    min-width: 70px;
  }
}
</style>