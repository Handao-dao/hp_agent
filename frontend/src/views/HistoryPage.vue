<script setup>
import { ref, onMounted, computed } from 'vue'
import { fetchHistoryList, fetchHistoryDetail, deleteHistory } from '../api/history'
import { fetchMasteredWords } from '../api/vocabulary'
import { formatAnnotatedText } from '../utils/formatText'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const expandedId = ref(null)
const expandedRecord = ref(null)
const expandedLoading = ref(false)
const masteredWords = ref(new Set())

async function load() {
  loading.value = true
  try {
    const res = await fetchHistoryList({ limit: 50 })
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function toggleExpand(taskId) {
  if (expandedId.value === taskId) {
    expandedId.value = null
    expandedRecord.value = null
    return
  }
  expandedId.value = taskId
  expandedLoading.value = true
  try {
    expandedRecord.value = await fetchHistoryDetail(taskId)
  } finally {
    expandedLoading.value = false
  }
}

async function handleDelete(taskId) {
  if (!confirm('确定要删除这条历史记录吗？')) return
  await deleteHistory(taskId)
  if (expandedId.value === taskId) {
    expandedId.value = null
    expandedRecord.value = null
  }
  await load()
}

const expandedHtml = computed(() => {
  if (!expandedRecord.value) return ''
  return formatAnnotatedText(expandedRecord.value.annotated_text, masteredWords.value)
})

onMounted(async () => {
  masteredWords.value = await fetchMasteredWords()
  await load()
})
</script>

<template>
  <div class="page-shell">
    <div class="parchment-container">
      <div class="page-header">
        <h2>历史记录</h2>
        <span class="count-badge" v-if="total">{{ total }} 篇</span>
      </div>

      <div class="history-list" v-if="items.length">
        <div
          v-for="item in items"
          :key="item.id"
          class="history-item"
          :class="{ expanded: expandedId === item.id }"
        >
          <div class="item-main" @click="toggleExpand(item.id)">
            <div class="item-title">{{ item.title || '无标题' }}</div>
            <div class="item-time">{{ item.created_at }}</div>
          </div>

          <div class="item-expand" v-if="expandedId === item.id">
            <div class="expand-loading" v-if="expandedLoading">加载中...</div>
            <div
              v-else
              class="reading-content"
              v-html="expandedHtml"
            ></div>
            <button class="delete-btn" @click="handleDelete(item.id)">删除此记录</button>
          </div>
        </div>
      </div>

      <div class="empty-state" v-else-if="!loading">
        暂无历史记录，去阅读页面翻译一篇文章吧。
      </div>

      <div class="loading" v-else>加载中...</div>
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
  flex: 1;
  padding: 32px 20px 60px;
}

.parchment-container {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  border-radius: 24px;
  background:
    radial-gradient(circle at 15% 10%, rgba(255, 255, 255, 0.26), transparent 18%),
    linear-gradient(135deg, #f3dfae 0%, #ead19a 45%, #dec184 100%);
  box-shadow:
    inset 0 0 42px rgba(84, 47, 15, 0.42),
    0 24px 70px rgba(0, 0, 0, 0.42);
  border: 1px solid rgba(98, 60, 24, 0.32);
  overflow: hidden;
  padding: 28px 32px 36px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(91, 57, 24, 0.22);
}

.page-header h2 {
  font-size: 22px;
  color: #3c2915;
  font-weight: 700;
}

.count-badge {
  font-size: 13px;
  color: #6c4b24;
  background: rgba(111, 72, 28, 0.1);
  padding: 2px 10px;
  border-radius: 10px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  border-radius: 12px;
  background: rgba(255, 250, 236, 0.5);
  border: 1px solid rgba(98, 60, 24, 0.1);
  transition: background 0.15s;
  overflow: hidden;
}

.history-item:hover {
  background: rgba(255, 250, 236, 0.8);
}

.item-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  cursor: pointer;
  gap: 12px;
}

.item-title {
  font-weight: 600;
  color: #2f2112;
  font-size: 15px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-time {
  font-size: 13px;
  color: #9e8466;
  flex-shrink: 0;
}

.item-expand {
  padding: 0 18px 18px;
}

.expand-loading {
  text-align: center;
  padding: 20px 0;
  color: rgba(64, 42, 18, 0.5);
  font-size: 14px;
}

.reading-content {
  font-family: 'Bookerly', Georgia, 'Times New Roman', serif;
  font-size: 16px;
  line-height: 1.9;
  color: #2f2112;
  margin-bottom: 16px;
  padding: 20px 24px;
  background: rgba(255, 250, 236, 0.7);
  border-radius: 12px;
}

.reading-content :deep(p) {
  margin-bottom: 1.2em;
}

.delete-btn {
  padding: 8px 18px;
  border: 1px solid rgba(180, 42, 42, 0.3);
  border-radius: 8px;
  background: rgba(180, 42, 42, 0.06);
  color: #8f1f1f;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.delete-btn:hover {
  background: rgba(180, 42, 42, 0.15);
}

.empty-state,
.loading {
  text-align: center;
  padding: 60px 0;
  color: rgba(64, 42, 18, 0.55);
  font-size: 15px;
}

@media (max-width: 640px) {
  .page-shell {
    padding: 16px 12px 40px;
  }

  .parchment-container {
    padding: 20px 16px 24px;
  }

  .item-main {
    padding: 12px 14px;
  }

  .reading-content {
    font-size: 14px;
    padding: 14px 16px;
  }
}
</style>
