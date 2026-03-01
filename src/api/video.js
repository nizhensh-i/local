import axios from 'axios'

// 动态获取 API 地址，支持局域网访问
const getApiBaseUrl = () => {
  // 如果指定了后端地址，使用指定的
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }
  
  // 自动检测当前页面的协议和主机
  const protocol = window.location.protocol
  const hostname = window.location.hostname
  const port = '8990'
  
  return `http://${hostname}:${port}/api`
}

const API_BASE_URL = getApiBaseUrl()
console.log('API Base URL:', API_BASE_URL)

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

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
    return `${API_BASE_URL}/videos/${filename}`
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
