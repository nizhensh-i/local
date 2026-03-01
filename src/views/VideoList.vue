<template>
  <div class="video-list-page">
    <PageHeader
      :total-videos="pagination.total"
      @search="handleSearch"
      @sort="handleSort"
      @page-size-change="handlePageSizeChange"
    />
    
    <div class="content-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="6" animated />
        <el-skeleton :rows="6" animated />
      </div>
      
      <!-- 空状态 -->
      <div v-else-if="videos.length === 0" class="empty-container">
        <el-empty :description="emptyText">
          <template #default>
            <el-button
              v-if="!searchKeyword"
              type="primary"
              @click="handleRefresh"
              :loading="refreshing"
            >
              刷新列表
            </el-button>
          </template>
        </el-empty>
      </div>
      
      <!-- 视频网格 -->
      <div v-else class="video-grid">
        <transition-group name="video-list" tag="div" class="grid-container">
          <div
            v-for="video in videos"
            :key="video.id"
            class="video-grid-item"
          >
            <VideoCard :video="video" />
          </div>
        </transition-group>
        
        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="pagination.total"
            :page-sizes="[12, 24, 48]"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>
      
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
import PageHeader from '../components/PageHeader.vue'
import VideoCard from '../components/VideoCard.vue'
import { videoApi } from '../api/video'

export default {
  name: 'VideoList',
  
  components: {
    PageHeader,
    VideoCard
  },
  
  data() {
    return {
      videos: [],
      loading: false,
      refreshing: false,
      error: null,
      searchKeyword: '',
      currentPage: 1,
      pageSize: 12,
      sortBy: 'name',
      pagination: {
        total: 0,
        page: 1,
        page_size: 12,
        total_pages: 1
      }
    }
  },
  
  computed: {
    emptyText() {
      if (this.searchKeyword) {
        return `未找到包含 "${this.searchKeyword}" 的视频`
      }
      return '暂无视频文件'
    }
  },
  
  mounted() {
    this.fetchVideos()
  },
  
  methods: {
    async fetchVideos() {
      this.loading = true
      this.error = null
      
      try {
        const params = {
          page: this.currentPage,
          page_size: this.pageSize,
          sort: this.sortBy
        }
        
        if (this.searchKeyword) {
          params.keyword = this.searchKeyword
        }
        
        const response = await videoApi.getVideos(params)
        
        if (response.data.success) {
          const videos = response.data.data?.videos || []
          const pagination = response.data.data?.pagination || {
            total: 0,
            page: 1,
            page_size: this.pageSize,
            total_pages: 1
          }
          this.videos = videos
          this.pagination = pagination
        } else {
          throw new Error(response.data.error || '获取视频列表失败')
        }
      } catch (err) {
        this.error = err.message
        this.$message.error('获取视频列表失败: ' + err.message)
      } finally {
        this.loading = false
      }
    },
    
    handleSearch(keyword) {
      this.searchKeyword = keyword
      this.currentPage = 1
      this.fetchVideos()
    },
    
    handleSort(sort) {
      this.sortBy = sort
      this.fetchVideos()
    },
    
    handlePageSizeChange(pageSize) {
      this.pageSize = pageSize
      this.currentPage = 1
      this.fetchVideos()
    },
    
    handlePageChange(page) {
      this.currentPage = page
      this.fetchVideos()
      
      // 滚动到顶部
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    },
    
    async handleRefresh() {
      this.refreshing = true
      try {
        await videoApi.refreshCache()
        this.fetchVideos()
        this.$message.success('视频列表已刷新')
      } catch (err) {
        this.$message.error('刷新失败: ' + err.message)
      } finally {
        this.refreshing = false
      }
    }
  }
}
</script>

<style scoped>
.video-list-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.content-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px 40px 20px;
}

.loading-container {
  padding: 40px 20px;
}

.empty-container {
  padding: 60px 20px;
  display: flex;
  justify-content: center;
}

.video-grid {
  margin-top: 20px;
}

.grid-container {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 40px;
}

.video-grid-item {
  min-width: 0;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 40px;
}

.error-alert {
  margin-top: 20px;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .grid-container {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 992px) {
  .grid-container {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }
}

@media (max-width: 768px) {
  .content-container {
    padding: 0 15px 30px 15px;
  }
  
  .grid-container {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .pagination-container {
    margin-top: 30px;
  }
}

/* 动画效果 */
.video-list-enter-active,
.video-list-leave-active {
  transition: all 0.5s ease;
}

.video-list-enter-from {
  opacity: 0;
  transform: translateY(30px);
}

.video-list-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.video-list-leave-active {
  position: absolute;
}
</style>
