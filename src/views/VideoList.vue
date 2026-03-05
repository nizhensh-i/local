<template>
  <div class="video-list-page">
    <PageHeader
      :total-videos="pagination.total"
      :show-folder-button="isTauri"
      @search="handleSearch"
      @sort="handleSort"
      @page-size-change="handlePageSizeChange"
      @select-folder="handleSelectFolder"
      @show-address="handleShowAddress"
    />
    
    <div class="content-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <div class="loading-surface">
          <el-skeleton :rows="6" animated />
        </div>
        <div class="loading-surface">
          <el-skeleton :rows="6" animated />
        </div>
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
            :layout="paginationLayout"
            size="small"
            background
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>
      
      <!-- 本地错误提示（非全局） -->
      <el-alert
        v-if="error"
        :title="listErrorTitle"
        type="error"
        show-icon
        closable
        @close="error = null"
        class="error-alert"
      />
    </div>

    <el-dialog
      v-model="addressDialogVisible"
      title="局域网连接地址"
      :width="addressDialogWidth"
      class="address-dialog"
    >
      <el-skeleton v-if="addressLoading" :rows="4" animated />
      <div v-else>
        <p class="address-tip">可在同一局域网设备打开以下地址：</p>
        <el-empty v-if="frontendUrls.length === 0" description="未检测到可用局域网 IP" />
        <el-space
          v-else
          direction="vertical"
          alignment="stretch"
          style="width: 100%;"
        >
          <el-alert
            v-for="url in frontendUrls"
            :key="url"
            :title="url"
            type="success"
            :closable="false"
            show-icon
            class="url-alert"
          />
        </el-space>
        <p class="address-note">
          若无法访问，请检查本机防火墙与端口放行设置。
        </p>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import PageHeader from '../components/PageHeader.vue'
import VideoCard from '../components/VideoCard.vue'
import { videoApi } from '../api/video'
import { isTauriRuntime } from '../utils/tauri'

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
      toastTimestamps: {},
      searchKeyword: '',
      currentPage: 1,
      pageSize: 12,
      sortBy: 'name',
      isMobile: window.innerWidth <= 768,
      isTauri: isTauriRuntime(),
      pagination: {
        total: 0,
        page: 1,
        page_size: 12,
        total_pages: 1
      },
      addressDialogVisible: false,
      addressLoading: false,
      frontendUrls: []
    }
  },
  
  computed: {
    emptyText() {
      if (this.searchKeyword) {
        return `未找到与“${this.searchKeyword}”相关的视频，请尝试更短关键词。`
      }
      return '当前目录暂无可播放视频'
    },
    listErrorTitle() {
      return `列表加载失败：${this.error}`
    },
    paginationLayout() {
      return this.isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next, jumper'
    },
    addressDialogWidth() {
      return this.isMobile ? '92vw' : '560px'
    }
  },
  
  mounted() {
    window.addEventListener('resize', this.handleResize)
    this.fetchVideos()
  },

  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
  },
  
  methods: {
    getErrorMessage(err) {
      if (err && typeof err === 'object') {
        const responseError = err.response?.data?.error
        if (typeof responseError === 'string' && responseError.trim()) {
          return responseError
        }
      }
      if (err && typeof err === 'object' && typeof err.message === 'string') {
        return err.message
      }
      if (typeof err === 'string') {
        return err
      }
      try {
        return JSON.stringify(err)
      } catch {
        return String(err)
      }
    },

    toastOnce(key, type, message, cooldownMs = 4000) {
      const now = Date.now()
      const lastAt = this.toastTimestamps[key] || 0
      if (now - lastAt < cooldownMs) return
      this.toastTimestamps[key] = now
      this.$message[type](message)
    },

    handleResize() {
      this.isMobile = window.innerWidth <= 768
    },
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
        const message = this.getErrorMessage(err)
        this.error = message
        this.toastOnce('fetchVideos', 'error', '列表加载失败，请稍后重试：' + message)
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
        this.$message.success('列表已更新')
      } catch (err) {
        const message = this.getErrorMessage(err)
        this.toastOnce('refresh', 'error', '列表刷新失败：' + message)
      } finally {
        this.refreshing = false
      }
    },

    async handleSelectFolder() {
      if (!this.isTauri) {
        // use a toast so the message appears at the top of the window
        this.$message.warning('当前运行环境不支持选择本地文件夹')
        return
      }

      try {
        const { open } = await import('@tauri-apps/plugin-dialog')
        const { writeTextFile, exists, mkdir } = await import('@tauri-apps/plugin-fs')
        const { BaseDirectory, appDataDir } = await import('@tauri-apps/api/path')

        const selected = await open({
          directory: true,
          multiple: false,
          title: '选择视频文件夹'
        })

        if (!selected) {
          return
        }

        const folderPath = Array.isArray(selected) ? selected[0] : selected
        
        // Verify the directory exists
        try {
          const dirExists = await exists(folderPath)
          if (!dirExists) {
            throw new Error('选中的目录不存在')
          }
        } catch (verifyErr) {
          console.warn('Directory verification skipped:', verifyErr)
        }
        
        // Ensure AppData directory exists
        const appDataPath = await appDataDir()
        try {
          await mkdir(appDataPath, { recursive: true })
        } catch (mkdirErr) {
          console.warn('AppData directory might already exist:', mkdirErr)
        }
        
        const payload = JSON.stringify({ video_folder: folderPath }, null, 2)
        await writeTextFile('video_folder.json', payload, { 
          baseDir: BaseDirectory.AppData 
        })

        // Refresh cache and reload videos using server response instead of fixed delays
        const refreshResponse = await videoApi.refreshCache()
        if (refreshResponse?.data?.success) {
          await this.fetchVideos()
          if (this.videos.length === 0) {
            this.$message.info('目录更新成功，但未找到可播放视频')
          } else {
            this.$message.success(`目录更新成功，已加载 ${this.videos.length} 个视频`)
          }
        } else {
          throw new Error(refreshResponse?.data?.error || '刷新视频目录失败')
        }
        
      } catch (err) {
        console.error('handleSelectFolder failed:', err)
        const message = this.getErrorMessage(err)
        // keep the detailed message in `error` so the alert can render it and also
        // show a global toast; the toast appears at the top and will auto‑dismiss.
        this.error = message
        this.$message.error('目录更新失败：' + message)
        this.toastOnce('selectFolder', 'error', '目录更新失败：' + message)
      }
    },

    async handleShowAddress() {
      this.addressDialogVisible = true
      this.addressLoading = true
      try {
        const currentPort = window.location.port || '3650'
        const response = await videoApi.getNetworkInfo(currentPort)
        if (response.data.success) {
          this.frontendUrls = response.data.data?.frontend_urls || []
        } else {
          throw new Error(response.data.error || '获取连接地址失败')
        }
      } catch (err) {
        const message = this.getErrorMessage(err)
        this.frontendUrls = []
        this.toastOnce('networkInfo', 'error', '获取连接地址失败：' + message)
      } finally {
        this.addressLoading = false
      }
    }
  }
}
</script>

<style scoped>
.video-list-page {
  min-height: 100vh;
  background: var(--bg-page);
  overflow-x: hidden;
}

.content-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 20px 24px;
}

.loading-container {
  padding: 20px 4px;
  display: grid;
  gap: 12px;
}

.loading-surface {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 14px;
}

.empty-container {
  padding: 48px 20px;
  display: flex;
  justify-content: center;
}

.video-grid {
  margin-top: 8px;
}

.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
  margin-bottom: 26px;
}

.video-grid-item {
  min-width: 0;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 14px;
  overflow-x: visible;
}

.error-alert {
  margin-bottom: 20px;
  border-radius: var(--radius-md);
}

.address-tip {
  margin-bottom: 12px;
  color: var(--text-primary);
}

.address-note {
  margin-top: 14px;
  color: var(--text-secondary);
  font-size: 13px;
  overflow-wrap: anywhere;
}

:deep(.address-dialog) {
  max-width: calc(100vw - 24px);
}

:deep(.url-alert .el-alert__title) {
  white-space: normal;
  word-break: break-all;
  line-height: 1.4;
}

@media (max-width: 1439px) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
}

@media (max-width: 1199px) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .content-container {
    padding: 0 12px 16px;
  }

  .video-grid {
    margin-top: 6px;
  }

  .grid-container {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 14px;
  }

  .pagination-container {
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 2px;
  }
}

@media (max-width: 359px) {
  .grid-container {
    grid-template-columns: 1fr;
  }
}

.video-list-enter-active,
.video-list-leave-active {
  transition: all var(--motion-base) ease;
}

.video-list-enter-from {
  opacity: 0;
  transform: translateY(16px);
}

.video-list-leave-to {
  opacity: 0;
  transform: scale(0.97);
}

.video-list-leave-active {
  position: absolute;
}
</style>
