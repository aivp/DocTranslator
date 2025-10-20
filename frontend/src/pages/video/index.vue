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
            <el-button type="primary" @click="loadVideoList" :loading="loading">
              <i class="el-icon-refresh"></i>
              刷新
            </el-button>
          </div>
        </div>

        <el-table :data="videoList" v-loading="loading" class="video-table">
          <el-table-column prop="original_filename" label="文件名" min-width="250">
            <template #default="scope">
              <div class="filename-cell">
                <i class="el-icon-video-camera" style="margin-right: 8px; color: #409EFF;"></i>
                {{ scope.row.original_filename || scope.row.filename }}
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="source_language" label="源语言" width="120">
            <template #default="scope">
              {{ getLanguageName(scope.row.source_language) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="target_language" label="目标语言" width="180">
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
          
          <el-table-column prop="status_info" label="状态信息" min-width="250">
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
          
          <el-table-column prop="file_size" label="文件大小" width="120">
            <template #default="scope">
              {{ formatFileSize(scope.row.file_size) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="280" fixed="right">
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
        
        <el-form-item label="目标语言" prop="target_languages">
          <el-select 
            v-model="translateForm.target_languages" 
            placeholder="请选择目标语言（支持多选）" 
            multiple
            collapse-tags
            collapse-tags-tooltip
            style="width: 100%;"
            @change="handleTargetLanguagesChange">
            <el-option
              v-for="lang in languages"
              :key="lang.lang_code"
              :label="lang.lang_name"
              :value="lang.lang_code">
            </el-option>
          </el-select>
          <div class="form-tip">支持同时选择多个目标语言进行翻译</div>
        </el-form-item>
        
        <!-- AI语音选择 - 为每个目标语言单独选择 -->
        <el-form-item label="AI语音" v-if="translateForm.target_languages && translateForm.target_languages.length > 0">
          <div class="voice-selection-container">
            <div 
              v-for="langCode in translateForm.target_languages" 
              :key="langCode" 
              class="voice-selection-item">
              <div class="voice-selection-label">
                <span>{{ getLanguageName(langCode) }}</span>
              </div>
              <el-select 
                v-model="voiceMap[langCode]" 
                :placeholder="languageVoicesLoading[langCode] ? '正在加载语音列表...' : `请为 ${getLanguageName(langCode)} 选择AI语音（可选）`" 
                clearable
                :loading="languageVoicesLoading[langCode]"
                style="width: 100%;"
                @change="(val) => handleVoiceChangeForLanguage(langCode, val)">
                <template #empty>
                  <div class="voice-loading-empty">
                    <i class="el-icon-loading" v-if="languageVoicesLoading[langCode]"></i>
                    <span v-if="languageVoicesLoading[langCode]">正在加载语音列表...</span>
                    <span v-else>暂无可用语音</span>
                  </div>
                </template>
                <el-option
                  v-for="voice in getVoicesForLanguage(langCode)"
                  :key="voice.voice_id"
                  :label="`${voice.name} (${voice.gender})`"
                  :value="voice.voice_id">
                  <div class="voice-option">
                    <div class="voice-info">
                      <span class="voice-name">{{ voice.name }}</span>
                      <span class="voice-gender">{{ voice.gender }}</span>
                    </div>
                    <div class="voice-details">
                      <span class="voice-language">{{ voice.language }}</span>
                      <span class="voice-style" v-if="voice.style && voice.style.length">
                        {{ voice.style.join(', ') }}
                      </span>
                    </div>
                  </div>
                </el-option>
              </el-select>
              
              <!-- 语音预览 -->
              <div class="voice-preview" v-if="voiceMap[langCode]">
                <div class="voice-preview-info">
                  <img 
                    :src="getVoicesForLanguage(langCode).find(v => v.voice_id === voiceMap[langCode])?.thumbnailUrl" 
                    class="voice-avatar" 
                    v-if="getVoicesForLanguage(langCode).find(v => v.voice_id === voiceMap[langCode])?.thumbnailUrl">
                  <div class="voice-details">
                    <h4>{{ getVoicesForLanguage(langCode).find(v => v.voice_id === voiceMap[langCode])?.name }}</h4>
                    <p>{{ getVoicesForLanguage(langCode).find(v => v.voice_id === voiceMap[langCode])?.language }} • {{ getVoicesForLanguage(langCode).find(v => v.voice_id === voiceMap[langCode])?.gender }}</p>
                    <div class="voice-tags">
                      <el-tag 
                        v-for="style in getVoicesForLanguage(langCode).find(v => v.voice_id === voiceMap[langCode])?.style" 
                        :key="style" 
                        size="small" 
                        style="margin-right: 4px;">
                        {{ style }}
                      </el-tag>
                    </div>
                  </div>
                </div>
                <div class="voice-preview-audio" v-if="getVoicesForLanguage(langCode).find(v => v.voice_id === voiceMap[langCode])?.preview">
                  <audio 
                    controls 
                    :src="getVoicesForLanguage(langCode).find(v => v.voice_id === voiceMap[langCode])?.preview" 
                    class="preview-audio">
                  </audio>
                </div>
              </div>
            </div>
          </div>
          <div class="form-tip">为每个目标语言单独选择AI语音，不选择则使用默认语音</div>
        </el-form-item>
        
        <el-form-item label="Lip Sync">
          <el-switch
            v-model="translateForm.lipsync_enabled"
            active-text="启用"
            inactive-text="禁用">
          </el-switch>
          <i class="el-icon-info" style="margin-left: 8px; color: #909399;"></i>
        </el-form-item>
        
        <!-- 唇语同步类型 -->
        <el-form-item label="唇语同步类型" v-if="translateForm.lipsync_enabled">
          <el-radio-group v-model="translateForm.lip_sync_type">
            <el-radio :label="0">标准</el-radio>
            <el-radio :label="1">增强</el-radio>
            <el-radio :label="2">专业</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="术语库">
          <el-select
            v-model="translateForm.terminology_ids"
            placeholder="请选择术语库（可选，可多选）"
            multiple
            clearable
            filterable
            style="width: 100%;"
            @focus="loadTerminologies"
            @visible-change="handleTerminologyVisible">
            <el-option 
              v-for="term in terminologies" 
              :key="term.id" 
              :label="term.title" 
              :value="term.id">
              <div class="terminology-option">
                <span class="terminology-title">{{ term.title }}</span>
                <span class="terminology-count">({{ term.term_count || 0 }}条术语)</span>
              </div>
            </el-option>
          </el-select>
          <div class="form-tip">选择术语库可以提高翻译的专业性和准确性</div>
          <div class="form-tip" style="color: #909399; font-size: 12px;">
            当前加载了 {{ terminologies.length }} 个术语库
          </div>
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
        
        <el-form-item label="翻译风格">
          <el-select v-model="translateForm.style" placeholder="请选择翻译风格" style="width: 100%;">
            <el-option
              v-for="option in styleOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value">
            </el-option>
          </el-select>
          <div class="form-tip">选择翻译风格，影响语音的情感表达</div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
        <el-button @click="translateDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="startTranslate"
          :loading="isTranslating"
          :disabled="isTranslating">
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
import request from '@/utils/request'

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
    
    // 新增：AI语音相关数据
    const availableVoices = ref([])
    const selectedVoice = ref(null)
    const showVoiceSelection = ref(false)
    const voiceMap = ref({}) // 存储每个语言对应的语音ID
    const languageVoices = ref({}) // 存储每个语言对应的可用语音列表
    const languageVoicesLoading = ref({}) // 存储每个语言的加载状态
    
    // 新增：术语库相关数据
    const terminologies = ref([])
    
    // 上传配置
    const upload_url = '/api/video/upload'
    const video_accepts = '.mp4,.avi,.mov,.wmv,.flv,.mkv,.webm'
    
    // 翻译表单
    const translateForm = reactive({
      video_id: null,
      source_language: 'auto',
      target_languages: [], // 改为数组支持多选
      speaker_num: 0,
      lipsync_enabled: false,
      lip_sync_type: 0, // 新增唇语同步类型
      voices_map: {}, // 改为对象，存储每个语言对应的语音ID
      terminology_ids: [], // 新增术语库ID列表
      style: 'professional' // 新增翻译风格参数
    })
    
    // 翻译风格选项
    const styleOptions = [
      { value: 'affectionate', label: '深情 (Affectionate)' },
      { value: 'angry', label: '愤怒 (Angry)' },
      { value: 'calm', label: '平静 (Calm)' },
      { value: 'cheerful', label: '愉快 (Cheerful)' },
      { value: 'depressed', label: '沮丧 (Depressed)' },
      { value: 'disgruntled', label: '不满 (Disgruntled)' },
      { value: 'embarrassed', label: '尴尬 (Embarrassed)' },
      { value: 'empathetic', label: '共情 (Empathetic)' },
      { value: 'excited', label: '兴奋 (Excited)' },
      { value: 'fearful', label: '恐惧 (Fearful)' },
      { value: 'friendly', label: '友好 (Friendly)' },
      { value: 'unfriendly', label: '不友好 (Unfriendly)' },
      { value: 'sad', label: '悲伤 (Sad)' },
      { value: 'serious', label: '严肃 (Serious)' },
      { value: 'relaxed', label: '放松 (Relaxed)' },
      { value: 'professional', label: '专业 (Professional)' }
    ]
    
    // 表单验证规则
    const translateRules = {
      source_language: [
        { required: true, message: '请选择源语言', trigger: 'change' }
      ],
      target_languages: [
        { required: true, message: '请选择目标语言', trigger: 'change' },
        { type: 'array', min: 1, message: '至少选择一个目标语言', trigger: 'change' }
      ]
    }
    
    // 计算属性
    const canStartTranslate = computed(() => {
      return currentVideo.value && 
             translateForm.source_language && 
             translateForm.target_languages.length > 0 &&
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
        target_languages: [], // 改为数组
        speaker_num: 0,
        lipsync_enabled: false,
        lip_sync_type: 0, // 新增
        voices_map: {}, // 改为对象
        terminology_ids: [], // 新增术语库ID列表
        style: 'professional' // 新增翻译风格参数
      })
      
      // 重置语音选择
      selectedVoice.value = null
      availableVoices.value = []
      showVoiceSelection.value = false
      voiceMap.value = {}
      languageVoices.value = {}
      languageVoicesLoading.value = {}
    }
    
    // 打开翻译设置弹窗
    const openTranslateDialog = () => {
      if (!currentVideo.value) {
        ElMessage.warning('请先上传视频')
        return
      }
      
      // 重置表单
      resetForm()
      
      // 设置视频ID
      translateForm.video_id = currentVideo.value.id
      
      // 加载术语库
      loadTerminologies()
      
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
        // 构建请求数据
        const requestData = {
          ...translateForm,
          voices_map: voiceMap.value // 使用语音映射对象
        }
        
        // 添加调试日志
        console.log('发送翻译请求数据:', requestData)
        console.log('当前视频:', currentVideo.value)
        console.log('语音映射:', voiceMap.value)
        
        // 验证必要参数
        if (!requestData.video_id) {
          ElMessage.error('视频ID不能为空')
          isTranslating.value = false
          return
        }
        if (!requestData.target_languages || requestData.target_languages.length === 0) {
          ElMessage.error('请选择目标语言')
          isTranslating.value = false
          return
        }
        
        // 语音选择默认可选，只有当API返回错误时才提示必选
        
        const response = await videoApi.startTranslate(requestData)
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
          // 检查是否是语音必选错误
          if (response.message && response.message.includes('必须选择AI语音')) {
            ElMessage.error(response.message)
          } else {
            ElMessage.error(response.message || '启动翻译失败')
          }
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
    
    // 新增：加载AI语音列表（为特定语言）
    const loadVoices = async (languageCode) => {
      try {
        // 如果已经加载过该语言的语音，直接返回
        if (languageVoices.value[languageCode]) {
          return languageVoices.value[languageCode]
        }
        
        // 设置加载状态
        languageVoicesLoading.value[languageCode] = true
        
        const params = { page: 1, size: 100 }
        if (languageCode) {
          params.language_code = languageCode
        }
        
        const response = await videoApi.getVoices(params)
        if (response.code === 200) {
          const voices = response.data.result || []
          languageVoices.value[languageCode] = voices
          return voices
        } else {
          languageVoices.value[languageCode] = []
          return []
        }
      } catch (error) {
        console.error('Load voices error:', error)
        languageVoices.value[languageCode] = []
        return []
      } finally {
        // 清除加载状态
        languageVoicesLoading.value[languageCode] = false
      }
    }
    
    // 新增：处理目标语言变化，为每个语言加载对应的语音
    const handleTargetLanguagesChange = async (languages) => {
      // 获取之前的语言列表
      const previousLanguages = Object.keys(voiceMap.value)
      
      // 找出被移除的语言
      const removedLanguages = previousLanguages.filter(lang => !languages.includes(lang))
      
      // 只清空被移除的语言的语音映射
      removedLanguages.forEach(lang => {
        delete voiceMap.value[lang]
      })
      
      // 找出新增的语言
      const newLanguages = languages.filter(lang => !previousLanguages.includes(lang))
      
      // 只为新增的语言加载语音列表
      for (const langCode of newLanguages) {
        await loadVoices(langCode)
      }
    }
    
    // 新增：处理单个语言的语音选择变化
    const handleVoiceChangeForLanguage = (langCode, voiceId) => {
      if (voiceId) {
        voiceMap.value[langCode] = voiceId
      } else {
        delete voiceMap.value[langCode]
      }
    }
    
    // 新增：获取某个语言的可用语音列表
    const getVoicesForLanguage = (langCode) => {
      return languageVoices.value[langCode] || []
    }
    
    // 新增：加载术语库列表
    const loadTerminologies = async () => {
      try {
        console.log('开始加载术语库...')
        const response = await request({
          url: '/comparison/my',
          method: 'get'
        })
        
        console.log('术语库API响应:', response)
        
        if (response.code === 200) {
          // 修复数据路径：API返回的是 data.data，不是 data.comparisons
          terminologies.value = response.data.data || response.data.comparisons || []
          console.log('加载术语库成功:', terminologies.value.length, '个术语库')
          console.log('术语库详情:', terminologies.value)
        } else {
          console.error('加载术语库失败:', response.message)
          terminologies.value = []
        }
      } catch (error) {
        console.error('加载术语库异常:', error)
        terminologies.value = []
      }
    }
    
    // 新增：处理术语库下拉框显示变化
    const handleTerminologyVisible = (visible) => {
      if (visible && terminologies.value.length === 0) {
        loadTerminologies()
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
      translateForm.target_languages = video.target_language ? [video.target_language] : []
      translateForm.lipsync_enabled = video.lipsync_enabled
      translateForm.speaker_num = 0
      
      // 打开翻译设置弹窗
      openTranslateDialog()
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
      
      // 新增：AI语音相关数据
      availableVoices,
      selectedVoice,
      showVoiceSelection,
      voiceMap,
      languageVoices,
      languageVoicesLoading,
      
      // 新增：术语库相关数据
      terminologies,
      
      // 新增：翻译风格选项
      styleOptions,
      
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
      loadLanguages,
      loadVoices, // 新增
      handleTargetLanguagesChange, // 新增
      handleVoiceChangeForLanguage, // 新增
      getVoicesForLanguage, // 新增
      loadTerminologies, // 新增
      handleTerminologyVisible, // 新增
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
  padding: 20px 40px; /* 左右增加更多留白 */
  max-width: 1600px;
  margin: 0 auto;
  min-height: 100vh;
  overflow-y: auto;
}

/* 新增：语音选择相关样式 */
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.voice-selection-container {
  width: 100%;
}

.voice-selection-item {
  margin-bottom: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.voice-selection-item:last-child {
  margin-bottom: 0;
}

.voice-selection-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
}

.voice-selection-label span {
  display: inline-block;
  padding: 4px 8px;
  background: #409EFF;
  color: white;
  border-radius: 4px;
}

.voice-selection {
  width: 100%;
}

.voice-option {
  padding: 8px 0;
}

.voice-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.voice-name {
  font-weight: 500;
  color: #303133;
}

.voice-gender {
  font-size: 12px;
  color: #909399;
  background: #f4f4f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.voice-details {
  font-size: 12px;
  color: #606266;
}

.voice-language {
  margin-right: 8px;
}

.voice-style {
  color: #909399;
}

.voice-preview {
  margin-top: 12px;
  padding: 12px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.voice-preview-info {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
}

.voice-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  margin-right: 12px;
  object-fit: cover;
}

.voice-preview-info .voice-details h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #303133;
}

.voice-preview-info .voice-details p {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #606266;
}

.voice-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.preview-audio {
  width: 100%;
  height: 32px;
}

/* 语音加载状态样式 */
.voice-loading-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #909399;
  font-size: 14px;
}

.voice-loading-empty i {
  margin-right: 8px;
  font-size: 16px;
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* 术语库选择器样式 */
.terminology-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.terminology-title {
  font-weight: 500;
  color: #303133;
}

.terminology-count {
  font-size: 12px;
  color: #909399;
  background: #f4f4f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.container {
  background: #fff;
  border-radius: 8px;
  padding: 24px 32px; /* 左右增加更多内边距 */
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  width: 100%;
  overflow-x: auto;
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
  flex-shrink: 0; /* 防止按钮被压缩 */
  margin-right: 20px; /* 添加右边距 */
}

.filter-box .el-button {
  white-space: nowrap; /* 防止按钮文字换行 */
  min-width: auto; /* 确保按钮有足够宽度 */
}

.video-table {
  margin-bottom: 20px;
  width: 100%;
  min-width: 1200px;
}

.video-table .el-table {
  width: 100%;
}

.video-table .el-table__body-wrapper {
  overflow-x: auto;
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

/* 确保页面可以滚动 */
body {
  overflow-y: auto;
}

/* 表格滚动优化 */
.video-table .el-table__body-wrapper {
  max-height: 600px;
  overflow-y: auto;
}

/* 响应式优化 */
@media (max-width: 1400px) {
  .page-center {
    max-width: 1400px;
    padding: 20px 30px; /* 中等屏幕减少留白 */
  }
}

@media (max-width: 1200px) {
  .page-center {
    max-width: 1200px;
    padding: 20px 24px; /* 小屏幕进一步减少留白 */
  }
  
  .container {
    padding: 24px 28px; /* 小屏幕减少容器内边距 */
  }
  
  .video-table {
    min-width: 1000px;
  }
}

@media (max-width: 768px) {
  .page-center {
    padding: 15px 16px; /* 移动端最小留白 */
  }
  
  .container {
    padding: 20px 16px; /* 移动端最小内边距 */
  }
}
</style>
