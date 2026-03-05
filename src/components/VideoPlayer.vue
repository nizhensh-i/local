<template>
  <div class="video-player-container">
    <div class="video-wrapper" :class="{ 'player-ready': isPlayerReady }">
      <VueVideoPlayer
        ref="vuePlayerRef"
        class="vjs-big-play-centered"
        :src="src"
        :poster="poster"
        :controls="true"
        :autoplay="false"
        preload="auto"
        :fluid="true"
        :responsive="true"
        :playback-rates="[0.5, 0.75, 1, 1.25, 1.5, 2]"
        :html5="html5Options"
        :control-bar="controlBarOptions"
        @mounted="handleMounted"
        @ready="handleReady"
        @error="handlePlayerError"
        @play="handlePlayerPlay"
        @loadstart="clearPlayerError"
        @loadeddata="clearPlayerError"
        @timeupdate="saveProgress"
        @ended="handlePlayerEnded"
      />
    </div>

    <div v-if="error" class="error-message">
      <el-alert :title="error" type="error" show-icon :closable="false" />
    </div>
  </div>
</template>

<script>
import { VideoPlayer as VueVideoPlayer } from '@videojs-player/vue'

export default {
  name: 'VideoPlayer',

  components: {
    VueVideoPlayer
  },

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
      error: null,
      isPlayerReady: false
    }
  },

  computed: {
    html5Options() {
      return {
        vhs: {
          overrideNative: true,
          enableLowInitialPlaylist: false,
          smoothQualityChange: true,
          bandwidth: 4194304
        },
        nativeVideoTracks: false,
        nativeAudioTracks: false,
        nativeTextTracks: false,
        handlePartialData: true
      }
    },
    controlBarOptions() {
      return {
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
  },

  methods: {
    handleMounted(payload) {
      this.player = payload?.player || null
      this.isPlayerReady = false
    },

    handleReady() {
      this.isPlayerReady = true
      this.$emit('ready', this.player)
      this.loadProgress()
    },

    clearPlayerError() {
      this.error = null
      if (this.player && this.player.error()) {
        this.player.error(null)
      }
    },

    handlePlayerPlay() {
      this.clearPlayerError()
    },

    handlePlayerError() {
      const currentPlayer = this.player
      if (!currentPlayer) return

      const playerError = currentPlayer.error()
      setTimeout(() => {
        if (!this.player) return

        const videoElement = this.player.el()?.querySelector('video')
        const readyState = this.player.readyState()
        const canPlay = Boolean(videoElement && videoElement.readyState >= 2)
        const networkState = videoElement ? videoElement.networkState : 0

        if (networkState === 2 || canPlay || readyState >= 2) {
          this.clearPlayerError()
          return
        }

        if (playerError && playerError.code === 4) {
          this.error = `视频格式不支持: ${playerError.message}。请确保视频使用 H.264 编码。`
          this.$emit('error', playerError)
          return
        }

        if (playerError) {
          this.error = `视频播放错误: ${playerError.message}`
          this.$emit('error', playerError)
        }
      }, 2000)
    },

    handlePlayerEnded() {
      this.clearProgress()
      this.$emit('ended')
    },

    saveProgress() {
      if (!this.player || !this.src) return

      const currentTime = this.player.currentTime()
      const duration = this.player.duration()

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
      if (!this.player) return

      const videoId = this.getVideoId()
      const saved = localStorage.getItem(`video_progress_${videoId}`)

      if (saved) {
        try {
          const progressData = JSON.parse(saved)
          const daysSinceSaved = (Date.now() - progressData.timestamp) / (1000 * 60 * 60 * 24)

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
    src() {
      this.isPlayerReady = false
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
}

.video-wrapper :deep(.video-js) {
  width: 100%;
  height: auto;
  aspect-ratio: 16/9;
  font-size: 14px;
}

.video-wrapper :deep(.vjs-big-play-button) {
  top: 50% !important;
  left: 50% !important;
  transform: translate(-50%, -50%);
  margin: 0 !important;
  transition: none !important;
}

.video-wrapper:not(.player-ready) :deep(.vjs-big-play-button) {
  opacity: 0;
  pointer-events: none;
}

.video-wrapper.player-ready :deep(.vjs-big-play-button) {
  opacity: 1;
}

.video-wrapper :deep(.vjs-control-bar) {
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
}

.video-wrapper :deep(.vjs-current-time),
.video-wrapper :deep(.vjs-duration),
.video-wrapper :deep(.vjs-time-divider) {
  display: flex !important;
  align-items: center;
}

.video-wrapper :deep(.vjs-play-control .vjs-icon-placeholder::before) {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.video-wrapper :deep(.vjs-playing .vjs-play-control .vjs-icon-placeholder::before),
.video-wrapper :deep(.vjs-paused .vjs-play-control .vjs-icon-placeholder::before) {
  transform: scale(1);
}

.video-wrapper :deep(.vjs-play-control:hover .vjs-icon-placeholder::before) {
  transform: scale(1.08);
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
