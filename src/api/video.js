import axios from 'axios'

const API_BASE_URL = 'http://localhost:8990/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
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
