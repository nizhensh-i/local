<template>
  <el-card class="video-card" shadow="hover" @click="handleClick">
    <div class="video-thumbnail">
      <img class="thumbnail-image" :src="posterSrc" :alt="video.name" loading="lazy" />

      <!-- <div class="play-overlay">
        <el-icon class="play-icon"><i-ep-VideoPlay /></el-icon>
      </div> -->
    </div>

    <div class="video-info">
      <h3 class="video-name" :title="video.name">{{ video.name }}</h3>

      <div class="video-meta">
        <span class="meta-text" :title="video.mtime_formatted">{{ video.mtime_formatted }}</span>
      </div>
    </div>
  </el-card>
</template>

<script>
import { videoApi } from '../api/video'

export default {
  name: 'VideoCard',

  props: {
    video: {
      type: Object,
      required: true
    }
  },

  computed: {
    posterSrc() {
      return videoApi.getVideoPosterUrl(this.video.name)
    }
  },

  methods: {
    handleClick() {
      this.$router.push({
        name: 'videoDetail',
        params: { filename: this.video.name },
        query: { id: this.video.id }
      })
    }
  }
}
</script>

<style scoped>
.video-card {
  cursor: pointer;
  transition: transform var(--motion-fast) ease, box-shadow var(--motion-fast) ease;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  overflow: hidden;
  min-width: 0;
  background: var(--bg-surface);
}

.video-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-soft);
}

.video-card:hover .play-overlay {
  opacity: 1;
}

.video-card:hover .play-icon {
  transform: scale(1.06);
}

.video-card :deep(.el-card__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
}

.video-thumbnail {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #e2e8f0;
  overflow: hidden;
}

.thumbnail-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.play-overlay {
  position: absolute;
  inset: 0;
  background: rgba(17, 24, 39, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--motion-fast) ease;
}

.play-icon {
  font-size: 34px;
  color: #ffffff;
  transition: transform var(--motion-fast) ease;
}

.video-info {
  padding: 11px 10px 10px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.video-name {
  margin: 0;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.4;
  font-weight: 600;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.video-meta {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.4;
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 6px;
}

.meta-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .play-overlay {
    opacity: 1;
    background: rgba(17, 24, 39, 0.2);
  }

  .play-icon {
    font-size: 30px;
  }

  .video-info {
    padding: 10px 9px 9px;
    gap: 7px;
  }

  .video-name {
    font-size: 13px;
  }
}
</style>
