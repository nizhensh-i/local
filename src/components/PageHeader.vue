<template>
  <div class="page-header">
    <div class="header-shell">
      <div class="header-top">
        <div>
          <h1 class="title">
            <el-icon class="icon"><i-ep-VideoCamera /></el-icon>
            本地视频播放器
          </h1>
          <p class="subtitle">浏览并筛选本地视频文件</p>
        </div>
      </div>

      <div class="header-controls" v-if="showControls">
        <div class="header-actions">
          <el-button
            v-if="showFolderButton"
            type="primary"
            class="folder-button"
            @click="handleSelectFolder"
          >
            <el-icon><i-ep-FolderOpened /></el-icon>
            选择文件夹
          </el-button>

          <el-button
            type="info"
            plain
            class="address-button"
            @click="handleShowAddress"
          >
            <el-icon><i-ep-Share /></el-icon>
            连接地址
          </el-button>
        </div>

        <div class="mobile-filter-bar" v-if="isMobile">
          <el-tag type="info" effect="plain" class="video-count mobile-count">
            共 {{ totalVideos }} 个视频
          </el-tag>
          <el-button class="filter-toggle" @click="mobileFilterVisible = true">
            筛选条件
            <span v-if="activeFilterCount > 0" class="filter-badge">
              {{ activeFilterCount }}
            </span>
          </el-button>
        </div>

        <div class="filter-row" v-else>
          <div class="filter-main">
            <el-input
              v-model="searchValue"
              placeholder="搜索视频文件名"
              class="search-input"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><i-ep-Search /></el-icon>
              </template>
            </el-input>

            <el-select
              v-model="sortValue"
              placeholder="排序方式"
              class="sort-select"
              @change="handleSort"
            >
              <el-option label="按名称" value="name" />
              <el-option label="按大小" value="size" />
              <el-option label="按修改时间" value="mtime" />
            </el-select>

            <el-select
              v-model="pageSizeValue"
              placeholder="每页数量"
              class="page-size-select"
              @change="handlePageSizeChange"
            >
              <el-option label="12 / 页" :value="12" />
              <el-option label="24 / 页" :value="24" />
              <el-option label="48 / 页" :value="48" />
            </el-select>
          </div>

          <div class="filter-meta">
            <el-tag type="info" effect="plain" size="large" class="video-count">
              共 {{ totalVideos }} 个视频
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <el-drawer
      v-model="mobileFilterVisible"
      direction="btt"
      size="72%"
      :with-header="false"
      class="mobile-filter-drawer"
    >
      <div class="mobile-filter-panel">
        <div class="mobile-filter-header">
          <h3>筛选条件</h3>
          <el-button text @click="resetMobileFilters">重置</el-button>
        </div>

        <div class="mobile-filter-body">
          <el-input
            v-model="searchValue"
            placeholder="搜索视频文件名"
            class="search-input"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><i-ep-Search /></el-icon>
            </template>
          </el-input>

          <el-select
            v-model="sortValue"
            placeholder="排序方式"
            class="sort-select"
            @change="handleSort"
          >
            <el-option label="按名称" value="name" />
            <el-option label="按大小" value="size" />
            <el-option label="按修改时间" value="mtime" />
          </el-select>

          <el-select
            v-model="pageSizeValue"
            placeholder="每页数量"
            class="page-size-select"
            @change="handlePageSizeChange"
          >
            <el-option label="12 / 页" :value="12" />
            <el-option label="24 / 页" :value="24" />
            <el-option label="48 / 页" :value="48" />
          </el-select>
        </div>

        <el-button type="primary" class="mobile-filter-close" @click="mobileFilterVisible = false">
          完成
        </el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script>
export default {
  name: 'PageHeader',

  props: {
    showControls: {
      type: Boolean,
      default: true
    },
    totalVideos: {
      type: Number,
      default: 0
    },
    showFolderButton: {
      type: Boolean,
      default: false
    }
  },

  data() {
    return {
      searchValue: '',
      sortValue: 'name',
      pageSizeValue: 12,
      isMobile: window.innerWidth <= 768,
      mobileFilterVisible: false
    }
  },

  computed: {
    activeFilterCount() {
      let count = 0
      if (this.searchValue.trim()) count += 1
      if (this.sortValue !== 'name') count += 1
      if (this.pageSizeValue !== 12) count += 1
      return count
    }
  },

  mounted() {
    window.addEventListener('resize', this.handleResize)
  },

  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
  },

  methods: {
    handleResize() {
      this.isMobile = window.innerWidth <= 768
      if (!this.isMobile) {
        this.mobileFilterVisible = false
      }
    },

    handleSearch() {
      this.$emit('search', this.searchValue)
    },

    handleSort() {
      this.$emit('sort', this.sortValue)
    },

    handlePageSizeChange() {
      this.$emit('page-size-change', this.pageSizeValue)
    },

    handleSelectFolder() {
      this.$emit('select-folder')
    },

    handleShowAddress() {
      this.$emit('show-address')
    },

    resetMobileFilters() {
      this.searchValue = ''
      this.sortValue = 'name'
      this.pageSizeValue = 12
      this.handleSearch()
      this.handleSort()
      this.handlePageSizeChange()
    }
  }
}
</script>

<style scoped>
.page-header {
  background: #f8fafc;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-default);
  margin-bottom: 20px;
}

.header-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 20px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}

.icon {
  font-size: 24px;
  color: #2563eb;
}

.subtitle {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 14px;
}

.header-controls {
  display: grid;
  gap: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.mobile-filter-bar {
  display: none;
}

.filter-row {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.filter-main {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 160px 130px;
  gap: 10px;
}

.filter-meta {
  flex-shrink: 0;
}

.search-input,
.sort-select,
.page-size-select {
  width: 100%;
}

.folder-button,
.address-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  border-radius: 8px;
}

.video-count {
  font-size: 13px;
  font-weight: 500;
  height: 34px;
  line-height: 32px;
}

.filter-toggle {
  height: 34px;
  border-radius: 8px;
}

.filter-badge {
  margin-left: 8px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #ffffff;
  background: #2563eb;
}

.mobile-filter-panel {
  display: grid;
  gap: 12px;
}

.mobile-filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mobile-filter-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.mobile-filter-body {
  display: grid;
  gap: 10px;
}

.mobile-filter-close {
  height: 36px;
}

:deep(.mobile-filter-drawer .el-drawer__body) {
  padding: 12px;
}

:deep(.search-input .el-input__wrapper),
:deep(.sort-select .el-select__wrapper),
:deep(.page-size-select .el-select__wrapper) {
  min-height: 36px;
  border-radius: 8px;
}

@media (max-width: 1024px) {
  .filter-main {
    grid-template-columns: minmax(200px, 1fr) 150px 120px;
  }
}

@media (max-width: 768px) {
  .header-shell {
    padding: 12px 12px;
  }

  .header-top {
    margin-bottom: 8px;
  }

  .title {
    font-size: 18px;
  }

  .subtitle {
    margin-top: 4px;
    font-size: 12px;
  }

  .header-actions {
    width: 100%;
  }

  .filter-row {
    display: none;
  }

  .mobile-filter-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mobile-count {
    min-width: 0;
  }

  .filter-main {
    width: 100%;
    grid-template-columns: 1fr;
  }

  .sort-select,
  .page-size-select {
    max-width: none;
  }

  .filter-meta {
    width: 100%;
  }

  .video-count {
    width: 100%;
    justify-content: center;
  }

  .folder-button,
  .address-button {
    flex: 1;
    justify-content: center;
    min-width: 0;
  }
}

@media (max-width: 420px) {
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
