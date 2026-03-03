<template>
  <div id="app">
    <el-alert
      v-if="backendError"
      :title="backendError"
      type="error"
      show-icon
      closable
      @close="backendError = null"
      style="position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:1000;width:calc(100% - 40px);max-width:600px;"
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'App',
  setup() {
    const backendError = ref(null)

    onMounted(() => {
      if (window.__TAURI__ && window.__TAURI__.event) {
        window.__TAURI__.event.listen('backend-error', event => {
          const msg = event.payload
          backendError.value = msg
          if (msg) {
            // log and show a global notification
            // eslint-disable-next-line no-console
            console.error('backend-error event:', msg)
            ElMessage.error({
              message: msg,
              duration: 0,
              showClose: true,
              center: true
            })
          }
        })
      }
    })

    return {
      backendError
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
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
