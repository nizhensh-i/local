<template>
  <el-card class="video-card" shadow="hover" @click="handleClick">
    <div class="video-thumbnail">
      <video
        ref="thumbnailVideo"
        class="thumbnail-video"
        preload="metadata"
        muted
        :src="video.url"
      />
      
      <div class="play-overlay">
        <el-icon class="play-icon"><VideoPlay /></el-icon>
      </div>
    </div>
    
    <div class="video-info">
      <h3 class="video-name" :title="video.name">{{ truncatedName }}</h3>
      
      <div class="video-meta">
        <div class="meta-item">
          <el-icon><Document /></el-icon>
          <span>{{ video.size_formatted }}</span>
        </div>
        
        <div class="meta-item">
          <el-icon><Clock /></el-icon>
          <span>{{ video.mtime_formatted }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script>
export default {
  name: 'VideoCard',
  
  props: {
    video: {
      type: Object,
      required: true
    }
  },
  
  computed: {
    truncatedName() {
      const maxLength = 40
      if (this.video.name.length > maxLength) {
        return this.video.name.substring(0, maxLength) + '...'
      }
      return this.video.name
    }
  },
  
  mounted() {
    // 尝试获取视频第一帧作为封面
    this.loadThumbnail()
  },
  
  methods: {
    loadThumbnail() {
      const video = this.$refs.thumbnailVideo
      if (!video) return
      
      video.addEventListener('loadedmetadata', () => {
        // 设置一个较小的尺寸来显示缩略图
        video.style.width = '100%'
        video.style.height = '100%'
        video.style.objectFit = 'cover'
      })
      
      // 尝试加载第一帧
      video.currentTime = 0.1
    },
    
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
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.video-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.video-card:hover .play-overlay {
  opacity: 1;
}

.video-card:hover .play-icon {
  transform: scale(1.1);
}

.video-thumbnail {
  position: relative;
  width: 100%;
  height: 180px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
  border-radius: 4px;
}

.thumbnail-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.play-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.play-icon {
  font-size: 48px;
  color: white;
  transition: transform 0.3s ease;
}

.video-info {
  padding: 15px 0 0 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.video-name {
  margin: 0 0 10px 0;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  line-height: 1.4;
}

.video-meta {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.meta-item .el-icon {
  font-size: 14px;
}

@media (max-width: 768px) {
  .video-thumbnail {
    height: 160px;
  }
  
  .play-overlay {
    opacity: 1;
  }
  
  .play-icon {
    font-size: 36px;
  }
}
</style>
