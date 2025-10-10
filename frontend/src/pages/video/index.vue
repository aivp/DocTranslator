<template>
  <div class="page-center">
    <div class="container">
      <!-- 视频上传区域 -->
      <div class="upload-container">
        <el-upload
          ref="uploadRef"
          class="dropzone"
          drag
          :action="upload_url"
          :accept="video_accepts"
          auto-upload
          :limit="1"
          :on-success="uploadSuccess"
          :on-error="uploadError"
          :on-exceed="handleExceed"
          :headers="{ Authorization: 'Bearer ' + userStore.token }"
          :before-upload="beforeUpload"
          :before-remove="delUploadFile"
          :on-change="handleFileChange">
          <div class="left_box pc_show">
            <div class="icon_box" v-if="!fileListShow">
              <i class="el-icon-video-camera" style="font-size: 48px; color: #409EFF;"></i>
            </div>
          </div>
          <div class="right_box">
            <div class="title pc_show">拖入/点击按钮选择视频文件</div>
            <button class="upload_btn" type="button">
              <i class="el-icon-upload" style="margin-right: 8px;"></i>
              <span>上传视频</span>
            </button>
            <div class="title phone_show">点击按钮选择视频文件</div>
            <div class="tips">支持格式：MP4、AVI、MOV、WMV、FLV、MKV、WEBM，建议文件≤300MB</div>
            <div class="file-count-tip success" 
                 v-if="currentVideo">
              已选择：{{ currentVideo.name }}
            </div>
          </div>
        </el-upload>
      </div>

      <!-- 生成翻译按钮区域 -->
      <div class="generate-container" v-if="currentVideo">
        <div class="video-preview">
          <div class="video-frame">
            <i class="el-icon-video-camera" style="font-size: 48px; color: #409EFF;"></i>
            <div class="video-info">
              <div class="video-name">{{ currentVideo.name }}</div>
              <div class="video-size">{{ formatFileSize(currentVideo.size) }}</div>
            </div>
          </div>
          <div class="action-buttons">
            <el-button 
              type="primary" 
              size="large"
              class="generate-btn"
              @click="openTranslateDialog">
              <i class="el-icon-magic-stick" style="margin-right: 8px;"></i>
              生成翻译 >
            </el-button>
          </div>
        </div>
      </div>

      <!-- 视频列表区域 -->
      <div class="list_box">
        <div class="title_box">
          <h3>视频翻译记录</h3>
          <div class="filter-box">
            <el-select v-model="statusFilter" placeholder="筛选状态" @change="loadVideoList" style="width: 150px;">
              <el-option label="全部" value=""></el-option>
              <el-option label="已上传" value="uploaded"></el-option>
              <el-option label="处理中" value="processing"></el-option>
              <el-option label="已完成" value="completed"></el-option>
              <el-option label="已失败" value="failed"></el-option>
              <el-option label="已过期" value="expired"></el-option>
            </el-select>
            <el-button @click="loadVideoList" :loading="loading">
              <i class="el-icon-refresh"></i>
              刷新
            </el-button>
          </div>
        </div>

        <el-table :data="videoList" v-loading="loading" class="video-table">
          <el-table-column prop="original_filename" label="文件名" min-width="200">
            <template #default="scope">
              <div class="filename-cell">
                <i class="el-icon-video-camera" style="margin-right: 8px; color: #409EFF;"></i>
                {{ scope.row.original_filename || scope.row.filename }}
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="source_language" label="源语言" width="100">
            <template #default="scope">
              {{ getLanguageName(scope.row.source_language) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="target_language" label="目标语言" width="100">
            <template #default="scope">
              {{ getLanguageName(scope.row.target_language) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="status_info" label="状态信息" min-width="200">
            <template #default="scope">
              <div class="status-info">
                <span :class="getStatusClass(scope.row.status_info?.status)">
                  {{ scope.row.status_info?.message }}
                </span>
                <span v-if="scope.row.status_info?.days_left" class="expiry-warning">
                  ⏰ {{ scope.row.status_info.days_left }}天后过期
                </span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="file_size" label="文件大小" width="100">
            <template #default="scope">
              {{ formatFileSize(scope.row.file_size) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="scope">
              <el-button 
                v-if="scope.row.status_info?.can_download"
                type="success" 
                size="mini"
                @click="previewVideo(scope.row)">
                预览
              </el-button>
              <el-button 
                v-if="scope.row.status_info?.can_download"
                type="primary" 
                size="mini"
                :loading="scope.row.downloading"
                @click="downloadVideo(scope.row)">
                下载
              </el-button>
              <el-button 
                v-if="scope.row.status === 'expired'"
                type="warning" 
                size="mini"
                @click="renewVideo(scope.row)">
                重新生成
              </el-button>
              <el-button 
                v-if="scope.row.status === 'uploaded'"
                type="success" 
                size="mini"
                @click="editVideo(scope.row)">
                编辑
              </el-button>
              <el-button 
                v-if="scope.row.status === 'processing'"
                type="warning" 
                size="mini"
                :loading="scope.row.refreshing"
                @click="refreshVideoStatus(scope.row)">
                刷新状态
              </el-button>
              <el-button 
                type="danger" 
                size="mini"
                @click="deleteVideo(scope.row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-box">
          <el-pagination
            @current-change="handlePageChange"
            :current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next, jumper">
          </el-pagination>
        </div>
      </div>
    </div>

    <!-- 翻译设置弹窗 -->
    <el-dialog
      title="生成翻译"
      v-model="translateDialogVisible"
      width="600px"
      :close-on-click-modal="false"
      :close-on-press-escape="false">
      
      <el-form :model="translateForm" :rules="translateRules" ref="translateFormRef" label-width="120px">
        <el-form-item label="源语言" prop="source_language">
          <el-select v-model="translateForm.source_language" placeholder="请选择源语言" style="width: 100%;">
            <el-option label="自动检测" value="auto"></el-option>
            <el-option
              v-for="lang in languages"
              :key="lang.lang_code"
              :label="lang.lang_name"
              :value="lang.lang_code">
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="目标语言" prop="target_language">
          <el-select v-model="translateForm.target_language" placeholder="请选择目标语言" style="width: 100%;">
            <el-option
              v-for="lang in languages"
              :key="lang.lang_code"
              :label="lang.lang_name"
              :value="lang.lang_code">
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="Lip Sync">
          <el-switch
            v-model="translateForm.lipsync_enabled"
            active-text="启用"
            inactive-text="禁用">
          </el-switch>
          <i class="el-icon-info" style="margin-left: 8px; color: #909399;"></i>
        </el-form-item>
        
        <el-form-item label="发言者人数">
          <el-select v-model="translateForm.speaker_num" placeholder="自动检测" style="width: 100%;">
            <el-option label="自动检测" :value="0"></el-option>
            <el-option
              v-for="num in [1,2,3,4,5]"
              :key="num"
              :label="`${num}人`"
              :value="num">
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
        <el-button @click="translateDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="startTranslate"
          :loading="isTranslating">
          翻译
        </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/store/user'
import { videoApi } from '@/api/video'

export default {
  name: 'VideoTranslate',
  setup() {
    const userStore = useUserStore()
    
    // 响应式数据
    const uploadRef = ref()
    const currentVideo = ref(null)
    const fileListShow = ref(false)
    const loading = ref(false)
    const isTranslating = ref(false)
    const videoList = ref([])
    const languages = ref([])
    const statusFilter = ref('')
    const currentPage = ref(1)
    const pageSize = ref(10)
    const total = ref(0)
    const translateDialogVisible = ref(false)
    const translateFormRef = ref()
    
    // 上传配置
    const upload_url = '/api/video/upload'
    const video_accepts = '.mp4,.avi,.mov,.wmv,.flv,.mkv,.webm'
    
    // 翻译表单
    const translateForm = reactive({
      video_id: null,
      source_language: 'auto',
      target_language: '',
      speaker_num: 0,
      lipsync_enabled: false
    })
    
    // 表单验证规则
    const translateRules = {
      source_language: [
        { required: true, message: '请选择源语言', trigger: 'change' }
      ],
      target_language: [
        { required: true, message: '请选择目标语言', trigger: 'change' }
      ]
    }
    
    // 计算属性
    const canStartTranslate = computed(() => {
      return currentVideo.value && 
             translateForm.source_language && 
             translateForm.target_language &&
             !isTranslating.value
    })
    
    // 方法
    const beforeUpload = (file) => {
      const isVideo = file.type.startsWith('video/')
      const isLt300M = file.size / 1024 / 1024 < 300
      
      if (!isVideo) {
        ElMessage.error('只能上传视频文件!')
        return false
      }
      if (!isLt300M) {
        ElMessage.error('视频文件大小不能超过 300MB!')
        return false
      }
      return true
    }
    
    const uploadSuccess = (response, file) => {
      if (response.code === 200) {
        currentVideo.value = {
          id: response.data.id,
          name: response.data.filename,
          url: response.data.video_url,
          size: response.data.file_size
        }
        translateForm.video_id = response.data.id
        ElMessage.success('视频上传成功!')
        loadVideoList()
      } else {
        ElMessage.error(response.message || '上传失败')
      }
    }
    
    const uploadError = (error) => {
      console.error('Upload error:', error)
      ElMessage.error('上传失败，请重试')
    }
    
    const handleExceed = () => {
      ElMessage.warning('最多只能上传一个视频文件')
    }
    
    const handleFileChange = (file, fileList) => {
      fileListShow.value = fileList.length > 0
    }
    
    const delUploadFile = () => {
      currentVideo.value = null
      translateForm.video_id = null
      resetForm()
      return true
    }
    
    const resetForm = () => {
      Object.assign(translateForm, {
        video_id: null,
        source_language: 'auto',
        target_language: '',
        speaker_num: 0,
        lipsync_enabled: false
      })
    }
    
    // 打开翻译设置弹窗
    const openTranslateDialog = () => {
      if (!currentVideo.value) {
        ElMessage.warning('请先上传视频')
        return
      }
      translateDialogVisible.value = true
    }
    
    
    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    const startTranslate = async () => {
      // 验证表单
      if (!translateFormRef.value) return
      
      try {
        await translateFormRef.value.validate()
      } catch (error) {
        return
      }
      
      if (!canStartTranslate.value) return
      
      isTranslating.value = true
      try {
        const response = await videoApi.startTranslate(translateForm)
        if (response.code === 200) {
          ElMessage.success('翻译任务已启动!')
          translateDialogVisible.value = false
          loadVideoList()
          resetForm()
          currentVideo.value = null
          uploadRef.value.clearFiles()
          
          // 启动自动刷新
          setTimeout(() => {
            startAutoRefresh()
          }, 1000)
        } else {
          ElMessage.error(response.message || '启动翻译失败')
        }
      } catch (error) {
        console.error('Start translate error:', error)
        ElMessage.error('启动翻译失败，请重试')
      } finally {
        isTranslating.value = false
      }
    }
    
    const loadVideoList = async () => {
      loading.value = true
      try {
        const params = {
          page: currentPage.value,
          per_page: pageSize.value
        }
        if (statusFilter.value) {
          params.status = statusFilter.value
        }
        
        const response = await videoApi.getVideoList(params)
        if (response.code === 200) {
          videoList.value = response.data.videos
          total.value = response.data.total
          
          // 检查是否有处理中的视频，启动或停止自动刷新
          const processingVideos = videoList.value.filter(video => video.status === 'processing')
          if (processingVideos.length > 0) {
            startAutoRefresh()
          } else {
            stopAutoRefresh()
          }
        } else {
          ElMessage.error(response.message || '获取视频列表失败')
        }
      } catch (error) {
        console.error('Load video list error:', error)
        ElMessage.error('获取视频列表失败')
      } finally {
        loading.value = false
      }
    }
    
    const loadLanguages = async () => {
      try {
        const response = await videoApi.getLanguages()
        if (response.code === 200) {
          languages.value = response.data.languages
        } else {
          // 如果API失败，使用默认语言列表
          languages.value = [
            { lang_code: 'en', lang_name: 'English' },
            { lang_code: 'zh', lang_name: 'Chinese (Simplified)' },
            { lang_code: 'fr', lang_name: 'French' },
            { lang_code: 'de', lang_name: 'German' },
            { lang_code: 'ja', lang_name: 'Japanese' },
            { lang_code: 'ko', lang_name: 'Korean' },
            { lang_code: 'es', lang_name: 'Spanish' },
            { lang_code: 'ru', lang_name: 'Russian' }
          ]
        }
      } catch (error) {
        console.error('Load languages error:', error)
        // 使用默认语言列表
        languages.value = [
          { lang_code: 'en', lang_name: 'English' },
          { lang_code: 'zh', lang_name: 'Chinese (Simplified)' },
          { lang_code: 'fr', lang_name: 'French' },
          { lang_code: 'de', lang_name: 'German' },
          { lang_code: 'ja', lang_name: 'Japanese' },
          { lang_code: 'ko', lang_name: 'Korean' },
          { lang_code: 'es', lang_name: 'Spanish' },
          { lang_code: 'ru', lang_name: 'Russian' }
        ]
      }
    }
    
    const previewVideo = (video) => {
      if (video.translated_video_url) {
        window.open(video.translated_video_url, '_blank')
      } else {
        ElMessage.warning('翻译视频不存在')
      }
    }
    
    const downloadVideo = async (video) => {
      if (video.translated_video_url) {
        try {
          // 设置loading状态
          video.downloading = true
          
          ElMessage.info('正在准备下载...')
          
          // 使用后端代理接口下载
          const response = await videoApi.downloadVideo(video.id)
          
          if (response instanceof Blob) {
            // 创建下载链接
            const url = window.URL.createObjectURL(response)
            const link = document.createElement('a')
            link.href = url
            
            // 设置下载文件名
            const filename = video.original_filename || video.filename || 'translated_video.mp4'
            const finalFilename = filename.endsWith('.mp4') ? filename : `${filename}.mp4`
            link.download = finalFilename
            
            // 添加到DOM并触发下载
            document.body.appendChild(link)
            link.click()
            
            // 清理DOM和URL
            document.body.removeChild(link)
            window.URL.revokeObjectURL(url)
            
            ElMessage.success('视频下载已开始')
          } else {
            throw new Error('下载响应格式错误')
          }
        } catch (error) {
          console.error('下载失败:', error)
          ElMessage.error('下载失败，请重试')
        } finally {
          // 清除loading状态
          video.downloading = false
        }
      } else {
        ElMessage.warning('翻译视频不存在')
      }
    }
    
    const renewVideo = async (video) => {
      try {
        await ElMessageBox.confirm('确定要重新生成这个视频吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        // 重新启动翻译
        const form = {
          video_id: video.id,
          source_language: video.source_language,
          target_language: video.target_language,
          lipsync_enabled: video.lipsync_enabled,
          speaker_num: 0
        }
        
        const response = await videoApi.startTranslate(form)
        if (response.code === 200) {
          ElMessage.success('重新生成任务已启动!')
          loadVideoList()
        } else {
          ElMessage.error(response.message || '重新生成失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('Renew video error:', error)
          ElMessage.error('重新生成失败')
        }
      }
    }
    
    const editVideo = (video) => {
      currentVideo.value = {
        id: video.id,
        name: video.filename,
        url: video.video_url,
        size: video.file_size
      }
      translateForm.video_id = video.id
      translateForm.source_language = video.source_language
      translateForm.target_language = video.target_language
      translateForm.lipsync_enabled = video.lipsync_enabled
      translateForm.speaker_num = 0
    }
    
    const deleteVideo = async (video) => {
      try {
        await ElMessageBox.confirm('确定要删除这个视频吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const response = await videoApi.deleteVideo(video.id)
        if (response.code === 200) {
          ElMessage.success('删除成功!')
          loadVideoList()
        } else {
          ElMessage.error(response.message || '删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('Delete video error:', error)
          ElMessage.error('删除失败')
        }
      }
    }
    
    const refreshVideoStatus = async (video) => {
      if (!video.akool_task_id) {
        ElMessage.warning('无法获取任务状态，缺少任务ID')
        return
      }
      
      try {
        // 设置刷新状态
        video.refreshing = true
        
        // 调用后端接口获取最新状态
        const response = await videoApi.getVideoStatus(video.id)
        
        if (response.code === 200) {
          // 更新视频状态
          const updatedVideo = response.data
          Object.assign(video, updatedVideo)
          
          ElMessage.success('状态已更新')
          
          // 如果状态变为已完成，刷新整个列表
          if (updatedVideo.status === 'completed' || updatedVideo.status === 'failed') {
            loadVideoList()
          }
        } else {
          ElMessage.error('获取状态失败')
        }
      } catch (error) {
        console.error('刷新状态失败:', error)
        ElMessage.error('刷新状态失败')
      } finally {
        video.refreshing = false
      }
    }
    
    const handlePageChange = (page) => {
      currentPage.value = page
      loadVideoList()
    }
    
    // 工具方法
    const getLanguageName = (code) => {
      const lang = languages.value.find(l => l.lang_code === code)
      return lang ? lang.lang_name : code
    }
    
    const getStatusType = (status) => {
      const types = {
        'uploaded': 'info',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'expired': 'info'
      }
      return types[status] || 'info'
    }
    
    const getStatusText = (status) => {
      const texts = {
        'uploaded': '已上传',
        'processing': '处理中',
        'completed': '已完成',
        'failed': '已失败',
        'expired': '已过期'
      }
      return texts[status] || status
    }
    
    const getStatusClass = (status) => {
      const classes = {
        'completed': 'status-completed',
        'expired': 'status-expired',
        'processing': 'status-processing',
        'failed': 'status-failed'
      }
      return classes[status] || ''
    }
    
    const formatDate = (dateString) => {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN')
    }
    
    // 自动刷新定时器
    let autoRefreshTimer = null
    
    // 自动刷新处理中的视频状态
    const startAutoRefresh = () => {
      // 清除现有定时器
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer)
      }
      
      // 检查是否有处理中的视频
      const processingVideos = videoList.value.filter(video => video.status === 'processing')
      
      if (processingVideos.length > 0) {
        console.log(`发现 ${processingVideos.length} 个处理中的视频，启动自动刷新`)
        
        autoRefreshTimer = setInterval(async () => {
          try {
            // 刷新所有处理中的视频状态
            for (const video of processingVideos) {
              if (video.status === 'processing' && video.akool_task_id) {
                console.log(`自动刷新视频 ${video.id} 状态`)
                await refreshVideoStatus(video)
              }
            }
            
            // 重新加载视频列表以获取最新状态
            await loadVideoList()
            
            // 检查是否还有处理中的视频
            const stillProcessing = videoList.value.filter(video => video.status === 'processing')
            if (stillProcessing.length === 0) {
              console.log('所有视频处理完成，停止自动刷新')
              stopAutoRefresh()
            }
          } catch (error) {
            console.error('自动刷新失败:', error)
          }
        }, 20000) // 20秒刷新一次
      }
    }
    
    // 停止自动刷新
    const stopAutoRefresh = () => {
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer)
        autoRefreshTimer = null
        console.log('自动刷新已停止')
      }
    }
    
    // 生命周期
    onMounted(() => {
      loadLanguages()
      loadVideoList()
      
      // 延迟启动自动刷新，确保视频列表已加载
      setTimeout(() => {
        startAutoRefresh()
      }, 2000)
    })
    
    onUnmounted(() => {
      stopAutoRefresh()
    })
    
    return {
      // 响应式数据
      uploadRef,
      currentVideo,
      fileListShow,
      loading,
      isTranslating,
      videoList,
      languages,
      statusFilter,
      currentPage,
      pageSize,
      total,
      upload_url,
      video_accepts,
      translateForm,
      translateRules,
      translateFormRef,
      translateDialogVisible,
      canStartTranslate,
      
      // 方法
      beforeUpload,
      uploadSuccess,
      uploadError,
      handleExceed,
      handleFileChange,
      delUploadFile,
      resetForm,
      openTranslateDialog,
      startTranslate,
      loadVideoList,
      previewVideo,
      downloadVideo,
      renewVideo,
      editVideo,
      deleteVideo,
      refreshVideoStatus,
      startAutoRefresh,
      stopAutoRefresh,
      handlePageChange,
      getLanguageName,
      getStatusType,
      getStatusText,
      getStatusClass,
      formatFileSize,
      formatDate,
      userStore
    }
  }
}
</script>

<style scoped>
.page-center {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.container {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.upload-container {
  margin-bottom: 24px;
}

.dropzone {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  transition: border-color 0.3s;
}

.dropzone:hover {
  border-color: #409EFF;
}

.left_box {
  display: inline-block;
  vertical-align: top;
  margin-right: 20px;
}

.icon_box {
  font-size: 48px;
  color: #409EFF;
}

.right_box {
  display: inline-block;
  vertical-align: top;
  text-align: left;
}

.title {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 16px;
  color: #333;
}

.upload_btn {
  background: #409EFF;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.upload_btn:hover {
  background: #66b1ff;
}

.tips {
  font-size: 14px;
  color: #666;
  margin-top: 12px;
}

.file-count-tip {
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
}

.file-count-tip.success {
  background: #f0f9ff;
  color: #409EFF;
  border: 1px solid #b3d8ff;
}

.generate-container {
  margin-bottom: 24px;
}

.video-preview {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 24px;
}

.video-frame {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 2px dashed #e1e5e9;
  min-width: 200px;
}

.video-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.video-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.video-size {
  font-size: 12px;
  color: #666;
}

.action-buttons {
  display: flex;
  gap: 12px;
  flex: 1;
  justify-content: center;
}

.generate-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  font-weight: 500;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 16px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.generate-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
}


.settings-container {
  margin-bottom: 24px;
}

.settings-card {
  border-radius: 8px;
}

.card-header {
  font-size: 16px;
  font-weight: 500;
}

.translate-form {
  margin-top: 20px;
}

.list_box {
  margin-top: 24px;
}

.title_box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.title_box h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.filter-box {
  display: flex;
  gap: 12px;
  align-items: center;
}

.video-table {
  margin-bottom: 20px;
}

.filename-cell {
  display: flex;
  align-items: center;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-completed {
  color: #67c23a;
}

.status-expired {
  color: #909399;
}

.status-processing {
  color: #e6a23c;
}

.status-failed {
  color: #f56c6c;
}

.expiry-warning {
  font-size: 12px;
  color: #e6a23c;
}

.pagination-box {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .pc_show {
    display: none;
  }
  
  .phone_show {
    display: block;
  }
  
  .left_box {
    display: none;
  }
  
  .right_box {
    display: block;
    text-align: center;
  }
}

@media (min-width: 769px) {
  .pc_show {
    display: block;
  }
  
  .phone_show {
    display: none;
  }
}
</style>
