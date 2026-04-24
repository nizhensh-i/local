<template>
  <div class="video-list-page">
    <PageHeader
      :total-videos="pagination.total"
      :show-folder-button="isTauri"
      folder-button-text="新增分类"
      @search="handleSearch"
      @sort="handleSort"
      @page-size-change="handlePageSizeChange"
      @select-folder="openCategoryDialog"
      @show-address="handleShowAddress"
      @show-settings="handleShowSettings"
    />

    <div class="content-container">
      <section v-if="categories.length > 0 || isTauri" class="category-toolbar-bar">
        <div class="category-toolbar-main">
          <el-tabs
            v-if="categories.length > 0"
            v-model="activeCategoryId"
            type="card"
            class="category-tabs"
            @tab-change="handleCategoryChange"
          >
            <el-tab-pane
              v-for="category in categories"
              :key="category.id"
              :name="category.id"
            >
              <template #label>
                <span class="category-tab-label">
                  <span class="category-tab-name">{{ category.name }}</span>
                  <el-button
                    v-if="isTauri"
                    text
                    class="category-tab-close"
                    @click.stop="removeCategory(category.id)"
                  >
                    <el-icon><i-ep-Close /></el-icon>
                  </el-button>
                </span>
              </template>
            </el-tab-pane>
          </el-tabs>

          <div v-if="activeCategoryId" class="category-toolbar-actions">
            <el-select
              v-model="activeSubfolder"
              class="subfolder-select"
              placeholder="筛选子文件夹"
              @change="handleSubfolderChange"
            >
              <el-option label="全部子文件夹" value="" />
              <el-option label="根目录" value="root" />
              <el-option
                v-for="folder in subfolderOptions"
                :key="folder"
                :label="folder"
                :value="folder"
              />
            </el-select>
          </div>
        </div>
      </section>

      <div v-if="!loading && categories.length === 0" class="empty-container">
        <div class="text-empty-state">
          <p class="text-empty-title">还没有分类</p>
          <p class="text-empty-description">先在宿主电脑上新建一个分类，并为它绑定本地视频文件夹。</p>
          <el-button
            v-if="isTauri"
            type="primary"
            @click="openCategoryDialog"
          >
            新增分类
          </el-button>
          <p v-else class="category-empty-note">当前设备仅支持浏览，新增分类请在宿主电脑上操作。</p>
        </div>
      </div>

      <div v-if="loading" class="loading-container">
        <div class="loading-surface">
          <el-skeleton :rows="6" animated />
        </div>
        <div class="loading-surface">
          <el-skeleton :rows="6" animated />
        </div>
      </div>

      <div v-else-if="categories.length > 0 && videos.length === 0" class="empty-container">
        <div class="text-empty-state text-empty-state--compact">
          <p class="text-empty-title">这个分类暂时空空的</p>
          <p class="text-empty-description">{{ emptyText }}</p>
          <el-button
            v-if="!searchKeyword"
            type="primary"
            @click="handleRefresh"
            :loading="refreshing"
          >
            刷新列表
          </el-button>
        </div>
      </div>

      <div v-else-if="videos.length > 0" class="video-grid">
        <transition-group name="video-list" tag="div" class="grid-container">
          <div
            v-for="video in videos"
            :key="video.video_key || video.id"
            class="video-grid-item"
          >
            <VideoCard :video="video" />
          </div>
        </transition-group>

        <div class="pagination-container">
          <el-config-provider :locale="zhCn">
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
          </el-config-provider>
        </div>
      </div>

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
      v-model="categoryDialogVisible"
      title="新增分类"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top" @submit.prevent="submitCategory">
        <el-form-item label="分类名称">
          <el-input
            v-model="categoryForm.name"
            maxlength="20"
            show-word-limit
            placeholder="例如：科幻、短剧"
          />
        </el-form-item>

        <el-form-item label="绑定文件夹">
          <div class="folder-picker">
            <el-input
              :model-value="categoryForm.folder"
              readonly
              placeholder="请选择一个本地文件夹"
            />
            <el-button @click="pickCategoryFolder">
              选择文件夹
            </el-button>
          </div>
        </el-form-item>

        <div class="dialog-actions">
          <el-button @click="categoryDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="categorySaving" :disabled="!canSubmitCategory" @click="submitCategory">
            保存分类
          </el-button>
        </div>
      </el-form>
    </el-dialog>

    <el-dialog
      v-model="addressDialogVisible"
      title="局域网连接地址"
      :width="addressDialogWidth"
      class="address-dialog"
    >
      <el-skeleton v-if="addressLoading" :rows="4" animated />
      <div v-else>
        <p class="address-tip">可在同一局域网设备的浏览器打开以下地址：</p>
        <el-empty v-if="frontendUrls.length === 0" description="未检测到可用局域网 IP" />
        <el-space
          v-else
          direction="vertical"
          alignment="stretch"
          style="width: 100%;"
        >
          <div
            v-for="url in frontendUrls"
            :key="url"
            class="url-row"
          >
            <div class="url-row-main">
              <el-icon class="url-row-icon"><i-ep-Link /></el-icon>
              <span class="url-row-text">{{ url }}</span>
            </div>
            <el-button
              size="small"
              class="url-copy-button"
              @click="copyAddress(url)"
            >
              复制
            </el-button>
          </div>
        </el-space>
        <p class="address-note">
          若无法访问，请检查电脑防火墙与端口放行设置。
        </p>
      </div>
    </el-dialog>

    <el-dialog
      v-model="settingsDialogVisible"
      title="设置"
      width="420px"
      :lock-scroll="false"
      :close-on-click-modal="false"
      class="settings-dialog"
    >
      <div class="settings-section">
        <div class="settings-section-header">
          <h3>修改登录密码</h3>
          <p>修改后，下次启动应用会继续使用新密码。</p>
        </div>

        <el-form label-position="top" @submit.prevent="submitPasswordChange">
          <el-form-item label="当前密码">
            <el-input
              v-model="passwordForm.currentPassword"
              show-password
              placeholder="请输入当前密码"
            />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input
              v-model="passwordForm.nextPassword"
              show-password
              placeholder="请输入新密码"
            />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input
              v-model="passwordForm.confirmPassword"
              show-password
              placeholder="请再次输入新密码"
              @keyup.enter="submitPasswordChange"
            />
          </el-form-item>
          <div class="settings-submit">
            <el-button
              type="primary"
              :loading="passwordSaving"
              @click="submitPasswordChange"
            >
              保存密码
            </el-button>
          </div>
        </el-form>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { ElMessageBox } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import VideoCard from '../components/VideoCard.vue'
import { videoApi } from '../api/video'
import { updatePassword } from '../utils/auth'
import { AUTH_KEY, REMEMBER_LOGIN_KEY } from '../utils/auth-keys'
import { isTauriRuntime } from '../utils/tauri'

const CONFIG_FILE_NAME = 'video_folder.json'
const TEMP_CONFIG_FILE_NAME = 'video_folder.json.tmp'

export default {
  name: 'VideoList',

  components: {
    PageHeader,
    VideoCard
  },

  data() {
    return {
      zhCn,
      videos: [],
      categories: [],
      subfolderOptions: [],
      activeCategoryId: '',
      activeSubfolder: '',
      loading: false,
      refreshing: false,
      categorySaving: false,
      error: null,
      toastTimestamps: {},
      searchKeyword: '',
      currentPage: 1,
      pageSize: 12,
      sortBy: 'name',
      folderAvailable: true,
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
      frontendUrls: [],
      settingsDialogVisible: false,
      passwordSaving: false,
      categoryDialogVisible: false,
      passwordForm: {
        currentPassword: '',
        nextPassword: '',
        confirmPassword: ''
      },
      categoryForm: {
        name: '',
        folder: ''
      }
    }
  },

  computed: {
    emptyText() {
      if (!this.activeCategoryId) {
        return '请先新增分类并选择文件夹。'
      }
      if (!this.folderAvailable) {
        return '当前分类绑定的文件夹不可用，请检查路径或重新设置分类。'
      }
      if (this.searchKeyword) {
        return `未找到与“${this.searchKeyword}”相关的视频，请尝试更短关键词。`
      }
      if (this.activeSubfolder === 'root') {
        return '当前分类根目录暂无可播放视频'
      }
      if (this.activeSubfolder) {
        return `当前子文件夹“${this.activeSubfolder}”暂无可播放视频`
      }
      return '当前分类暂无可播放视频'
    },
    listErrorTitle() {
      return `列表加载失败：${this.error}`
    },
    paginationLayout() {
      return this.isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next, jumper'
    },
    addressDialogWidth() {
      return this.isMobile ? '92vw' : '560px'
    },
    canSubmitCategory() {
      return Boolean(this.categoryForm.name.trim() && this.categoryForm.folder.trim())
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
        if (this.activeCategoryId) {
          params.category_id = this.activeCategoryId
        }
        if (this.activeSubfolder) {
          params.subfolder = this.activeSubfolder
        }

        const response = await videoApi.getVideos(params)

        if (!response.data.success) {
          throw new Error(response.data.error || '获取视频列表失败')
        }

        const payload = response.data.data || {}
        this.videos = payload.videos || []
        this.categories = payload.categories || []
        this.subfolderOptions = payload.subfolders || []
        this.pagination = payload.pagination || {
          total: 0,
          page: 1,
          page_size: this.pageSize,
          total_pages: 1
        }

        const nextActiveCategoryId = payload.active_category_id || this.categories[0]?.id || ''
        if (nextActiveCategoryId !== this.activeCategoryId) {
          this.activeCategoryId = nextActiveCategoryId
        }

        const folderExistsMap = payload.folder_exists_map || {}
        this.folderAvailable = this.activeCategoryId ? folderExistsMap[this.activeCategoryId] !== false : true

        if (this.activeSubfolder && this.activeSubfolder !== 'root' && !this.subfolderOptions.includes(this.activeSubfolder)) {
          this.activeSubfolder = ''
        }
      } catch (err) {
        const message = this.getErrorMessage(err)
        this.folderAvailable = true
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

      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    },

    handleCategoryChange(categoryId) {
      this.activeCategoryId = categoryId
      this.activeSubfolder = ''
      this.currentPage = 1
      this.fetchVideos()
    },

    handleSubfolderChange() {
      this.currentPage = 1
      this.fetchVideos()
    },

    async handleRefresh() {
      this.refreshing = true
      try {
        await videoApi.refreshCache()
        await this.fetchVideos()
        this.$message.success('列表已更新')
      } catch (err) {
        const message = this.getErrorMessage(err)
        this.toastOnce('refresh', 'error', '列表刷新失败：' + message)
      } finally {
        this.refreshing = false
      }
    },

    openCategoryDialog() {
      if (!this.isTauri) {
        this.$message.warning('当前运行环境不支持选择本地文件夹')
        return
      }
      this.categoryForm = {
        name: '',
        folder: ''
      }
      this.categoryDialogVisible = true
    },

    async pickCategoryFolder() {
      if (!this.isTauri) {
        this.$message.warning('当前运行环境不支持选择本地文件夹')
        return
      }

      try {
        const { open } = await import('@tauri-apps/plugin-dialog')
        const selected = await open({
          directory: true,
          multiple: false,
          title: '选择分类文件夹'
        })

        if (!selected) return
        this.categoryForm.folder = Array.isArray(selected) ? selected[0] : selected
      } catch (err) {
        const message = this.getErrorMessage(err)
        this.toastOnce('pickFolder', 'error', '选择文件夹失败：' + message)
      }
    },

    async readConfigData() {
      const { readTextFile, exists } = await import('@tauri-apps/plugin-fs')
      const { BaseDirectory } = await import('@tauri-apps/api/path')

      const hasConfig = await exists(CONFIG_FILE_NAME, { baseDir: BaseDirectory.AppData })
      if (!hasConfig) {
        return {
          categories: this.categories.map((item) => ({
            id: item.id,
            name: item.name,
            folder: item.folder,
            enabled: item.enabled !== false
          })),
          active_category_id: this.activeCategoryId || this.categories[0]?.id || ''
        }
      }

      const raw = await readTextFile(CONFIG_FILE_NAME, { baseDir: BaseDirectory.AppData })
      const parsed = JSON.parse(raw)

      if (Array.isArray(parsed.categories)) {
        return {
          categories: parsed.categories.map((item) => ({
            id: item.id,
            name: item.name,
            folder: item.folder || item.path,
            enabled: item.enabled !== false
          })),
          active_category_id: parsed.active_category_id || ''
        }
      }

      if (parsed.video_folder) {
        const migratedId = `cat_${Date.now()}`
        return {
          categories: [{
            id: migratedId,
            name: '默认分类',
            folder: parsed.video_folder,
            enabled: true
          }],
          active_category_id: migratedId
        }
      }

      return {
        categories: [],
        active_category_id: ''
      }
    },

    async writeConfigData(data) {
      const { writeTextFile, exists, mkdir, remove, rename } = await import('@tauri-apps/plugin-fs')
      const { BaseDirectory, appDataDir } = await import('@tauri-apps/api/path')

      const appDataPath = await appDataDir()
      try {
        await mkdir(appDataPath, { recursive: true })
      } catch (_) {
        // no-op
      }

      const payload = JSON.stringify(data, null, 2)
      if (await exists(TEMP_CONFIG_FILE_NAME, { baseDir: BaseDirectory.AppData })) {
        await remove(TEMP_CONFIG_FILE_NAME, { baseDir: BaseDirectory.AppData })
      }
      await writeTextFile(TEMP_CONFIG_FILE_NAME, payload, {
        baseDir: BaseDirectory.AppData
      })
      if (await exists(CONFIG_FILE_NAME, { baseDir: BaseDirectory.AppData })) {
        await remove(CONFIG_FILE_NAME, { baseDir: BaseDirectory.AppData })
      }
      await rename(TEMP_CONFIG_FILE_NAME, CONFIG_FILE_NAME, {
        oldPathBaseDir: BaseDirectory.AppData,
        newPathBaseDir: BaseDirectory.AppData
      })
    },

    async submitCategory() {
      const name = this.categoryForm.name.trim()
      const folder = this.categoryForm.folder.trim()

      if (!name) {
        this.$message.error('请输入分类名称')
        return
      }
      if (!folder) {
        this.$message.error('请选择分类文件夹')
        return
      }
      if (this.categories.some((item) => item.name === name)) {
        this.$message.error('分类名称已存在，请更换一个名称')
        return
      }

      this.categorySaving = true
      try {
        const { exists } = await import('@tauri-apps/plugin-fs')
        const folderExists = await exists(folder)
        if (!folderExists) {
          throw new Error('选中的目录不存在')
        }

        const current = await this.readConfigData()
        const newCategoryId = `cat_${Date.now()}`
        const nextConfig = {
          categories: [
            ...(current.categories || []),
            {
              id: newCategoryId,
              name,
              folder,
              enabled: true
            }
          ],
          active_category_id: newCategoryId
        }

        await this.writeConfigData(nextConfig)
        const refreshResponse = await videoApi.refreshCache()
        if (!refreshResponse?.data?.success) {
          throw new Error(refreshResponse?.data?.error || '刷新视频目录失败')
        }

        this.activeCategoryId = newCategoryId
        this.activeSubfolder = ''
        this.currentPage = 1
        await this.fetchVideos()
        this.categoryDialogVisible = false
        this.$message.success(`分类“${name}”已创建`)
      } catch (err) {
        const message = this.getErrorMessage(err)
        this.error = message
        this.toastOnce('saveCategory', 'error', '分类创建失败：' + message)
      } finally {
        this.categorySaving = false
      }
    },

    async removeCategory(categoryId) {
      const target = this.categories.find((item) => item.id === categoryId)
      if (!target) return

      try {
        await ElMessageBox.confirm(
          `确认删除分类“${target.name}”吗？不会删除本地文件，只会移除分类映射。`,
          '删除分类',
          {
            type: 'warning',
            confirmButtonText: '删除',
            cancelButtonText: '取消'
          }
        )
      } catch {
        return
      }

      try {
        const current = await this.readConfigData()
        const nextCategories = (current.categories || []).filter((item) => item.id !== categoryId)
        const nextActiveCategoryId = this.activeCategoryId === categoryId
          ? (nextCategories[0]?.id || '')
          : (current.active_category_id || nextCategories[0]?.id || '')

        if (nextCategories.length === (current.categories || []).length) {
          throw new Error('未找到要删除的分类')
        }

        await this.writeConfigData({
          categories: nextCategories,
          active_category_id: nextActiveCategoryId
        })

        this.categories = nextCategories
        this.activeCategoryId = nextActiveCategoryId
        this.activeSubfolder = ''
        this.currentPage = 1
        await videoApi.refreshCache()
        await this.fetchVideos()
        this.$message.success(`分类“${target.name}”已删除`)
      } catch (err) {
        const message = this.getErrorMessage(err)
        this.toastOnce('removeCategory', 'error', '删除分类失败：' + message)
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
    },

    async copyAddress(url) {
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(url)
        } else {
          const input = document.createElement('input')
          input.value = url
          input.setAttribute('readonly', 'readonly')
          input.style.position = 'absolute'
          input.style.left = '-9999px'
          document.body.appendChild(input)
          input.select()
          document.execCommand('copy')
          document.body.removeChild(input)
        }
        this.$message.success('连接地址已复制')
      } catch (_) {
        this.$message.error('复制失败，请手动复制地址')
      }
    },

    handleShowSettings() {
      this.resetPasswordForm()
      this.settingsDialogVisible = true
    },

    resetPasswordForm() {
      this.passwordForm = {
        currentPassword: '',
        nextPassword: '',
        confirmPassword: ''
      }
    },

    async submitPasswordChange() {
      const { currentPassword, nextPassword, confirmPassword } = this.passwordForm
      const trimmedCurrentPassword = currentPassword.trim()
      const trimmedNextPassword = nextPassword.trim()
      const trimmedConfirmPassword = confirmPassword.trim()

      if (!trimmedCurrentPassword) {
        this.$message.error('请输入当前密码')
        return
      }

      if (!trimmedNextPassword) {
        this.$message.error('请输入新密码')
        return
      }

      if (trimmedNextPassword !== trimmedConfirmPassword) {
        this.$message.error('两次输入的新密码不一致')
        return
      }

      this.passwordSaving = true
      try {
        updatePassword(trimmedCurrentPassword, trimmedNextPassword)
        sessionStorage.setItem(AUTH_KEY, '1')
        localStorage.removeItem(REMEMBER_LOGIN_KEY)
        this.$message.success('密码修改成功')
        this.settingsDialogVisible = false
        this.resetPasswordForm()
      } catch (err) {
        this.$message.error(this.getErrorMessage(err))
      } finally {
        this.passwordSaving = false
      }
    }
  }
}
</script>

<style scoped>
.video-list-page {
  min-height: 100vh;
  background: var(--bg-page);
}

.content-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 20px 24px;
}

.category-toolbar-bar {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 8px 10px;
  margin-bottom: 12px;
}

.category-toolbar-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.category-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.category-tabs {
  flex: 1;
  min-width: 0;
}

.category-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.category-tabs :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
  scrollbar-width: none;
}

.category-tabs :deep(.el-tabs__nav-wrap::-webkit-scrollbar) {
  display: none;
}

.category-tabs :deep(.el-tabs__item) {
  height: 32px;
  line-height: 32px;
  padding: 0 14px;
}

.category-tab-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
}

.category-tab-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-tab-close {
  width: 18px;
  min-width: 18px;
  height: 18px;
  padding: 0;
}

.category-toolbar-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-shrink: 0;
}

.subfolder-select {
  width: 170px;
  max-width: 100%;
}

.category-empty-note {
  color: var(--text-secondary);
  font-size: 13px;
}

.text-empty-state {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
}

.text-empty-state--compact {
  min-height: 180px;
}

.text-empty-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}

.text-empty-description {
  margin: 0;
  max-width: 420px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
}

.loading-container {
  padding: 20px 4px;
  display: grid;
  gap: 12px;
}

.loading-surface,
.empty-container,
.video-grid {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
}

.video-grid-item {
  min-width: 0;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 14px;
}

.error-alert {
  margin-bottom: 20px;
}

.folder-picker {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.dialog-actions,
.settings-submit {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.settings-section-header h3 {
  margin: 0;
  color: var(--text-primary);
}

.settings-section-header p {
  margin: 6px 0 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.address-tip,
.address-note {
  color: var(--text-secondary);
  font-size: 13px;
}

.url-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-surface);
}

.url-row-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.url-row-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-list-enter-active,
.video-list-leave-active {
  transition: all 0.25s ease;
}

.video-list-enter-from,
.video-list-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.video-list-leave-active {
  position: absolute;
}

@media (max-width: 1199px) {
  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  }
}

@media (max-width: 768px) {
  .content-container {
    padding: 0 12px 16px;
  }

  .category-toolbar-bar {
    padding: 8px;
    margin-bottom: 10px;
  }

  .category-toolbar-main {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .category-toolbar-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .subfolder-select {
    width: 100%;
  }

  .folder-picker {
    grid-template-columns: 1fr;
  }

  .grid-container {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .pagination-container {
    justify-content: flex-start;
  }
}

@media (max-width: 359px) {
  .grid-container {
    grid-template-columns: 1fr;
  }
}
</style>
