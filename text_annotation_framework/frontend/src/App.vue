<script setup>
import { computed, onMounted, ref } from 'vue'
import { annotateStream, fetchProfiles } from './api'
import { renderAnnotatedText } from './renderer'

const profiles = ref([])
const profile = ref('english_reading')
const inputText = ref(
  'The resilient framework can annotate technical keywords and preserve useful context during streaming.'
)
const result = ref(null)
const progress = ref({ current: 0, total: 0 })
const isProcessing = ref(false)
const errorMessage = ref('')
const selectedAnnotation = ref(null)

const renderedHtml = computed(() => {
  // demo 强调框架核心：原文 + 结构化 annotations → 可点击阅读层。
  if (!result.value) return ''
  return renderAnnotatedText(result.value.original_text, result.value.annotations || [])
})

onMounted(async () => {
  const payload = await fetchProfiles()
  profiles.value = payload.profiles || []
})

async function runAnnotation() {
  const text = inputText.value.trim()
  if (!text || isProcessing.value) return

  isProcessing.value = true
  errorMessage.value = ''
  result.value = null
  selectedAnnotation.value = null
  progress.value = { current: 0, total: 0 }

  try {
    await annotateStream({
      text,
      profile: profile.value,
      onEvent(event) {
        if (event.type === 'start' || event.type === 'progress') {
          progress.value = {
            current: event.current || 0,
            total: event.total || 0
          }
        }
        if (event.type === 'completed') {
          result.value = event.result
          isProcessing.value = false
        }
        if (event.type === 'error') {
          errorMessage.value = event.message || 'Annotation failed'
          isProcessing.value = false
        }
      }
    })
  } catch (error) {
    errorMessage.value = error.message || 'Annotation failed'
    isProcessing.value = false
  }
}

function handleRenderedClick(event) {
  const mark = event.target.closest('[data-annotation-index]')
  if (!mark || !result.value) return
  const index = Number(mark.dataset.annotationIndex)
  selectedAnnotation.value = result.value.annotations[index] || null
}
</script>

<template>
  <main class="app-shell">
    <section class="workspace">
      <header class="topbar">
        <div>
          <h1>Text Annotation Framework</h1>
          <p>Generic annotation engine with an English-reading reference app.</p>
        </div>

        <label class="profile-picker">
          <span>Profile</span>
          <select v-model="profile" :disabled="isProcessing">
            <option v-for="item in profiles" :key="item.key" :value="item.key">
              {{ item.label }}
            </option>
          </select>
        </label>
      </header>

      <div class="editor-grid">
        <section class="pane">
          <div class="pane-title">Input</div>
          <textarea v-model="inputText" :disabled="isProcessing"></textarea>
          <button class="primary-action" :disabled="isProcessing || !inputText.trim()" @click="runAnnotation">
            {{ isProcessing ? 'Annotating...' : 'Annotate' }}
          </button>
        </section>

        <section class="pane output-pane">
          <div class="pane-title">
            Output
            <span v-if="isProcessing">{{ progress.current }} / {{ progress.total }}</span>
          </div>

          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
          <div
            v-else-if="renderedHtml"
            class="annotated-output"
            v-html="renderedHtml"
            @click="handleRenderedClick"
          ></div>
          <div v-else class="empty-state">Run annotation to see clickable spans.</div>
        </section>
      </div>

      <aside class="details-panel">
        <template v-if="selectedAnnotation">
          <div class="detail-surface">{{ selectedAnnotation.surface }}</div>
          <div class="detail-label">{{ selectedAnnotation.label }}</div>
          <div class="detail-meta">
            <span>{{ selectedAnnotation.type }}</span>
            <span>{{ selectedAnnotation.start_index }}-{{ selectedAnnotation.end_index }}</span>
          </div>
          <p>{{ selectedAnnotation.context }}</p>
        </template>
        <span v-else>Select an annotation to inspect its structured payload.</span>
      </aside>
    </section>
  </main>
</template>
