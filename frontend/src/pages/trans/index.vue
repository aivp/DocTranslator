<template>
  <div class="page-center">
    <div class="container">
      <div class="upload-container">
        <el-upload
          ref="uploadRef"
          class="dropzone"
          drag
          multiple
          :action="upload_url"
          :accept="accepts"
          auto-upload
          :limit="5"
          :on-success="uploadSuccess"
          :on-error="uploadError"
          :on-exceed="handleExceed"
          :headers="{ Authorization: 'Bearer ' + userStore.token }"
          :before-upload="beforeUpload"
          :before-remove="delUploadFile"
          :on-change="(file, fileList) => flhandleFileListChange(file, fileList)">
          <div class="left_box pc_show">
            <div class="icon_box" v-if="!fileListShow">
              <img src="@/assets/icon_a.png" />
              <img src="@/assets/icon_w.png" />
              <img src="@/assets/icon_p.png" />
              <img src="@/assets/icon_x.png" />
            </div>
          </div>
          <div class="right_box">
            <div class="title pc_show">拖入/点击按钮选择添加文档</div>
            <button class="upload_btn" type="button">
              <img :src="uploadPng" />
              <span>上传文档</span>
            </button>
            <div class="title phone_show">点击按钮选择添加文档</div>
            <div class="tips">支持格式{{ accpet_tip }}，建议文件≤500MB</div>
            <div class="upload-limit-tip">最多可同时上传5个文件</div>
          </div>
        </el-upload>
      </div>
      <!-- 翻译列表表格展示 -->
      <div class="list_box">
        <div class="title_box">
          <div class="t">
            <div class="t_left">
              <span>翻译任务列表</span>
              <div class="tips" v-if="false">
                <el-icon><SuccessFilled /></el-icon>
                已累计为用户成功翻译文件
                <span>{{ transCount }}</span>
                份
              </div>
            </div>

            <div class="t_right">
              <el-button
                type="text"
                class="phone_show"
                @click="downAllTransFile"
                :loading="downloadAllButtonState.isLoading"
                :disabled="downloadAllButtonState.disabled"
                v-if="editionInfo !== 'community' && translatesData.length > 0">
                全部下载
              </el-button>
              <el-button
                type="text"
                class="phone_show"
                @click="delAllTransFile"
                v-if="translatesData && translatesData.length > 0">
                全部删除
              </el-button>
            </div>
          </div>
          <!-- 存储空间展示 -->
          <div class="t_right">
            <span class="storage">存储空间({{ storageTotal }}M)</span>
            <el-progress class="translated-process" :percentage="storagePercentage" color="#055CF9" />
            <el-button 
              class="pc_show all_down" 
              @click="downAllTransFile" 
              :loading="downloadAllButtonState.isLoading"
              :disabled="downloadAllButtonState.disabled"
              v-if="translatesData.length > 0">
              全部下载
            </el-button>
            <el-button class="pc_show" @click="delAllTransFile" v-if="translatesData.length > 0">全部删除</el-button>
          </div>
          <!-- <div class="t_right">
            <el-button class="pc_show" @click="delAllTransFile" v-if="translatesData.length > 0"
              >全部删除</el-button
            >
          </div> -->
        </div>
        <!-- 翻译列表表格数据 -->
        <div class="table_box" v-loading="isLoadingData" element-loading-text="加载中...">
          <div class="table_row table_top pc_show">
            <div class="table_li">文档名称</div>
            <div class="table_li">任务状态</div>
            <div class="table_li">用时</div>
            <div class="table_li">完成时间</div>
            <div class="table_li">语言</div>
            <div class="table_li">操作</div>
          </div>
          <div class="table_row phone_row" v-for="(res, index) in result" :key="index">
            <div class="table_li">
              <img :src="getFileIcon(res.file_type, res.file_name)" alt="" />
              <span class="file_name">{{ res.file_name }}</span>
            </div>
            <div class="table_li status">
              <el-progress class="translated-process" :percentage="res['percentage']" color="#055CF9">
                <template #default="{ percentage }">
                  <span class="percentage">{{ percentage }}%</span>
                </template>
              </el-progress>
              <img src="@assets/waring.gif" alt="" />
              <span class="process">翻译中</span>
            </div>
            <div class="table_li pc_show">--</div>
            <div class="table_li pc_show">--</div>
            <div class="table_li pc_show">{{ getLanguageDisplayName(res.lang) }}</div>
            <div class="table_li pc_show">
              <img src="@assets/icon_no_down.png" alt="" />
            </div>
          </div>

          <div class="table_row phone_row" v-for="(item, index) in translatesData" :key="index">
            <div class="table_li">
              <img :src="getFileIcon(item.file_type, item.origin_filename)" alt="" />
              <span class="file_name">{{ item.origin_filename }}</span>
            </div>
            <div :class="item.status == 'done' ? 'pc_show table_li status' : 'table_li status'">
              <!-- 进行中显示实际进度，已完成显示100% -->
              <el-progress 
                class="translated-process" 
                :percentage="item.status === 'done' ? 100 : Number(item.process)" 
                color="#055CF9" 
              />
              <img v-if="item.status == 'none'" src="@assets/waring.png" alt="未开始" />
              <img v-if="item.status == 'changing'" src="@assets/waring.png" alt="转换中" />
              <img v-if="item.status == 'done'" src="@assets/success.png" alt="已完成" />
              <img v-if="item.status == 'process'" src="@assets/waring.png" alt="进行中" />
              <img v-if="item.status == 'failed'" src="@assets/waring.png" alt="失败" />
              <span :class="item.status">{{ item.status_name }}</span>
            </div>
            <div :class="item.status == 'done' ? 'table_li' : 'table_li pc_show'">
              <span class="phone_show">用时:</span>
              {{ (item.status == 'done' && item.spend_time) ? item.spend_time : '-:-' }}
            </div>
            <div :class="item.status == 'done' ? 'table_li' : 'table_li pc_show'">
              <span class="phone_show">完成时间:</span>
              {{ item.end_at ? formatTime(item.end_at) : '--' }}
            </div>
            <div :class="item.status == 'done' ? 'table_li' : 'table_li pc_show'">
              <span class="phone_show">语言:</span>
              {{ item.prompt_id ? '提示词翻译' : (item.lang ? getLanguageDisplayName(item.lang) : '--') }}
            </div>
            <!-- 操作 -->
            <div class="table_li">
              <!-- 翻译成功图标：进度100%且状态为已完成时才显示 -->
              <template v-if="item.status === 'done' && Number(item.process) >= 100">
                <el-link class="icon_down" :href="API_URL + '/translate/download/' + item.id" target="_blank">
                  <span class="icon_handle"><DownloadIcon /></span>
                  <!-- <img src="@assets/icon_down.png" alt="" /> -->
                </el-link>
              </template>
              
              <!-- 失败重试图标 -->
              <template v-if="item.status == 'failed' || item.status == 'none'">
                <span 
                  class="icon_handle" 
                  :class="{ 'disabled': autoStartingTasks.has(item.uuid) }"
                  @click="!autoStartingTasks.has(item.uuid) && retryTranslate(item)"
                  :title="autoStartingTasks.has(item.uuid) ? '任务正在自动启动中，请稍候...' : '重试'">
                  <RetryIcon />
                </span>
              </template>

              <!-- 删除图标 -->
              <span class="icon_handle" @click="delTransFile(item.id, index)">
                <DeleteIcon />
              </span>
            </div>
          </div>
          <div
            v-if="no_data"
            class="table_row no_data"
            style="border: none; padding-top: 15px; justify-content: center; color: #c4c4c4">
            暂无数据
          </div>
        </div>
      </div>

      <!-- 备案信息 -->
      <Filing v-if="false"/>
    </div>

    <!-- pc 立即翻译按钮 -->
    <div class="fixed_bottom">
      <el-button
        type="primary"
        :disabled="(upload_load || translateButtonState.disabled || form.files.length === 0 || (form.files.length > 0 && !areAllFilesUploaded)) && !translateButtonState.isLoading"
        :loading="translateButtonState.isLoading"
        size="large"
        color="#055CF9"
        class="translate-btn"
        @click="handleTranslate(transform)">
        立即翻译
      </el-button>
    </div>
  </div>
</template>
<script setup>
import Filing from '@/components/filing.vue'
import RetryIcon from '@/components/icons/RetryIcon.vue'
import DeleteIcon from '../../components/icons/DeleteIcon.vue'
import DownloadIcon from '../../components/icons/DownloadIcon.vue'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { formatTime } from '@/utils/tools'
import { Loading } from '@element-plus/icons-vue'
const API_URL = import.meta.env.VITE_API_URL
import {
  checkPdf,
  transalteFile,
  transalteProcess,
  delFile,
  translates,
  delTranslate,
  delAllTranslate,
  downAllTranslate,
  doc2xStartService,
  doc2xQueryStatusService,
  getFinishCount,
  getTranslateProgress,
  getQueueStatus
} from '@/api/trans'
import { storage } from '@/api/account'
import uploadPng from '@assets/upload.png'
// 使用 file_icon 目录下的成套图标
import docIcon from '@assets/file_icon/office-doc.svg'
import excelIcon from '@assets/file_icon/office-els.svg'
import pptIcon from '@assets/file_icon/office-ppt.svg'
import pdfIcon from '@assets/file_icon/office-pdf.svg'
import txtIcon from '@assets/file_icon/office-txt.svg'
import mdIcon from '@assets/file_icon/code.svg' // code.svg 用于 .md 文件
import csvIcon from '@assets/file_icon/file.svg' // file.svg 用于 csv 文件
import jsonIcon from '@assets/file_icon/code.svg' // JSON 使用 code 图标
import jsIcon from '@assets/file_icon/js.svg' // JS 使用专门的 js.svg 图标
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTranslateStore } from '@/store/translate'
import { useUserStore } from '@/store/user'
const userStore = useUserStore()
const translateStore = useTranslateStore()
// 当前翻译服务 computed计算
const currentServiceType = computed(() => translateStore.currentService)
// 翻译数据表格加载状态
const isLoadingData = ref(true)
const upload_load = ref(false)

const no_data = ref(true)

const accepts = '.docx,.xlsx,.pptx,.pdf,.txt,.csv,.md'
const fileListShow = ref(false)

const result = ref({})
const target_count = ref('')
const target_time = ref('')
const target_url = ref('')
const upload_url = API_URL + '/upload'

const translatesData = ref([])
const translatesTotal = ref(0)
const translatesLimit = ref(100)

// 队列状态
const queueStatus = ref({
  queued_count: 0,
  running_count: 0,
  memory_usage_gb: 0,
  memory_limit_gb: 8,
  can_start_new: true
})
const storageTotal = ref(0)
const storageUsed = ref(0)
const storagePercentage = ref(0.0)

//版本状态信息
const editionInfo = ref(false)
//翻译累积数量
const transCount = ref(0)

// 自动进度更新相关变量
const autoRefreshInterval = ref(null)
const isPageVisible = ref(true)
const refreshInterval = 5000 // 5秒刷新一次

const uploadRef = ref(null)

const form = ref({
  files: [],
  file_name: '',
  api_url: 'https://api.openai.com',
  api_key: null,
  app_key: null,
  app_id: null,
  model: 'qwen-mt-plus',
  backup_model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',
  langs: ['','英语'],
  lang: '英语',
  to_lang: null,
  type: ['trans_text', 'trans_text_only', 'trans_text_only_inherit'],
  uuid: '',
  prompt:
    '你是一个文档翻译助手，请将以下文本、单词或短语直接翻译成{target_lang}，不返回原文本。如果文本中包含{target_lang}文本、特殊名词（比如邮箱、品牌名、单位名词如mm、px、℃等）、无法翻译等特殊情况，请直接返回原文而无需解释原因。遇到无法翻译的文本直接返回原内容。保留多余空格。',
  threads: 30,
  size: 0,
  scanned: false, // 添加 scanned 字段
  origin_lang: '', // 添加起始语言字段
  comparison_id: '', //术语id
  prompt_id: '', //提示词id,
  translate_id: null,
  doc2x_secret_key: '',
  server: 'openai',
  doc2x_flag: 'N',
})

// 翻译队列管理
const translationQueue = ref({
  isRunning: false,
  currentTask: null,
  pendingTasks: [],
  completedTasks: [],
  failedTasks: []
})

// 翻译按钮状态管理
const translateButtonState = ref({
  isLoading: false,
  disabled: false
})

// 所有文件是否都已上传完成
const areAllFilesUploaded = ref(false)

// 正在自动启动的任务UUID集合（用于禁用重试按钮）
const autoStartingTasks = ref(new Set())

// 全部下载按钮状态管理
const downloadAllButtonState = ref({
  isLoading: false,
  disabled: false
})

// 获取文件图标：根据文件类型或文件名返回对应的图标路径
function getFileIcon(fileType, filename) {
  // 如果提供了文件名，优先从文件名提取扩展名
  if (filename) {
    const ext = filename.split('.').pop()?.toLowerCase()
    if (ext === 'doc' || ext === 'docx') return docIcon
    if (ext === 'xls' || ext === 'xlsx') return excelIcon
    if (ext === 'ppt' || ext === 'pptx') return pptIcon
    if (ext === 'pdf') return pdfIcon
    if (ext === 'txt') return txtIcon // txt 使用 office-txt.svg
    if (ext === 'md') return mdIcon // md 使用 code.svg
    if (ext === 'csv') return csvIcon // CSV 使用 file.svg
    if (ext === 'json') return jsonIcon // JSON 使用 code.svg
    if (ext === 'js') return jsIcon // JS 使用 code.svg
  }
  
  // 根据后端返回的file_type（中文描述）判断
  if (fileType === 'Word' || fileType === 'word') return docIcon
  if (fileType === 'Excel' || fileType === 'excel') return excelIcon
  if (fileType === 'PPT' || fileType === 'ppt') return pptIcon
  if (fileType === 'PDF' || fileType === 'pdf') return pdfIcon
  if (fileType === '文本') return txtIcon // txt 使用 office-txt.svg
  if (fileType === 'CSV') return csvIcon // CSV 使用 file.svg
  if (fileType === 'JSON' || fileType === 'json') return jsonIcon
  if (fileType === 'JS' || fileType === 'js' || fileType === 'JavaScript') return jsIcon
  
  // 兼容旧的扩展名判断（向后兼容）
  if (fileType === 'docx' || fileType === 'doc') return docIcon
  if (fileType === 'xlsx' || fileType === 'xls') return excelIcon
  if (fileType === 'pptx' || fileType === 'ppt') return pptIcon
  
  // 默认返回PDF图标
  return pdfIcon
}

// 语言映射：将英文名转换为中文名用于显示
const languageNameMap = {
  'English': '英语',
  'Chinese': '简体中文',
  'Traditional Chinese': '繁体中文',
  'Russian': '俄语',
  'Japanese': '日语',
  'Korean': '韩语',
  'Spanish': '西班牙语',
  'French': '法语',
  'Portuguese': '葡萄牙语',
  'German': '德语',
  'Italian': '意大利语',
  'Thai': '泰语',
  'Vietnamese': '越南语',
  'Indonesian': '印度尼西亚语',
  'Malay': '马来语',
  'Arabic': '阿拉伯语',
  'Hindi': '印地语',
  'Hebrew': '希伯来语',
  'Burmese': '缅甸语',
  'Tamil': '泰米尔语',
  'Urdu': '乌尔都语',
  'Bengali': '孟加拉语',
  'Polish': '波兰语',
  'Dutch': '荷兰语',
  'Romanian': '罗马尼亚语',
  'Turkish': '土耳其语',
  'Khmer': '高棉语',
  'Lao': '老挝语',
  'Cantonese': '粤语',
  'Czech': '捷克语',
  'Greek': '希腊语',
  'Swedish': '瑞典语',
  'Hungarian': '匈牙利语',
  'Danish': '丹麦语',
  'Finnish': '芬兰语',
  'Ukrainian': '乌克兰语',
  'Bulgarian': '保加利亚语',
  'Serbian': '塞尔维亚语',
  'Telugu': '泰卢固语',
  'Afrikaans': '南非荷兰语',
  'Armenian': '亚美尼亚语',
  'Assamese': '阿萨姆语',
  'Asturian': '阿斯图里亚斯语',
  'Basque': '巴斯克语',
  'Belarusian': '白俄罗斯语',
  'Bosnian': '波斯尼亚语',
  'Catalan': '加泰罗尼亚语',
  'Cebuano': '宿务语',
  'Croatian': '克罗地亚语',
  'Egyptian Arabic': '埃及阿拉伯语',
  'Estonian': '爱沙尼亚语',
  'Galician': '加利西亚语',
  'Georgian': '格鲁吉亚语',
  'Gujarati': '古吉拉特语',
  'Icelandic': '冰岛语',
  'Javanese': '爪哇语',
  'Kannada': '卡纳达语',
  'Kazakh': '哈萨克语',
  'Latvian': '拉脱维亚语',
  'Lithuanian': '立陶宛语',
  'Luxembourgish': '卢森堡语',
  'Macedonian': '马其顿语',
  'Maithili': '迈蒂利语',
  'Maltese': '马耳他语',
  'Marathi': '马拉地语',
  'Mesopotamian Arabic': '美索不达米亚阿拉伯语',
  'Moroccan Arabic': '摩洛哥阿拉伯语',
  'Najdi Arabic': '纳吉迪阿拉伯语',
  'Nepali': '尼泊尔语',
  'North Azerbaijani': '北阿塞拜疆语',
  'North Levantine Arabic': '北黎凡特阿拉伯语',
  'Northern Uzbek': '北乌兹别克语',
  'Norwegian Bokmål': '挪威语（博克马尔）',
  'Norwegian Nynorsk': '挪威语（尼诺斯克）',
  'Occitan': '奥克语',
  'Odia': '奥里亚语',
  'Pangasinan': '邦阿西楠语',
  'Sicilian': '西西里语',
  'Sindhi': '信德语',
  'Sinhala': '僧伽罗语',
  'Slovak': '斯洛伐克语',
  'Slovenian': '斯洛文尼亚语',
  'South Levantine Arabic': '南黎凡特阿拉伯语',
  'Swahili': '斯瓦希里语',
  'Tagalog': '他加禄语',
  "Ta'izzi-Adeni Arabic": '塔伊兹-亚丁阿拉伯语',
  'Tosk Albanian': '托斯克阿尔巴尼亚语',
  'Tunisian Arabic': '突尼斯阿拉伯语',
  'Venetian': '威尼斯语',
  'Waray': '瓦瑞语',
  'Welsh': '威尔士语',
  'Western Persian': '西波斯语'
}

// 获取语言的中文显示名称
function getLanguageDisplayName(langName) {
  if (!langName) return '--'
  // 如果已经是中文，直接返回
  if (languageNameMap[langName]) {
    return languageNameMap[langName]
  }
  // 如果找不到映射，返回原值（兼容旧数据或其他情况）
  return langName
}

// 检查翻译队列状态
function checkTranslationQueue() {
  if (translationQueue.value.isRunning) {
    console.log('翻译队列正在运行中，跳过检查')
    return
  }
  
  // 如果队列中有待处理任务，启动下一个
  if (translationQueue.value.pendingTasks.length > 0) {
    startNextTranslation()
  }
}

const target_tip = computed(() => {
  return '翻译完成！共计翻译' + this.target_count + '字数，' + this.target_time
})

const accpet_tip = computed(() => {
  return accepts.split(',').join('/')
})

//获取翻译数量
function getCount() {
  getFinishCount().then((data) => {
    if (data.code == 200) {
      transCount.value = data.data.total
    }
  })
}

function flhandleFileListChange(file, fileList) {
  fileListShow.value = fileList.length > 0 ? true : false
  // 检查是否所有文件都已上传完成（成功或失败）
  // 使用 nextTick 确保 el-upload 组件状态已更新
  setTimeout(() => {
    if (uploadRef.value && uploadRef.value.uploadFiles) {
      checkAllFilesUploaded(uploadRef.value.uploadFiles)
    } else {
      // 如果没有 uploadRef，使用传入的 fileList
      checkAllFilesUploaded(fileList)
    }
  }, 50)
}

// 检查是否所有文件都已上传完成
function checkAllFilesUploaded(fileList) {
  // 如果没有文件列表，直接返回
  if (!fileList || fileList.length === 0) {
    upload_load.value = false
    areAllFilesUploaded.value = false
    return
  }
  
  // 检查是否还有文件正在上传中或准备上传
  const hasUploading = fileList.some(file => {
    // el-upload 的文件状态：'ready' 准备上传, 'uploading' 上传中, 'success' 成功, 'fail' 失败
    const isUploading = file.status === 'ready' || file.status === 'uploading'
    return isUploading
  })
  
  // 检查是否所有文件都已上传完成（成功或失败）
  const allCompleted = fileList.every(file => {
    return file.status === 'success' || file.status === 'fail'
  })
  
  // 如果有文件正在上传，保持按钮禁用状态
  upload_load.value = hasUploading
  // 只有当所有文件都完成（成功或失败）且没有文件正在上传时，才允许点击
  areAllFilesUploaded.value = allCompleted && !hasUploading
  
  // 调试日志（需要时可打开）
  // console.log(`文件列表检查: 总数=${fileList.length}, 正在上传=${hasUploading}, 全部完成=${allCompleted}, areAllFilesUploaded=${areAllFilesUploaded.value}`)
  // fileList.forEach((file, index) => {
  //   console.log(`  文件${index + 1}: ${file.name}, 状态: ${file.status}`)
  // })
}

// 进度查询 status: "done"
function process(uuid) {
  // 检查列表是否为空，如果为空则不调用
  if (!translatesData.value || translatesData.value.length === 0) {
    console.log('翻译列表为空，停止进度查询:', uuid)
    return
  }
  
  // 检查任务是否还在列表中
  const taskExists = translatesData.value.some(item => item.uuid === uuid)
  if (!taskExists) {
    console.log('任务不在列表中，停止进度查询:', uuid)
    return
  }
  
  // // 检查是否已经完成或失败
  // if (
  //   result.value[uuid] &&
  //   (result.value[uuid].status === 'done' || result.value[uuid].status === 'failed')
  // ) {
  //   return // 如果任务已完成或失败，直接返回
  // }

  // // 检查是否正在翻译
  // if (!translating[uuid]) {
  //   return
  // }

  // 调用翻译处理函数
  transalteProcess({ uuid })
    .then((res) => {
      if (res.code == 200) {
        // console.log('进度查询', res.data)
        // 如果返回的字段中明确表示任务失败
        if (res.data.status === 'failed') {
          // 处理任务失败
          ElMessage({
            message: '翻译失败' || '未知错误',
            type: 'error',
            duration: 5000,
          })
          
          // 任务失败后，刷新一次列表，让用户看到状态变化
          getTranslatesData(1)
          
          // 任务失败时，从form.files中移除失败的文件
          const failedFileIndex = form.value.files.findIndex(file => file.uuid === uuid)
          if (failedFileIndex !== -1) {
            form.value.files.splice(failedFileIndex, 1)
            console.log('已从文件列表中移除翻译失败的文件:', uuid)
          }
          
          // 任务失败后，尝试启动下一个
          setTimeout(() => startNextTranslation(), 2000)
          return // 直接返回，不再继续查询
        }
        
        // 如果返回的字段中明确表示任务完成
        if (res.data.status === 'done') {
          // 任务状态已完成，立即刷新列表
          ElMessage.success({
            message: '文件翻译完成！',
          })
          
          // 立即刷新列表，让用户看到状态变化
          getTranslatesData(1)
          
          // 翻译完成后，从form.files中移除已完成的文件
          const completedFileIndex = form.value.files.findIndex(file => file.uuid === uuid)
          if (completedFileIndex !== -1) {
            form.value.files.splice(completedFileIndex, 1)
            console.log('已从文件列表中移除翻译完成的文件:', uuid)
          }
          
          // 翻译完成后，自动启动下一个待翻译的文件
          setTimeout(() => startNextTranslation(), 2000)
          return // 直接返回，不再继续查询
        }

        if (res.data.progress == 100) {
          // 进度达到100%但状态还不是done，继续监控状态变化
          console.log("进度达到100%，等待状态更新...")
          
          // 继续监控状态变化，缩短间隔以便更快检测
          // 在继续调用前，检查任务是否还在列表中
          setTimeout(() => {
            if (translatesData.value && translatesData.value.length > 0 && 
                translatesData.value.some(item => item.uuid === uuid)) {
              process(uuid)
            }
          }, 5000)
        } else {
          // 如果未完成，继续调用 process 函数
          // 在继续调用前，检查任务是否还在列表中
          setTimeout(() => {
            if (translatesData.value && translatesData.value.length > 0 && 
                translatesData.value.some(item => item.uuid === uuid)) {
              process(uuid)
            }
          }, 10000)
        }
      } else {
        // 处理错误情况（res.code != 200）
        ElMessage({
          message: res.message || '查询任务进度失败',
          type: 'error',
          duration: 5000,
        })
        
        // 任务失败后，刷新一次列表，让用户看到状态变化
        getTranslatesData(1)
        
        // 任务失败时，从form.files中移除失败的文件
        const failedFileIndex = form.value.files.findIndex(file => file.uuid === uuid)
        if (failedFileIndex !== -1) {
          form.value.files.splice(failedFileIndex, 1)
          console.log('已从文件列表中移除查询失败的文件:', uuid)
        }
        
        // 任务失败后，尝试启动下一个
        setTimeout(() => startNextTranslation(), 2000)
      }
    })
    .catch((error) => {
      // 处理网络错误或其他异常
      ElMessage({
        message: '翻译过程失败.',
        type: 'error',
        duration: 5000,
      })
      
      // 网络错误后，刷新一次列表，让用户看到状态变化
      getTranslatesData(1)
      
      // 网络错误时，从form.files中移除失败的文件
      const failedFileIndex = form.value.files.findIndex(file => file.uuid === uuid)
      if (failedFileIndex !== -1) {
        form.value.files.splice(failedFileIndex, 1)
        console.log('已从文件列表中移除网络错误的文件:', uuid)
      }
      
      // 任务失败后，尝试启动下一个
      setTimeout(() => startNextTranslation(), 2000)
    })
}

// 自动启动下一个待翻译的文件
async function startNextTranslation() {
  try {
    // 获取当前翻译列表
    const res = await translates({ page: 1, limit: 100 })
    if (res.code !== 200) {
      console.log('获取翻译列表失败，无法启动下一个任务')
      return
    }
    
    const translateList = res.data.data
    if (!translateList || translateList.length === 0) {
      console.log('没有待翻译的文件')
      return
    }
    
    // 查找状态为 'none' 的第一个文件
    const nextTask = translateList.find(item => item.status === 'none')
    if (!nextTask) {
      // 没有待翻译的文件，所有任务已完成或进行中
      // 这是正常情况，不需要记录日志
      return
    }
    
    // 检查必要参数
    if (!nextTask.uuid) {
      console.error('任务缺少 uuid:', nextTask)
      return
    }
    
    if (!nextTask.origin_filename) {
      console.error('任务缺少 origin_filename:', nextTask)
      return
    }
    
    // 在启动前等待更长时间，让后端队列管理器有机会先启动任务
    // 队列管理器通常每几秒检查一次，所以等待时间要足够
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // 再次获取最新状态，检查任务是否已被队列管理器启动
    const refreshRes = await translates({ page: 1, limit: 100 })
    if (refreshRes.code === 200) {
      const refreshedList = refreshRes.data.data
      const refreshedTask = refreshedList.find(item => item.uuid === nextTask.uuid)
      
      // 如果任务状态已经不是 'none'，说明已经被其他进程启动了，跳过
      if (!refreshedTask) {
        // 任务不存在了，跳过
        return
      }
      
      // 检查任务状态：如果已经是 'queued', 'process', 'changing', 'done'，说明已经被启动
      if (refreshedTask.status !== 'none') {
        // 任务已被启动（可能是队列管理器），这是正常情况，静默处理
        console.log(`任务 ${nextTask.origin_filename} 已被启动，当前状态: ${refreshedTask.status}`)
        return
      }
    }
    
    // 再次等待一小段时间，确保状态稳定
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 最后一次检查状态
    const finalCheckRes = await translates({ page: 1, limit: 100 })
    if (finalCheckRes.code === 200) {
      const finalList = finalCheckRes.data.data
      const finalTask = finalList.find(item => item.uuid === nextTask.uuid)
      
      if (!finalTask || finalTask.status !== 'none') {
        // 任务状态已改变，跳过
        if (finalTask) {
          console.log(`任务 ${nextTask.origin_filename} 状态已改变为: ${finalTask.status}，跳过自动启动`)
        }
        return
      }
    }
    
    console.log('自动启动下一个翻译任务:', nextTask.origin_filename)
    
    // 将任务添加到自动启动集合中，禁用重试按钮
    autoStartingTasks.value.add(nextTask.uuid)
    
    // 验证 lang 参数
    if (!nextTask.lang || !nextTask.lang.trim()) {
      console.error('任务缺少 lang 参数:', nextTask)
      // 如果参数缺失，从自动启动集合中移除
      autoStartingTasks.value.delete(nextTask.uuid)
      return
    }
    
    // 准备翻译参数
    const translateParams = {
      server: nextTask.server || 'openai',
      model: nextTask.model || 'qwen-mt-plus',
      lang: nextTask.lang,  // 必须使用任务中的 lang，不使用默认值
      uuid: nextTask.uuid,
      prompt: nextTask.prompt || '请将以下内容翻译为{target_lang}',
      threads: nextTask.threads || 30,
      file_name: nextTask.origin_filename,
      api_url: nextTask.api_url || '',
      api_key: nextTask.api_key || '',
      app_id: nextTask.app_id || '',
      app_key: nextTask.app_key || '',
      backup_model: nextTask.backup_model || '',
      origin_lang: nextTask.origin_lang || '',
      type: nextTask.type || 'trans_all_only_inherit',
      comparison_id: nextTask.comparison_id || '',
      prompt_id: nextTask.prompt_id || '',
      doc2x_flag: nextTask.doc2x_flag || 'N',
      doc2x_secret_key: nextTask.doc2x_secret_key || 'sk-6jr7hx69652pzdd4o4poj3hp5mauana0',
      size: nextTask.size || 0
    }
    
    try {
      // 启动翻译任务
      const translateRes = await transalteFile(translateParams)
      
      if (translateRes.code === 200) {
        console.log('自动启动翻译任务成功:', nextTask.origin_filename)
        // 使用专门的进度更新函数，而不是刷新整个列表
        updateProgressOnly()
        // 启动进度查询
        process(nextTask.uuid)
        // 任务启动成功，从自动启动集合中移除（允许用户手动重试）
        autoStartingTasks.value.delete(nextTask.uuid)
      } else {
        // 检查是否是"任务已在处理中"的错误（这是正常情况，不需要警告）
        const errorMsg = translateRes.message || translateRes.data?.message || ''
        const isTaskAlreadyProcessing = errorMsg.includes('已在处理中') || 
                                        errorMsg.includes('already') ||
                                        translateRes.code === 400
        
        if (!isTaskAlreadyProcessing) {
          // 只有非"已在处理中"的错误才记录警告
          console.warn('自动启动翻译任务失败:', {
            filename: nextTask.origin_filename,
            error: errorMsg,
            response: translateRes
          })
        }
        // 如果是"已在处理中"，静默处理（任务可能已被队列管理器启动）
        // 任务启动失败或已在处理中，从自动启动集合中移除
        autoStartingTasks.value.delete(nextTask.uuid)
      }
    } catch (error) {
      // 发生异常，从自动启动集合中移除
      autoStartingTasks.value.delete(nextTask.uuid)
      throw error
    }
    
  } catch (error) {
    // 检查是否是"任务已在处理中"的错误
    const errorMsg = error?.response?.data?.message || error?.message || ''
    const isTaskAlreadyProcessing = errorMsg.includes('已在处理中') || 
                                    errorMsg.includes('already') ||
                                    (error?.response?.status === 400)
    
    if (!isTaskAlreadyProcessing) {
      // 只有非"已在处理中"的错误才记录警告
      console.warn('自动启动下一个翻译任务时发生异常:', {
        error: errorMsg,
        fullError: error
      })
    }
    // 如果是"已在处理中"，静默处理（任务可能已被队列管理器启动）
  }
}

// 批量启动翻译任务
async function startBatchTranslation() {
  // 注意：防重复提交检查已在 handleTranslate 中完成，这里不需要重复检查
  // 按钮状态也已在 handleTranslate 中设置
  
  try {
    console.log('开始批量启动翻译任务，文件数量:', form.value.files.length)
    
    // 检查文件列表是否为空
    if (!form.value.files || form.value.files.length === 0) {
      console.error('文件列表为空，无法启动批量翻译')
      ElMessage.error('文件列表为空，请先上传文件')
      return
    }
    
    // 验证语言参数必须存在且不为空
    if (!form.value.lang || !form.value.lang.trim()) {
      console.error('目标语言参数缺失或为空:', form.value)
      ElMessage.error('请先选择目标语言')
      return
    }
    
    // 获取第一个文件的配置作为模板
    const firstFile = form.value.files[0]
    
    // 确保必要参数有默认值（但lang必须有值，不能使用默认值）
    // 注意：这里必须使用 form.value 中的值，确保与 handleTranslate 中的逻辑一致
    const templateConfig = {
      // 必需参数（后端 required_fields）
      server: form.value.server || 'openai',
      model: form.value.model || 'qwen-mt-plus',
      lang: form.value.lang,  // 必须使用用户选择的值，不使用默认值
      prompt: form.value.prompt || '请将以下内容翻译为{target_lang}',
      threads: form.value.threads || 30,
      
      // API 配置
      api_url: form.value.api_url || '',
      api_key: form.value.api_key || '',
      
      // 其他配置
      app_id: form.value.app_id || '',
      app_key: form.value.app_key || '',
      backup_model: form.value.backup_model || '',
      origin_lang: form.value.origin_lang || '',
      type: form.value.type || 'trans_all_only_inherit',
      comparison_id: form.value.comparison_id || '',
      prompt_id: form.value.prompt_id || '',
      doc2x_flag: form.value.doc2x_flag || 'N',
      doc2x_secret_key: form.value.doc2x_secret_key || 'sk-6jr7hx69652pzdd4o4poj3hp5mauana0',
      
      // PDF 翻译方式
      pdf_translate_method: form.value.pdf_translate_method || translateStore.common?.pdf_translate_method || 'direct'
    }
    
    // 验证所有必需参数都存在
    const requiredParams = ['server', 'model', 'lang', 'prompt', 'threads']
    const missingParams = requiredParams.filter(param => !templateConfig[param] || (typeof templateConfig[param] === 'string' && !templateConfig[param].trim()))
    if (missingParams.length > 0) {
      console.error('批量翻译缺少必需参数:', missingParams, 'templateConfig:', templateConfig)
      ElMessage.error(`批量翻译缺少必需参数: ${missingParams.join(', ')}`)
      return
    }
    
    console.log('批量翻译模板配置:', templateConfig)
    
    // 直接以上传返回的文件列表发起任务（通过uuid关联），不依赖列表匹配，避免"未找到对应任务"误判
    const filesToTranslate = [...form.value.files]
    
    console.log(`实际需要翻译的文件数量: ${filesToTranslate.length}/${form.value.files.length}`)
    
    // 验证所有文件都有必要信息
    const invalidFiles = filesToTranslate.filter(file => !file.uuid || !file.file_name)
    if (invalidFiles.length > 0) {
      console.error('发现无效文件（缺少 uuid 或 file_name）:', invalidFiles)
      ElMessage.error(`有 ${invalidFiles.length} 个文件信息不完整，请重新上传`)
      return
    }
    
    let successCount = 0
    let failCount = 0
    let skipCount = form.value.files.length - filesToTranslate.length
    
    // 先显示批量翻译开始提示
    if (filesToTranslate.length > 0) {
      ElMessage.info({
        message: `正在启动 ${filesToTranslate.length} 个文件的翻译任务...`,
        duration: 2000
      })
    }
    
    // 在批量启动开始前，一次性将所有任务添加到自动启动集合中，禁用所有重试按钮
    filesToTranslate.forEach(file => {
      if (file.uuid) {
        autoStartingTasks.value.add(file.uuid)
      }
    })
    
    // 逐个启动翻译任务
    for (let i = 0; i < filesToTranslate.length; i++) {
      const file = filesToTranslate[i]
      
      // 检查文件必要信息
      if (!file.uuid) {
        console.error(`文件 ${i + 1}/${filesToTranslate.length} 缺少 uuid:`, file)
        failCount++
        // 注意：如果缺少 uuid，理论上不应该在集合中，但为了安全起见，尝试移除
        // 由于没有 uuid，无法从集合中移除，这是正常的
        continue
      }
      
      if (!file.file_name) {
        console.error(`文件 ${i + 1}/${filesToTranslate.length} 缺少 file_name:`, file)
        failCount++
        // 如果缺少 file_name，从自动启动集合中移除
        autoStartingTasks.value.delete(file.uuid)
        continue
      }
      
      try {
        // 准备翻译参数（确保所有必需参数都存在）
        const translateParams = {
          ...templateConfig,
          // 文件相关参数（每个文件不同）
          uuid: file.uuid,
          file_name: file.file_name,
          size: file.size || 0
        }
        
        // 最终验证：确保所有必需参数都存在且不为空
        const requiredParams = ['server', 'model', 'lang', 'uuid', 'prompt', 'threads', 'file_name']
        const missingParams = requiredParams.filter(param => {
          const value = translateParams[param]
          return !value || (typeof value === 'string' && !value.trim())
        })
        
        if (missingParams.length > 0) {
          console.error(`文件 ${i + 1}/${filesToTranslate.length} 缺少必需参数:`, missingParams, 'translateParams:', translateParams)
          failCount++
          // 如果缺少必需参数，从自动启动集合中移除
          autoStartingTasks.value.delete(file.uuid)
          continue
        }
        
        console.log(`准备启动文件 ${i + 1}/${filesToTranslate.length} 的翻译任务:`, {
          filename: file.file_name,
          uuid: file.uuid,
          lang: translateParams.lang,  // 特别记录 lang 参数
          params: translateParams
        })
        
        // 注意：任务已在循环开始前添加到自动启动集合中，这里不需要重复添加
        
        // 启动翻译任务
        const res = await transalteFile(translateParams)
        console.log(`文件 ${i + 1}/${filesToTranslate.length} 翻译任务启动响应:`, file.file_name, res)
        
        if (res.code === 200) {
          // 检查返回的状态
          const taskStatus = res.data?.status || 'unknown'
          
          // 如果状态是 'none'，说明任务没有被启动，可能是参数问题
          if (taskStatus === 'none') {
            console.error(`文件 ${i + 1}/${filesToTranslate.length} 翻译任务启动后状态仍为 'none':`, file.file_name, res)
            failCount++
            // 任务启动失败，从自动启动集合中移除
            autoStartingTasks.value.delete(file.uuid)
            ElMessage.warning({
              message: `任务 ${file.file_name} 启动失败，状态异常`,
              duration: 3000
            })
            continue
          }
          
          successCount++
          console.log(`文件 ${i + 1}/${filesToTranslate.length} 翻译任务启动成功:`, file.file_name, '状态:', taskStatus)
          
          // 检查是否进入队列
          if (taskStatus === 'queued') {
            console.log(`文件 ${file.file_name} 已加入队列`)
            // 如果任务被加入队列，立即刷新一次列表，让用户看到状态变化
            await getTranslatesData(1)
          } else if (taskStatus === 'started' || taskStatus === 'process') {
            console.log(`文件 ${file.file_name} 已直接启动`)
            // 如果任务直接启动，也刷新一次列表，确保任务在列表中
            await getTranslatesData(1)
          } else {
            // 其他状态，记录日志
            console.warn(`文件 ${file.file_name} 返回了未知状态:`, taskStatus)
          }
          
          // 启动进度查询（使用返回的uuid或原有的uuid）
          // 注意：在刷新列表后再调用 process，确保任务在列表中
          const taskUuid = res.data.uuid || file.uuid
          if (taskUuid) {
            // 任务启动成功，从自动启动集合中移除（允许用户手动重试）
            autoStartingTasks.value.delete(file.uuid)
            
            // 确保列表已刷新后再调用 process
            // 如果列表为空，等待一下再调用，给列表刷新时间
            if (!translatesData.value || translatesData.value.length === 0) {
              // 列表为空，等待一下再调用
              setTimeout(() => {
                if (translatesData.value && translatesData.value.length > 0) {
                  process(taskUuid)
                }
              }, 500)
            } else {
              // 列表不为空，直接调用
              process(taskUuid)
            }
          } else {
            // 如果没有uuid，从自动启动集合中移除
            autoStartingTasks.value.delete(file.uuid)
          }
          
          // 如果不是最后一个文件，等待一下再启动下一个（避免API限流）
          if (i < filesToTranslate.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 1000))
          }
        } else {
          failCount++
          // 任务启动失败，从自动启动集合中移除
          autoStartingTasks.value.delete(file.uuid)
          const errorMsg = res.message || res.data?.message || '未知错误'
          console.error(`文件 ${i + 1}/${filesToTranslate.length} 翻译任务启动失败:`, file.file_name, {
            code: res.code,
            message: errorMsg,
            response: res
          })
          // 显示错误信息，让用户知道哪个文件启动失败
          ElMessage.error({
            message: `任务 ${file.file_name} 启动失败: ${errorMsg}`,
            duration: 5000
          })
        }
      } catch (error) {
        failCount++
        // 任务启动异常，从自动启动集合中移除
        autoStartingTasks.value.delete(file.uuid)
        const errorMsg = error?.response?.data?.message || error?.message || '网络错误'
        console.error(`文件 ${i + 1}/${filesToTranslate.length} 翻译任务启动异常:`, file.file_name, {
          error: errorMsg,
          fullError: error
        })
        // 显示错误信息，让用户知道哪个文件启动失败
        ElMessage.error({
          message: `任务 ${file.file_name} 启动异常: ${errorMsg}`,
          duration: 5000
        })
      }
    }
    
    // 刷新翻译列表，确保新任务显示在最前面（在显示结果前先刷新）
    if (successCount > 0) {
      // 立即刷新一次，显示所有任务的最新状态
      await getTranslatesData(1)
      
      // 等待更长时间，让队列管理器有时间启动队列中的任务
      // 队列管理器通常每几秒检查一次，所以等待时间要足够
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // 再次刷新列表，获取最新状态（包括队列管理器启动的任务）
      await getTranslatesData(1)
      
      // 再等待一段时间，确保所有任务状态都已更新
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // 最后一次刷新，确保状态准确
      await getTranslatesData(1)
      
      // 根据实际任务状态统计
      const startedUuids = filesToTranslate
        .filter(file => file.uuid)
        .map(file => file.uuid)
      
      const actualTasks = translatesData.value.filter(item => 
        startedUuids.includes(item.uuid)
      )
      
      const doneCount = actualTasks.filter(item => item.status === 'done').length
      const processCount = actualTasks.filter(item => 
        item.status === 'process' || item.status === 'changing' || item.status === 'queued'
      ).length
      const failedCount = actualTasks.filter(item => item.status === 'failed').length
      
      // 根据实际状态显示提示
      if (successCount > 0) {
        let message = ''
        if (doneCount > 0 && processCount === 0) {
          // 全部已完成
          message = `${doneCount} 个文件翻译已完成`
          ElMessage.success({
            message: message,
            duration: 3000
          })
        } else if (doneCount > 0 && processCount > 0) {
          // 部分已完成，部分进行中
          message = `${doneCount} 个已完成，${processCount} 个进行中`
          ElMessage.success({
            message: message,
            duration: 3000
          })
        } else if (processCount > 0) {
          // 全部进行中
          message = `已启动 ${processCount} 个翻译任务`
          ElMessage.success({
            message: message,
            duration: 3000
          })
        } else {
          // 其他情况
          message = `已启动 ${successCount} 个翻译任务`
          ElMessage.success({
            message: message,
            duration: 3000
          })
        }
        
        if (failCount > 0) {
          ElMessage.warning({
            message: `${failCount} 个任务启动失败`,
            duration: 3000
          })
        }
      }
      
      // 批量翻译任务启动成功后才清空上传文件列表
      // 只要有文件成功启动，就清空所有文件列表（包括失败的文件）
      uploadRef.value.clearFiles()
      form.value.files = []  // 清空表单文件数组
      areAllFilesUploaded.value = false  // 重置状态（文件列表已清空）
    } else if (failCount > 0) {
      ElMessage.error({
        message: `翻译任务启动失败: ${failCount} 个文件`,
        duration: 5000
      })
      // 全部失败时不清空文件列表，让用户可以重试
    } else {
      ElMessage.warning({
        message: '没有可启动的翻译任务',
        duration: 3000
      })
      // 没有成功也没有失败（全部跳过）时，也不清空文件列表
    }
    
  } catch (error) {
    console.error('批量启动翻译任务时发生错误:', error)
    ElMessage.error({
      message: error.message || '批量启动翻译任务失败，请检查控制台日志',
      duration: 5000
    })
    
    // 失败时不清空文件列表，让用户可以重试
    // uploadRef.value.clearFiles()
    // form.value.files = []  // 清空表单文件数组
  }
}

// doc2x进度查询
const doc2xStatusQuery = async (data) => {
  const res = await doc2xQueryStatusService(data)
  if (res.code == 200) {
    console.log('doc2x进度查询', res.data)
    // 如果返回的字段中明确表示任务失败
    if (res.data.status === 'failed') {
      // 处理任务失败
      ElMessage({
        message: '翻译失败' || '未知错误',
        type: 'error',
        duration: 5000,
      })
      
      // doc2x翻译失败后，刷新一次列表，让用户看到状态变化
      getTranslatesData(1)
      
      // doc2x翻译失败时，从form.files中移除失败的文件
      const failedFileIndex = form.value.files.findIndex(file => file.uuid === data.uuid)
      if (failedFileIndex !== -1) {
        form.value.files.splice(failedFileIndex, 1)
        console.log('已从文件列表中移除doc2x翻译失败的文件:', data.uuid)
      }
      
      return // 直接返回，不再继续查询
    } else if (res.data.status == 'done') {
      // 任务完成时，显示成功消息
      ElMessage.success({
        message: '文件翻译成功！',
      })
      
      // doc2x翻译完成后，刷新一次列表，让用户看到状态变化
      getTranslatesData(1)
      
      // doc2x翻译完成后，从form.files中移除已完成的文件
      const completedFileIndex = form.value.files.findIndex(file => file.uuid === data.uuid)
      if (completedFileIndex !== -1) {
        form.value.files.splice(completedFileIndex, 1)
        console.log('已从文件列表中移除doc2x翻译完成的文件:', data.uuid)
      }
    } else {
      // 如果未完成，继续调用 process 函数
      setTimeout(() => doc2xStatusQuery(data), 10000)
    }
  } else {
    // 处理错误情况（res.code != 200）
    ElMessage({
      message: res.message || '查询任务进度失败',
      type: 'error',
      duration: 5000,
    })
    
    // doc2x查询失败后，刷新一次列表，让用户看到状态变化
    getTranslatesData(1)
    
    // doc2x查询失败时，从form.files中移除失败的文件
    const failedFileIndex = form.value.files.findIndex(file => file.uuid === data.uuid)
    if (failedFileIndex !== -1) {
      form.value.files.splice(failedFileIndex, 1)
      console.log('已从文件列表中移除doc2x查询失败的文件:', data.uuid)
    }
  }
}
// 启动翻译-----立即翻译-------
async function handleTranslate(transform) {
  // 检查是否有文件需要翻译
  if (!form.value.files || form.value.files.length === 0) {
    ElMessage({
      message: '请先上传文件',
      type: 'warning'
    })
    return
  }
  
  // 防重复提交：如果正在处理中，直接返回（在文件检查之后，避免误判）
  if (translateButtonState.value.isLoading || translateButtonState.value.disabled) {
    console.log('翻译任务正在处理中，忽略重复点击')
    return
  }
  
  // 立即设置按钮状态，防止重复点击
  translateButtonState.value.isLoading = true
  translateButtonState.value.disabled = true
  
  // 检查用户翻译配置
  try {
    const { getCustomerSetting } = await import('@/api/trans')
    const settingRes = await getCustomerSetting()
    
    if (settingRes.code === 200 && settingRes.data) {
      const userSetting = settingRes.data
      
      // 检查是否设置了目标语言
      if (!userSetting.lang || !userSetting.lang.trim()) {
        ElMessage({
          message: '请先进行翻译设置，选择目标语言后再开始翻译',
          type: 'warning',
          duration: 5000
        })
        translateButtonState.value.isLoading = false
        translateButtonState.value.disabled = false
        return
      }
      
      // 从数据库配置更新到store
      translateStore.updateAIServerSettings({
        lang: userSetting.lang,
        comparison_id: userSetting.comparison_id && userSetting.comparison_id.length > 0 
          ? userSetting.comparison_id.map(id => parseInt(id)) 
          : [],
        prompt_id: userSetting.prompt_id || null,
      })
      translateStore.updateCommonSettings({
        pdf_translate_method: userSetting.pdf_translate_method || 'direct',
      })
    } else {
      // 如果获取配置失败，提示用户先设置
      ElMessage({
        message: '请先进行翻译设置，选择目标语言后再开始翻译',
        type: 'warning',
        duration: 5000
      })
      translateButtonState.value.isLoading = false
      translateButtonState.value.disabled = false
      return
    }
  } catch (error) {
    console.error('检查用户配置失败:', error)
    ElMessage({
      message: '检查翻译配置失败，请先进行翻译设置',
      type: 'error',
      duration: 5000
    })
    translateButtonState.value.isLoading = false
    translateButtonState.value.disabled = false
    return
  }
  
  // 首先再次赋值，防止没有更新
  form.value = { ...form.value, ...translateStore.getCurrentServiceForm }
  
  // 添加调试信息
  console.log('翻译设置中的术语库:', translateStore.aiServer.comparison_id)
  console.log('翻译设置中的目标语言:', translateStore.aiServer.lang)
  console.log('当前表单数据:', form.value)
  console.log('当前服务类型:', currentServiceType.value)
  
  // 确保语言字段正确设置（从store中获取）
  if (currentServiceType.value === 'ai') {
    if (translateStore.aiServer.lang && translateStore.aiServer.lang.trim()) {
      form.value.lang = translateStore.aiServer.lang
      // 如果langs数组为空，则使用lang设置
      if (!form.value.langs || form.value.langs.length === 0) {
        form.value.langs = [translateStore.aiServer.lang]
      }
    } else {
      // 如果语言未设置，阻止翻译
      ElMessage.error('请先进行翻译设置，选择目标语言')
      translateButtonState.value.isLoading = false
      translateButtonState.value.disabled = false
      return
    }
  }
  
  // 最终验证：确保lang字段存在且不为空
  if (!form.value.lang || !form.value.lang.trim()) {
    console.error('目标语言参数缺失或为空:', form.value)
    ElMessage.error('请先进行翻译设置，选择目标语言')
    translateButtonState.value.isLoading = false
    translateButtonState.value.disabled = false
    return
  }
  
  // 1.判断是否上传文件
  // if (form.value.files.length <= 0) {
  //   ElMessage({
  //     message: '请上传文件',
  //     type: 'error'
  //   })
  //   return
  // }
  const file_suffix = form.value.files[0].file_name.split('.').pop().toLowerCase()
  // 先判断是不是pdf文件和是否启用doc2x
  // if (file_suffix == 'pdf' && translateStore.common.doc2x_flag == 'N') {
  //   return ElMessage({
  //     message: '使用pdf翻译请先配置doc2x密钥',
  //     type: 'error',
  //   })
  // }
  if (
    file_suffix == 'pdf' &&
    translateStore.common.doc2x_flag == 'Y' 
  ) {
    form.value.server = 'doc2x'
    form.value.doc2x_flag = translateStore.common.doc2x_flag
    form.value.doc2x_secret_key = 'sk-6jr7hx69652pzdd4o4poj3hp5mauana0'
    console.log('翻译pdf表单：', form.value)
    // 1.启动doc2x翻译
    // const res = await doc2xStartService(form.value)
    // if (res.code == 200) {
    //   ElMessage({
    //     message: '提交doc2x翻译任务成功！',
    //     type: 'success',
    //   })
    //   // 更新uuid
    //   form.value.uuid = res.data.uuid
    //   // 刷新翻译列表
    //   getTranslatesData(1)
    //   // 启动任务查询
    //   doc2xStatusQuery({ translate_id: form.value.translate_id })
    // } else {
    //   ElMessage({
    //     message: '提交翻译任务失败~',
    //     type: 'error',
    //   })
    // }
    // // 4.清空上传文件列表
    // uploadRef.value.clearFiles()
    // return res
  }

  // if (currentServiceType.value == 'ai') {
  //   // 2.检查翻译设置是否完整
  //   if (form.value.server === '') {
  //     ElMessage({
  //       message: '请选择翻译服务提供商',
  //       type: 'error',
  //     })
  //     return
  //   }

  //   if (form.value.type === '') {
  //     ElMessage({
  //       message: '请选择翻译类型',
  //       type: 'error',
  //     })
  //     return
  //   }

  //   if (form.value.model === '') {
  //     ElMessage({
  //       message: '请选择翻译模型',
  //       type: 'error',
  //     })
  //     return
  //   }

  //   if (form.value.langs.length < 1) {
  //     ElMessage({
  //       message: '请选择目标语言',
  //       type: 'error',
  //     })
  //     return
  //   }

  //   if (form.value.prompt === '') {
  //     ElMessage({
  //       message: '请输入翻译提示词',
  //       type: 'error',
  //     })
  //     return
  //   }
  //   // 翻译服务 检查api密钥是否为空 会员不需要提供key
  //   if (form.value.api_key === '' && !userStore.isVip) {
  //     ElMessage({
  //       message: '请输入API密钥',
  //       type: 'error',
  //     })
  //     return
  //   }
  // } else if (currentServiceType.value == 'baidu') {
  //   if (form.value.app_key === '' || form.value.app_id === '' || form.value.to_lang === '') {
  //     ElMessage({
  //       message: '请填写百度翻译相关信息!',
  //       type: 'error',
  //     })
  //     return
  //   }
  // }

  // 3.提交翻译任务
  // 如果是会员，不需要提供api和key
  form.value.api_key = userStore.isVip ? '' : form.value.api_key
  form.value.api_url = userStore.isVip ? '' : form.value.api_url

  // 按钮状态已在函数开头设置，这里不需要重复设置

  try {
    // 先检查队列状态，如果系统繁忙则弹出确认对话框
    await checkQueueStatus()
    if (!queueStatus.value.can_start_new) {
      const confirmed = await showQueueConfirmDialog()
      if (!confirmed) {
        // 用户取消，恢复按钮状态
        translateButtonState.value.isLoading = false
        translateButtonState.value.disabled = false
        return
      }
    }

    // 检查是否有多个文件需要翻译
    if (form.value.files.length > 1) {
      // 批量启动翻译任务
      await startBatchTranslation()
    } else {
      // 单个文件翻译（保持原有逻辑）
      console.log('翻译表单：', form.value)
      
      // 最终验证：确保lang字段存在且不为空
      if (!form.value.lang || !form.value.lang.trim()) {
        console.error('目标语言参数缺失或为空:', form.value)
        ElMessage.error('请先选择目标语言')
        translateButtonState.value.isLoading = false
        translateButtonState.value.disabled = false
        return
      }
      
      // 明确传递PDF翻译方式，避免后端回退默认值
      form.value.pdf_translate_method = translateStore.common?.pdf_translate_method || 'direct'
      
      // 确保传递 uuid（从 files[0] 中获取）
      if (form.value.files && form.value.files.length > 0) {
        const file = form.value.files[0]
        if (file.uuid) {
          form.value.uuid = file.uuid
          console.log('使用文件中的 uuid:', file.uuid)
        } else {
          console.error('文件缺少 uuid:', file)
          ElMessage({
            message: '文件信息不完整，请重新上传',
            type: 'error',
          })
          translateButtonState.value.isLoading = false
          translateButtonState.value.disabled = false
          return
        }
      } else {
        console.error('没有文件需要翻译')
        ElMessage({
          message: '请先上传文件',
          type: 'warning',
        })
        translateButtonState.value.isLoading = false
        translateButtonState.value.disabled = false
        return
      }
      
      const res = await transalteFile(form.value)
      console.log('翻译任务启动响应:', res)
      
      if (res.code == 200) {
        // 检查任务状态
        if (res.data.status === 'queued') {
          ElMessage({
            message: res.data.message || '任务已加入队列，等待系统资源释放后自动开始',
            type: 'warning',
            duration: 5000
          })
        } else if (res.data.status === 'started' || res.data.status === 'process') {
          ElMessage({
            message: '提交翻译任务成功！',
            type: 'success',
          })
        } else {
          ElMessage({
            message: res.data.message || '提交翻译任务成功！',
            type: 'success',
          })
        }
        
        // 先刷新一次列表，让用户看到新创建的翻译任务
        await getTranslatesData(1)
        
        // 然后启动任务查询（使用返回的uuid或原有的uuid）
        const taskUuid = res.data.uuid || form.value.uuid
        if (taskUuid) {
          process(taskUuid)
        }
        
        // 翻译任务启动成功后才清空文件列表
        uploadRef.value.clearFiles()
        form.value.files = []  // 清空表单文件数组
        areAllFilesUploaded.value = false  // 重置状态（文件列表已清空）
      } else {
        console.error('翻译任务启动失败:', res)
        ElMessage({
          message: res.message || '提交翻译任务失败，请检查控制台日志',
          type: 'error',
          duration: 5000
        })
        // 翻译失败时不清空文件列表，让用户可以重试
      }
    }
  } catch (error) {
    console.error('翻译任务提交失败:', error)
    ElMessage({
      message: error.message || '提交翻译任务失败，请稍后重试',
      type: 'error',
    })
  } finally {
    // 无论成功失败，都恢复按钮状态
    translateButtonState.value.isLoading = false
    translateButtonState.value.disabled = false
    
    // 注意：文件列表不清空，让用户可以看到上传的文件
    // 只有在翻译任务成功启动后才清空（在 startBatchTranslation 或单个文件翻译成功后清空）
    // uploadRef.value.clearFiles()
    // form.value.files = []  // 清空表单文件数组
    
    // 注意：不要重置 areAllFilesUploaded，因为文件还在，只是翻译任务已提交
    // 只有在文件列表被清空时才重置
    // areAllFilesUploaded.value = false
  }
}
// 重启翻译任务
async function retryTranslate(item) {
  form.value.uuid = item.uuid
  form.value.file_name = item.origin_filename
  form.value.server = item.server
  // 先判断是不是doc2x失败
  // if (item.server == 'doc2x') {
  //   // 1.启动doc2x翻译
  //   const res = await doc2xStartService(form.value)
  //   if (res.code == 200) {
  //     ElMessage({
  //       message: '提交doc2x翻译任务成功！',
  //       type: 'success',
  //     })
  //     // 刷新翻译列表
  //     getTranslatesData(1)
  //     // 启动任务查询
  //     doc2xStatusQuery({ translate_id: item.id })
  //   } else {
  //     ElMessage({
  //       message: '提交doc2x任务失败~',
  //       type: 'error',
  //     })
  //   }
  //   return
  // }
  // 3.重启翻译任务
  const res = await transalteFile(form.value)
  if (res.code == 200) {
    ElMessage({
      message: '启动翻译任务成功！',
      type: 'success',
    })
    
    // 先刷新一次列表，让用户看到重启的翻译任务状态
    await getTranslatesData(1)
    
    // 然后启动任务查询
    process(form.value.uuid)
  } else {
    ElMessage({
      message: '启动翻译任务失败~',
          type: 'error',
        })
      }
}

// 上传之前   && editionInfo.value != 'community'
function beforeUpload(file) {
  if (!userStore.token) {
    return false
  }
  let ext = file.name.split('.').pop()
  if (!accepts.split(',').includes('.' + ext)) {
    ElMessage({
      message: '不支持该文件格式',
      type: 'error',
      duration: 5000,
    })
    return false
  }
  // 文件开始上传时，检查并更新按钮状态
  setTimeout(() => {
    if (uploadRef.value) {
      checkAllFilesUploaded(uploadRef.value.uploadFiles)
    }
  }, 100)
  return true
}
// 上传成功
function uploadSuccess(res, file) {
  //  console.log('上传成功', file.size)
  if (res.code == 200) {
    const uploadedFile = {
      file_path: res.data.save_path,  // 使用save_path而不是filepath
      file_name: res.data.filename,
      uuid: res.data.uuid,
      translate_id: res.data.translate_id,  // 确保包含translate_id
      size: file.size  // 保存文件大小
    }
    form.value.file_name = res.data.filename
    form.value.files.push(uploadedFile)
    // 更新文件大小
    form.value.size = file.size
    // 获取到uuid和translate_id
    form.value.uuid = res.data.uuid
    form.value.translate_id = res.data.translate_id
    // 更新存储空间
    getStorageInfo()
  } else {
    ElMessage({
      message: res.message,
      type: 'error',
    })
  }
  
  // 延迟检查，确保 el-upload 的文件状态已更新
  // 使用更长的延迟，确保 el-upload 组件内部状态已完全更新
  setTimeout(() => {
    if (uploadRef.value && uploadRef.value.uploadFiles) {
      checkAllFilesUploaded(uploadRef.value.uploadFiles)
    }
  }, 200)
}

function uploadError(data) {
  ElMessage({
    message: `上传失败，${JSON.parse(data.message).message}`,
    type: 'error',
  })
  
  // 延迟检查，确保 el-upload 的文件状态已更新
  setTimeout(() => {
    if (uploadRef.value) {
      checkAllFilesUploaded(uploadRef.value.uploadFiles)
    }
  }, 100)
}

function handleExceed(files, uploadFiles) {
  // ElMessage.warning(`最多只能上传 5 个文件，当前已有 ${uploadFiles.length} 个文件，请删除一些文件后再上传！`)
  ElMessage.warning(`最多只能上传 5 个文件！`)

}

function delUploadFile(file, files) {
  let filepath = ''
  let uuid = '' // 初始化 uuid 变量
  form.value.files.forEach((item, index) => {
    if (item.file_name === file.name) {
      filepath = item.file_path
      uuid = item.uuid // 获取要删除文件的 uuid
      form.value.files.splice(index, 1)
    }
  })

  // 删除文件
  delFile({ filepath, uuid })
    .then((response) => {
      if (response.code === 200) {
        ElMessage({
          message: '文件删除成功',
          type: 'success',
        })
        // 更新存储空间
        getStorageInfo()
      } else {
        // 404 错误可能是上传中删除的情况，不显示错误消息
        if (response.code !== 404) {
          ElMessage({
            message: response.message || '文件删除失败，请稍后再试',
            type: 'error',
          })
        } else {
          // 404 错误时静默处理，只更新存储空间
          getStorageInfo()
        }
      }
    })
    .catch((error) => {
      // 网络错误或其他异常，检查是否是 404
      if (error.response && error.response.status === 404) {
        // 404 错误静默处理
        getStorageInfo()
      } else {
        ElMessage({
          message: '文件删除失败，请稍后再试',
          type: 'error',
        })
      }
    })

  // 从 result.value 中删除对应的文件
  for (let key in result.value) {
    if (result.value[key]['file_name'] === file.name) {
      delete result.value[key]
    }
  }

  // 更新 fileListShow 状态
  if (files.length <= 1) {
    fileListShow.value = false
  }
  
  // 检查是否所有文件都已上传完成
  // 使用 nextTick 确保 el-upload 组件状态已更新
  setTimeout(() => {
    if (uploadRef.value && uploadRef.value.uploadFiles) {
      checkAllFilesUploaded(uploadRef.value.uploadFiles)
    } else if (files && files.length > 0) {
      // 如果没有 uploadRef，使用传入的 files 参数
      checkAllFilesUploaded(files)
    } else {
      // 如果文件列表为空，重置状态
      upload_load.value = false
      areAllFilesUploaded.value = false
    }
  }, 150)
}

//获取翻译列表数据
async function getTranslatesData(page, uuid) {
  //删除翻译中的任务
  if (uuid) {
    delete result.value[uuid]
  }
  let skip_uuids = Object.keys(result.value)
  isLoadingData.value = true

  await translates({ page, limit: translatesLimit.value, skip_uuids: skip_uuids }).then((data) => {
    if (data.code == 200) {
      data.data.data.forEach((item) => {
        //获取文档类型
        let fileArr = item.origin_filename.split('.')
        let fileType = fileArr[fileArr.length - 1]
        let fileType_f = ''
        if (fileType == 'docx' || fileType == 'xlsx' || fileType == 'pptx') {
          fileType_f = fileType
        } else {
          fileType_f = 'other'
        }
        item.file_type = fileType_f
      })
      translatesData.value = data.data.data
      translatesTotal.value = data.data.total
      if (translatesData.value.length > 0 || result.value.length > 0) {
        no_data.value = false
      } else {
        no_data.value = true
      }
      
      // 检查是否需要启动自动进度更新
      const hasProcessingTasks = translatesData.value.some(item => 
        item.status === 'process' || item.status === 'changing' || item.status === 'none'
      )
      
      if (hasProcessingTasks && !autoRefreshInterval.value) {
        console.log('🚀 检测到翻译任务，启动自动进度更新')
        startAutoRefresh()
      } else if (!hasProcessingTasks && autoRefreshInterval.value) {
        console.log('✅ 所有翻译任务完成，停止自动进度更新')
        stopAutoRefresh()
      }
      
      // 切换状态
      isLoadingData.value = false
    }
  })
  // 切换状态
  isLoadingData.value = false
  getStorageInfo()
  getCount()
}

// 检查队列状态
async function checkQueueStatus() {
  try {
    const res = await getQueueStatus()
    if (res.code === 200) {
      queueStatus.value = res.data.system_status
    }
  } catch (error) {
    console.error('获取队列状态失败:', error)
  }
}

// 显示队列确认对话框
async function showQueueConfirmDialog() {
  try {
    await checkQueueStatus()
    
    const { queued_count, running_count, memory_usage_gb, memory_limit_gb } = queueStatus.value
    
    const message = `
      <div style="text-align: left;">
        <p><strong>系统资源紧张，需要进入等待队列</strong></p>
        <p>• 当前运行任务: ${running_count} 个</p>
        <p>• 队列中等待: ${queued_count} 个</p>
        <p>• 内存使用: ${memory_usage_gb}GB / ${memory_limit_gb}GB</p>
        <p style="margin-top: 10px; color: #666;">
          任务将按提交顺序自动开始，请耐心等待
        </p>
      </div>
    `
    
    return await ElMessageBox.confirm(message, '系统繁忙提示', {
      confirmButtonText: '继续提交',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: true,
      customClass: 'queue-confirm-dialog'
    })
  } catch (error) {
    if (error === 'cancel') {
      return false
    }
    throw error
  }
}

// 专门的进度更新函数（只更新进度，不刷新整个列表）
async function updateProgressOnly() {
  try {
    // 获取所有正在进行的翻译任务
    const processingTasks = translatesData.value.filter(item => 
      item.status === 'process' || item.status === 'changing' || item.status === 'none' || item.status === 'queued'
    )
    
    if (processingTasks.length === 0) {
      return
    }
    
    console.log(`🔄 更新 ${processingTasks.length} 个任务的进度...`)
    
    // 并行查询所有任务的进度
    const progressPromises = processingTasks.map(task => 
      getTranslateProgress({ uuid: task.uuid })
        .then(res => ({ task, res }))
        .catch(err => ({ task, error: err }))
    )
    
    const results = await Promise.allSettled(progressPromises)
    
    // 需要从列表中移除的任务UUID（任务不存在或已删除）
    const tasksToRemove = []
    
    // 更新本地数据中的进度信息
    results.forEach(result => {
      if (result.status === 'fulfilled') {
        const { task, res, error } = result.value
        
        // 处理错误情况（任务不存在、已删除等）
        if (error) {
          // 检查是否是404错误（任务不存在）
          const is404 = error.response?.status === 404 || 
                       error.response?.data?.code === 404 ||
                       (res && res.code === 404)
          
          if (is404) {
            // 任务不存在（可能已被删除），标记为需要移除
            tasksToRemove.push(task.uuid)
            console.log(`⚠️ 任务 ${task.uuid} 不存在（可能已删除），将从列表中移除`)
            return
          } else {
            // 其他错误，记录但不移除（可能是网络问题）
            console.warn(`⚠️ 任务 ${task.uuid} 进度查询失败:`, error)
            return
          }
        }
        
        // 处理成功情况
        if (res?.code === 200) {
          const progressData = res.data
          
          // 找到对应的任务并更新进度
          const taskIndex = translatesData.value.findIndex(item => item.uuid === task.uuid)
          if (taskIndex !== -1) {
            // 只更新进度相关字段，不触发整个列表刷新
            translatesData.value[taskIndex].process = progressData.process
            translatesData.value[taskIndex].status = progressData.status
            translatesData.value[taskIndex].status_name = progressData.status_name  // 添加状态名称更新
            translatesData.value[taskIndex].spend_time = progressData.spend_time
            
            // 如果任务完成，更新结束时间
            if (progressData.end_at) {
              translatesData.value[taskIndex].end_at = progressData.end_at
            }
            
            console.log(`✅ 任务 ${task.uuid} 进度更新: ${progressData.process}%, 状态: ${progressData.status_name}`)
          }
        } else if (res?.code === 404) {
          // 后端返回404（任务不存在）
          tasksToRemove.push(task.uuid)
          console.log(`⚠️ 任务 ${task.uuid} 不存在（后端返回404），将从列表中移除`)
        }
      } else {
        // Promise rejected 的情况
        console.warn(`⚠️ 任务进度查询Promise被拒绝:`, result.reason)
      }
    })
    
    // 从列表中移除不存在的任务
    if (tasksToRemove.length > 0) {
      const beforeLength = translatesData.value.length
      translatesData.value = translatesData.value.filter(item => !tasksToRemove.includes(item.uuid))
      const removedCount = beforeLength - translatesData.value.length
      console.log(`🗑️ 已从列表中移除 ${removedCount} 个不存在的任务`)
      
      // 如果列表为空，更新状态
      if (translatesData.value.length === 0) {
        no_data.value = true
      }
      
      // 从 result.value 中也移除这些任务
      tasksToRemove.forEach(uuid => {
        delete result.value[uuid]
      })
    }
    
  } catch (error) {
    console.error('更新进度失败:', error)
  }
}

// 自动进度更新函数
function startAutoRefresh() {
  // 清除现有定时器
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
  }
  
  // 启动新的定时器
  autoRefreshInterval.value = setInterval(() => {
    // 只在页面可见且有翻译任务时刷新
    if (isPageVisible.value && translatesData.value.length > 0) {
      // 检查是否有正在进行的翻译任务
      const hasProcessingTasks = translatesData.value.some(item => 
        item.status === 'process' || item.status === 'changing' || item.status === 'none'
      )
      
      if (hasProcessingTasks) {
        console.log('🔄 自动更新翻译进度...')
        updateProgressOnly() // 使用专门的进度更新函数
      }
    }
  }, refreshInterval)
}

// 停止自动进度更新
function stopAutoRefresh() {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
    autoRefreshInterval.value = null
  }
}

// 页面可见性变化处理
function handleVisibilityChange() {
  isPageVisible.value = !document.hidden
  if (isPageVisible.value) {
    // 页面变为可见时，立即更新进度一次
    if (translatesData.value.length > 0) {
      updateProgressOnly()
    }
    // 重新启动自动刷新
    startAutoRefresh()
  } else {
    // 页面不可见时，停止自动刷新以节省资源
    stopAutoRefresh()
  }
}

//获取存储空间等信息的方法
function getStorageInfo() {
  storage().then((res) => {
    if (res.code == 200) {
      const storage = res.data.used_storage
      // 更新存储空间
      userStore.updateStorage(storage)
      // 修复存储空间计算：total_storage是字节，需要转换为MB
      storageTotal.value = (parseInt(res.data.total_storage) / (1024 * 1024)).toFixed(2)
      storageUsed.value = res.data.used_storage
      storagePercentage.value = parseFloat(res.data.percentage)
    }
  })
}

async function delTransFile(id, index) {
  try {
    await ElMessageBox.confirm('是否确定要删除？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    isLoadingData.value = true
    
    // 先找到要删除的任务的uuid，用于清理result.value
    const taskToDelete = translatesData.value.find(item => item.id === id)
    const taskUuid = taskToDelete?.uuid
    
    // 立即从列表中移除（优化用户体验）
    translatesData.value.splice(index, 1)
    if (translatesData.value.length < 1) {
      no_data.value = true
    }
    
    // 从 result.value 中移除（如果存在）
    if (taskUuid && result.value[taskUuid]) {
      delete result.value[taskUuid]
      console.log(`🗑️ 已从进度跟踪中移除任务: ${taskUuid}`)
    }

    const res = await delTranslate(id)
    if (res.code == 200) {
      // 再次确认从列表中移除（防止重复）
      translatesData.value = translatesData.value.filter((item) => item.id != id)
      if (translatesData.value.length < 1) {
        no_data.value = true
      }
      isLoadingData.value = false
      ElMessage.success('删除成功')
      getStorageInfo()
      
      // 检查是否还有正在进行的任务，如果没有则停止自动刷新
      const hasProcessingTasks = translatesData.value.some(item => 
        item.status === 'process' || item.status === 'changing' || item.status === 'none' || item.status === 'queued'
      )
      if (!hasProcessingTasks && autoRefreshInterval.value) {
        console.log('🛑 没有正在进行的任务，停止自动进度更新')
        stopAutoRefresh()
      }
    }
  } catch (error) {
    // 用户点击取消或请求失败
    console.log('删除操作已取消或失败:', error)
    isLoadingData.value = false
  }
}

//全部删除的方法
function delAllTransFile() {
  ElMessageBox.confirm('是否确定要删除全部？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    translatesData.value = []
    no_data.value = true

    delAllTranslate().then((data) => {
      if (data.code == 200) {
        translatesData.value = []
        no_data.value = true
        getStorageInfo()
      }
    })
  })
}

// 验证JWT token是否有效
function isTokenValid() {
  // 使用userStore中的token，而不是localStorage
  if (!userStore.token) {
    ElMessage.error('请先登录')
    return false
  }
  
  // 简单的token格式验证
  if (userStore.token.split('.').length !== 3) {
    ElMessage.error('登录状态异常，请重新登录')
    userStore.logout() // 使用store的logout方法
    return false
  }
  
  return true
}

//下载全部文件
async function downAllTransFile() {
  try {
    // 验证token是否有效
    if (!isTokenValid()) {
      return
    }
    
    // 设置按钮为加载状态
    downloadAllButtonState.value.isLoading = true
    downloadAllButtonState.value.disabled = true
    
    // 使用更兼容的下载方式，避免HTTP环境下blob URL限制
    // 方法1：直接使用window.open（浏览器原生下载，兼容HTTP）
    const downloadUrl = API_URL + '/translate/download/all'
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = `translations_${new Date().toISOString().slice(0, 10)}.zip`
    
    // 添加Authorization header通过URL参数或使用fetch后转为data URL
    // 但更好的方式是后端支持Cookie认证，这里先用fetch获取后再下载
    try {
      const response = await fetch(downloadUrl, {
        headers: {
          'Authorization': 'Bearer ' + userStore.token
        }
      })
      
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status} ${response.statusText}`)
      }
      
      // 获取blob
      const blob = await response.blob()
      
      // 尝试多种下载方式以提高兼容性
      // 方式1：使用blob URL（优先）
      try {
        const blobUrl = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.style.display = 'none'
        a.href = blobUrl
        a.download = `translations_${new Date().toISOString().slice(0, 10)}.zip`
        document.body.appendChild(a)
        a.click()
        
        // 延迟清理，确保下载开始
        setTimeout(() => {
          document.body.removeChild(a)
          window.URL.revokeObjectURL(blobUrl)
        }, 100)
        
        ElMessage({
          message: '批量下载成功！文件已保存到浏览器默认下载目录',
          type: 'success',
          duration: 5000
        })
      } catch (blobError) {
        // 方式2：blob URL失败时，尝试使用data URL（适用于小文件）
        console.warn('blob URL下载失败，尝试data URL方式:', blobError)
        if (blob.size < 50 * 1024 * 1024) { // 小于50MB才用data URL
          const reader = new FileReader()
          reader.onload = function(e) {
            const dataUrl = e.target.result
            const a = document.createElement('a')
            a.style.display = 'none'
            a.href = dataUrl
            a.download = `translations_${new Date().toISOString().slice(0, 10)}.zip`
            document.body.appendChild(a)
            a.click()
            setTimeout(() => {
              document.body.removeChild(a)
            }, 100)
            ElMessage({
              message: '批量下载成功！文件已保存到浏览器默认下载目录',
              type: 'success',
              duration: 5000
            })
          }
          reader.onerror = () => {
            throw new Error('文件读取失败')
          }
          reader.readAsDataURL(blob)
        } else {
          throw new Error('文件过大，无法使用备用下载方式。请配置HTTPS或使用单个文件下载。')
        }
      }
    } catch (error) {
      console.error('下载失败:', error)
      // 如果是HTTP环境下的blob限制，给出友好提示
      if (error.message && error.message.includes('blob')) {
        ElMessage.error('当前环境不支持批量下载，请使用HTTPS或逐个下载文件')
      } else {
        ElMessage.error(`文件下载失败: ${error.message || '未知错误'}，请稍后重试`)
      }
      throw error
    }
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('文件下载失败，请稍后重试')
  } finally {
    // 恢复按钮状态
    downloadAllButtonState.value.isLoading = false
    downloadAllButtonState.value.disabled = false
  }
}


onMounted(async () => {
  if (userStore.token) {
    getTranslatesData(1)
    
    // 从数据库加载用户翻译配置到Store（作为缓存）
    try {
      const { getCustomerSetting } = await import('@/api/trans')
      const settingRes = await getCustomerSetting()
      if (settingRes.code === 200 && settingRes.data) {
        const userSetting = settingRes.data
        // 同步到Store（作为缓存）
        translateStore.updateAIServerSettings({
          lang: userSetting.lang || 'English',
          comparison_id: userSetting.comparison_id && userSetting.comparison_id.length > 0 
            ? userSetting.comparison_id.map(id => parseInt(id)) 
            : [],
          prompt_id: userSetting.prompt_id || null,
        })
        translateStore.updateCommonSettings({
          pdf_translate_method: userSetting.pdf_translate_method || 'direct',
        })
      }
    } catch (error) {
      console.error('加载用户翻译配置失败:', error)
    }
    
    form.value = { ...form.value, ...translateStore.getCurrentServiceForm }
    
    // 检查提示词的有效性
    if (form.value.prompt_id) {
      try {
        const { prompt_my } = await import('@/api/corpus')
        const res = await prompt_my()
        if (res.code === 200) {
          const promptExists = res.data.data.some(prompt => prompt.id === form.value.prompt_id)
          if (!promptExists) {
            console.log(`提示词ID ${form.value.prompt_id} 不存在于当前用户的提示词列表中，自动置空`)
            form.value.prompt_id = ''
            // 同时更新store中的数据
            translateStore.updateAIServerSettings({ prompt_id: null })
          }
        }
      } catch (error) {
        console.error('检查提示词有效性失败:', error)
      }
    }
    
    // 添加调试信息
    console.log('页面初始化 - 翻译设置:', translateStore.aiServer)
    console.log('页面初始化 - 术语库:', translateStore.aiServer.comparison_id)
    console.log('页面初始化 - 目标语言:', translateStore.aiServer.lang)
    console.log('页面初始化 - 表单数据:', form.value)
    
    // 启动自动进度更新
    startAutoRefresh()
    
    // 监听页面可见性变化
    document.addEventListener('visibilitychange', handleVisibilityChange)
  }
})

onUnmounted(() => {
  // 清理定时器
  stopAutoRefresh()
  
  // 移除事件监听器
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>
<style scoped lang="scss">
.page-center {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 90px;
}
// 滚动条样式
.page-center::-webkit-scrollbar {
  width: 0px;
}
.page-center::-webkit-scrollbar-thumb {
  border-radius: 10px;
  -webkit-box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.2);
  opacity: 0.2;
  background: fade(#d8d8d8, 60%);
}
.page-center::-webkit-scrollbar-track {
  -webkit-box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.2);
  border-radius: 0;
  background: fade(#d8d8d8, 30%);
}
.container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 20px;
}
.upload-container {
  background: #ffffff;
  box-shadow: 0px 12px 20px 0px rgba(228, 238, 253, 0.5);
  border-radius: 12px;
  width: 100%;
  padding: 28px 28px;
  box-sizing: border-box;
  margin-top: 20px;
}
::v-deep {
  .dropzone {
    position: relative;
    .el-upload-dragger {
      border: 2px dashed #ccdaff;
      border-radius: 12px;
      padding-left: 0;
      padding-right: 0;
      &:hover {
        border-color: #3f66ff;
        background: #f8f9fe;
      }
    }
    .el-upload-list {
      position: absolute;
      width: 50%;
      left: 0;
      top: 50%;
      transform: translate(0, -50%);
      box-sizing: border-box;
      padding-left: 36px;
      padding-right: 36px;
      .el-upload-list__item:hover {
        background: #fff;
        .el-upload-list__item-file-name {
          color: var(--el-color-primary);
        }
      }
      .el-upload-list__item {
        display: inline-flex;
        align-items: center;
        margin-bottom: 20px;
        outline: none;
      }
      .el-upload-list__item-info {
        max-width: 90%;
        width: auto;
        .el-icon {
          display: none;
        }
      }
      .el-upload-list__item-status-label {
        position: relative;
        right: 0;
      }
      .el-icon--close {
        position: relative;
        top: 0;
        right: 0;
        transform: none;
      }
    }
    .left_box {
      width: 50%;
      float: left;
      height: 224px;
      border-right: 2px dashed #bcd4ff;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: center;
      img {
        margin: 0 15px;
      }
    }
    .right_box {
      width: 50%;
      float: right;
      height: 224px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      box-sizing: border-box;
      padding: 0 20px;
      .title {
        font-family: PingFang SC;
        font-weight: bold;
        font-size: 18px;
        color: #111111;
        line-height: 24px;
      }
      .tips {
        font-family: PingFang SC;
        font-weight: 400;
        font-size: 14px;
        color: #666666;
        line-height: 18px;
      }
      .upload_btn {
        margin-top: 24px;
        margin-bottom: 18px;
        width: 180px;
        height: 40px;
        background: #f7faff;
        border-radius: 4px;
        border: 1px dashed #055cf9;
        display: flex;
        align-items: center;
        justify-content: center;
        outline: none;
        cursor: pointer;
        img {
          height: 18px;
        }
        span {
          font-family: PingFang SC;
          font-weight: bold;
          font-size: 16px;
          color: #045cf9;
          margin-left: 12px;
        }
      }
    }
  }

  .fixed_bottom {
    position: fixed;
    bottom: 0;
    width: 100%;
    background: #fff;
    height: 68px;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 99;
    
    .translate-btn {
      min-width: 120px;
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      
      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
      
      &.is-loading {
        .el-icon {
          margin-right: 8px;
        }
      }
    }
  }

  .list_box {
    width: 100%;
    margin-top: 20px;
    background: #fff;
    box-shadow: 0px 12px 20px 0px rgba(228, 238, 253, 0.5);
    border-radius: 12px;
    padding: 0 28px;
    box-sizing: border-box;
    padding-bottom: 30px;
    .title_box {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 40px;
      padding-top: 14px;
      .t {
        font-weight: bold;
        font-size: 16px;
        color: #000000;
        .t_left {
          display: flex;
          align-items: center;
          .tips {
            margin-left: 30px;
            font-size: 14px;
            color: #666666;
            font-weight: 400;
            display: flex;
            align-items: center;
            span,
            i {
              color: #045cf9;
            }
          }
        }
      }
      .t_right {
        display: flex;
        align-items: center;
        flex: 1;
        justify-content: flex-end;
        .storage {
          font-size: 14px;
          color: #333333;
          margin-right: 9px;
        }
        .all_down {
          border-color: #055cf9;
          span {
            color: #055cf9;
          }
        }
      }
    }
    /*任务列表*/
    .table_box {
      width: 100;
      .table_row {
        display: flex;
        min-height: 40px;
        border-bottom: 1px solid #e5e5e5;
        align-items: center;
        font-size: 14px;
        color: #333;
        padding: 5px 0;
        .table_li {
          box-sizing: border-box;
          padding: 0 6px;
          display: flex;
          align-items: center;
          img {
            margin-right: 12px;
            width: 16px;
            height: 20px;
            object-fit: contain;
            flex-shrink: 0;
          }
          .file_name {
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-overflow: ellipsis;
          }
          .p_show {
            display: none;
          }
        }
        .table_li:first-child {
          width: 420px;
        }
        .table_li:nth-child(2) {
          width: 370px;
        }
        .table_li:nth-child(3) {
          width: 90px;
          white-space: nowrap;
        }
        .table_li:nth-child(4) {
          width: 180px;
        }
        .table_li:nth-child(5) {
          width: 50px;
        }
      }
      .table_top {
        color: #999999;
      }
      .status {
        img {
          margin-left: 5px;
          margin-right: 7px;
        }
        span {
          white-space: nowrap;
          width: 68px;
        }
        .failed {
          color: #ff4940;
        }
        .done {
          color: #20b759;
        }
        .process {
          color: #ff9c00;
        }
        .changing {
          color: #ff9c00;  /* 转换中状态，使用橙色 */
        }
      }
      .icon_down::after {
        content: none;
      }
    }
  }
  .translate-btn {
    line-height: 36px;
    width: 180px;
    color: white;
    border: none;
    background: #055cf9;
    border-radius: 4px;
    cursor: pointer;
    &:hover {
      opacity: 0.7;
    }
  }
}
</style>
<style type="text/css" lang="scss">
.translated-process {
  max-width: 270px;
  width: 80%;
}
/*手机端处理*/
@media screen and (max-width: 767px) {
  .upload-container {
    padding: 20px !important;
  }
  .list_box {
    padding: 0 20px !important;
    .title_box {
      flex-direction: column !important;
      height: auto !important;
      align-items: flex-start !important;
      .t {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        width: 100%;
      }
      .t_right {
        width: 100%;
        .storage {
          white-space: nowrap;
        }
      }
    }
    .table_box {
      padding-top: 10px;
      .table_row:last-child {
        border: none;
      }
    }
    .phone_row {
      display: inline-block !important;
      width: 100%;
      overflow: hidden;
      padding-top: 10px !important;
      .table_li {
        margin-bottom: 10px;
        .p_show {
          display: block;
        }
      }
      .table_li:first-child {
        width: 100% !important;
      }
      .status {
        width: 100% !important;
      }
      .table_li:nth-child(3) {
        display: inline-block !important;
        width: auto !important;
        font-size: 12px !important;
        color: #969fa9;
        &.pc_show {
          display: none !important;
        }
      }
      .table_li:nth-child(4) {
        display: inline-block !important;
        width: auto !important;
        font-size: 12px !important;
        color: #969fa9;
        &.pc_show {
          display: none !important;
        }
      }
      .table_li:nth-child(5) {
        display: inline-block !important;
        width: auto !important;
        font-size: 12px !important;
        color: #969fa9;
        &.pc_show {
          display: none !important;
        }
      }
    }
  }
  .dropzone {
    .el-upload-dragger {
      padding: 0 !important;
    }
    .right_box {
      width: 100% !important;
      height: auto !important;
      .tips {
        margin-top: 10px;
        margin-bottom: 20px;
      }
    }
    .el-upload-list {
      position: relative !important;
      width: 100% !important;
      left: unset !important;
      transform: none !important;
      padding: 0 !important;
      margin: 0;
      .el-upload-list__item {
        margin-top: 18px !important;
        margin-bottom: 0 !important;
      }
    }
  }
  .t_left {
    display: inline-block !important;
    .tips {
      margin-top: 10px;
      margin-left: 0 !important;
      font-size: 12px !important;
    }
  }
  .no_data {
    padding-bottom: 20px !important;
  }

  /*调整间距、字体大小*/
  .upload_btn span {
    font-size: 14px !important;
  }
  .dropzone .right_box .title {
    font-size: 16px !important;
  }
  .translate-btn {
    width: 90% !important;
  }
}

.icon_handle {
  margin-right: 10px;
  cursor: pointer; /* 鼠标悬停时显示手型 */
  
  &.disabled {
    opacity: 0.5;
    cursor: not-allowed; /* 禁用时显示禁止图标 */
    pointer-events: none; /* 禁用点击事件 */
  }
}

/* 上传限制提示样式 */
.upload-limit-tip {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
  text-align: center;
  font-style: italic;
}
</style>
