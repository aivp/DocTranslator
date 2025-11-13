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
              <img v-if="res.file_type == 'pptx'" src="@assets/PPT.png" alt="" />
              <img v-else-if="res.file_type == 'docx'" src="@assets/DOC.png" alt="" />
              <img v-else-if="res.file_type == 'xlsx'" src="@assets/Excel.png" alt="" />
              <img v-else src="@assets/PDF.png" alt="" />
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
              <img v-if="item.file_type == 'pptx'" src="@assets/PPT.png" alt="" />
              <img v-else-if="item.file_type == 'docx'" src="@assets/DOC.png" alt="" />
              <img v-else-if="item.file_type == 'xlsx'" src="@assets/Excel.png" alt="" />
              <img v-else src="@assets/PDF.png" alt="" />
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
                <span class="icon_handle" @click="retryTranslate(item)">
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
        :disabled="upload_load || translateButtonState.disabled"
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

// 全部下载按钮状态管理
const downloadAllButtonState = ref({
  isLoading: false,
  disabled: false
})

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
}

// 进度查询 status: "done"
function process(uuid) {
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
          setTimeout(() => process(uuid), 5000)
        } else {
          // 如果未完成，继续调用 process 函数
          setTimeout(() => process(uuid), 10000)
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
      console.log('没有待翻译的文件，所有任务已完成或进行中')
      return
    }
    
    console.log('自动启动下一个翻译任务:', nextTask.origin_filename)
    
    // 准备翻译参数
    const translateParams = {
      server: nextTask.server || 'openai',
      model: nextTask.model || 'qwen-mt-plus',
      lang: nextTask.lang || '英语',
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
    
    // 启动翻译任务
    const translateRes = await transalteFile(translateParams)
    if (translateRes.code === 200) {
      console.log('自动启动翻译任务成功:', nextTask.origin_filename)
      ElMessage.success({
        message: `自动启动翻译任务: ${nextTask.origin_filename}`,
        duration: 3000
      })
      
      // 使用专门的进度更新函数，而不是刷新整个列表
      updateProgressOnly()
      
      // 启动进度查询
      process(nextTask.uuid)
    } else {
      console.log('自动启动翻译任务失败:', translateRes.message)
      ElMessage.warning({
        message: `自动启动翻译任务失败: ${nextTask.origin_filename}`,
        duration: 3000
      })
    }
    
  } catch (error) {
    console.error('自动启动下一个翻译任务时发生错误:', error)
  }
}

// 批量启动翻译任务
async function startBatchTranslation() {
  try {
    console.log('开始批量启动翻译任务，文件数量:', form.value.files.length)
    
    // 获取第一个文件的配置作为模板
    const firstFile = form.value.files[0]
    const templateConfig = {
      server: form.value.server,
      model: form.value.model,
      lang: form.value.lang,
      prompt: form.value.prompt,
      threads: form.value.threads,
      api_url: form.value.api_url,
      api_key: form.value.api_key,
      app_id: form.value.app_id,
      app_key: form.value.app_key,
      backup_model: form.value.backup_model,
      origin_lang: form.value.origin_lang,
      type: form.value.type,
      comparison_id: form.value.comparison_id,
      prompt_id: form.value.prompt_id,
      doc2x_flag: form.value.doc2x_flag,
      doc2x_secret_key: form.value.doc2x_secret_key,
      // 明确传递PDF翻译方式，避免后端回退默认值
      pdf_translate_method: translateStore.common?.pdf_translate_method || 'direct'
    }
    
    // 直接以上传返回的文件列表发起任务（通过uuid关联），不依赖列表匹配，避免“未找到对应任务”误判
    const filesToTranslate = [...form.value.files]
    
    console.log(`实际需要翻译的文件数量: ${filesToTranslate.length}/${form.value.files.length}`)
    
    let successCount = 0
    let failCount = 0
    let skipCount = form.value.files.length - filesToTranslate.length
    
    // 逐个启动翻译任务
    for (let i = 0; i < filesToTranslate.length; i++) {
      const file = filesToTranslate[i]
      
      try {
        // 准备翻译参数
        const translateParams = {
          ...templateConfig,
          uuid: file.uuid,
          file_name: file.file_name,
          size: file.size || 0
        }
        
        // 启动翻译任务
        const res = await transalteFile(translateParams)
        if (res.code === 200) {
          successCount++
          console.log(`文件 ${i + 1}/${filesToTranslate.length} 翻译任务启动成功:`, file.file_name)
          
          // 检查是否进入队列
          if (res.data.status === 'queued') {
            console.log(`文件 ${file.file_name} 已加入队列`)
          }
          
          // 启动进度查询
          process(file.uuid)
          
          // 如果不是最后一个文件，等待一下再启动下一个（避免API限流）
          if (i < filesToTranslate.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 1000))
          }
        } else {
          failCount++
          console.log(`文件 ${i + 1}/${filesToTranslate.length} 翻译任务启动失败:`, file.file_name, res.message)
        }
      } catch (error) {
        failCount++
        console.error(`文件 ${i + 1}/${filesToTranslate.length} 翻译任务启动异常:`, file.file_name, error)
      }
    }
    
    // 显示批量启动结果
    let message = `批量翻译任务启动完成！`
    if (successCount > 0) {
      message += `成功: ${successCount} 个`
    }
    if (failCount > 0) {
      message += `，失败: ${failCount} 个`
    }
    if (skipCount > 0) {
      message += `，跳过: ${skipCount} 个（已完成或进行中）`
    }
    
    if (successCount > 0) {
      ElMessage.success({
        message: message,
        duration: 5000
      })
    } else if (failCount > 0) {
      ElMessage.error({
        message: message,
        duration: 5000
      })
    } else {
      ElMessage.warning({
        message: message,
        duration: 5000
      })
    }
    
    // 刷新翻译列表，确保新任务显示在最前面
    await getTranslatesData(1)
    
    // 清空上传文件列表
    uploadRef.value.clearFiles()
    form.value.files = []  // 清空表单文件数组
    
  } catch (error) {
    console.error('批量启动翻译任务时发生错误:', error)
    ElMessage.error({
      message: '批量启动翻译任务失败',
      duration: 3000
    })
    
    // 即使失败也要清空文件列表
    uploadRef.value.clearFiles()
    form.value.files = []  // 清空表单文件数组
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
  // 首先再次赋值，防止没有更新
  form.value = { ...form.value, ...translateStore.getCurrentServiceForm }
  
  // 添加调试信息
  console.log('翻译设置中的术语库:', translateStore.aiServer.comparison_id)
  console.log('翻译设置中的目标语言:', translateStore.aiServer.lang)
  console.log('当前表单数据:', form.value)
  console.log('当前服务类型:', currentServiceType.value)
  
  // 确保语言字段正确设置
  if (currentServiceType.value === 'ai' && translateStore.aiServer.lang) {
    form.value.lang = translateStore.aiServer.lang
    // 如果langs数组为空，则使用lang设置
    if (!form.value.langs || form.value.langs.length === 0) {
      form.value.langs = [translateStore.aiServer.lang]
    }
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

  // 设置按钮为加载状态
  translateButtonState.value.isLoading = true
  translateButtonState.value.disabled = true

  try {
    // 先检查队列状态，如果系统繁忙则弹出确认对话框
    await checkQueueStatus()
    if (!queueStatus.value.can_start_new) {
      const confirmed = await showQueueConfirmDialog()
      if (!confirmed) {
        // 用户取消，恢复按钮状态并清空文件列表
        translateButtonState.value.isLoading = false
        translateButtonState.value.disabled = false
        uploadRef.value.clearFiles()
        form.value.files = []  // 清空表单文件数组
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
      // 明确传递PDF翻译方式，避免后端回退默认值
      form.value.pdf_translate_method = translateStore.common?.pdf_translate_method || 'direct'
      const res = await transalteFile(form.value)
      if (res.code == 200) {
        // 检查任务状态
        if (res.data.status === 'queued') {
          ElMessage({
            message: res.data.message || '任务已加入队列，等待系统资源释放后自动开始',
            type: 'warning',
            duration: 5000
          })
        } else {
          ElMessage({
            message: '提交翻译任务成功！',
            type: 'success',
          })
        }
        
        // 先刷新一次列表，让用户看到新创建的翻译任务
        await getTranslatesData(1)
        
        // 然后启动任务查询
        process(form.value.uuid)
      } else {
        ElMessage({
          message: '提交翻译任务失败~',
          type: 'error',
        })
      }
    }
  } finally {
    // 无论成功失败，都恢复按钮状态
    translateButtonState.value.isLoading = false
    translateButtonState.value.disabled = false
  }

  // 4.清空上传文件列表
  uploadRef.value.clearFiles()
  form.value.files = []  // 清空表单文件数组
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
  upload_load.value = true
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
  setTimeout(() => {
    upload_load.value = false
  }, 1000)
}

function uploadError(data) {
  ElMessage({
    message: `上传失败，${JSON.parse(data.message).message}`,
    type: 'error',
  })
}

function handleExceed(files, uploadFiles) {
  ElMessage.warning(`最多只能上传 5 个文件，当前已有 ${uploadFiles.length} 个文件，请删除一些文件后再上传！`)
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
    
    // 更新本地数据中的进度信息
    results.forEach(result => {
      if (result.status === 'fulfilled' && result.value.res?.code === 200) {
        const { task, res } = result.value
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
      }
    })
    
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
    translatesData.value.splice(index, 1)
    if (translatesData.value.length < 1) {
      no_data.value = true
    }

    const res = await delTranslate(id)
    if (res.code == 200) {
      translatesData.value = translatesData.value.filter((item) => item.id != id)
      if (translatesData.value.length < 1) {
        no_data.value = true
      }
      isLoadingData.value = false
      ElMessage.success('删除成功')
      getStorageInfo()
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
