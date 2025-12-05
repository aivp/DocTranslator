<template>
  <div class="pdf-to-image-page">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="page-header">
        <div class="header-left">
          <el-button :icon="ArrowLeft" circle @click="goBack" />
          <h2>PDF转图片</h2>
        </div>
      </div>

      <!-- 主要内容 -->
      <div class="main-content">
        <!-- 左侧：上传和设置 -->
        <div class="left-panel">
          <el-card class="upload-card">
            <template #header>
              <div class="card-header">
                <span>上传PDF文件</span>
              </div>
            </template>

            <el-upload
              ref="uploadRef"
              class="pdf-uploader"
              drag
              :action="uploadUrl"
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :before-upload="beforeUpload"
              accept="application/pdf,.pdf"
              :headers="{ Authorization: 'Bearer ' + userStore.token }"
            >
              <div class="upload-area">
                <el-icon :size="64" color="#409EFF">
                  <Document />
                </el-icon>
                <div class="upload-text">
                  <p class="upload-title">点击或拖拽PDF文件到此处上传</p>
                  <p class="upload-tips">支持PDF格式，文件大小 ≤ 100MB</p>
                </div>
              </div>
            </el-upload>

            <div v-if="pdfFile" class="file-info">
              <el-icon><Document /></el-icon>
              <span class="file-name">{{ pdfFile.name }}</span>
              <span class="file-size">{{ formatFileSize(pdfFile.size) }}</span>
              <el-button
                type="danger"
                :icon="Delete"
                size="small"
                circle
                @click="removeFile"
              />
            </div>
          </el-card>

          <el-card class="settings-card">
            <template #header>
              <div class="card-header">
                <span>转换设置</span>
              </div>
            </template>

            <el-form :model="form" label-width="120px" label-position="left">
              <el-form-item label="图片格式">
                <el-select v-model="form.imageFormat" placeholder="请选择图片格式" style="width: 100%">
                  <el-option label="PNG（推荐，支持透明背景）" value="png" />
                  <el-option label="JPG（文件更小）" value="jpg" />
                  <el-option label="WEBP（现代格式，文件最小）" value="webp" />
                </el-select>
              </el-form-item>

              <el-form-item label="分辨率 (DPI)">
                <el-slider
                  v-model="form.dpi"
                  :min="72"
                  :max="600"
                  :step="10"
                  show-input
                  :show-input-controls="false"
                />
                <div class="dpi-tips">
                  <span class="tip-item">72 DPI - 网页显示</span>
                  <span class="tip-item">200 DPI - 标准打印（推荐）</span>
                  <span class="tip-item">300 DPI - 高质量打印</span>
                  <span class="tip-item">600 DPI - 超高质量</span>
                </div>
              </el-form-item>

              <el-form-item label="页面范围">
                <el-input
                  v-model="form.pageRange"
                  placeholder="留空转换所有页面，例如: 1-5 或 1"
                  clearable
                />
                <div class="page-range-tips">
                  <span>留空：转换所有页面</span>
                  <span>示例：1-5（转换第1到第5页）</span>
                  <span>示例：1（只转换第1页）</span>
                </div>
              </el-form-item>
            </el-form>

            <div class="action-buttons">
              <el-button
                type="primary"
                size="large"
                :icon="Promotion"
                @click="handleConvert"
                :loading="converting"
                :disabled="!pdfFile"
                style="width: 100%"
              >
                {{ converting ? '转换中...' : '开始转换' }}
              </el-button>
            </div>
          </el-card>
        </div>

        <!-- 右侧：结果展示 -->
        <div class="right-panel">
          <el-card class="result-card">
            <template #header>
              <div class="card-header">
                <span>转换结果</span>
                <el-button
                  v-if="result && result.images && result.images.length > 1"
                  type="primary"
                  size="small"
                  :icon="Download"
                  @click="downloadZip"
                >
                  下载全部 (ZIP)
                </el-button>
              </div>
            </template>

            <div v-if="!result && !converting" class="empty-result">
              <el-empty description="上传PDF文件并点击转换按钮开始转换" />
            </div>

            <div v-if="converting" class="converting-result">
              <el-progress
                :percentage="convertingProgress"
                :status="convertingProgress === 100 ? 'success' : null"
                :stroke-width="8"
              />
              <p class="converting-text">正在转换PDF，请稍候...</p>
            </div>

            <div v-if="result && !converting" class="result-content">
              <el-alert
                :title="result.message"
                type="success"
                :closable="false"
                show-icon
                style="margin-bottom: 20px"
              />

              <div class="result-info">
                <div class="info-item">
                  <span class="label">总页数：</span>
                  <span class="value">{{ result.total_pages }}</span>
                </div>
                <div class="info-item">
                  <span class="label">图片格式：</span>
                  <span class="value">{{ result.image_format }}</span>
                </div>
                <div class="info-item">
                  <span class="label">分辨率：</span>
                  <span class="value">{{ result.dpi }} DPI</span>
                </div>
              </div>

              <div class="images-grid">
                <div
                  v-for="(image, index) in result.images"
                  :key="index"
                  class="image-item"
                >
                  <div class="image-wrapper">
                    <img :src="image.url" :alt="image.filename" @click="previewImage(image.url)" />
                    <div class="image-overlay">
                      <el-button
                        type="primary"
                        :icon="ZoomIn"
                        circle
                        size="small"
                        @click="previewImage(image.url)"
                        title="预览"
                      />
                      <el-button
                        type="success"
                        :icon="Download"
                        circle
                        size="small"
                        @click="downloadImage(image.url, image.filename)"
                        title="下载"
                      />
                    </div>
                  </div>
                  <div class="image-name">{{ image.filename }}</div>
                </div>
              </div>
            </div>
          </el-card>
        </div>
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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  Document,
  Delete,
  Promotion,
  Download,
  ZoomIn
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { pdfToImage } from '@/api/tools'

const router = useRouter()
const userStore = useUserStore()

const uploadRef = ref(null)
const pdfFile = ref(null)
const converting = ref(false)
const convertingProgress = ref(0)
const result = ref(null)
const previewVisible = ref(false)
const previewImageUrl = ref('')

const uploadUrl = '/api/tools/pdf-to-image'

const form = ref({
  imageFormat: 'png',
  dpi: 200,
  pageRange: ''
})

// 返回上一页
function goBack() {
  router.back()
}

// 文件选择
function handleFileChange(file) {
  pdfFile.value = file.raw
}

// 移除文件
function handleFileRemove() {
  pdfFile.value = null
  result.value = null
}

// 移除文件（手动）
function removeFile() {
  pdfFile.value = null
  result.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// 上传前验证
function beforeUpload(file) {
  const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  const isLt100M = file.size / 1024 / 1024 < 100

  if (!isPDF) {
    ElMessage.error('只能上传PDF格式的文件!')
    return false
  }
  if (!isLt100M) {
    ElMessage.error('文件大小不能超过 100MB!')
    return false
  }
  return false // 阻止自动上传
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 转换PDF
async function handleConvert() {
  if (!pdfFile.value) {
    ElMessage.warning('请先上传PDF文件')
    return
  }

  converting.value = true
  convertingProgress.value = 0
  result.value = null

  // 模拟进度
  const progressTimer = setInterval(() => {
    if (convertingProgress.value < 90) {
      convertingProgress.value += 10
    }
  }, 500)

  try {
    const formData = new FormData()
    formData.append('file', pdfFile.value)
    formData.append('image_format', form.value.imageFormat)
    formData.append('dpi', form.value.dpi.toString())
    if (form.value.pageRange) {
      formData.append('page_range', form.value.pageRange)
    }

    const response = await pdfToImage(formData)
    clearInterval(progressTimer)
    convertingProgress.value = 100

    if (response.code === 200) {
      result.value = response.data
      ElMessage.success(response.data.message || '转换成功')
      // 转换成功后，清理上传的文件列表（源PDF已在服务器端删除）
      pdfFile.value = null
      if (uploadRef.value) {
        uploadRef.value.clearFiles()
      }
    } else {
      ElMessage.error(response.message || '转换失败')
    }
  } catch (error) {
    clearInterval(progressTimer)
    console.error('PDF转换失败:', error)
    ElMessage.error('转换失败，请稍后重试')
  } finally {
    converting.value = false
    setTimeout(() => {
      convertingProgress.value = 0
    }, 1000)
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
    const link = document.createElement('a')
    link.href = imageUrl
    link.download = filename || 'image.png'
    link.target = '_blank'

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

// 下载ZIP
function downloadZip() {
  if (!result.value || !result.value.zip_url) {
    ElMessage.warning('ZIP文件不存在')
    return
  }

  try {
    const link = document.createElement('a')
    link.href = result.value.zip_url
    link.download = `pdf_images_${new Date().getTime()}.zip`
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success('ZIP文件下载中...')
  } catch (error) {
    console.error('下载ZIP失败:', error)
    ElMessage.error('下载ZIP失败')
  }
}
</script>

<style scoped lang="scss">
.pdf-to-image-page {
  min-height: calc(100vh - 60px);
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto; // 允许垂直滚动
  height: calc(100vh - 60px); // 限制高度，确保可以滚动
  
  // 小屏幕适配
  @media screen and (max-width: 768px) {
    padding: 12px;
    height: calc(100vh - 60px);
  }
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100%; // 确保内容至少占满容器
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-shrink: 0; // 防止头部被压缩

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    h2 {
      font-size: 24px;
      font-weight: bold;
      color: #111111;
      margin: 0;
      
      // 小屏幕适配
      @media screen and (max-width: 768px) {
        font-size: 20px;
      }
    }
  }
}

.main-content {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  align-items: start; // 顶部对齐，避免拉伸

  @media screen and (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  // 在小屏幕上，确保内容可以正常显示
  @media screen and (max-width: 1200px) {
    width: 100%;
  }
}

.right-panel {
  min-height: 600px;
  // 确保在小屏幕上也能正常显示
  @media screen and (max-width: 1200px) {
    width: 100%;
    min-height: auto;
  }
}

.upload-card,
.settings-card,
.result-card {
  // 确保卡片内容不会溢出
  overflow: visible;
  
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: bold;
  }
  
  // 在小屏幕上，确保卡片内容可以正常显示
  @media screen and (max-width: 768px) {
    :deep(.el-card__body) {
      padding: 16px;
    }
  }
}

.pdf-uploader {
  width: 100%;

  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    width: 100%;
    height: 200px;
    border: 2px dashed #d9d9d9;
    border-radius: 8px;
    background: #fafafa;
    transition: all 0.3s;

    &:hover {
      border-color: #409EFF;
      background: #f0f7ff;
    }
  }
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;

  .upload-text {
    margin-top: 16px;
    text-align: center;

    .upload-title {
      font-size: 16px;
      color: #333;
      margin: 8px 0;
    }

    .upload-tips {
      font-size: 12px;
      color: #999;
      margin: 0;
    }
  }
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;

  .file-name {
    flex: 1;
    font-size: 14px;
    color: #333;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-size {
    font-size: 12px;
    color: #999;
  }
}

.dpi-tips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: #666;

  .tip-item {
    padding: 2px 8px;
    background: #f0f7ff;
    border-radius: 4px;
  }
}

.page-range-tips {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.action-buttons {
  margin-top: 24px;
}

.empty-result {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.converting-result {
  padding: 40px 20px;
  text-align: center;

  .converting-text {
    margin-top: 20px;
    color: #666;
    font-size: 14px;
  }
}

.result-content {
  .result-info {
    display: flex;
    gap: 24px;
    margin-bottom: 24px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 8px;

    .info-item {
      .label {
        color: #666;
        margin-right: 8px;
      }

      .value {
        color: #333;
        font-weight: bold;
      }
    }
  }

  .images-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;

    .image-item {
      .image-wrapper {
        position: relative;
        width: 100%;
        padding-top: 141.4%; // A4比例
        background: #f5f7fa;
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;

        img {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          object-fit: contain;
          transition: transform 0.3s;
        }

        .image-overlay {
          position: absolute;
          top: 8px;
          right: 8px;
          display: flex;
          gap: 8px;
          opacity: 0;
          transition: opacity 0.3s;
        }

        &:hover {
          img {
            transform: scale(1.05);
          }

          .image-overlay {
            opacity: 1;
          }
        }
      }

      .image-name {
        margin-top: 8px;
        font-size: 12px;
        color: #666;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
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

