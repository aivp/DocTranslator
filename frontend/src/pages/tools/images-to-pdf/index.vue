<template>
  <div class="images-to-pdf-page">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="page-header">
        <div class="header-left">
          <el-button :icon="ArrowLeft" circle @click="goBack" />
          <h2>图片合并PDF</h2>
        </div>
      </div>

      <!-- 主要内容 -->
      <div class="main-content">
        <!-- 左侧：上传和设置 -->
        <div class="left-panel">
          <el-card class="upload-card">
            <template #header>
              <div class="card-header">
                <span>上传图片</span>
              </div>
            </template>

            <el-upload
              ref="uploadRef"
              class="images-uploader"
              drag
              :action="uploadUrl"
              :auto-upload="false"
              :limit="50"
              multiple
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :before-upload="beforeUpload"
              accept="image/jpeg,image/jpg,image/png,image/webp,image/gif,image/bmp"
              :headers="{ Authorization: 'Bearer ' + userStore.token }"
            >
              <div class="upload-area">
                <el-icon :size="64" color="#409EFF">
                  <Picture />
                </el-icon>
                <div class="upload-text">
                  <p class="upload-title">点击或拖拽图片到此处上传</p>
                  <p class="upload-tips">支持 JPG、PNG、WEBP、GIF、BMP 格式，最多50张</p>
                </div>
              </div>
            </el-upload>

            <div v-if="imageList.length > 0" class="images-count">
              已上传 {{ imageList.length }} 张图片
            </div>
          </el-card>

          <el-card class="settings-card" v-if="imageList.length > 0">
            <template #header>
              <div class="card-header">
                <span>PDF设置</span>
              </div>
            </template>

            <el-form :model="form" label-width="120px" label-position="left">
              <el-form-item label="页面尺寸">
                <el-select v-model="form.pageSizePreset" placeholder="请选择页面尺寸" style="width: 100%">
                  <el-option-group label="A4">
                    <el-option label="A4 竖版 (210mm × 297mm)" value="A4" />
                    <el-option label="A4 横版 (297mm × 210mm)" value="A4-Landscape" />
                  </el-option-group>
                  <el-option-group label="A3">
                    <el-option label="A3 竖版 (297mm × 420mm)" value="A3" />
                    <el-option label="A3 横版 (420mm × 297mm)" value="A3-Landscape" />
                  </el-option-group>
                  <el-option-group label="A5">
                    <el-option label="A5 竖版 (148mm × 210mm)" value="A5" />
                    <el-option label="A5 横版 (210mm × 148mm)" value="A5-Landscape" />
                  </el-option-group>
                  <el-option-group label="Letter">
                    <el-option label="Letter 竖版 (8.5英寸 × 11英寸)" value="Letter" />
                    <el-option label="Letter 横版 (11英寸 × 8.5英寸)" value="Letter-Landscape" />
                  </el-option-group>
                  <el-option-group label="Legal">
                    <el-option label="Legal 竖版 (8.5英寸 × 14英寸)" value="Legal" />
                    <el-option label="Legal 横版 (14英寸 × 8.5英寸)" value="Legal-Landscape" />
                  </el-option-group>
                </el-select>
              </el-form-item>

              <el-form-item label="适应模式">
                <el-select v-model="form.fitMode" placeholder="请选择适应模式" style="width: 100%">
                  <el-option label="适应（保持比例，适应页面）" value="fit" />
                  <el-option label="拉伸（填满页面，不保持比例）" value="stretch" />
                  <el-option label="居中（保持原始尺寸，居中显示）" value="center" />
                </el-select>
              </el-form-item>

              <el-form-item label="边距">
                <el-input-number
                  v-model="form.margin"
                  :min="0"
                  :max="100"
                  :step="5"
                  placeholder="边距"
                  style="width: 100%"
                />
                <div class="margin-tips">单位：点（72 DPI），仅在"适应"模式下生效</div>
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <!-- 右侧：图片列表和预览 -->
        <div class="right-panel" v-if="imageList.length > 0">
          <el-card class="images-card">
            <template #header>
              <div class="card-header">
                <span>图片列表（可拖拽调整顺序）</span>
                <el-button type="danger" size="small" @click="clearAll">清空全部</el-button>
              </div>
            </template>

            <div class="images-list" v-if="imageList.length > 0">
              <div
                v-for="(item, index) in imageList"
                :key="item.id"
                class="image-item"
                :class="{ 'dragging': draggedIndex === index }"
                draggable="true"
                @dragstart="handleDragStart(index, $event)"
                @dragover.prevent="handleDragOver(index, $event)"
                @drop="handleDrop(index, $event)"
                @dragend="handleDragEnd"
              >
                <div class="image-preview">
                  <img :src="item.preview" :alt="item.name" />
                  <div class="image-overlay">
                    <div class="image-index">{{ index + 1 }}</div>
                    <el-button
                      type="danger"
                      :icon="Delete"
                      circle
                      size="small"
                      @click="removeImage(index)"
                    />
                  </div>
                </div>
                <div class="image-info">
                  <div class="image-name" :title="item.name">{{ item.name }}</div>
                  <div class="image-size">{{ formatFileSize(item.size) }}</div>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 生成成功提示 -->
      <el-card v-if="generatedPdfUrl" class="success-card">
        <div class="success-content">
          <div class="success-icon">
            <el-icon :size="48" color="#67C23A"><CircleCheckFilled /></el-icon>
          </div>
          <div class="success-info">
            <h3>PDF生成成功！</h3>
            <p>已成功合并 {{ imageList.length }} 张图片为PDF文件</p>
            <div class="download-tip">
              <el-icon class="tip-icon"><Warning /></el-icon>
              <span class="tip-text">请尽快下载，页面关闭后将清理生成的文件</span>
            </div>
          </div>
          <div class="success-actions">
            <el-button type="primary" :icon="Download" @click="downloadPdf" size="large" class="download-btn">
              下载PDF
            </el-button>
            <el-button @click="resetAndContinue" size="large">继续合并</el-button>
          </div>
        </div>
      </el-card>

      <!-- 底部操作栏 -->
      <div class="page-footer" v-if="imageList.length > 0 && !generatedPdfUrl">
        <el-button @click="goBack" size="large">取消</el-button>
        <el-button
          type="primary"
          @click="handleGenerate"
          :loading="generating"
          :disabled="imageList.length === 0 || generating"
          size="large"
          class="generate-btn"
        >
          <el-icon v-if="!generating" class="generate-icon"><Document /></el-icon>
          <span class="generate-text">{{ generating ? '生成中...' : `生成PDF（${imageList.length}张）` }}</span>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture, Delete, Document, ArrowLeft, CircleCheckFilled, Download, Warning } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { imagesToPdf } from '@/api/tools'

const router = useRouter()
const userStore = useUserStore()
const uploadRef = ref(null)

const imageList = ref([])
const draggedIndex = ref(-1)
const generating = ref(false)
const generatedPdfUrl = ref('')

const form = ref({
  pageSizePreset: 'A4',
  fitMode: 'fit',
  margin: 0
})

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 文件选择处理
function handleFileChange(file, fileList) {
  // 检查是否超过限制
  if (imageList.value.length >= 50) {
    ElMessage.warning('最多只能上传50张图片')
    return
  }

  // 检查文件是否已存在
  const exists = imageList.value.some(item => 
    item.name === file.name && item.size === file.raw.size
  )
  if (exists) {
    ElMessage.warning('该图片已存在，请勿重复添加')
    return
  }

  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif', 'image/bmp']
  if (!allowedTypes.includes(file.raw.type)) {
    ElMessage.error('不支持的图片格式')
    return
  }

  // 验证文件大小（50MB）
  const maxSize = 50 * 1024 * 1024
  if (file.raw.size > maxSize) {
    ElMessage.error('图片大小不能超过50MB')
    return
  }

  // 生成预览
  const reader = new FileReader()
  reader.onload = (e) => {
    const imageItem = {
      id: Date.now() + Math.random(), // 唯一ID
      file: file.raw,
      preview: e.target.result,
      name: file.name,
      size: file.raw.size
    }
    imageList.value.push(imageItem)
  }
  reader.readAsDataURL(file.raw)
}

// 文件移除处理
function handleFileRemove(file, fileList) {
  const index = imageList.value.findIndex(item => item.name === file.name)
  if (index !== -1) {
    imageList.value.splice(index, 1)
  }
}

// 移除图片
function removeImage(index) {
  const item = imageList.value[index]
  imageList.value.splice(index, 1)
  // 同时从upload组件中移除
  if (uploadRef.value && item) {
    const fileList = uploadRef.value.uploadFiles
    const fileIndex = fileList.findIndex(f => f.name === item.name)
    if (fileIndex !== -1) {
      uploadRef.value.handleRemove(fileList[fileIndex])
    }
  }
}

// 清空全部
async function clearAll() {
  // 如果有已生成的PDF，先提示确认
  if (generatedPdfUrl.value) {
    try {
      await ElMessageBox.confirm(
        '清空后将无法下载已生成的PDF文件，确定要继续吗？',
        '确认清空',
        {
          confirmButtonText: '确定清空',
          cancelButtonText: '取消',
          type: 'warning',
          distinguishCancelAndClose: true
        }
      )
      // 用户确认，清空所有内容
      generatedPdfUrl.value = ''
      imageList.value = []
      if (uploadRef.value) {
        uploadRef.value.clearFiles()
      }
      ElMessage.success('已清空')
    } catch {
      // 用户取消，不做任何操作
    }
  } else {
    // 没有生成的PDF，直接清空
    imageList.value = []
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
    ElMessage.success('已清空')
  }
}

// 上传前验证
function beforeUpload(file) {
  return false // 阻止自动上传，手动控制
}

// 拖拽开始
function handleDragStart(index, event) {
  draggedIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
}

// 拖拽悬停
function handleDragOver(index, event) {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

// 拖拽放下
function handleDrop(index, event) {
  event.preventDefault()
  if (draggedIndex.value === -1 || draggedIndex.value === index) {
    return
  }

  // 移动图片
  const draggedItem = imageList.value[draggedIndex.value]
  imageList.value.splice(draggedIndex.value, 1)
  imageList.value.splice(index, 0, draggedItem)
  
  draggedIndex.value = -1
}

// 拖拽结束
function handleDragEnd() {
  draggedIndex.value = -1
}

// 返回上一页
function goBack() {
  router.back()
}

// 下载PDF
function downloadPdf() {
  if (!generatedPdfUrl.value) {
    ElMessage.warning('PDF链接不存在')
    return
  }
  
  // 先检查文件是否存在（异步检测，不阻塞下载）
  fetch(generatedPdfUrl.value, { method: 'HEAD' })
    .then(response => {
      if (response.status === 404) {
        // 文件不存在，已过期
        ElMessage.error({
          message: '文件已过期，请重新生成PDF',
          duration: 5000
        })
        generatedPdfUrl.value = ''
      }
    })
    .catch(() => {
      // HEAD请求失败不影响下载，继续尝试下载
    })
  
  // 直接使用a标签下载（和之前自动下载的方式一样）
  try {
    const link = document.createElement('a')
    link.href = generatedPdfUrl.value
    link.download = `合并图片_${Date.now()}.pdf`
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('下载PDF失败:', error)
    ElMessage.error('下载失败，请重试')
  }
}

// 重置并继续
async function resetAndContinue() {
  // 如果有已生成的PDF，先提示确认
  if (generatedPdfUrl.value) {
    try {
      await ElMessageBox.confirm(
        '继续合并将清空当前已生成的PDF文件，确定要继续吗？',
        '确认继续合并',
        {
          confirmButtonText: '确定继续',
          cancelButtonText: '取消',
          type: 'warning',
          distinguishCancelAndClose: true
        }
      )
      // 用户确认，清空所有内容
      generatedPdfUrl.value = ''
      imageList.value = []
      if (uploadRef.value) {
        uploadRef.value.clearFiles()
      }
      ElMessage.success('已清空，可以继续上传图片')
    } catch {
      // 用户取消，不做任何操作
    }
  } else {
    // 没有生成的PDF，直接清空
    generatedPdfUrl.value = ''
    imageList.value = []
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
  }
}

// 生成PDF
async function handleGenerate() {
  if (imageList.value.length === 0) {
    ElMessage.warning('请先上传图片')
    return
  }

  generating.value = true

  try {
    // 准备FormData
    const formData = new FormData()
    
    // 添加所有图片文件
    imageList.value.forEach(item => {
      formData.append('files', item.file)
    })

    // 准备参数
    const params = {
      page_size_preset: form.value.pageSizePreset,
      page_size: null,
      fit_mode: form.value.fitMode,
      margin: form.value.margin,
      image_order: imageList.value.map((_, index) => index) // 当前顺序
    }

    formData.append('data', JSON.stringify(params))

    // 调用API
    const response = await imagesToPdf(formData)

    if (response.code === 200) {
      // 保存PDF URL，不自动下载
      const pdfUrl = response.data.pdf_url
      if (pdfUrl) {
        generatedPdfUrl.value = pdfUrl
        ElMessage.success('PDF生成成功！请点击下载按钮下载文件')
      } else {
        ElMessage.error('生成成功但未获取到下载链接')
      }
    } else {
      ElMessage.error(response.message || '生成PDF失败')
    }
  } catch (error) {
    console.error('生成PDF失败:', error)
    ElMessage.error('生成PDF失败，请重试')
  } finally {
    generating.value = false
  }
}
</script>

<style scoped lang="scss">
.images-to-pdf-page {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
  height: calc(100vh - 60px); // 限制高度，确保可以滚动
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100%; // 确保内容至少占满容器
  display: flex;
  flex-direction: column;
  
  // 小屏幕适配
  @media screen and (max-width: 768px) {
    padding: 12px;
  }
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
  flex: 1;
  align-items: start; // 顶部对齐，避免拉伸

  @media screen and (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  
  // 在小屏幕上，确保内容可以正常显示
  @media screen and (max-width: 1024px) {
    width: 100%;
  }
}

.right-panel {
  display: flex;
  flex-direction: column;
  
  // 在小屏幕上，确保内容可以正常显示
  @media screen and (max-width: 1024px) {
    width: 100%;
  }
}

.upload-card,
.settings-card,
.images-card {
  // 确保卡片内容不会溢出
  overflow: visible;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
  
  // 在小屏幕上，确保卡片内容可以正常显示
  @media screen and (max-width: 768px) {
    :deep(.el-card__body) {
      padding: 16px;
    }
  }
}

.images-uploader {
  width: 100%;

  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    width: 100%;
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
  padding: 40px;
  text-align: center;

  .upload-text {
    margin-top: 20px;

    .upload-title {
      font-size: 16px;
      color: #333333;
      margin-bottom: 8px;
    }

    .upload-tips {
      font-size: 14px;
      color: #999999;
    }
  }
}

.images-count {
  margin-top: 16px;
  padding: 12px;
  background: #f0f7ff;
  border-radius: 6px;
  text-align: center;
  color: #409EFF;
  font-weight: 500;
}

.margin-tips {
  margin-top: 8px;
  font-size: 12px;
  color: #999999;
}

.images-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  max-height: calc(100vh - 300px);
  overflow-y: auto;
  padding: 8px;
  
  // 小屏幕适配：降低最大高度，确保可以滚动
  @media screen and (max-width: 768px) {
    max-height: calc(100vh - 400px);
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
  }
}

.image-item {
  position: relative;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  transition: all 0.3s;
  cursor: move;

  &:hover {
    border-color: #409EFF;
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
    transform: translateY(-2px);
  }

  &.dragging {
    opacity: 0.5;
    border-color: #409EFF;
  }

  .image-preview {
    position: relative;
    width: 100%;
    padding-top: 100%;
    background: #f5f5f5;

    img {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .image-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.3s;

      .image-index {
        position: absolute;
        top: 8px;
        left: 8px;
        background: #409EFF;
        color: #fff;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: bold;
      }
    }

    &:hover .image-overlay {
      opacity: 1;
    }
  }

  .image-info {
    padding: 8px;
    background: #fff;

    .image-name {
      font-size: 12px;
      color: #333333;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      margin-bottom: 4px;
    }

    .image-size {
      font-size: 11px;
      color: #999999;
    }
  }
}

.success-card {
  margin-top: 24px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 2px solid #67C23A;
  
  .success-content {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 20px;
    
    .success-icon {
      flex-shrink: 0;
    }
    
    .success-info {
      flex: 1;
      
      h3 {
        font-size: 20px;
        font-weight: bold;
        color: #67C23A;
        margin: 0 0 8px 0;
      }
      
      p {
        font-size: 14px;
        color: #666666;
        margin: 0 0 12px 0;
      }
      
      .download-tip {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 14px;
        background: linear-gradient(135deg, #fff7e6 0%, #fff3cd 100%);
        border: 1px solid #ffd591;
        border-radius: 6px;
        margin-top: 12px;
        animation: fadeInUp 0.5s ease;
        
        .tip-icon {
          font-size: 18px;
          color: #fa8c16;
          flex-shrink: 0;
          animation: pulse 2s infinite;
        }
        
        .tip-text {
          font-size: 14px;
          color: #d46b08;
          font-weight: 500;
          line-height: 1.5;
        }
      }
    }
    
    .download-btn {
      box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
      
      &:hover {
        box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
      }
    }
    
    .success-actions {
      display: flex;
      gap: 12px;
      flex-shrink: 0;
    }
  }
}

.page-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
  padding: 24px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border-top: 2px solid #f0f0f0;
  flex-shrink: 0; // 防止底部被压缩
  
  // 小屏幕适配
  @media screen and (max-width: 768px) {
    padding: 16px;
    flex-direction: column;
    
    .generate-btn {
      width: 100%;
      min-width: auto;
    }
  }
  
  .generate-btn {
    min-width: 200px;
    height: 56px;
    font-size: 18px;
    font-weight: 600;
    background: linear-gradient(135deg, #409EFF 0%, #67C23A 100%);
    border: none;
    box-shadow: 0 4px 16px rgba(64, 158, 255, 0.4);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
    
    &:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(64, 158, 255, 0.5);
      background: linear-gradient(135deg, #66b1ff 0%, #85ce61 100%);
    }
    
    &:active:not(:disabled) {
      transform: translateY(0);
      box-shadow: 0 2px 8px rgba(64, 158, 255, 0.4);
    }
    
    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    
    .generate-icon {
      font-size: 24px;
      margin-right: 8px;
      animation: pulse 2s infinite;
    }
    
    .generate-text {
      font-weight: 600;
      letter-spacing: 0.5px;
    }
    
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
      transition: left 0.5s;
    }
    
    &:hover:not(:disabled)::before {
      left: 100%;
    }
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media screen and (max-width: 768px) {
  .page-container {
    padding: 12px;
  }

  .main-content {
    gap: 16px;
  }
  
  .success-card {
    margin-top: 16px;
    
    .success-content {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
      
      .success-actions {
        width: 100%;
        flex-direction: column;
        
        .download-btn {
          width: 100%;
        }
      }
    }
  }
}
</style>

