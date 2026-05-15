import { ref, onBeforeUnmount } from 'vue'
import { createProcessTask } from '../api/reading'

export function useReadingStream() {
  const annotatedText = ref('')
  const vocabulary = ref([])
  const isProcessing = ref(false)
  const errorMessage = ref('')

  const progress = ref({
    current: 0,
    total: 0
  })

  let eventSource = null

  const closeEventSource = () => {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  const handleSseData = (data) => {
    if (data.type === 'start') {
      progress.value.current = 0
      progress.value.total = data.total || 0
      annotatedText.value = ''
      vocabulary.value = []
      errorMessage.value = ''
      isProcessing.value = true
      return
    }

    if (data.type === 'progress') {
      progress.value.current = data.current || 0
      progress.value.total = data.total || progress.value.total
      return
    }

    if (data.type === 'chunk') {
      const chunkText = data.annotated_text || ''
      if (!chunkText) return
      annotatedText.value += annotatedText.value
        ? '\n\n' + chunkText
        : chunkText
      return
    }

    if (data.type === 'completed') {
      annotatedText.value = data.annotated_text || annotatedText.value
      vocabulary.value = data.total_vocab || []
      isProcessing.value = false
      closeEventSource()
      return
    }

    if (data.type === 'error') {
      errorMessage.value = data.message || '后端处理失败'
      isProcessing.value = false
      closeEventSource()
    }
  }

  const startProcessStream = async (longText, level = 'intermediate') => {
    const text = String(longText || '').trim()

    if (!text) {
      errorMessage.value = '请输入需要处理的文本'
      return
    }

    closeEventSource()

    annotatedText.value = ''
    vocabulary.value = []
    errorMessage.value = ''
    progress.value.current = 0
    progress.value.total = 0
    isProcessing.value = true

    try {
      const result = await createProcessTask(text, level)
      const taskId = result.task_id

      if (!taskId) {
        throw new Error('后端没有返回 task_id')
      }

      eventSource = new EventSource(
        `/api/process-stream?task_id=${encodeURIComponent(taskId)}`
      )

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleSseData(data)
        } catch (error) {
          console.error('SSE 数据解析失败:', error)
          errorMessage.value = 'SSE 数据解析失败'
        }
      }

      eventSource.onerror = (error) => {
        console.error('SSE 连接错误:', error)
        errorMessage.value = 'SSE 连接异常，请检查后端服务'
        isProcessing.value = false
        closeEventSource()
      }
    } catch (error) {
      console.error('处理任务启动失败:', error)
      errorMessage.value = error.message || '处理任务启动失败'
      isProcessing.value = false
      closeEventSource()
    }
  }

  onBeforeUnmount(() => {
    closeEventSource()
  })

  return {
    annotatedText,
    vocabulary,
    isProcessing,
    progress,
    errorMessage,
    startProcessStream,
    closeEventSource
  }
}
