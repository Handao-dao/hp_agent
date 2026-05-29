<script setup>
/**
 * 生词本页面。
 *
 * 功能：
 * - 子 Tab：生词 / 已掌握
 * - 搜索（300ms 防抖）、全选、批量标记已掌握/忽略
 * - 展开查看上下文例句
 * - Promise.allSettled 批量操作，部分失败不阻塞其余
 */
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { fetchVocabulary, setMastered, deleteVocabulary as deleteVocab } from '../api/vocabulary'
import { addMasteredWord, removeMasteredWord } from '../composables/useMasteredWords'

const activeTab = ref('unmastered') // 'unmastered' | 'mastered'
const search = ref('')

// ---- 生词 ----
const unmasteredItems = ref([])
const unmasteredTotal = ref(0)
const unmasteredLoading = ref(false)
const expandedId = ref(null)

// ---- 已掌握 ----
const masteredItems = ref([])
const masteredTotal = ref(0)
const masteredLoading = ref(false)

const errorMsg = ref('')

async function loadUnmastered() {
  unmasteredLoading.value = true
  errorMsg.value = ''
  try {
    const res = await fetchVocabulary({ search: search.value, mastered: 0, limit: 200 })
    unmasteredItems.value = res.items
    unmasteredTotal.value = res.total
  } catch {
    errorMsg.value = '加载生词失败，请检查后端服务'
  } finally {
    unmasteredLoading.value = false
  }
}

async function loadMastered() {
  masteredLoading.value = true
  try {
    const res = await fetchVocabulary({ mastered: 1, limit: 200 })
    masteredItems.value = res.items
    masteredTotal.value = res.total
  } catch {
    // 静默 — 已掌握数据加载失败不影响生词 Tab
  } finally {
    masteredLoading.value = false
  }
}

async function markMastered(item) {
  await setMastered(item.id, true)
  unmasteredItems.value = unmasteredItems.value.filter(i => i.id !== item.id)
  unmasteredTotal.value = Math.max(0, unmasteredTotal.value - 1)
  // 插入已掌握列表头部（最新掌握的排最前）
  item.mastered = 1
  item.mastered_at = new Date().toISOString().replace('T', ' ').slice(0, 19)
  masteredItems.value = [item, ...masteredItems.value.filter(i => i.id !== item.id)]
  masteredTotal.value++
  addMasteredWord(item.word)
}

async function unmarkMastered(item) {
  await setMastered(item.id, false)
  masteredItems.value = masteredItems.value.filter(i => i.id !== item.id)
  masteredTotal.value = Math.max(0, masteredTotal.value - 1)
  removeMasteredWord(item.word)
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

async function handleDelete(item) {
  if (!confirm(`确定要删除"${item.word}"吗？`)) return
  const wasUnmastered = unmasteredItems.value.some(i => i.id === item.id)
  const wasMastered = masteredItems.value.some(i => i.id === item.id)
  await deleteVocab(item.id)
  unmasteredItems.value = unmasteredItems.value.filter(i => i.id !== item.id)
  if (wasUnmastered) {
    unmasteredTotal.value = Math.max(0, unmasteredTotal.value - 1)
  }
  masteredItems.value = masteredItems.value.filter(i => i.id !== item.id)
  if (wasMastered) {
    masteredTotal.value = Math.max(0, masteredTotal.value - 1)
    removeMasteredWord(item.word)
  }
  if (expandedId.value === item.id) expandedId.value = null
}

function switchTab(tab) {
  activeTab.value = tab
  selectedIds.value.clear()
}

// ---- 批量操作 ----
const selectedIds = ref(new Set())
const batchProcessing = ref(false)

function isSelected(id) {
  return selectedIds.value.has(id)
}

function toggleSelectAll(items) {
  const allSelected = items.length > 0 && items.every(i => selectedIds.value.has(i.id))
  if (allSelected) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(items.map(i => i.id))
  }
}

function toggleSelect(id) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

async function batchMarkMastered(items) {
  batchProcessing.value = true
  const ids = [...selectedIds.value]
  try {
    const results = await Promise.allSettled(ids.map(id => setMastered(id, true)))
    const successfulIds = ids.filter((_, idx) => results[idx].status === 'fulfilled')
    const successSet = new Set(successfulIds)
    const failed = ids.length - successfulIds.length
    const movedItems = unmasteredItems.value.filter(i => successSet.has(i.id))
    unmasteredItems.value = unmasteredItems.value.filter(i => !successSet.has(i.id))
    unmasteredTotal.value = Math.max(0, unmasteredTotal.value - movedItems.length)

    const now = new Date().toISOString().replace('T', ' ').slice(0, 19)
    const existingMasteredIds = new Set(masteredItems.value.map(i => i.id))
    const newlyMastered = movedItems
      .filter(i => !existingMasteredIds.has(i.id))
      .map(i => ({ ...i, mastered: 1, mastered_at: now }))
    masteredItems.value = [...newlyMastered, ...masteredItems.value]
    masteredTotal.value += newlyMastered.length
    movedItems.forEach(item => addMasteredWord(item.word))
    clearSelection()
    if (failed > 0) alert(`${failed} 个标记失败，其余已处理`)
  } finally {
    batchProcessing.value = false
  }
}

async function batchDelete(items) {
  const count = selectedIds.value.size
  if (!confirm(`确定要忽略 ${count} 个生词吗？`)) return
  batchProcessing.value = true
  const ids = [...selectedIds.value]
  try {
    const results = await Promise.allSettled(ids.map(id => deleteVocab(id)))
    const successfulIds = ids.filter((_, idx) => results[idx].status === 'fulfilled')
    const successSet = new Set(successfulIds)
    const failed = ids.length - successfulIds.length
    const deletedUnmastered = unmasteredItems.value.filter(i => successSet.has(i.id))
    const deletedMastered = masteredItems.value.filter(i => successSet.has(i.id))
    unmasteredItems.value = unmasteredItems.value.filter(i => !successSet.has(i.id))
    unmasteredTotal.value = Math.max(0, unmasteredTotal.value - deletedUnmastered.length)
    masteredItems.value = masteredItems.value.filter(i => !successSet.has(i.id))
    masteredTotal.value = Math.max(0, masteredTotal.value - deletedMastered.length)
    deletedMastered.forEach(item => removeMasteredWord(item.word))
    clearSelection()
    if (failed > 0) alert(`${failed} 个删除失败，其余已处理`)
  } finally {
    batchProcessing.value = false
  }
}

let debounceTimer
watch(search, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadUnmastered, 300)
})

onMounted(() => {
  loadUnmastered()
  loadMastered()
})

onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
})

// 切换 tab 时不重新请求，只在 onMounted 时加载
</script>

<template>
  <div class="page-shell">
    <div class="parchment-container">
      <div class="page-header">
        <h2>生词本</h2>
        <span class="count-badge" v-if="unmasteredTotal + masteredTotal">
          {{ unmasteredTotal + masteredTotal }} 词
        </span>
      </div>

      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

      <!-- 子 Tab -->
      <div class="sub-tabs">
        <button
          class="sub-tab"
          :class="{ active: activeTab === 'unmastered' }"
          @click="switchTab('unmastered')"
        >
          生词
          <span class="sub-count" v-if="unmasteredTotal">{{ unmasteredTotal }}</span>
        </button>
        <button
          class="sub-tab"
          :class="{ active: activeTab === 'mastered' }"
          @click="switchTab('mastered')"
        >
          已掌握
          <span class="sub-count" v-if="masteredTotal">{{ masteredTotal }}</span>
        </button>
      </div>

      <!-- ========== 生词 Tab ========== -->
      <template v-if="activeTab === 'unmastered'">
        <div class="filter-bar">
          <label class="select-all" v-if="unmasteredItems.length">
            <input
              type="checkbox"
              :checked="unmasteredItems.length > 0 && unmasteredItems.every(i => selectedIds.has(i.id))"
              @change="toggleSelectAll(unmasteredItems)"
            />
            全选
          </label>
          <input
            v-model="search"
            class="search-input"
            placeholder="搜索生词..."
          />
        </div>

        <div v-if="selectedIds.size" class="batch-bar">
          <span class="batch-count">已选 {{ selectedIds.size }} 项</span>
          <button class="batch-btn batch-btn-master" :disabled="batchProcessing" @click="batchMarkMastered(unmasteredItems)">
            标记已掌握
          </button>
          <button class="batch-btn batch-btn-ignore" :disabled="batchProcessing" @click="batchDelete(unmasteredItems)">
            忽略
          </button>
          <button class="batch-btn batch-btn-cancel" @click="clearSelection">取消</button>
        </div>

        <div class="vocab-list" v-if="unmasteredItems.length">
          <div
            v-for="item in unmasteredItems"
            :key="item.id"
            class="vocab-row"
            :class="{ expanded: expandedId === item.id, selected: isSelected(item.id) }"
          >
            <input
              type="checkbox"
              class="row-check"
              :checked="isSelected(item.id)"
              @click.stop
              @change="toggleSelect(item.id)"
            />
            <div class="row-main" @click="toggleExpand(item.id)">
              <span class="row-word">{{ item.word }}</span>
              <span class="row-trans">{{ item.translation }}</span>
              <span class="row-count">×{{ item.encounter_count }}</span>
            </div>
            <div class="row-context" v-if="expandedId === item.id && item.context">
              {{ item.context }}
            </div>
            <button class="master-btn" @click.stop="markMastered(item)">
              已掌握
            </button>
            <button class="ignore-btn" @click.stop="handleDelete(item)">忽略</button>
          </div>
        </div>

        <div class="empty-state" v-else-if="!unmasteredLoading">
          暂无生词，去阅读页面翻译一篇文章吧。
        </div>

        <div class="loading" v-else>加载中...</div>

      </template>

      <!-- ========== 已掌握 Tab ========== -->
      <template v-if="activeTab === 'mastered'">
        <div class="vocab-list" v-if="masteredItems.length">
          <div
            v-for="item in masteredItems"
            :key="item.id"
            class="vocab-row mastered-row"
          >
            <div class="row-main">
              <span class="row-word">{{ item.word }}</span>
              <span class="row-trans">{{ item.translation }}</span>
              <span class="row-date">{{ item.mastered_at?.slice(0, 10) || '' }}</span>
            </div>
            <button class="unmaster-btn" @click.stop="unmarkMastered(item)">
              取消掌握
            </button>
          </div>
        </div>

        <div class="empty-state" v-else-if="!masteredLoading">
          还没有掌握任何生词。
        </div>

        <div class="loading" v-else>加载中...</div>
      </template>
    </div>
  </div>
</template>

<style scoped>
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
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(91, 57, 24, 0.22);
}

.page-header h2 {
  font-size: 22px;
  color: #3c2915;
  font-weight: 700;
}

.error-msg {
  padding: 10px 14px;
  margin-bottom: 16px;
  border-radius: 10px;
  background: rgba(180, 42, 42, 0.08);
  color: #8f1f1f;
  font-size: 13px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.count-badge {
  font-size: 13px;
  color: #6c4b24;
  background: rgba(111, 72, 28, 0.1);
  padding: 2px 10px;
  border-radius: 10px;
}

/* ---- 子 Tab ---- */
.sub-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
}

.sub-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border: 1px solid rgba(98, 60, 24, 0.2);
  border-radius: 10px;
  background: rgba(255, 250, 236, 0.5);
  color: #6c4b24;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.sub-tab:hover {
  background: rgba(255, 250, 236, 0.8);
}

.sub-tab.active {
  background: #5a3417;
  color: #fff2d5;
  border-color: #5a3417;
}

.sub-count {
  font-size: 12px;
  background: rgba(0,0,0,0.12);
  padding: 1px 7px;
  border-radius: 8px;
}

.sub-tab.active .sub-count {
  background: rgba(255,255,255,0.18);
}

/* ---- 全选 + 搜索栏 ---- */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.select-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6c4b24;
  cursor: pointer;
  white-space: nowrap;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.select-all input {
  accent-color: #5a3417;
}

.search-input {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid rgba(98, 60, 24, 0.28);
  border-radius: 12px;
  background: rgba(255, 250, 236, 0.88);
  color: #2f2112;
  font-size: 14px;
  outline: none;
  font-family: inherit;
}

.search-input:focus {
  border-color: #B8860B;
}

/* ---- 词列表 ---- */
.vocab-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.vocab-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 250, 236, 0.5);
  border: 1px solid rgba(98, 60, 24, 0.1);
  transition: background 0.15s;
  gap: 12px;
}

.vocab-row:hover {
  background: rgba(255, 250, 236, 0.8);
}

.vocab-row.selected {
  background: rgba(184, 134, 11, 0.08);
  border-color: rgba(184, 134, 11, 0.25);
}

.row-check {
  flex-shrink: 0;
  accent-color: #5a3417;
}

.row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.row-word {
  font-weight: 600;
  color: #2f2112;
  font-size: 16px;
}

.row-trans {
  color: #6c4b24;
  font-size: 14px;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.row-count {
  font-size: 12px;
  color: #9e8466;
  margin-left: auto;
}

.row-date {
  font-size: 12px;
  color: #9e8466;
  margin-left: auto;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.row-context {
  flex: 1;
  padding: 10px 14px;
  font-size: 13px;
  color: #5c4a32;
  background: rgba(111, 72, 28, 0.06);
  border-radius: 8px;
  line-height: 1.6;
  font-style: italic;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.ignore-btn {
  flex-shrink: 0;
  padding: 6px 14px;
  border: 1px solid rgba(98, 60, 24, 0.15);
  border-radius: 8px;
  background: rgba(91, 52, 23, 0.04);
  color: #8c7359;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.ignore-btn:hover {
  background: rgba(180, 42, 42, 0.1);
  color: #8f1f1f;
  border-color: rgba(180, 42, 42, 0.25);
}

/* ---- 按钮 ---- */
.master-btn {
  flex-shrink: 0;
  padding: 6px 14px;
  border: 1px solid rgba(98, 60, 24, 0.25);
  border-radius: 8px;
  background: rgba(255, 250, 236, 0.6);
  color: #5a3417;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.master-btn:hover {
  background: #5a3417;
  color: #fff2d5;
}

.unmaster-btn {
  flex-shrink: 0;
  padding: 6px 14px;
  border: 1px solid rgba(98, 60, 24, 0.15);
  border-radius: 8px;
  background: rgba(91, 52, 23, 0.06);
  color: #8c7359;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.unmaster-btn:hover {
  background: rgba(180, 42, 42, 0.1);
  color: #8f1f1f;
  border-color: rgba(180, 42, 42, 0.25);
}

/* ---- 批量操作栏 ---- */
.batch-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: rgba(255, 245, 220, 0.7);
  border-radius: 10px;
  border: 1px solid rgba(98, 60, 24, 0.15);
}

.batch-count {
  font-size: 13px;
  color: #6c4b24;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.batch-btn {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.batch-btn-master {
  border: 1px solid rgba(98, 60, 24, 0.25);
  background: rgba(255, 250, 236, 0.8);
  color: #5a3417;
}

.batch-btn-master:hover:not(:disabled) {
  background: #5a3417;
  color: #fff2d5;
}

.batch-btn-ignore {
  border: 1px solid rgba(98, 60, 24, 0.12);
  background: rgba(91, 52, 23, 0.04);
  color: #8c7359;
}

.batch-btn-ignore:hover:not(:disabled) {
  background: rgba(180, 42, 42, 0.1);
  color: #8f1f1f;
  border-color: rgba(180, 42, 42, 0.2);
}

.batch-btn-cancel {
  border: none;
  background: transparent;
  color: #8c7359;
}

.batch-btn-cancel:hover {
  color: #5a3417;
}

.batch-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ---- 空状态 ---- */
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

  .vocab-row {
    padding: 10px 12px;
    gap: 8px;
  }

  .row-word {
    font-size: 14px;
  }
}
</style>
