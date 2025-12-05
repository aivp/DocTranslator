<template>
  <el-dialog
    v-model="dialogVisible"
    title="图片翻译"
    width="1200px"
    :close-on-click-modal="false"
    :close-on-press-escape="true"
    @close="handleClose"
    class="image-translate-dialog"
    :fullscreen="isMobile"
    align-center
  >
    <div class="dialog-content">
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

      <!-- 翻译结果 -->
      <div class="result-section" v-if="translationResults.length > 0">
        <div class="section-header">
          <h3>翻译结果</h3>
        </div>
        <div class="result-list">
          <div 
            v-for="(result, index) in translationResults" 
            :key="index"
            class="result-item"
          >
            <div class="result-header">
              <span class="result-image-name">{{ result.imageName }}</span>
              <el-tag :type="result.success ? 'success' : 'danger'" size="small">
                {{ result.success ? '翻译成功' : '翻译失败' }}
              </el-tag>
            </div>
            <div class="result-content" v-if="result.success && result.data">
              <div class="result-text-item" v-if="result.data.original_text">
                <div class="result-label">原文：</div>
                <div class="result-text">{{ result.data.original_text }}</div>
              </div>
              <div class="result-text-item" v-if="result.data.translated_text">
                <div class="result-label">译文：</div>
                <div class="result-text translated">{{ result.data.translated_text }}</div>
              </div>
            </div>
            <div class="result-error" v-if="!result.success">
              {{ result.error || '翻译失败' }}
            </div>
          </div>
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

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose" size="large">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleTranslate"
          :loading="translating"
          :disabled="imageList.length === 0 || !form.sourceLanguage || !form.targetLanguage || hasUploading || translating"
          size="large"
        >
          <el-icon v-if="!translating" style="margin-right: 4px"><Promotion /></el-icon>
          {{ translating ? '翻译中...' : `开始翻译（${imageList.length}张）` }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, Delete, Check, Close, Plus, Promotion } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { uploadImage, translateImageBatch } from '@/api/tools'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'close'])

const userStore = useUserStore()
const uploadRef = ref(null)
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const imageAccepts = 'image/jpeg,image/jpg,image/png,image/webp'

// 图片列表，每个元素包含：file, preview, name, size, uploading, uploaded, error, progress, imageId, savePath
const imageList = ref([])
const form = ref({
  sourceLanguage: '',      // 源语言，必选
  targetLanguage: 'zh'     // 目标语言
})
const translating = ref(false)
const translationResults = ref([])
const errorMessage = ref('')

// 语言列表 - 根据 Qwen-MT-Image API 文档
// 支持作为源语言和目标语言的语种
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

// 只能作为目标语言的语种
const targetOnlyLanguages = [
  { label: '越南语', value: 'vi', canBeSource: false, canBeTarget: true },
  { label: '马来语', value: 'ms', canBeSource: false, canBeTarget: true },
  { label: '泰语', value: 'th', canBeSource: false, canBeTarget: true },
  { label: '印尼语', value: 'id', canBeSource: false, canBeTarget: true },
  { label: '阿拉伯语', value: 'ar', canBeSource: false, canBeTarget: true }
]

// 所有目标语言（源语言 + 仅目标语言）
const targetLanguages = [...sourceLanguages, ...targetOnlyLanguages]

// 所有语言（用于显示）
const languages = targetLanguages

// 检测是否为移动端
const isMobile = computed(() => {
  return window.innerWidth <= 768
})

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

// 文件变化处理
function handleFileChange(file, fileList) {
  const isImage = file.raw.type.startsWith('image/')
  const isLt10M = file.raw.size / 1024 / 1024 < 10

  if (!isImage) {
    ElMessage.error('只能上传图片文件！')
    uploadRef.value.handleRemove(file)
    return false
  }

  if (!isLt10M) {
    ElMessage.error('图片大小不能超过 10MB！')
    uploadRef.value.handleRemove(file)
    return false
  }

  // 检查是否已存在
  const exists = imageList.value.some(item => item.name === file.name)
  if (exists) {
    ElMessage.warning('该图片已存在')
    uploadRef.value.handleRemove(file)
    return false
  }

  // 创建预览
  const reader = new FileReader()
  reader.onload = (e) => {
    imageList.value.push({
      file: file.raw,
      preview: e.target.result,
      name: file.name,
      size: file.size,
      uploading: false,
      uploaded: false,
      error: false,
      progress: 0,
      imageId: null,
      savePath: null
    })
  }
  reader.readAsDataURL(file.raw)
  
  // 清空之前的结果
  translationResults.value = []
  errorMessage.value = ''
}

// 文件移除处理
function handleFileRemove(file, fileList) {
  const index = imageList.value.findIndex(item => item.name === file.name)
  if (index !== -1) {
    imageList.value.splice(index, 1)
  }
  
  // 如果所有图片都移除了，清空结果
  if (imageList.value.length === 0) {
    translationResults.value = []
  }
}

// 手动移除图片
function removeImage(index) {
  const item = imageList.value[index]
  if (item.uploading) {
    ElMessage.warning('图片正在上传，无法删除')
    return
  }
  
  // 从upload组件中移除
  const fileList = uploadRef.value.uploadFiles
  const fileIndex = fileList.findIndex(f => f.name === item.name)
  if (fileIndex !== -1) {
    uploadRef.value.handleRemove(fileList[fileIndex])
  }
  
  imageList.value.splice(index, 1)
}

// 超出限制处理
function handleExceed(files, fileList) {
  ElMessage.warning(`最多只能上传10张图片，当前已有${fileList.length}张`)
}

// 上传前验证
function beforeUpload(file) {
  const isImage = file.type.startsWith('image/')
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isImage) {
    ElMessage.error('只能上传图片文件！')
    return false
  }
  if (!isLt10M) {
    ElMessage.error('图片大小不能超过 10MB！')
    return false
  }
  return false // 阻止自动上传
}

// 上传单张图片
async function uploadSingleImage(imageItem) {
  const index = imageList.value.findIndex(item => item.name === imageItem.name)
  if (index === -1) return null

  imageList.value[index].uploading = true
  imageList.value[index].progress = 0
  imageList.value[index].error = false

  try {
    const formData = new FormData()
    formData.append('file', imageItem.file)

    const uploadResult = await uploadImage(formData)
    
    if (uploadResult.code !== 200) {
      throw new Error(uploadResult.message || '图片上传失败')
    }

    imageList.value[index].uploaded = true
    // 注意：上传接口不返回id，翻译时才会创建记录并返回id
    imageList.value[index].imageId = uploadResult.data.id || null
    imageList.value[index].savePath = uploadResult.data.save_path
    imageList.value[index].progress = 100
    return uploadResult.data
  } catch (error) {
    imageList.value[index].error = true
    imageList.value[index].uploading = false
    throw error
  } finally {
    imageList.value[index].uploading = false
  }
}

// 验证语言组合是否有效
function validateLanguagePair(sourceLang, targetLang) {
  // 源语言和目标语言都必须选择
  if (!sourceLang || !targetLang) {
    return false
  }
  
  // 规则：源语种或目标语种必须至少有一种是中文或英文
  const isSourceZhOrEn = sourceLang === 'zh' || sourceLang === 'en'
  const isTargetZhOrEn = targetLang === 'zh' || targetLang === 'en'
  
  if (!isSourceZhOrEn && !isTargetZhOrEn) {
    return false
  }
  
  return true
}

// 翻译处理
async function handleTranslate() {
  if (imageList.value.length === 0) {
    ElMessage.warning('请先上传图片')
    return
  }

  if (!form.value.sourceLanguage) {
    ElMessage.warning('请选择源语言')
    return
  }

  if (!form.value.targetLanguage) {
    ElMessage.warning('请选择目标语言')
    return
  }
  
  // 验证语言组合
  if (!validateLanguagePair(form.value.sourceLanguage, form.value.targetLanguage)) {
    ElMessage.error('源语言和目标语言必须至少有一种是中文或英文。不支持在两个非中、英语种之间直接翻译（例如：从日语翻译为韩语）')
    return
  }

  translating.value = true
  errorMessage.value = ''
  translationResults.value = []

  try {
    // 先上传所有图片
    const uploadPromises = imageList.value.map(item => {
      if (item.uploaded && item.savePath) {
        // 已经上传过，直接返回
        return Promise.resolve({ savePath: item.savePath, name: item.name })
      }
      return uploadSingleImage(item).then(data => ({
        savePath: data.save_path || data.url,
        name: item.name
      }))
    })

    const uploadResults = await Promise.allSettled(uploadPromises)
    
    // 检查上传结果
    const failedUploads = uploadResults.filter(r => r.status === 'rejected')
    if (failedUploads.length > 0) {
      ElMessage.warning(`${failedUploads.length}张图片上传失败`)
    }

    // 获取成功上传的图片
    const successUploads = uploadResults
      .filter(r => r.status === 'fulfilled')
      .map(r => {
        const value = r.value
        // 从imageList中找到对应的信息
        const imageItem = imageList.value.find(item => item.name === value.name)
        return {
          ...value,
          imageId: imageItem?.imageId || null,  // 上传时可能没有id
          savePath: imageItem?.savePath || value.save_path
        }
      })

    if (successUploads.length === 0) {
      throw new Error('所有图片上传失败')
    }

    // 批量翻译 - 使用批量接口，后端控制并发和延迟
    const imageIds = successUploads
      .filter(uploadData => uploadData.imageId)
      .map(uploadData => uploadData.imageId)

    if (imageIds.length === 0) {
      throw new Error('没有可翻译的图片ID')
    }

    try {
      const result = await translateImageBatch({
        image_ids: imageIds,
        source_language: form.value.sourceLanguage,
        target_language: form.value.targetLanguage
      })

      if (result.code === 200) {
        const { success_count, failed_count, results: batchResults } = result.data
        
        // 构建翻译结果，匹配原有的数据结构
        translationResults.value = successUploads.map((uploadData) => {
          const batchResult = batchResults?.find(r => r.image_id === uploadData.imageId)
          return {
            imageName: uploadData.name,
            imageId: uploadData.imageId,
            success: batchResult?.success || false,
            data: batchResult?.success ? { image_id: uploadData.imageId } : null,
            error: batchResult?.error || null
          }
        })

        if (failed_count > 0) {
          ElMessage.warning(`成功提交 ${success_count} 个翻译任务，${failed_count} 个失败`)
        } else {
          ElMessage.success(`成功提交 ${success_count} 个翻译任务，正在处理中...`)
        }
      } else {
        throw new Error(result.message || '批量翻译失败')
      }
    } catch (error) {
      console.error('批量翻译失败:', error)
      ElMessage.error(error.message || '批量翻译失败，请稍后重试')
      throw error
    }
  } catch (error) {
    console.error('翻译失败:', error)
    errorMessage.value = error.message || '翻译失败，请稍后重试'
    ElMessage.error(errorMessage.value)
  } finally {
    translating.value = false
  }
}

// 关闭对话框
function handleClose() {
  dialogVisible.value = false
  emit('close')
  // 重置状态
  setTimeout(() => {
    imageList.value = []
    translationResults.value = []
    errorMessage.value = ''
    form.value.sourceLanguage = ''
    form.value.targetLanguage = 'zh'
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
  }, 300)
}

// 监听对话框关闭
watch(() => props.modelValue, (val) => {
  if (!val) {
    handleClose()
  }
})
</script>

<style scoped lang="scss">
.image-translate-dialog {
  ::v-deep(.el-dialog__body) {
    padding: 24px;
    max-height: 75vh;
    overflow-y: auto;
  }

  ::v-deep(.el-dialog__header) {
    padding: 20px 24px;
    border-bottom: 1px solid #f0f0f0;
  }

  ::v-deep(.el-dialog__footer) {
    padding: 16px 24px;
    border-top: 1px solid #f0f0f0;
  }

  ::v-deep(.el-upload-list--picture-card) {
    display: none;
  }
}

.dialog-content {
  // 上传区域（初始状态）
  .upload-section {
    margin-bottom: 0;

    .image-uploader {
      width: 100%;

      ::v-deep(.el-upload-dragger) {
        width: 100%;
        border: 2px dashed #d9d9d9;
        border-radius: 12px;
        background: linear-gradient(135deg, #fafafa 0%, #f5f7fa 100%);
        transition: all 0.3s ease;
        padding: 40px 20px;

        &:hover {
          border-color: #409EFF;
          background: linear-gradient(135deg, #f0f7ff 0%, #e6f2ff 100%);
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
        }
      }

      .upload-area {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;

        .upload-icon-wrapper {
          margin-bottom: 16px;
          padding: 20px;
          background: rgba(64, 158, 255, 0.1);
          border-radius: 50%;
        }

        .upload-text {
          text-align: center;

          .upload-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
          }

          .upload-tips {
            font-size: 14px;
            color: #666;
            line-height: 1.5;
          }
        }
      }
    }
  }


  // 主要内容区域（左右分栏）
  .main-content {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 24px;
    margin-top: 20px;

    @media screen and (max-width: 1024px) {
      grid-template-columns: 1fr;
    }
  }

  // 图片预览区域
  .preview-section {
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 2px solid #f0f0f0;

      .header-left {
        display: flex;
        align-items: center;
        gap: 12px;

        h3 {
          font-size: 16px;
          font-weight: 600;
          color: #333;
          margin: 0;
        }

        .image-count {
          font-size: 14px;
          color: #409EFF;
          font-weight: 500;
          padding: 4px 12px;
          background: #f0f7ff;
          border-radius: 12px;
        }
      }

      .header-right {
        display: flex;
        align-items: center;
      }
    }

    .preview-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
      gap: 12px;
      max-height: 400px;
      overflow-y: auto;
      padding-right: 8px;

      &::-webkit-scrollbar {
        width: 6px;
      }

      &::-webkit-scrollbar-track {
        background: #f5f5f5;
        border-radius: 3px;
      }

      &::-webkit-scrollbar-thumb {
        background: #d9d9d9;
        border-radius: 3px;

        &:hover {
          background: #bfbfbf;
        }
      }

      @media screen and (max-width: 768px) {
        grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
        gap: 10px;
      }
    }

    .preview-item {
      position: relative;
      border: 2px solid #e8e8e8;
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
      transition: all 0.3s ease;
      cursor: pointer;

      &:hover {
        border-color: #409EFF;
        box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
        transform: translateY(-2px);

        .preview-actions-overlay {
          opacity: 1;
        }
      }

      &.uploading {
        border-color: #409EFF;
        box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
      }

      &.uploaded {
        border-color: #67C23A;
      }

      &.error {
        border-color: #F56C6C;
      }

      .preview-image-wrapper {
        position: relative;
        width: 100%;
        padding-top: 100%;
        background: #f5f5f5;

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
          background: rgba(0, 0, 0, 0.6);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 2;

          &.success {
            background: rgba(103, 194, 58, 0.85);
          }

          &.error {
            background: rgba(245, 108, 108, 0.85);
          }
        }

        .preview-actions-overlay {
          position: absolute;
          top: 8px;
          right: 8px;
          opacity: 0;
          transition: opacity 0.3s;
          z-index: 3;
        }
      }

      .preview-info {
        padding: 8px;
        font-size: 12px;
        background: #fff;

        .preview-name {
          color: #333;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          margin-bottom: 4px;
          font-weight: 500;
        }

        .preview-size {
          color: #999;
          font-size: 11px;
        }
      }
    }
  }

  // 翻译设置区域
  .settings-section {
    background: #fff;
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    padding: 20px;
    height: fit-content;
    position: sticky;
    top: 20px;

    .section-header {
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 2px solid #f0f0f0;

      h3 {
        font-size: 16px;
        font-weight: 600;
        color: #333;
        margin: 0;
      }
    }

    .translate-form {
      ::v-deep(.el-form-item__label) {
        font-weight: 500;
        color: #333;
        margin-bottom: 8px;
      }

      ::v-deep(.el-select) {
        .el-input__inner {
          height: 40px;
        }
      }
    }

    .form-tip {
      font-size: 12px;
      color: #999;
      margin-top: 6px;
      line-height: 1.5;
    }
  }

  // 翻译结果区域
  .result-section {
    margin-top: 24px;
    padding: 20px;
    background: #fff;
    border: 1px solid #e8e8e8;
    border-radius: 12px;

    .section-header {
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 2px solid #f0f0f0;

      h3 {
        font-size: 18px;
        font-weight: 600;
        color: #333;
        margin: 0;
      }
    }

    .result-list {
      .result-item {
        margin-bottom: 16px;
        padding: 16px;
        background: #fafafa;
        border-radius: 8px;
        border: 1px solid #e8e8e8;
        transition: all 0.3s;

        &:hover {
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        &:last-child {
          margin-bottom: 0;
        }

        .result-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid #e8e8e8;

          .result-image-name {
            font-size: 15px;
            font-weight: 600;
            color: #333;
          }
        }

        .result-content {
          .result-text-item {
            margin-bottom: 16px;

            &:last-child {
              margin-bottom: 0;
            }

            .result-label {
              font-size: 13px;
              font-weight: 600;
              color: #666;
              margin-bottom: 8px;
              text-transform: uppercase;
              letter-spacing: 0.5px;
            }

            .result-text {
              font-size: 15px;
              color: #333;
              line-height: 1.8;
              padding: 14px;
              background: #fff;
              border-radius: 8px;
              border: 1px solid #e8e8e8;
              word-break: break-word;

              &.translated {
                color: #409EFF;
                border-color: #409EFF;
                background: linear-gradient(135deg, #f0f7ff 0%, #e6f2ff 100%);
                font-weight: 500;
              }
            }
          }
        }

        .result-error {
          color: #F56C6C;
          font-size: 14px;
          padding: 12px;
          background: #fef0f0;
          border-radius: 6px;
          border: 1px solid #fde2e2;
        }
      }
    }
  }

  .error-section {
    margin-top: 20px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;

  .el-button {
    min-width: 100px;
  }
}

@media screen and (max-width: 768px) {
  .dialog-content {
    .preview-section {
      .preview-grid {
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
      }
    }

    .settings-section,
    .result-section {
      padding: 16px;
    }
  }
}
</style>
