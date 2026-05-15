<script setup>
</script>

<template>
  <div class="app-shell">
    <nav class="tab-bar">
      <div class="tab-inner">
        <router-link to="/" class="tab-link" active-class="tab-active">阅读</router-link>
        <router-link to="/vocabulary" class="tab-link" active-class="tab-active">生词本</router-link>
        <router-link to="/history" class="tab-link" active-class="tab-active">历史记录</router-link>
      </div>
    </nav>
    <router-view />
  </div>
</template>

<style>
/* 全局重置 */
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

/* 全局生词与翻译样式（跨页面复用） */
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
