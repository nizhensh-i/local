<template>
  <div class="video-player-container">
    <div class="video-wrapper">
      <video
        ref="videoPlayer"
        class="video-js vjs-big-play-centered vjs-theme-city"
        controls
        preload="auto"
        :poster="poster"
        data-setup='{}'
      >
        <source :src="src" :type="type" />
        <p class="vjs-no-js">
          要查看此视频，请启用 JavaScript，并考虑升级到支持 HTML5 视频的网络浏览器。
        </p>
      </video>
    </div>
    
    <div v-if="error" class="error-message">
      <el-alert :title="error" type="error" show-icon :closable="false" />
    </div>
  </div>
</template>

<script>
import videojs from 'video.js'

export default {
  name: 'VideoPlayer',
  
  props: {
    src: {
      type: String,
      required: true
    },
    type: {
      type: String,
      default: 'video/mp4'
    },
    poster: {
      type: String,
      default: ''
    },
    options: {
      type: Object,
      default: () => ({})
    }
  },
  
  data() {
    return {
      player: null,
      error: null
    }
  },
  
  mounted() {
    this.initPlayer()
  },
  
  beforeUnmount() {
    this.disposePlayer()
  },
  
  methods: {
    initPlayer() {
      if (!this.$refs.videoPlayer) return
      
      // 增加大文件支持的超时时间
      const defaultOptions = {
        controls: true,
        autoplay: false,
        preload: 'auto',
        fluid: true,
        responsive: true,
        playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
        html5: {
          vhs: {
            // 启用 HTTP 流式传输支持
            overrideNative: true,
            enableLowInitialPlaylist: false,
            smoothQualityChange: true,
            bandwidth: 4194304 // 4MB/s
          },
          nativeVideoTracks: false,
          nativeAudioTracks: false,
          nativeTextTracks: false,
          handlePartialData: true
        },
        controlBar: {
          children: [
            'playToggle',
            'volumePanel',
            'currentTimeDisplay',
            'timeDivider',
            'durationDisplay',
            'progressControl',
            'playbackRateMenuButton',
            'fullscreenToggle'
          ]
        }
      }
      
      const playerOptions = {
        ...defaultOptions,
        ...this.options,
        sources: [{
          src: this.src,
          type: this.type
        }]
      }
      
      try {
        this.player = videojs(this.$refs.videoPlayer, playerOptions, () => {
          this.$emit('ready', this.player)
          this.loadProgress()
        })
        
        // 监听错误事件 - 增加延迟时间，避免大文件误报
        this.player.on('error', (e) => {
          const error = this.player.error()
          
          // 对大文件增加延迟检查时间
          setTimeout(() => {
            // 检查是否真的无法播放
            const playerReady = this.player.readyState()
            const videoElement = this.player.el().querySelector('video')
            const canPlay = videoElement && videoElement.readyState >= 2
            const networkState = videoElement ? videoElement.networkState : 0
            
            // 网络加载中（networkState === 2）时不认为是错误
            if (networkState === 2) {
              console.log('视频正在加载中，忽略暂时错误')
              this.error = null
              if (this.player) this.player.error(null)
              return
            }
            
            // 如果视频可以播放，忽略错误（可能是误报）
            if (canPlay || playerReady >= 2) {
              console.warn('Video.js 误报错误，视频可以正常播放:', error)
              if (this.player) this.player.error(null)
              this.error = null
              return
            }
            
            // 确认是真实错误
            if (error && error.code === 4) { // MEDIA_ERR_SRC_NOT_SUPPORTED
              // 检查是否是编码问题
              console.error('视频格式不支持，检查视频编码:', error)
              this.error = `视频格式不支持: ${error.message}。请确保视频使用 H.264 编码。`
              this.$emit('error', error)
            } else if (error) {
              this.error = `视频播放错误: ${error.message}`
              this.$emit('error', error)
            }
          }, 2000) // 对大文件增加延迟到 2 秒
        })
        
        // 监听播放开始，清除错误状态
        this.player.on('play', () => {
          // 如果视频能播放，清除之前的错误
          this.error = null
          if (this.player.error()) {
            this.player.error(null)
          }
        })
        
        // 监听加载开始
        this.player.on('loadstart', () => {
          // 开始加载时清除错误状态
          this.error = null
        })
        
        // 监听加载进度
        this.player.on('loadeddata', () => {
          // 数据加载成功，清除错误
          this.error = null
          if (this.player.error()) {
            this.player.error(null)
          }
        })
        
        // 监听播放进度，保存到 localStorage
        this.player.on('timeupdate', () => {
          this.saveProgress()
        })
        
        // 监听视频结束
        this.player.on('ended', () => {
          this.clearProgress()
          this.$emit('ended')
        })
        
      } catch (err) {
        this.error = `初始化播放器失败: ${err.message}`
        console.error('VideoPlayer init error:', err)
      }
    },
    
    disposePlayer() {
      if (this.player) {
        this.player.dispose()
        this.player = null
      }
    },
    
    saveProgress() {
      if (!this.player || !this.src) return
      
      const currentTime = this.player.currentTime()
      const duration = this.player.duration()
      
      if (duration > 0 && currentTime < duration - 5) { // 不保存接近结尾的进度
        const videoId = this.getVideoId()
        const progressData = {
          currentTime,
          duration,
          timestamp: Date.now()
        }
        localStorage.setItem(`video_progress_${videoId}`, JSON.stringify(progressData))
      }
    },
    
    loadProgress() {
      if (!this.player) return
      
      const videoId = this.getVideoId()
      const saved = localStorage.getItem(`video_progress_${videoId}`)
      
      if (saved) {
        try {
          const progressData = JSON.parse(saved)
          const daysSinceSaved = (Date.now() - progressData.timestamp) / (1000 * 60 * 60 * 24)
          
          // 只加载一周内的进度
          if (daysSinceSaved < 7) {
            this.player.currentTime(progressData.currentTime)
            
            this.$notify({
              title: '继续播放',
              message: `从 ${this.formatTime(progressData.currentTime)} 继续播放`,
              type: 'info',
              duration: 3000,
              position: 'top-right'
            })
          }
        } catch (e) {
          console.warn('Failed to load progress:', e)
        }
      }
    },
    
    clearProgress() {
      const videoId = this.getVideoId()
      localStorage.removeItem(`video_progress_${videoId}`)
    },
    
    getVideoId() {
      // 从 URL 中提取视频 ID 或文件名
      const url = new URL(this.src)
      const filename = url.pathname.split('/').pop()
      return this.$route.query.id || filename
    },
    
    formatTime(seconds) {
      const minutes = Math.floor(seconds / 60)
      const secs = Math.floor(seconds % 60)
      return `${minutes}:${secs.toString().padStart(2, '0')}`
    },
    
    play() {
      if (this.player) {
        this.player.play()
      }
    },
    
    pause() {
      if (this.player) {
        this.player.pause()
      }
    }
  },
  
  watch: {
    src(newSrc) {
      if (this.player && newSrc) {
        this.error = null
        this.player.src({ src: newSrc, type: this.type })
        this.player.load()
        this.clearProgress()
      }
    }
  }
}
</script>

<style scoped>
.video-player-container {
  width: 100%;
}

.video-wrapper {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.video-wrapper :deep(.video-js) {
  width: 100%;
  height: auto;
  aspect-ratio: 16/9;
  font-size: 14px;
}

.video-wrapper :deep(.vjs-control-bar) {
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
}

.error-message {
  margin-top: 20px;
}

@media (max-width: 768px) {
  .video-wrapper :deep(.video-js) {
    font-size: 12px;
  }
  
  .video-wrapper :deep(.vjs-control-bar) {
    height: 3em;
  }
}
</style>
