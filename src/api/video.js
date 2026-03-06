import axios from 'axios'

// 动态获取 API 地址，支持局域网访问
const getApiBaseUrl = () => {
  // 如果指定了后端地址，使用指定的
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }

  // Tauri WebView 场景下 hostname 可能是 tauri.localhost，
  // 不能直接用于 http 请求，统一回落到本机回环地址。
  const hostname = window.location.hostname || '127.0.0.1'
  const protocol = window.location.protocol
  const port = '56173'

  const isTauriHost = protocol === 'tauri:' || hostname.endsWith('tauri.localhost')
  if (isTauriHost || hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://127.0.0.1:${port}/api`
  }

  return `http://${hostname}:${port}/api`
}

const API_BASE_URL = getApiBaseUrl()

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

export async function waitForApiReady(options = {}) {
  const {
    attempts = 25,
    intervalMs = 400,
    requestTimeoutMs = 1200
  } = options

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await api.get('/health', {
        timeout: requestTimeoutMs
      })
      if (response?.data?.success) {
        return true
      }
    } catch (_) {
      // Keep polling until the backend is ready or we hit the attempt limit.
    }

    if (attempt < attempts - 1) {
      await sleep(intervalMs)
    }
  }

  throw new Error('请关闭应用后重新打开。')
}

export const videoApi = {
  /**
   * 获取视频列表
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   * @param {string} params.keyword - 搜索关键词
   * @param {string} params.sort - 排序方式(name/size/mtime)
   * @returns {Promise<Object>}
   */
  getVideos(params = {}) {
    return api.get('/videos', { params })
  },

  /**
   * 获取视频流URL
   * @param {string} filename - 视频文件名
   * @returns {string}
   */
  getVideoStreamUrl(filename) {
    return `${API_BASE_URL}/videos/${encodeURIComponent(filename)}`
  },

  getVideoPosterUrl(filename) {
    return `${API_BASE_URL}/videos/${encodeURIComponent(filename)}/poster`
  },

  /**
   * 获取视频元信息（详情页使用）
   * @param {string} filename - 视频文件名
   * @returns {Promise<Object>}
   */
  getVideoMeta(filename) {
    return api.get(`/videos/${encodeURIComponent(filename)}/meta`)
  },

  /**
   * 获取局域网访问地址信息
   * @param {string|number} frontendPort - 前端访问端口
   * @returns {Promise<Object>}
   */
  getNetworkInfo(frontendPort) {
    return api.get('/network-info', { params: { frontend_port: frontendPort } })
  },

  /**
   * 刷新视频列表缓存
   * @returns {Promise<Object>}
   */
  refreshCache() {
    return api.post('/refresh')
  },

  /**
   * 健康检查
   * @returns {Promise<Object>}
   */
  healthCheck() {
    return api.get('/health')
  }
}

export default videoApi
