import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { isTauriRuntime } from './utils/tauri'

let tauriInvoke = null

async function sendFrontendLog(level, message) {
  if (!isTauriRuntime()) {
    return
  }

  try {
    if (!tauriInvoke) {
      const core = await import('@tauri-apps/api/core')
      tauriInvoke = core.invoke
    }
    await tauriInvoke('append_frontend_log', { level, message })
  } catch (_) {
    // Avoid affecting normal rendering when logging is unavailable.
  }
}

const app = createApp(App)

window.addEventListener('error', (event) => {
  const message = event.error?.stack
    || `${event.message} @ ${event.filename}:${event.lineno}:${event.colno}`
  void sendFrontendLog('error', message)
})

window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason?.stack || String(event.reason)
  void sendFrontendLog('error', `UnhandledRejection: ${reason}`)
})

app.config.errorHandler = (error, _, info) => {
  const detail = error?.stack || String(error)
  void sendFrontendLog('error', `VueError(${info}): ${detail}`)
}

app.use(createPinia())
app.use(router)

app.use(ElementPlus)

app.mount('#app')
void sendFrontendLog('info', 'frontend mounted')
