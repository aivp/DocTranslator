<template>
  <div class="image-translate-page">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="page-header">
        <div class="header-left">
          <el-button :icon="ArrowLeft" circle @click="goBack" />
          <h2>图片翻译</h2>
        </div>
        <div class="header-right">
          <el-button :icon="List" @click="goToList">查看任务列表</el-button>
        </div>
      </div>

      <div class="page-content">
        <!-- 上传区域（仅在没有图片时显示） -->
        <div class="upload-section" v-if="imageList.length === 0">
          <el-upload
            ref="uploadRef"
            class="image-uploader"
            drag
            :action="uploadUrl"
            :accept="imageAccepts"
            :auto-upload="false"
            :limit="10"
            multiple
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :on-exceed="handleExceed"
            :before-upload="beforeUpload"
            :headers="{ Authorization: 'Bearer ' + userStore.token }"
          >
            <div class="upload-area">
              <div class="upload-icon-wrapper">
                <el-icon :size="64" color="#409EFF">
                  <Picture />
                </el-icon>
              </div>
              <div class="upload-text">
                <p class="upload-title">点击或拖拽图片到此处上传</p>
                <p class="upload-tips">支持 JPG、PNG、WEBP、GIF 格式，最多10张，每张 ≤ 10MB</p>
              </div>
            </div>
          </el-upload>
        </div>

        <!-- 主要内容区域：图片预览 + 翻译设置（有图片时显示） -->
        <div class="main-content" v-if="imageList.length > 0">
          <!-- 左侧：图片预览 -->
          <div class="preview-section">
            <div class="section-header">
              <div class="header-left">
                <h3>已上传图片</h3>
                <span class="image-count">{{ imageList.length }}/10</span>
              </div>
              <div class="header-right">
                <el-upload
                  ref="compactUploadRef"
                  class="compact-uploader"
                  :action="uploadUrl"
                  :accept="imageAccepts"
                  :auto-upload="false"
                  :limit="10"
                  multiple
                  :on-change="handleFileChange"
                  :on-remove="handleFileRemove"
                  :on-exceed="handleExceed"
                  :before-upload="beforeUpload"
                  :headers="{ Authorization: 'Bearer ' + userStore.token }"
                  :show-file-list="false"
                  v-if="imageList.length < 10"
                >
                  <el-button type="primary" size="small" :icon="Plus" plain>添加图片</el-button>
                </el-upload>
              </div>
            </div>
            <div class="preview-grid">
              <div 
                v-for="(item, index) in imageList" 
                :key="index"
                class="preview-item"
                :class="{ 'uploading': item.uploading, 'uploaded': item.uploaded, 'error': item.error }"
              >
                <div class="preview-image-wrapper">
                  <img :src="item.preview" class="preview-thumb" />
                  <div class="preview-overlay" v-if="item.uploading">
                    <el-progress 
                      :percentage="item.progress || 0" 
                      :status="item.error ? 'exception' : undefined"
                      :width="50"
                      type="circle"
                    />
                  </div>
                  <div class="preview-overlay success" v-if="item.uploaded && !item.uploading">
                    <el-icon :size="24" color="#fff"><Check /></el-icon>
                  </div>
                  <div class="preview-overlay error" v-if="item.error">
                    <el-icon :size="24" color="#fff"><Close /></el-icon>
                  </div>
                  <div class="preview-actions-overlay">
                    <el-button
                      type="danger"
                      :icon="Delete"
                      circle
                      size="small"
                      @click="removeImage(index)"
                      :disabled="item.uploading"
                    />
                  </div>
                </div>
                <div class="preview-info">
                  <div class="preview-name" :title="item.name">{{ item.name }}</div>
                  <div class="preview-size">{{ formatFileSize(item.size) }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：翻译设置 -->
          <div class="settings-section">
            <div class="section-header">
              <h3>翻译设置</h3>
            </div>
            <el-form :model="form" label-width="90px" label-position="top" class="translate-form">
              <el-form-item label="源语言" required>
                <el-select 
                  v-model="form.sourceLanguage" 
                  placeholder="请选择源语言" 
                  size="large"
                  style="width: 100%"
                >
                  <el-option
                    v-for="lang in sourceLanguages"
                    :key="lang.value"
                    :label="lang.label"
                    :value="lang.value"
                  />
                </el-select>
                <div class="form-tip">必须选择源语言</div>
              </el-form-item>
              <el-form-item label="目标语言" required>
                <el-select 
                  v-model="form.targetLanguage" 
                  placeholder="请选择目标语言" 
                  size="large"
                  style="width: 100%"
                >
                  <el-option
                    v-for="lang in targetLanguages"
                    :key="lang.value"
                    :label="lang.label"
                    :value="lang.value"
                  />
                </el-select>
                <div class="form-tip">至少有一个是中文或英文</div>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- 错误信息 -->
        <div class="error-section" v-if="errorMessage">
          <el-alert
            :title="errorMessage"
            type="error"
            :closable="false"
            show-icon
          />
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="page-footer" v-if="imageList.length > 0">
        <el-button @click="goBack" size="large">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleTranslate"
          :loading="submitting"
          :disabled="imageList.length === 0 || !form.sourceLanguage || !form.targetLanguage || hasUploading || submitting"
          size="large"
        >
          <el-icon v-if="!submitting" style="margin-right: 4px"><Promotion /></el-icon>
          {{ submitting ? '提交中...' : `提交翻译（${imageList.length}张）` }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Picture, Delete, Check, Close, Plus, Promotion, ArrowLeft, List } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { uploadImage, translateImageBatch } from '@/api/tools'

const router = useRouter()
const userStore = useUserStore()
const uploadRef = ref(null)
const compactUploadRef = ref(null)

const imageAccepts = 'image/jpeg,image/jpg,image/png,image/webp,image/gif'
const uploadUrl = '/api/tools/image-upload'

// 图片列表，每个元素包含：file, preview, name, size, uploading, uploaded, error, progress, imageId, savePath
const imageList = ref([])
const form = ref({
  sourceLanguage: '',      // 源语言，必选
  targetLanguage: 'zh'     // 目标语言
})
const submitting = ref(false)
const errorMessage = ref('')

// 语言列表 - 根据 Qwen-MT-Image API 文档
const sourceLanguages = [
  { label: '简体中文', value: 'zh', canBeSource: true, canBeTarget: true },
  { label: '英文', value: 'en', canBeSource: true, canBeTarget: true },
  { label: '韩语', value: 'ko', canBeSource: true, canBeTarget: true },
  { label: '日语', value: 'ja', canBeSource: true, canBeTarget: true },
  { label: '俄语', value: 'ru', canBeSource: true, canBeTarget: true },
  { label: '西班牙语', value: 'es', canBeSource: true, canBeTarget: true },
  { label: '法语', value: 'fr', canBeSource: true, canBeTarget: true },
  { label: '葡萄牙语', value: 'pt', canBeSource: true, canBeTarget: true },
  { label: '意大利语', value: 'it', canBeSource: true, canBeTarget: true },
  { label: '德语', value: 'de', canBeSource: true, canBeTarget: true }
]

const targetOnlyLanguages = [
  { label: '越南语', value: 'vi', canBeSource: false, canBeTarget: true },
  { label: '马来语', value: 'ms', canBeSource: false, canBeTarget: true },
  { label: '泰语', value: 'th', canBeSource: false, canBeTarget: true },
  { label: '印尼语', value: 'id', canBeSource: false, canBeTarget: true },
  { label: '阿拉伯语', value: 'ar', canBeSource: false, canBeTarget: true }
]

const targetLanguages = [...sourceLanguages, ...targetOnlyLanguages]

// 是否有正在上传的图片
const hasUploading = computed(() => {
  return imageList.value.some(item => item.uploading)
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
  if (imageList.value.length >= 10) {
    ElMessage.warning('最多只能上传10张图片')
    return
  }

  // 检查文件是否已存在（根据文件名和大小判断）
  const exists = imageList.value.some(item => 
    item.name === file.name && item.size === file.raw.size
  )
  if (exists) {
    ElMessage.warning('该图片已存在，请勿重复添加')
    return
  }

  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
  if (!allowedTypes.includes(file.raw.type)) {
    ElMessage.error('不支持的图片格式')
    return
  }

  // 验证文件大小（10MB）
  const maxSize = 10 * 1024 * 1024
  if (file.raw.size > maxSize) {
    ElMessage.error('图片大小不能超过10MB')
    return
  }

  // 生成预览
  const reader = new FileReader()
  reader.onload = (e) => {
    const imageItem = {
      file: file.raw,
      preview: e.target.result,
      name: file.name,
      size: file.raw.size,
      uploading: false,
      uploaded: false,
      error: false,
      progress: 0,
      imageId: null,
      savePath: null
    }
    imageList.value.push(imageItem)
  }
  reader.readAsDataURL(file.raw)
}

// 文件移除处理
function handleFileRemove(file, fileList) {
  // 从imageList中移除对应的文件
  const index = imageList.value.findIndex(item => item.name === file.name)
  if (index !== -1) {
    imageList.value.splice(index, 1)
  }
}

// 移除图片
function removeImage(index) {
  imageList.value.splice(index, 1)
}

// 超出限制处理
function handleExceed() {
  ElMessage.warning('最多只能上传10张图片')
}

// 上传前验证
function beforeUpload(file) {
  return false // 阻止自动上传，手动控制
}

// 返回上一页
function goBack() {
  router.back()
}

// 跳转到任务列表
function goToList() {
  router.push('/tools/image-translate/list')
}

// 提交翻译
async function handleTranslate() {
  // 验证语言选择
  if (!form.value.sourceLanguage) {
    ElMessage.error('请选择源语言')
    return
  }
  if (!form.value.targetLanguage) {
    ElMessage.error('请选择目标语言')
    return
  }

  // 验证语言组合
  const isSourceZhOrEn = form.value.sourceLanguage === 'zh' || form.value.sourceLanguage === 'en'
  const isTargetZhOrEn = form.value.targetLanguage === 'zh' || form.value.targetLanguage === 'en'
  if (!isSourceZhOrEn && !isTargetZhOrEn) {
    ElMessage.error('源语言和目标语言必须至少有一种是中文或英文')
    return
  }

  // 先上传所有图片
  submitting.value = true
  errorMessage.value = ''

  try {
    const uploadPromises = imageList.value.map(async (item, index) => {
      if (item.uploaded && item.savePath) {
        return { index, success: true, savePath: item.savePath }
      }

      item.uploading = true
      item.progress = 0
      item.error = false

      try {
        const formData = new FormData()
        formData.append('file', item.file)

        const response = await uploadImage(formData)
        if (response.code === 200) {
          item.uploaded = true
          item.uploading = false
          item.savePath = response.data.save_path
          item.imageId = response.data.id || null
          return { index, success: true, savePath: response.data.save_path }
        } else {
          throw new Error(response.message || '上传失败')
        }
      } catch (error) {
        item.uploading = false
        item.error = true
        console.error(`图片 ${item.name} 上传失败:`, error)
        return { index, success: false, error: error.message || '上传失败' }
      }
    })

    const uploadResults = await Promise.all(uploadPromises)
    const failedUploads = uploadResults.filter(r => !r.success)

    if (failedUploads.length > 0) {
      errorMessage.value = `${failedUploads.length}张图片上传失败，请重试`
      submitting.value = false
      return
    }

    // 所有图片上传成功后，批量提交翻译任务（后端控制并发和延迟）
    try {
      const imageIds = imageList.value
        .filter(item => item.uploaded && item.imageId)
        .map(item => item.imageId)

      if (imageIds.length === 0) {
        ElMessage.error('没有可提交的图片')
        submitting.value = false
        return
      }

      const response = await translateImageBatch({
        image_ids: imageIds,
        source_language: form.value.sourceLanguage,
        target_language: form.value.targetLanguage
      })

      if (response.code === 200) {
        const { success_count, failed_count, message } = response.data
        if (failed_count > 0) {
          ElMessage.warning(message || `${failed_count}个翻译任务提交失败，请稍后查看任务列表`)
        } else {
          ElMessage.success('翻译任务已提交，正在跳转到任务列表...')
        }
        
        // 延迟跳转，让用户看到成功消息
        setTimeout(() => {
          router.push('/tools/image-translate/list')
        }, 500)
      } else {
        ElMessage.error(response.message || '提交翻译任务失败，请重试')
      }
    } catch (error) {
      console.error('提交翻译任务失败:', error)
      ElMessage.error('提交翻译任务失败，请重试')
    } finally {
      submitting.value = false
    }

  } catch (error) {
    console.error('提交翻译失败:', error)
    errorMessage.value = error.message || '提交翻译失败，请重试'
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.image-translate-page {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  min-height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
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

  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }
}

.page-content {
  flex: 1;
  background: #ffffff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.upload-section {
  padding: 60px 20px;
}

.image-uploader {
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

  .upload-icon-wrapper {
    margin-bottom: 20px;
  }

  .upload-text {
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

.main-content {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 24px;

  @media screen and (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
}

.preview-section {
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    h3 {
      font-size: 18px;
      font-weight: bold;
      color: #111111;
      margin: 0;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .image-count {
        font-size: 14px;
        color: #999999;
        background: #f5f7fa;
        padding: 4px 12px;
        border-radius: 12px;
      }
    }
  }
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  max-height: 500px;
  overflow-y: auto;
  padding-right: 8px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: #f5f7fa;
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: #d9d9d9;
    border-radius: 3px;

    &:hover {
      background: #bfbfbf;
    }
  }
}

.preview-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.uploading {
    border: 2px solid #409EFF;
  }

  &.uploaded {
    border: 2px solid #67C23A;
  }

  &.error {
    border: 2px solid #F56C6C;
  }
}

.preview-image-wrapper {
  position: relative;
  width: 100%;
  padding-top: 100%;
  background: #f5f7fa;

  .preview-thumb {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .preview-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;

    &.success {
      background: rgba(103, 194, 58, 0.8);
    }

    &.error {
      background: rgba(245, 108, 108, 0.8);
    }
  }

  .preview-actions-overlay {
    position: absolute;
    top: 8px;
    right: 8px;
    opacity: 0;
    transition: opacity 0.3s;
  }

  &:hover .preview-actions-overlay {
    opacity: 1;
  }
}

.preview-info {
  padding: 8px;
  background: #ffffff;

  .preview-name {
    font-size: 12px;
    color: #333333;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 4px;
  }

  .preview-size {
    font-size: 11px;
    color: #999999;
  }
}

.settings-section {
  .section-header {
    margin-bottom: 20px;

    h3 {
      font-size: 18px;
      font-weight: bold;
      color: #111111;
      margin: 0;
    }
  }
}

.translate-form {
  .form-tip {
    font-size: 12px;
    color: #999999;
    margin-top: 4px;
  }
}

.error-section {
  margin-top: 20px;
}

.page-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

@media screen and (max-width: 768px) {
  .page-container {
    padding: 12px;
  }

  .page-content {
    padding: 16px;
  }

  .main-content {
    gap: 16px;
  }

  .preview-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
  }
}
</style>

