<template>
  <div class="video-detail-page">
    <div class="detail-container">
      <div class="detail-topbar">
        <el-button @click="goBack" :icon="ArrowLeft" class="back-button">
          返回列表
        </el-button>
        <div class="topbar-title-group">
          <h1 class="page-title" :title="filename">{{ filename }}</h1>
          <p class="page-subtitle">视频详情与播放</p>
        </div>
      </div>

      <div class="detail-layout">
        <main class="detail-main">
          <div class="player-section">
            <VideoPlayer
              :src="videoSrc"
              :poster="videoPoster"
              type="video/mp4"
              @ready="handlePlayerReady"
              @error="handlePlayerError"
              @ended="handleVideoEnded"
              ref="videoPlayerRef"
            />
          </div>

          <div v-if="error" class="error-container">
            <el-alert
              :title="errorHeadline"
              :description="error"
              type="error"
              show-icon
              closable
              @close="error = null"
              class="error-alert"
            />

            <el-card v-if="videoCheckResult" class="check-result-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <h3>视频文件检查</h3>
                </div>
              </template>

              <div v-if="videoCheckResult.issues && videoCheckResult.issues.length > 0" class="issues-list">
                <h4>发现的问题：</h4>
                <ul>
                  <li v-for="(issue, index) in videoCheckResult.issues" :key="index">
                    {{ issue }}
                  </li>
                </ul>
              </div>

              <div v-if="videoCheckResult.encoding_tips" class="encoding-tips">
                <h4>解决建议：</h4>
                <ol>
                  <li v-for="(tip, index) in videoCheckResult.encoding_tips" :key="index">
                    <code v-if="tip.includes('ffmpeg')">{{ tip }}</code>
                    <span v-else>{{ tip }}</span>
                  </li>
                </ol>
              </div>

              <div v-if="videoCheckResult.is_large_file" class="large-file-notice">
                <el-icon><Warning /></el-icon>
                <span>文件较大 ({{ videoCheckResult.size_formatted }})，可能需要更长的加载时间</span>
              </div>
            </el-card>

            <div v-if="errorSuggestions.length > 0" class="suggestions">
              <h4>排查建议：</h4>
              <ul>
                <li v-for="(suggestion, index) in errorSuggestions" :key="index">
                  {{ suggestion }}
                </li>
              </ul>
            </div>
          </div>
        </main>

        <aside class="detail-side">
          <el-card class="video-info-card" shadow="never">
            <template #header>
              <div class="card-header">
                <h2 class="video-title">视频信息</h2>
              </div>
            </template>

            <div class="video-meta">
              <div class="meta-item">
                <el-icon><Document /></el-icon>
                <span class="meta-label">文件名</span>
                <span class="meta-value" :title="filename">{{ filename }}</span>
              </div>

              <div class="meta-item">
                <el-icon><Document /></el-icon>
                <span class="meta-label">文件大小</span>
                <span class="meta-value">{{ fileSize || '-' }}</span>
              </div>

              <div class="meta-item">
                <el-icon><Clock /></el-icon>
                <span class="meta-label">修改时间</span>
                <span class="meta-value">{{ modifyTime || '-' }}</span>
              </div>
            </div>
          </el-card>
        </aside>
      </div>
    </div>
  </div>
</template>

<script>
import { ArrowLeft } from '@element-plus/icons-vue'
import VideoPlayer from '../components/VideoPlayer.vue'
import { videoApi } from '../api/video'

export default {
  name: 'VideoDetail',
  
  components: {
    VideoPlayer
  },
  
  props: {
    filename: {
      type: String,
      required: true
    }
  },
  
  data() {
    return {
      ArrowLeft,
      videoSrc: '',
      videoPoster: '',
      fileSize: '',
      modifyTime: '',
      error: null,
      videoInfo: null,
      videoCheckResult: null,
      isCheckingVideo: false
    }
  },
  
  computed: {
    errorHeadline() {
      if (!this.error) return ''
      if (this.error.includes('格式不支持')) return '播放失败：视频格式不受支持'
      if (this.error.includes('损坏')) return '播放失败：视频文件可能已损坏'
      return '播放失败，请按以下建议排查'
    },
    errorSuggestions() {
      if (!this.error) return []
      
      const suggestions = []
      
      if (this.error.includes('格式不支持') || this.error.includes('MEDIA_ERR_SRC_NOT_SUPPORTED')) {
        suggestions.push('检查视频文件是否完整')
        suggestions.push('确保视频使用 H.264 (AVC) 编码')
        suggestions.push('尝试使用 ffmpeg 转换视频格式')
        suggestions.push('命令: ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4')
      }
      
      if (this.videoInfo && this.videoInfo.size > 2 * 1024 * 1024 * 1024) {
        suggestions.push('文件较大，请等待加载完成')
        suggestions.push('检查网络连接是否稳定')
      }
      
      suggestions.push('刷新页面重试')
      suggestions.push('检查视频文件是否存在')
      
      return suggestions
    }
  },
  
  mounted() {
    this.loadVideoDetail()
  },
  
  beforeUnmount() {
    // VideoPlayer 组件会自动清理
  },
  
  methods: {
    async loadVideoDetail() {
      try {
        // 精确获取目标视频元信息，避免分页导致的漏查
        const response = await videoApi.getVideoMeta(this.filename)
        
        if (response.data.success) {
          const video = response.data.data
          this.videoInfo = video
          this.videoSrc = videoApi.getVideoStreamUrl(this.filename)
          this.videoPoster = videoApi.getVideoPosterUrl(this.filename)
          this.fileSize = video.size_formatted
          this.modifyTime = video.mtime_formatted
        } else {
          throw new Error(response.data.error || '获取视频信息失败')
        }
      } catch (err) {
        this.error = err.message
        this.$message.error('视频信息加载失败：' + err.message)
      }
    },
    
    goBack() {
      this.$router.push('/')
    },
    
    handlePlayerReady(player) {
      // 播放器准备好，清除错误状态
      this.error = null
    },
    
    async handlePlayerError(error) {
      console.error('Video player error:', error)
      
      // 添加延迟检查，避免显示误报的错误
      setTimeout(async () => {
        // 检查视频是否实际上正在播放或可以播放
        const player = this.$refs.videoPlayerRef?.player
        if (player) {
          const isPlaying = !player.paused()
          const readyState = player.readyState()
          const videoElement = player.el().querySelector('video')
          const canPlay = videoElement && videoElement.readyState >= 2
          const networkState = videoElement ? videoElement.networkState : 0
          
          // 网络加载中（networkState === 2）时不认为是错误
          if (networkState === 2) {
            console.log('视频正在加载中，忽略暂时错误')
            this.error = null
            return
          }
          
          // 如果视频可以播放，忽略错误（可能是误报）
          if (isPlaying || canPlay || readyState >= 2) {
            console.log('错误为误报，视频可以正常播放')
            this.error = null
            return
          }
        }
        
        // 确认是真实错误，检查视频文件
        await this.checkVideoFile()
        
        // 显示错误信息
        if (error && error.code === 4) {
          this.error = '视频格式不支持或文件已损坏'
        } else if (error && error.message) {
          this.error = `视频播放错误: ${error.message}`
        } else {
          this.error = '视频播放出错，请检查文件是否存在或格式是否支持'
        }
      }, 2000) // 增加延迟到 2 秒，给大文件更多加载时间
    },
    
    async checkVideoFile() {
      this.isCheckingVideo = true
      try {
        const response = await fetch(`${videoApi.getVideoStreamUrl(this.filename)}/check`)
        const result = await response.json()
        
        if (result.success) {
          this.videoCheckResult = result.data
          console.log('视频检查结果:', result.data)
        }
      } catch (err) {
        console.error('检查视频失败:', err)
      } finally {
        this.isCheckingVideo = false
      }
    },
    
    handleVideoEnded() {
      this.$notify({
        title: '播放完成',
        message: '视频播放已结束',
        type: 'success',
        duration: 3000,
        position: 'top-right'
      })
    }
  }
}
</script>

<style scoped>
.video-detail-page {
  min-height: 100vh;
  background: var(--bg-page);
  padding: 12px 0 16px;
}

.detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.detail-topbar {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.back-button {
  height: 34px;
  border-radius: 8px;
  flex-shrink: 0;
}

.topbar-title-group {
  min-width: 0;
}

.page-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
  line-height: 1.35;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-subtitle {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 12px;
  align-items: start;
}

.player-section {
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.video-info-card {
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-default);
  position: sticky;
  top: 14px;
}

.card-header {
  display: flex;
  align-items: center;
}

.video-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}

.video-meta {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 2px 0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #4b5563;
  min-width: 0;
}

.meta-item .el-icon {
  font-size: 16px;
  color: #9ca3af;
}

.meta-label {
  font-weight: 500;
  width: 64px;
  flex-shrink: 0;
}

.meta-value {
  color: var(--text-primary);
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.error-container {
  margin-top: 10px;
}

.error-alert {
  margin-bottom: 10px;
}

.check-result-card {
  border: 1px solid #fecaca;
  background: #fff7f7;
  border-radius: var(--radius-lg);
}

.check-result-card h3,
.check-result-card h4 {
  margin: 0;
  color: #7f1d1d;
}

.check-result-card h4 {
  margin-bottom: 6px;
  font-size: 14px;
}

.issues-list ul,
.encoding-tips ol,
.suggestions ul {
  margin: 0;
  padding-left: 18px;
}

.issues-list li,
.encoding-tips li,
.suggestions li {
  margin-bottom: 6px;
  line-height: 1.45;
  color: #374151;
}

.encoding-tips code {
  display: inline-block;
  white-space: normal;
  word-break: break-word;
  padding: 2px 6px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #111827;
}

.large-file-notice {
  margin-top: 8px;
  font-size: 13px;
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 6px;
}

.suggestions {
  margin-top: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 10px;
}

.suggestions h4 {
  margin: 0 0 8px;
  color: var(--text-primary);
  font-size: 14px;
}

@media (max-width: 1100px) {
  .detail-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .video-info-card {
    position: static;
  }
}

@media (max-width: 768px) {
  .video-detail-page {
    padding: 10px 0 14px;
  }

  .detail-container {
    padding: 0 12px;
  }

  .detail-topbar {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .back-button {
    width: 100%;
    justify-content: center;
  }

  .page-title {
    font-size: 16px;
    white-space: normal;
    overflow-wrap: anywhere;
  }

  .detail-layout {
    gap: 10px;
  }

  .video-title {
    font-size: 15px;
  }

  .meta-item {
    font-size: 14px;
    align-items: flex-start;
  }

  .meta-item .el-icon {
    margin-top: 2px;
  }

  .meta-label {
    width: 56px;
  }

  .meta-value {
    white-space: normal;
    overflow-wrap: anywhere;
  }
}
</style>
