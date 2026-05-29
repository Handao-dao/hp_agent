/**
 * SSE 阅读流状态管理。
 *
 * 职责：
 * - 调用 createProcessTask 获取 task_id → EventSource 连接 SSE
 * - 解析 start/progress/completed/error 事件 → 驱动 UI 状态
 * - 60 秒空闲超时保护，每次收到消息时重置计时器
 * - 组件卸载时自动关闭 EventSource
 *
 * 返回：{ annotatedText, vocabulary, isProcessing, progress, errorMessage, startProcessStream, closeEventSource }
 */
import { ref, onBeforeUnmount } from 'vue'
import { createProcessTask } from '../api/reading'
import { useAppBusy } from './useAppBusy'

const READING_BUSY_SOURCE = 'reading-stream'

export function useReadingStream() {
  const { setBusy } = useAppBusy()
  const annotatedText = ref('')
  const vocabulary = ref([])
  const isProcessing = ref(false)
  const errorMessage = ref('')

  const progress = ref({
    current: 0,
    total: 0
  })

  let eventSource = null

  let idleTimer = null

  const closeEventSource = () => {
    clearTimeout(idleTimer)
    idleTimer = null
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    setBusy(READING_BUSY_SOURCE, false)
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

  const startProcessStream = async (longText, level = 'intermediate', profile = 'general') => {
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
    setBusy(READING_BUSY_SOURCE, true)

    try {
      const result = await createProcessTask(text, level, profile)
      const taskId = result.task_id

      if (!taskId) {
        throw new Error('后端没有返回 task_id')
      }

      eventSource = new EventSource(
        `/api/process-stream?task_id=${encodeURIComponent(taskId)}`
      )

      idleTimer = setTimeout(() => {
        errorMessage.value = '处理超时，请重试'
        isProcessing.value = false
        closeEventSource()
      }, 60000)

      eventSource.onmessage = (event) => {
        clearTimeout(idleTimer)
        idleTimer = setTimeout(() => {
          errorMessage.value = '处理超时，请重试'
          isProcessing.value = false
          closeEventSource()
        }, 60000)
        try {
          const data = JSON.parse(event.data)
          handleSseData(data)
        } catch (error) {
          console.error('SSE 数据解析失败:', error)
          errorMessage.value = 'SSE 数据解析失败'
        }
      }

      eventSource.onerror = () => {
        if (!eventSource || eventSource.readyState === EventSource.CLOSED) return
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
