<script setup>
// 根组件：全局背景 + Tab 导航栏 + <router-view> 页面出口
import { useAppBusy } from './composables/useAppBusy'

const { isAppBusy } = useAppBusy()

function guardNavigation(event) {
  if (!isAppBusy.value) return
  event.preventDefault()
}
</script>

<template>
  <div class="app-shell">
    <nav class="tab-bar">
      <div class="tab-inner">
        <router-link
          to="/"
          class="tab-link"
          active-class="tab-active"
          :class="{ disabled: isAppBusy }"
          @click="guardNavigation"
        >阅读</router-link>
        <router-link
          to="/vocabulary"
          class="tab-link"
          active-class="tab-active"
          :class="{ disabled: isAppBusy }"
          @click="guardNavigation"
        >生词本</router-link>
        <router-link
          to="/history"
          class="tab-link"
          active-class="tab-active"
          :class="{ disabled: isAppBusy }"
          @click="guardNavigation"
        >历史记录</router-link>
        <router-link
          to="/settings"
          class="tab-link"
          active-class="tab-active"
          :class="{ disabled: isAppBusy }"
          @click="guardNavigation"
        >设置</router-link>
      </div>
    </nav>
    <router-view />
  </div>
</template>

<style>
/* ===== 全局字体 ===== */
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

/* ===== 全局重置 ===== */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Bookerly', Georgia, 'Times New Roman', serif;
  background: #1d1710;
}

/* ===== 全局生词与翻译样式（跨页面复用） ===== */
.vocab-word {
  color: #B8860B;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 1px solid transparent;
}

.vocab-word:hover {
  color: #9F7928;
  border-bottom: 1px dashed #9F7928;
}

.translation {
  color: #2C2825;
  font-size: 0.9em;
  margin-left: 4px;
  opacity: 0.8;
}

.text-word {
  cursor: pointer;
  transition: all 0.15s ease;
}

.text-word:hover {
  opacity: 0.7;
  border-bottom: 1px dashed rgba(184, 134, 11, 0.5);
}
</style>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at top, rgba(255, 245, 210, 0.35), transparent 32%),
    linear-gradient(135deg, #1d1710 0%, #2f2519 45%, #17110b 100%);
}

.tab-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0 20px;
  background: rgba(24, 15, 8, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(98, 60, 24, 0.32);
}

.tab-inner {
  max-width: 980px;
  margin: 0 auto;
  display: flex;
  gap: 4px;
}

.tab-link {
  display: inline-block;
  padding: 14px 24px;
  color: rgba(255, 244, 213, 0.7);
  text-decoration: none;
  font-size: 15px;
  font-weight: 500;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}

.tab-link:hover {
  color: rgba(255, 244, 213, 0.95);
}

.tab-link.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tab-link.disabled:hover {
  color: rgba(255, 244, 213, 0.7);
}

.tab-active {
  color: #e6c87c;
  border-bottom-color: #B8860B;
}

@media (max-width: 640px) {
  .tab-bar {
    padding: 0 8px;
  }

  .tab-link {
    padding: 12px 14px;
    font-size: 13px;
  }
}
</style>
