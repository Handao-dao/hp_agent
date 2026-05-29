/**
 * vue-router 路由配置。
 * 三个路由均使用懒加载（动态 import），按需拆分 chunk。
 * - /            阅读页 (ReadingPage)
 * - /vocabulary  生词本 (VocabularyPage)
 * - /history     历史记录 (HistoryPage)
 * - /settings    设置 (SettingsPage)
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Reading',
    component: () => import('../views/ReadingPage.vue'),
  },
  {
    path: '/vocabulary',
    name: 'Vocabulary',
    component: () => import('../views/VocabularyPage.vue'),
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/HistoryPage.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
