<template>
  <div class="video-player-container">
    <div class="video-wrapper" :class="{ 'player-ready': isPlayerReady }">
      <video
        ref="videoElementRef"
        class="native-video"
        :src="src"
        :poster="poster"
        :preload="preload"
        controls
        playsinline
        @loadstart="handleLoadStart"
        @loadedmetadata="handleLoadedMetadata"
        @loadeddata="clearPlayerError"
        @canplay="handleCanPlay"
        @play="handlePlayerPlay"
        @timeupdate="saveProgress"
        @ended="handlePlayerEnded"
        @error="handlePlayerError"
      />
    </div>

    <div v-if="error" class="error-message">
      <el-alert :title="error" type="error" show-icon :closable="false" />
    </div>
  </div>
</template>

<script>
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
    },
    preload: {
      type: String,
      default: 'metadata'
    }
  },

  data() {
    return {
      player: null,
      error: null,
      isPlayerReady: false,
      progressLoaded: false
    }
  },

  mounted() {
    this.player = this.createPlayerFacade()
  },

  methods: {
    getVideoElement() {
      return this.$refs.videoElementRef || null
    },

    createPlayerFacade() {
      return {
        play: () => this.getVideoElement()?.play(),
        pause: () => this.getVideoElement()?.pause(),
        paused: () => {
          const video = this.getVideoElement()
          return video ? video.paused : true
        },
        readyState: () => {
          const video = this.getVideoElement()
          return video ? video.readyState : 0
        },
        error: () => this.getVideoElement()?.error || null,
        currentTime: (value) => {
          const video = this.getVideoElement()
          if (!video) return 0
          if (typeof value === 'number') {
            video.currentTime = value
          }
          return video.currentTime
        },
        duration: () => this.getVideoElement()?.duration || 0,
        el: () => this.$el
      }
    },

    handleLoadStart() {
      this.isPlayerReady = false
      this.progressLoaded = false
      this.clearPlayerError()
    },

    handleLoadedMetadata() {
      this.loadProgress()
    },

    handleCanPlay() {
      this.isPlayerReady = true
      this.clearPlayerError()
      this.$emit('ready', this.player)
    },

    clearPlayerError() {
      this.error = null
    },

    handlePlayerPlay() {
      this.clearPlayerError()
    },

    handlePlayerError() {
      const video = this.getVideoElement()
      if (!video) return

      const mediaError = video.error
      if (!mediaError) {
        return
      }

      if (mediaError.code === 4) {
        this.error = '视频格式不支持，请确保视频使用浏览器可播放的编码。'
      } else {
        this.error = `视频播放错误: ${mediaError.message || '未知错误'}`
      }

      this.$emit('error', mediaError)
    },

    handlePlayerEnded() {
      this.clearProgress()
      this.$emit('ended')
    },

    saveProgress() {
      const video = this.getVideoElement()
      if (!video || !this.src) return

      const currentTime = video.currentTime
      const duration = Number.isFinite(video.duration) ? video.duration : 0

      if (duration > 0 && currentTime < duration - 5) {
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
      if (this.progressLoaded) return

      const video = this.getVideoElement()
      if (!video) return

      const videoId = this.getVideoId()
      const saved = localStorage.getItem(`video_progress_${videoId}`)
      this.progressLoaded = true

      if (!saved) return

      try {
        const progressData = JSON.parse(saved)
        const daysSinceSaved = (Date.now() - progressData.timestamp) / (1000 * 60 * 60 * 24)

        if (daysSinceSaved < 7 && Number.isFinite(progressData.currentTime)) {
          video.currentTime = progressData.currentTime

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
    },

    clearProgress() {
      const videoId = this.getVideoId()
      localStorage.removeItem(`video_progress_${videoId}`)
    },

    getVideoId() {
      try {
        const url = new URL(this.src, window.location.href)
        const filename = decodeURIComponent(url.pathname.split('/').pop() || '')
        return this.$route.query.id || filename || this.src
      } catch (_) {
        return this.$route.query.id || this.src
      }
    },

    formatTime(seconds) {
      const minutes = Math.floor(seconds / 60)
      const secs = Math.floor(seconds % 60)
      return `${minutes}:${secs.toString().padStart(2, '0')}`
    },

    play() {
      this.getVideoElement()?.play()
    },

    pause() {
      this.getVideoElement()?.pause()
    }
  },

  watch: {
    src() {
      this.isPlayerReady = false
      this.progressLoaded = false
      this.clearPlayerError()
    }
  }
}
</script>

<style scoped>
.video-player-container {
  width: 100%;
}

.video-wrapper {
  position: relative;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background-color: #111827;
}

.native-video {
  width: 100%;
  height: 100%;
  aspect-ratio: 16 / 9;
  display: block;
  background-color: #111827;
}

.video-wrapper:not(.player-ready) .native-video {
  opacity: 0;
}

.video-wrapper.player-ready .native-video {
  opacity: 1;
}

.error-message {
  margin-top: 20px;
}
</style>
