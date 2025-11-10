<template>
  <div class="image-translate-list-page">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="page-header">
        <div class="header-left">
          <el-button :icon="ArrowLeft" circle @click="goBack" />
          <h2>翻译任务列表</h2>
        </div>
        <div class="header-right">
          <el-button type="primary" :icon="Plus" @click="goToTranslate">新建翻译</el-button>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <div class="filter-left">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="handleFilterChange" style="width: 150px">
            <el-option label="全部" value="" />
            <el-option label="已上传" value="uploaded" />
            <el-option label="翻译中" value="translating" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
          <el-button :icon="Refresh" circle @click="loadList" />
          <el-button 
            v-if="selectedTasks.length > 0"
            type="primary" 
            :icon="Download"
            @click="handleBatchDownload"
            :disabled="!hasCompletedInSelection"
          >
            批量下载 ({{ selectedTasks.length }})
          </el-button>
          <el-button 
            v-if="selectedTasks.length > 0"
            type="danger" 
            :icon="Delete"
            @click="handleBatchDelete"
            :disabled="hasTranslatingInSelection"
          >
            批量删除 ({{ selectedTasks.length }})
          </el-button>
        </div>
        <div class="filter-right">
          <el-checkbox 
            v-model="selectAll" 
            :indeterminate="isIndeterminate"
            @change="handleSelectAll"
          >
            全选
          </el-checkbox>
        </div>
      </div>

      <!-- 任务列表 -->
      <div class="task-list" v-loading="loading">
        <el-empty v-if="!loading && taskList.length === 0" description="暂无翻译任务" />
        
        <div v-else class="task-items">
          <div 
            v-for="task in taskList" 
            :key="task.id"
            class="task-item"
            :class="{
              'status-uploaded': task.status === 'uploaded',
              'status-translating': task.status === 'translating',
              'status-completed': task.status === 'completed',
              'status-failed': task.status === 'failed',
              'expired': isExpired(task.created_at),
              'selected': selectedTasks.includes(task.id)
            }"
          >
            <div class="task-header">
              <div class="task-checkbox">
                <el-checkbox 
                  :model-value="selectedTasks.includes(task.id)"
                  @change="(val) => handleTaskSelect(task.id, val)"
                  :disabled="task.status === 'translating'"
                />
              </div>
              <div class="task-info">
                <div class="task-name">{{ task.original_filename }}</div>
                <div class="task-meta">
                  <el-tag :type="getStatusType(task.status)" size="small">
                    {{ getStatusText(task.status) }}
                  </el-tag>
                  <span class="task-time">{{ formatTime(task.created_at) }}</span>
                  <span v-if="isExpired(task.created_at)" class="expired-tag">已过期</span>
                </div>
              </div>
              <div class="task-actions">
                <el-button 
                  type="danger" 
                  :icon="Delete" 
                  size="small" 
                  circle
                  @click="handleDelete(task.id)"
                  :disabled="task.status === 'translating'"
                />
              </div>
            </div>

            <div class="task-content">
              <!-- 图片预览 -->
              <div class="task-image">
                <div class="image-wrapper">
                  <img
                    :src="getImageUrl(task.filepath)"
                    :alt="task.original_filename"
                    class="task-image-preview"
                    @click="previewImage(getImageUrl(task.filepath))"
                  />
                  <div class="image-actions">
                    <el-button
                      type="primary"
                      :icon="Download"
                      size="small"
                      circle
                      @click.stop="downloadImage(getImageUrl(task.filepath), task.original_filename)"
                      title="下载原图"
                    />
                  </div>
                </div>
              </div>

              <!-- 翻译信息 -->
              <div class="task-details">
                <div class="detail-row">
                  <span class="label">源语言：</span>
                  <span class="value">{{ getLanguageName(task.source_language) }}</span>
                  <span class="label" style="margin-left: 20px">目标语言：</span>
                  <span class="value">{{ getLanguageName(task.target_language) }}</span>
                </div>

                <!-- 翻译中状态 -->
                <div v-if="task.status === 'translating'" class="translating-info">
                  <el-progress :percentage="50" :status="null" :show-text="false" />
                  <span class="translating-text">正在翻译中，请稍候...</span>
                </div>

                <!-- 已完成状态 -->
                <div v-if="task.status === 'completed'" class="result-info">
                  <div class="result-item" v-if="task.original_text">
                    <div class="result-label">原文：</div>
                    <div class="result-text">{{ task.original_text }}</div>
                  </div>
                  <div class="result-item" v-if="task.translated_text">
                    <div class="result-label">译文：</div>
                    <div class="result-text translated">{{ task.translated_text }}</div>
                  </div>
                  <div v-if="task.translated_image_url" class="result-image">
                    <div class="result-label">翻译后图片：</div>
                    <div class="image-wrapper">
                      <img
                        :src="task.translated_image_url"
                        alt="翻译后的图片"
                        class="result-image-preview"
                        @click="previewImage(task.translated_image_url)"
                      />
                      <div class="image-actions">
                        <el-button
                          type="primary"
                          :icon="Download"
                          size="small"
                          circle
                          @click.stop="downloadImage(task.translated_image_url, `${task.original_filename.replace(/\.[^/.]+$/, '')}_translated.png`)"
                          title="下载翻译后的图片"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 失败状态 -->
                <div v-if="task.status === 'failed'" class="error-info">
                  <el-alert
                    :title="task.error_message || '翻译失败'"
                    type="error"
                    :closable="false"
                    show-icon
                  />
                  <div class="retry-action">
                    <el-button 
                      type="primary" 
                      size="small" 
                      :icon="RefreshRight"
                      @click="handleRetry(task.id)"
                      :loading="retryingTasks.includes(task.id)"
                    >
                      重试
                    </el-button>
                  </div>
                </div>

                <!-- 已过期提示 -->
                <div v-if="isExpired(task.created_at)" class="expired-info">
                  <el-alert
                    title="此任务已超过24小时，结果可能已失效"
                    type="warning"
                    :closable="false"
                    show-icon
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-wrapper" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 图片预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      title="图片预览"
      width="90%"
      :close-on-click-modal="true"
      align-center
      class="image-preview-dialog"
    >
      <div class="preview-content">
        <img :src="previewImageUrl" alt="预览图片" class="preview-full-image" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Plus, Refresh, Delete, RefreshRight, Download, ZoomIn } from '@element-plus/icons-vue'
import { getImageList, deleteImage, batchDeleteImages, batchDownloadImages, getImageTranslateStatus, retryImageTranslate } from '@/api/tools'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const taskList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const filterStatus = ref('')
const selectedTasks = ref([]) // 选中的任务ID列表
const selectAll = ref(false) // 全选状态
const retryingTasks = ref([]) // 正在重试的任务ID列表
const previewImageUrl = ref('') // 预览图片URL
const previewVisible = ref(false) // 预览对话框显示状态

// 轮询定时器
let pollingTimer = null
const pollingInterval = 30000 // 30秒轮询一次

// 语言映射
const languageMap = {
  'zh': '简体中文',
  'en': '英文',
  'ko': '韩语',
  'ja': '日语',
  'ru': '俄语',
  'es': '西班牙语',
  'fr': '法语',
  'pt': '葡萄牙语',
  'it': '意大利语',
  'de': '德语',
  'vi': '越南语',
  'ms': '马来语',
  'th': '泰语',
  'id': '印尼语',
  'ar': '阿拉伯语'
}

// 获取语言名称
function getLanguageName(code) {
  return languageMap[code] || code
}

// 获取状态类型
function getStatusType(status) {
  const map = {
    'uploaded': 'info',
    'translating': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

// 获取状态文本
function getStatusText(status) {
  const map = {
    'uploaded': '已上传',
    'translating': '翻译中',
    'completed': '已完成',
    'failed': '失败'
  }
  return map[status] || status
}

// 格式化时间
function formatTime(timeStr) {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 1) return '今天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// 检查是否过期（24小时）
function isExpired(createdAt) {
  if (!createdAt) return false
  const created = new Date(createdAt)
  const now = new Date()
  const diff = now - created
  return diff > 24 * 60 * 60 * 1000 // 24小时
}

// 获取图片URL
function getImageUrl(filepath) {
  if (!filepath) return ''
  if (filepath.startsWith('http://') || filepath.startsWith('https://')) {
    return filepath
  }
  // 转换为相对路径URL
  if (filepath.includes('/uploads/')) {
    const parts = filepath.split('/uploads/')
    return `/uploads/${parts[1]}`
  }
  return filepath
}

// 筛选变化
function handleFilterChange() {
  selectedTasks.value = [] // 筛选时清空选中
  selectAll.value = false
  currentPage.value = 1 // 重置到第一页
  loadList()
}

// 加载列表
async function loadList() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      limit: pageSize.value
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }

    const response = await getImageList(params)
    if (response.code === 200) {
      const list = response.data.data || []
      
      // 对于正在翻译的任务，查询最新状态（前端轮询间隔30秒，不会触发速率限制）
      const translatingTasks = list.filter(task => task.status === 'translating' && task.qwen_task_id)
      
      if (translatingTasks.length > 0) {
        // 串行查询状态，避免触发速率限制
        for (const task of translatingTasks) {
          try {
            const statusResponse = await getImageTranslateStatus(task.id)
            if (statusResponse.code === 200) {
              const index = list.findIndex(t => t.id === task.id)
              if (index !== -1) {
                Object.assign(list[index], statusResponse.data)
              }
            }
            // 每个请求间隔100ms，避免触发速率限制
            if (translatingTasks.indexOf(task) < translatingTasks.length - 1) {
              await new Promise(resolve => setTimeout(resolve, 100))
            }
          } catch (error) {
            console.error(`查询任务 ${task.id} 状态失败:`, error)
          }
        }
      }
      
      taskList.value = list
      total.value = response.data.total || 0
      
      // 更新全选状态
      updateSelectAllState()
    } else {
      ElMessage.error(response.message || '加载失败')
    }
  } catch (error) {
    console.error('加载列表失败:', error)
    ElMessage.error('加载列表失败')
  } finally {
    loading.value = false
  }
}

// 选择任务
function handleTaskSelect(taskId, selected) {
  if (selected) {
    if (!selectedTasks.value.includes(taskId)) {
      selectedTasks.value.push(taskId)
    }
  } else {
    const index = selectedTasks.value.indexOf(taskId)
    if (index > -1) {
      selectedTasks.value.splice(index, 1)
    }
  }
  updateSelectAllState()
}

// 全选/取消全选
function handleSelectAll(val) {
  if (val) {
    // 只选择非翻译中的任务
    selectedTasks.value = taskList.value
      .filter(task => task.status !== 'translating')
      .map(task => task.id)
  } else {
    selectedTasks.value = []
  }
}

// 更新全选状态
function updateSelectAllState() {
  const selectableTasks = taskList.value.filter(task => task.status !== 'translating')
  if (selectableTasks.length === 0) {
    selectAll.value = false
    return
  }
  const selectedCount = selectedTasks.value.length
  selectAll.value = selectedCount === selectableTasks.length
}

// 计算属性：是否有翻译中的任务被选中
const hasTranslatingInSelection = computed(() => {
  return selectedTasks.value.some(id => {
    const task = taskList.value.find(t => t.id === id)
    return task && task.status === 'translating'
  })
})

// 计算属性：是否有已完成的任务被选中（用于批量下载）
const hasCompletedInSelection = computed(() => {
  return selectedTasks.value.some(id => {
    const task = taskList.value.find(t => t.id === id)
    return task && task.status === 'completed' && task.translated_image_url
  })
})

// 计算属性：全选状态（半选）
const isIndeterminate = computed(() => {
  const selectableTasks = taskList.value.filter(task => task.status !== 'translating')
  if (selectableTasks.length === 0) return false
  const selectedCount = selectedTasks.value.length
  return selectedCount > 0 && selectedCount < selectableTasks.length
})

// 删除任务
async function handleDelete(taskId) {
  try {
    await ElMessageBox.confirm('确定要删除这个翻译任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const response = await deleteImage(taskId)
    if (response.code === 200) {
      ElMessage.success('删除成功')
      // 从选中列表中移除
      const index = selectedTasks.value.indexOf(taskId)
      if (index > -1) {
        selectedTasks.value.splice(index, 1)
      }
      loadList()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 重试失败的翻译任务
async function handleRetry(taskId) {
  if (retryingTasks.value.includes(taskId)) {
    return // 正在重试中，避免重复点击
  }

  try {
    retryingTasks.value.push(taskId)
    
    const response = await retryImageTranslate(taskId)
    if (response.code === 200) {
      ElMessage.success('重试成功，任务已加入队列')
      // 刷新列表
      await loadList()
      // 如果重试后状态变为translating，启动轮询
      if (hasTranslatingTasks.value) {
        startPolling()
      }
    } else {
      ElMessage.error(response.message || '重试失败')
    }
  } catch (error) {
    console.error('重试失败:', error)
    ElMessage.error('重试失败，请稍后重试')
  } finally {
    const index = retryingTasks.value.indexOf(taskId)
    if (index > -1) {
      retryingTasks.value.splice(index, 1)
    }
  }
}

// 预览图片
function previewImage(imageUrl) {
  previewImageUrl.value = imageUrl
  previewVisible.value = true
}

// 下载单张图片
function downloadImage(imageUrl, filename) {
  try {
    // 创建一个临时的 a 标签来触发下载
    const link = document.createElement('a')
    link.href = imageUrl
    link.download = filename || 'image.png'
    link.target = '_blank'
    
    // 对于跨域图片，需要先 fetch 然后创建 blob
    fetch(imageUrl)
      .then(response => response.blob())
      .then(blob => {
        const url = window.URL.createObjectURL(blob)
        link.href = url
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        ElMessage.success('图片下载成功')
      })
      .catch(error => {
        console.error('下载图片失败:', error)
        // 如果 fetch 失败，尝试直接打开链接
        link.href = imageUrl
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        ElMessage.warning('图片下载中，如未自动下载请右键保存')
      })
  } catch (error) {
    console.error('下载图片失败:', error)
    ElMessage.error('下载图片失败')
  }
}

// 批量下载
async function handleBatchDownload() {
  if (selectedTasks.value.length === 0) {
    ElMessage.warning('请先选择要下载的任务')
    return
  }

  // 检查是否有已完成的任务
  const completedTasks = selectedTasks.value.filter(id => {
    const task = taskList.value.find(t => t.id === id)
    return task && task.status === 'completed' && task.translated_image_url
  })

  if (completedTasks.length === 0) {
    ElMessage.warning('选中的任务中没有已完成的翻译，无法下载')
    return
  }

  try {
    // 显示加载提示
    const loadingMessage = ElMessage({
      message: '正在打包下载，请稍候...',
      type: 'info',
      duration: 0
    })

    const response = await batchDownloadImages(completedTasks)
    
    // 关闭加载提示
    loadingMessage.close()

    // 创建下载链接
    const blob = new Blob([response], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `translated_images_${new Date().getTime()}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success(`成功下载${completedTasks.length}张翻译后的图片`)
  } catch (error) {
    console.error('批量下载失败:', error)
    ElMessage.error('批量下载失败，请稍后重试')
  }
}

// 批量删除
async function handleBatchDelete() {
  if (selectedTasks.value.length === 0) {
    ElMessage.warning('请先选择要删除的任务')
    return
  }

  // 检查是否有翻译中的任务
  const translatingTasks = selectedTasks.value.filter(id => {
    const task = taskList.value.find(t => t.id === id)
    return task && task.status === 'translating'
  })

  if (translatingTasks.length > 0) {
    ElMessage.warning('不能删除正在翻译中的任务')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedTasks.value.length} 个翻译任务吗？`,
      '批量删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await batchDeleteImages(selectedTasks.value)
    if (response.code === 200) {
      const { deleted_count, failed_count, message } = response.data
      if (failed_count > 0) {
        ElMessage.warning(message || `成功删除${deleted_count}个，失败${failed_count}个`)
      } else {
        ElMessage.success(`成功删除${deleted_count}个任务`)
      }
      selectedTasks.value = []
      selectAll.value = false
      loadList()
    } else {
      ElMessage.error(response.message || '批量删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

// 分页变化
function handlePageChange(page) {
  currentPage.value = page
  selectedTasks.value = [] // 切换页面时清空选中
  selectAll.value = false
  loadList()
}

function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  selectedTasks.value = [] // 切换页面大小时清空选中
  selectAll.value = false
  loadList()
}

// 返回上一页
function goBack() {
  router.back()
}

// 跳转到翻译页面
function goToTranslate() {
  router.push('/tools/image-translate')
}

// 开始轮询（无超时和次数限制）
function startPolling() {
  // 如果已经在轮询，先停止
  stopPolling()
  
  // 检查是否有正在翻译的任务
  const hasTranslating = taskList.value.some(task => task.status === 'translating' && !isExpired(task.created_at))
  
  if (hasTranslating) {
    // 立即执行一次
    loadList()
    
    // 然后设置定时器，每30秒轮询一次
    pollingTimer = setInterval(() => {
      // 检查是否还有正在翻译的任务
      const stillHasTranslating = taskList.value.some(task => task.status === 'translating' && !isExpired(task.created_at))
      if (stillHasTranslating) {
        loadList()
      } else {
        // 如果没有正在翻译的任务了，停止轮询
        stopPolling()
      }
    }, pollingInterval)
  }
}

// 停止轮询
function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

// 检查是否需要轮询
const hasTranslatingTasks = computed(() => {
  return taskList.value.some(task => task.status === 'translating' && !isExpired(task.created_at))
})

// 监听翻译任务状态变化
watch(hasTranslatingTasks, (newVal) => {
  if (newVal) {
    startPolling()
  } else {
    stopPolling()
  }
})

onMounted(async () => {
  await loadList()
  
  // 检查是否有正在翻译的任务，如果有则开始轮询
  if (hasTranslatingTasks.value) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})

</script>


<style scoped lang="scss">
.image-translate-list-page {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  min-height: calc(100vh - 60px);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    h2 {
      font-size: 24px;
      font-weight: bold;
      color: #111111;
      margin: 0;
    }
  }
}

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  background: #ffffff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

  .filter-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .filter-right {
    display: flex;
    align-items: center;
  }
}

.task-list {
  background: #ffffff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 400px;
}

.task-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.status-uploaded {
    border-left: 4px solid #909399;
  }

  &.status-translating {
    border-left: 4px solid #E6A23C;
  }

  &.status-completed {
    border-left: 4px solid #67C23A;
  }

  &.status-failed {
    border-left: 4px solid #F56C6C;
  }

  &.expired {
    opacity: 0.7;
  }

  &.selected {
    border-color: #409EFF;
    background-color: #f0f7ff;
  }
}

.task-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;

  .task-checkbox {
    display: flex;
    align-items: center;
    padding-top: 2px;
  }
}

.task-info {
  flex: 1;

  .task-name {
    font-size: 16px;
    font-weight: bold;
    color: #111111;
    margin-bottom: 8px;
  }

  .task-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    color: #666666;

    .task-time {
      color: #999999;
    }

    .expired-tag {
      color: #E6A23C;
      font-weight: bold;
    }
  }
}

.task-content {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 20px;

  @media screen and (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.task-image {
  width: 200px;
  height: 200px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;

  .image-wrapper {
    position: relative;
    width: 100%;
    height: 100%;

    .task-image-preview {
      width: 100%;
      height: 100%;
      cursor: pointer;
    }

    .image-actions {
      position: absolute;
      top: 8px;
      right: 8px;
      opacity: 0;
      transition: opacity 0.3s;
      z-index: 10;
    }

    &:hover .image-actions {
      opacity: 1;
    }
  }

  @media screen and (max-width: 768px) {
    width: 100%;
    height: auto;
    max-height: 300px;
  }
}

.task-details {
  flex: 1;
}

.detail-row {
  margin-bottom: 16px;
  font-size: 14px;

  .label {
    color: #666666;
  }

  .value {
    color: #111111;
    font-weight: 500;
  }
}

.translating-info {
  margin-top: 16px;

  .translating-text {
    display: block;
    margin-top: 8px;
    font-size: 14px;
    color: #E6A23C;
  }
}

.result-info {
  margin-top: 16px;
}

.result-item {
  margin-bottom: 12px;

  .result-label {
    font-size: 14px;
    color: #666666;
    margin-bottom: 4px;
  }

  .result-text {
    font-size: 14px;
    color: #111111;
    line-height: 1.6;
    padding: 8px 12px;
    background: #f5f7fa;
    border-radius: 4px;

    &.translated {
      background: #f0f9ff;
      color: #409EFF;
    }
  }
}

.result-image {
  margin-top: 16px;

  .result-label {
    font-size: 14px;
    color: #666666;
    margin-bottom: 8px;
  }

  .image-wrapper {
    position: relative;
    display: inline-block;

    .result-image-preview {
      max-width: 300px;
      max-height: 300px;
      width: auto;
      height: auto;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      cursor: pointer;
      transition: transform 0.2s;

      &:hover {
        transform: scale(1.05);
      }
    }

    .image-actions {
      position: absolute;
      top: 8px;
      right: 8px;
      opacity: 0;
      transition: opacity 0.3s;
      z-index: 10;
    }

    &:hover .image-actions {
      opacity: 1;
    }
  }
}

.error-info {
  margin-top: 16px;

  .retry-action {
    margin-top: 12px;
    display: flex;
    justify-content: flex-start;
  }
}

.expired-info {
  margin-top: 16px;
}

.pagination-wrapper {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.image-preview-dialog {
  .preview-content {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 400px;
    max-height: 80vh;
    overflow: auto;

    .preview-full-image {
      max-width: 100%;
      max-height: 80vh;
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
  }
}
</style>

