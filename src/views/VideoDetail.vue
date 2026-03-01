<template>
  <div class="video-detail-page">
    <div class="detail-container">
      <!-- 返回按钮 -->
      <div class="back-button-container">
        <el-button @click="goBack" :icon="ArrowLeft" size="large" round>
          返回列表
        </el-button>
      </div>
      
      <!-- 视频播放器 -->
      <div class="player-section">
        <VideoPlayer
          :src="videoSrc"
          type="video/mp4"
          @ready="handlePlayerReady"
          @error="handlePlayerError"
          @ended="handleVideoEnded"
          ref="videoPlayerRef"
        />
      </div>
      
      <!-- 视频信息 -->
      <el-card class="video-info-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <h2 class="video-title">{{ filename }}</h2>
          </div>
        </template>
        
        <div class="video-meta">
          <div class="meta-item">
            <el-icon><Document /></el-icon>
            <span class="meta-label">文件大小：</span>
            <span class="meta-value">{{ fileSize }}</span>
          </div>
          
          <div class="meta-item">
            <el-icon><Clock /></el-icon>
            <span class="meta-label">修改时间：</span>
            <span class="meta-value">{{ modifyTime }}</span>
          </div>
        </div>
      </el-card>
      
      <!-- 错误提示 -->
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        closable
        @close="error = null"
        class="error-alert"
      />
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
      fileSize: '',
      modifyTime: '',
      error: null,
      videoInfo: null
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
        // 从 API 获取视频信息
        const response = await videoApi.getVideos({
          keyword: this.filename
        })
        
        if (response.data.success) {
          const videos = response.data.data.videos
          const video = videos.find(v => v.name === this.filename)
          
          if (video) {
            this.videoInfo = video
            this.videoSrc = videoApi.getVideoStreamUrl(this.filename)
            this.fileSize = video.size_formatted
            this.modifyTime = video.mtime_formatted
          } else {
            throw new Error('视频信息未找到')
          }
        } else {
          throw new Error(response.data.error || '获取视频信息失败')
        }
      } catch (err) {
        this.error = err.message
        this.$message.error('加载视频失败: ' + err.message)
      }
    },
    
    goBack() {
      this.$router.push('/')
    },
    
    handlePlayerReady(player) {
      // 播放器准备好，清除错误状态
      this.error = null
    },
    
    handlePlayerError(error) {
      console.error('Video player error:', error)
      
      // 添加延迟检查，避免显示误报的错误
      setTimeout(() => {
        // 检查视频是否实际上正在播放或可以播放
        const player = this.$refs.videoPlayerRef?.player
        if (player) {
          const isPlaying = !player.paused()
          const readyState = player.readyState()
          const videoElement = player.el().querySelector('video')
          const canPlay = videoElement && videoElement.readyState >= 2
          
          // 如果视频可以播放或正在播放，忽略错误（可能是误报）
          if (isPlaying || canPlay || readyState >= 2) {
            console.log('错误为误报，视频可以正常播放')
            this.error = null
            return
          }
        }
        
        // 确认是真实错误
        if (error && error.code === 4) {
          this.error = '视频格式不支持或文件已损坏'
        } else if (error && error.message) {
          this.error = `视频播放错误: ${error.message}`
        } else {
          this.error = '视频播放出错，请检查文件是否存在或格式是否支持'
        }
      }, 1000)
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
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 20px 0 40px 0;
}

.detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.back-button-container {
  margin-bottom: 20px;
}

.player-section {
  margin-bottom: 30px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.video-info-card {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
}

.video-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
}

.video-meta {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 10px 0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  color: #606266;
}

.meta-item .el-icon {
  font-size: 18px;
  color: #909399;
}

.meta-label {
  font-weight: 500;
  min-width: 80px;
}

.meta-value {
  color: #303133;
  font-weight: 500;
}

.error-alert {
  margin-top: 20px;
}

@media (max-width: 768px) {
  .video-detail-page {
    padding: 15px 0 30px 0;
  }
  
  .detail-container {
    padding: 0 15px;
  }
  
  .video-title {
    font-size: 18px;
  }
  
  .meta-item {
    font-size: 14px;
  }
  
  .meta-item .el-icon {
    font-size: 16px;
  }
  
  .meta-label {
    min-width: 70px;
  }
}
</style>
