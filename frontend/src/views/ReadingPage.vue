<script setup>
/**
 * 阅读页面 — 核心交互页面。
 *
 * 功能：
 * - 文本输入 + 三级水平选择器（localStorage 持久化）
 * - SSE 流式渲染标注文本（羊皮纸主题 + Bookerly 字体）
 * - 事件委托捕获单词点击 → 请求 LookupAgent → 气泡弹窗
 * - 气泡中支持添加生词/标记已掌握，通过 reactive Map/Set 即时渲染
 *
 * 关键 composables：
 * - useReadingStream: SSE 连接 + 状态管理
 * - useMasteredWords:  已掌握词 Set（单例共享）
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useReadingStream } from '../composables/useReadingStream'
import { formatAnnotatedText } from '../utils/formatText'
import { setMasteredByWord } from '../api/vocabulary'
import { lookupWord, addVocabToDB } from '../api/lookup'
import { addMasteredWord, useMasteredWords } from '../composables/useMasteredWords'
import { useSettings } from '../composables/useSettings'

const LEVEL_LABELS = { beginner: '初级', intermediate: '中级', advanced: '高级' }
const PROFILE_LABELS = {
  general: '通用阅读',
  fiction: '小说文学',
  harry_potter: '哈利波特',
  technical: '技术文档',
  academic: '学术论文',
  news_business: '新闻商业'
}

const inputText = ref('')
const masteredWords = useMasteredWords()
const manuallyAnnotated = ref(new Map())
const level = ref(localStorage.getItem('hp_level') || 'intermediate')
const profile = ref(localStorage.getItem('hp_profile') || 'general')

watch(level, (val) => localStorage.setItem('hp_level', val))
watch(profile, (val) => localStorage.setItem('hp_profile', val))

const {
  annotatedText,
  vocabulary,
  isProcessing,
  progress,
  errorMessage,
  startProcessStream
} = useReadingStream()

const {
  isConfigured,
  loading: settingsLoading,
  loadSettings,
} = useSettings()

const formattedHtml = computed(() => {
  return formatAnnotatedText(annotatedText.value, masteredWords.value, manuallyAnnotated.value)
})

const canSubmit = computed(() => {
  return isConfigured.value && !isProcessing.value && Boolean(inputText.value.trim())
})

const inputPlaceholder = computed(() => {
  if (settingsLoading.value) return '正在检查模型配置...'
  if (!isConfigured.value) return '请先在设置页配置 DeepSeek API Key'
  return '请输入需要翻译和标注的英文文本，按 Enter 开始处理，Shift + Enter 换行'
})

const handleSubmit = async () => {
  const text = inputText.value.trim()

  if (!text || isProcessing.value || !isConfigured.value) return

  await startProcessStream(text, level.value, profile.value)
  inputText.value = ''
}

const handleKeydown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSubmit()
  }
}

// ---- 气泡查词 ----
const bubbleVisible = ref(false)
const bubbleLoading = ref(false)
const bubbleWord = ref('')
const bubbleSentence = ref('')
const bubbleIsAnnotated = ref(false)
const bubbleResult = ref(null)
const bubbleAddState = ref('idle')
const bubbleStyle = ref({})

function calcBubbleStyle(el) {
  const rect = el.getBoundingClientRect()
  const bubbleH = 200
  const bubbleW = 420
  let top = rect.bottom + 8
  // 如果词在视口下半部分，气泡向上弹出
  if (rect.bottom > window.innerHeight * 0.6) {
    top = rect.top - bubbleH - 8
    if (top < 0) top = 8
  }
  let left = rect.left + rect.width / 2
  const halfW = Math.min(bubbleW / 2, (window.innerWidth - 48) / 2)
  if (left - halfW < 24) left = halfW + 24
  if (left + halfW > window.innerWidth - 24) left = window.innerWidth - halfW - 24
  return {
    position: 'fixed',
    top: top + 'px',
    left: left + 'px',
    transform: 'translateX(-50%)',
    width: bubbleW + 'px',
    maxWidth: 'calc(100vw - 48px)',
  }
}

function extractSentence(el) {
  const parent = el.parentNode
  if (!parent) return ''
  const nodes = [...parent.childNodes]

  let idx = nodes.indexOf(el)
  if (idx === -1) return ''

  // 向左扫描到句子开头
  let start = idx
  for (let i = idx - 1; i >= 0; i--) {
    const t = (nodes[i].textContent || '').trim()
    if (/[.!?]$/.test(t)) { start = i + 1; break }
    if (i === 0) start = 0
  }

  // 向右扫描到句子结尾
  let end = idx
  for (let i = idx; i < nodes.length; i++) {
    const t = (nodes[i].textContent || '').trim()
    if (i > idx && /[.!?]$/.test(t)) { end = i; break }
    if (i === nodes.length - 1) end = i
  }

  return nodes.slice(start, end + 1).map(n => (n.textContent || '').trim()).join(' ')
}

async function handleContentClick(e) {
  if (isProcessing.value) return

  const wordEl = e.target.closest('[data-word]')
  if (!wordEl) {
    bubbleVisible.value = false
    return
  }

  const word = wordEl.dataset.word
  const isAnnotated = wordEl.classList.contains('vocab-word')

  bubbleWord.value = word
  bubbleSentence.value = extractSentence(wordEl)
  bubbleIsAnnotated.value = isAnnotated
  bubbleResult.value = null
  bubbleAddState.value = 'idle'
  bubbleStyle.value = calcBubbleStyle(wordEl)
  bubbleVisible.value = true
  bubbleLoading.value = true

  try {
    const result = await lookupWord(word, bubbleSentence.value)
    bubbleResult.value = result
  } catch {
    bubbleResult.value = { word, word_cn: '查询失败', sentence_cn: '' }
  } finally {
    bubbleLoading.value = false
  }
}

async function addToVocabFromBubble() {
  if (!bubbleResult.value) return
  bubbleAddState.value = 'loading'
  try {
    await addVocabToDB(
      bubbleResult.value.word,
      bubbleResult.value.word_cn,
      bubbleSentence.value
    )
    bubbleAddState.value = 'done'
    bubbleIsAnnotated.value = true
    const key = bubbleResult.value.word.toLowerCase()
    manuallyAnnotated.value = new Map(manuallyAnnotated.value).set(key, bubbleResult.value.word_cn)
  } catch {
    bubbleAddState.value = 'error'
  }
}

const bubbleMastering = ref(false)

async function markMasteredFromBubble() {
  bubbleMastering.value = true
  try {
    const result = await setMasteredByWord(bubbleWord.value, true)
    if (!result.found) {
      bubbleAddState.value = 'error'
      return
    }
    addMasteredWord(bubbleWord.value)
    bubbleVisible.value = false
  } finally {
    bubbleMastering.value = false
  }
}

function handleEscKey(e) {
  if (e.key === 'Escape') bubbleVisible.value = false
}

onMounted(() => {
  loadSettings()
  document.addEventListener('keydown', handleEscKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleEscKey)
})
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

        <div class="reading-controls">
          <label class="profile-selector">
            <span class="profile-label">阅读场景</span>
            <select
              v-model="profile"
              class="profile-select"
              :disabled="isProcessing"
            >
              <option
                v-for="(label, key) in PROFILE_LABELS"
                :key="key"
                :value="key"
              >
                {{ label }}
              </option>
            </select>
          </label>

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

      <div
        v-if="!settingsLoading && !isConfigured"
        class="setup-message"
      >
        <span>请先配置 DeepSeek API Key 后再开始阅读标注。</span>
        <router-link to="/settings">去设置</router-link>
      </div>

      <!-- 阅读主体区：居中对齐，限制最大宽度以保证阅读视线不疲劳 -->
      <div class="reading-scroll-area">
        <div
          v-if="formattedHtml"
          class="reading-content"
          :class="{ locked: isProcessing }"
          v-html="formattedHtml"
          @click="handleContentClick"
        ></div>

        <!-- 单词气泡弹窗 -->
        <div v-if="bubbleVisible" class="word-bubble" :style="bubbleStyle" @click.stop>
          <div v-if="bubbleLoading" class="bubble-loading">查询中...</div>
          <template v-else-if="bubbleResult">
            <div class="bubble-word">{{ bubbleResult.word }}</div>
            <div class="bubble-word-cn">{{ bubbleResult.word_cn }}</div>
            <div v-if="bubbleResult.sentence_cn" class="bubble-sentence-cn">
              {{ bubbleResult.sentence_cn }}
            </div>
            <div class="bubble-actions">
              <button
                v-if="!bubbleIsAnnotated"
                class="bubble-btn bubble-btn-add"
                :disabled="bubbleAddState === 'loading'"
                @click="addToVocabFromBubble"
              >
                <template v-if="bubbleAddState === 'loading'">添加中...</template>
                <template v-else-if="bubbleAddState === 'error'">添加失败，重试</template>
                <template v-else>添加生词</template>
              </button>
              <span v-if="bubbleAddState === 'done' && !bubbleIsAnnotated" class="bubble-added-hint">已添加</span>
              <button
                v-if="bubbleIsAnnotated"
                class="bubble-btn bubble-btn-master"
                :disabled="bubbleMastering"
                @click="markMasteredFromBubble"
              >{{ bubbleMastering ? '标记中...' : '已掌握' }}</button>
              <button
                v-else
                class="bubble-btn bubble-btn-disabled"
                disabled
              >已掌握</button>
              <button class="bubble-btn bubble-btn-dismiss" @click="bubbleVisible = false">忽略</button>
            </div>
          </template>
          <div v-else class="bubble-loading">查询失败</div>
        </div>

        <div
          v-else
          class="empty-state"
        >
          <p>在下方输入一段英文文本，</p>
          <p>等右上方进度条加载完毕返回翻译标注后的阅读内容。</p>
        </div>
      </div>
    </div>

    <!-- 底部输入区：类似 GPT 对话输入框 -->
    <div class="input-wrapper">
      <div class="input-panel">
        <textarea
          v-model="inputText"
          class="text-input"
          :placeholder="inputPlaceholder"
          rows="2"
          :disabled="isProcessing || settingsLoading || !isConfigured"
          @keydown="handleKeydown"
        ></textarea>

        <button
          class="send-button"
          :disabled="!canSubmit"
          @click="handleSubmit"
        >
          {{ isProcessing ? '处理中' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
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

/* 阅读控制区 */
.reading-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.profile-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6c4b24;
  font-size: 13px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.profile-select {
  height: 30px;
  padding: 0 28px 0 10px;
  border: 1px solid rgba(98, 60, 24, 0.18);
  border-radius: 8px;
  background: rgba(255, 250, 236, 0.72);
  color: #5a3417;
  font-size: 13px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  cursor: pointer;
}

.profile-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.setup-message {
  margin: 16px 28px 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(111, 72, 28, 0.08);
  color: #6c4b24;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  font-size: 14px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.setup-message a {
  color: #5a3417;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
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

.reading-content.locked {
  cursor: wait;
  pointer-events: none;
}

/* 保证段落间距留白 */
:deep(.reading-content p) {
  margin-bottom: 1.5em;
  text-align: justify;
}

/* 单词气泡弹窗 */
.word-bubble {
  z-index: 200;
  padding: 20px 24px;
  border-radius: 16px;
  background:
    radial-gradient(circle at 50% 0%, rgba(255, 245, 210, 0.3), transparent 60%),
    linear-gradient(160deg, #f8e8c0 0%, #ead19a 40%, #d4ba78 100%);
  box-shadow:
    0 16px 48px rgba(0, 0, 0, 0.45),
    inset 0 0 24px rgba(84, 47, 15, 0.15);
  border: 1px solid rgba(98, 60, 24, 0.35);
}

.bubble-loading {
  text-align: center;
  color: rgba(64, 42, 18, 0.5);
  font-size: 14px;
  padding: 12px 0;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.bubble-word {
  font-family: 'Bookerly', Georgia, serif;
  font-size: 20px;
  font-weight: 600;
  color: #2f2112;
  margin-bottom: 4px;
}

.bubble-word-cn {
  font-size: 16px;
  color: #6c4b24;
  margin-bottom: 12px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.bubble-sentence-cn {
  font-size: 13px;
  color: #5c4a32;
  line-height: 1.7;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: rgba(111, 72, 28, 0.06);
  border-radius: 8px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.bubble-actions {
  display: flex;
  gap: 8px;
}

.bubble-btn {
  padding: 6px 16px;
  border: 1px solid rgba(98, 60, 24, 0.25);
  border-radius: 8px;
  background: rgba(255, 250, 236, 0.6);
  color: #5a3417;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.bubble-btn-add:hover:not(:disabled) {
  background: #5a3417;
  color: #fff2d5;
}

.bubble-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.bubble-btn-master:hover:not(:disabled) {
  background: #5a3417;
  color: #fff2d5;
}

.bubble-btn-disabled {
  border-color: rgba(98, 60, 24, 0.08);
  background: rgba(91, 52, 23, 0.02);
  color: rgba(140, 115, 89, 0.5);
  cursor: not-allowed;
}

.bubble-btn-dismiss {
  border-color: rgba(98, 60, 24, 0.12);
  background: rgba(91, 52, 23, 0.04);
  color: #8c7359;
}

.bubble-btn-dismiss:hover {
  background: rgba(180, 42, 42, 0.08);
  color: #8f1f1f;
  border-color: rgba(180, 42, 42, 0.2);
}

.bubble-added-hint {
  font-size: 13px;
  color: #6c4b24;
  align-self: center;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
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

  .reading-controls {
    width: 100%;
  }

  .profile-selector {
    width: 100%;
    justify-content: space-between;
  }

  .profile-select {
    flex: 1;
    max-width: 220px;
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

  .word-bubble {
    width: calc(100vw - 48px) !important;
  }
}
</style>
