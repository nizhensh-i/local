<template>
  <div id="app">
    <el-alert
      v-if="backendError"
      :title="backendError"
      type="error"
      show-icon
      closable
      @close="backendError = null"
      style="position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:10000;width:calc(100% - 40px);max-width:600px;pointer-events:auto;"
    />

    <router-view v-slot="{ Component, route }">
      <keep-alive>
        <component :is="Component" v-if="route.meta.keepAlive" />
      </keep-alive>
      <component :is="Component" v-if="!route.meta.keepAlive" />
    </router-view>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount } from 'vue'

export default {
  name: 'App',
  setup() {
    const backendError = ref(null)
    let unlistenBackendError = null

    onMounted(() => {
      if (window.__TAURI__ && window.__TAURI__.event) {
        window.__TAURI__.event.listen('backend-error', event => {
          const msg = event.payload
          if (msg && !backendError.value) {
            backendError.value = msg
            // eslint-disable-next-line no-console
            console.error('backend-error event:', msg)
          }
        }).then(unlisten => {
          unlistenBackendError = unlisten
        })
      }
    })

    onBeforeUnmount(() => {
      if (unlistenBackendError) {
        unlistenBackendError()
        unlistenBackendError = null
      }
    })

    return {
      backendError
    }
  }
}
</script>

<style>
:root {
  --bg-page: #f3f4f6;
  --bg-surface: #ffffff;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --border-default: #e5e7eb;
  --border-muted: #d1d5db;
  --shadow-soft: 0 8px 20px rgba(15, 23, 42, 0.06);
  --radius-md: 10px;
  --radius-lg: 12px;
  --space-1: 8px;
  --space-2: 12px;
  --space-3: 16px;
  --space-4: 20px;
  --motion-fast: 0.2s;
  --motion-base: 0.24s;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: var(--text-primary);
  background: var(--bg-page);
}

#app {
  min-height: 100vh;
}

/* 全局滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
