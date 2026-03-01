<template>
  <div class="page-header">
    <div class="header-content">
      <div class="header-left">
        <h1 class="title">
          <el-icon class="icon"><VideoCamera /></el-icon>
          本地视频浏览器
        </h1>
      </div>
      
      <div class="header-right" v-if="showControls">
        <el-input
          v-model="searchValue"
          placeholder="搜索视频..."
          class="search-input"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
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
          <el-option label="每页 12 个" :value="12" />
          <el-option label="每页 24 个" :value="24" />
          <el-option label="每页 48 个" :value="48" />
        </el-select>
        
        <el-tag type="info" size="large" class="video-count">
          共 {{ totalVideos }} 个视频
        </el-tag>
      </div>
    </div>
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
    }
  },
  
  data() {
    return {
      searchValue: '',
      sortValue: 'name',
      pageSizeValue: 12
    }
  },
  
  methods: {
    handleSearch() {
      this.$emit('search', this.searchValue)
    },
    
    handleSort() {
      this.$emit('sort', this.sortValue)
    },
    
    handlePageSizeChange() {
      this.$emit('page-size-change', this.pageSizeValue)
    }
  }
}
</script>

<style scoped>
.page-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon {
  font-size: 28px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.search-input {
  width: 250px;
}

.sort-select,
.page-size-select {
  width: 140px;
}

.video-count {
  font-size: 14px;
  font-weight: 500;
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-right {
    width: 100%;
    justify-content: flex-start;
  }
  
  .search-input {
    width: 100%;
    max-width: 300px;
  }
}
</style>
