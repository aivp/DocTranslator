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
            <div class="file-count-tip" 
                 v-if="form.files.length > 0"
                 :class="{
                   'warning': form.files.length >= 4,
                   'error': form.files.length >= 5
                 }">
              已选择 {{ form.files.length }}/5 个文件
            </div>
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
            <el-button class="pc_show all_down" @click="downAllTransFile" v-if="translatesData.length > 0">
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
            <div class="table_li pc_show">{{ res.lang }}</div>
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
              <el-progress class="translated-process" :percentage="item.process" color="#055CF9" />
              <img v-if="item.status == 'none'" src="@assets/waring.png" alt="未开始" />
              <img v-if="item.status == 'done'" src="@assets/success.png" alt="已完成" />
              <img v-if="item.status == 'process'" src="@assets/waring.png" alt="进行中" />
              <img v-if="item.status == 'failed'" src="@assets/waring.png" alt="失败" />
              <span :class="item.status">{{ item.status_name }}</span>
            </div>
            <div :class="item.status == 'done' ? 'table_li' : 'table_li pc_show'">
              <span class="phone_show">用时:</span>
              {{ item.spend_time ? item.spend_time : '--' }}
            </div>
            <div :class="item.status == 'done' ? 'table_li' : 'table_li pc_show'">
              <span class="phone_show">完成时间:</span>
              {{ item.end_at ? item.end_at : '--' }}
            </div>
            <div :class="item.status == 'done' ? 'table_li' : 'table_li pc_show'">
              <span class="phone_show">语言:</span>
              {{ item.lang ? item.lang : '--' }}
            </div>
            <!-- 操作 -->
            <div class="table_li">
              <!-- 翻译成功图标 -->
              <template v-if="item.status == 'done'">
                <el-link class="icon_down" :href="API_URL + '/api/translate/download/' + item.id" target="_blank">
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
  getFinishCount
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
const upload_url = API_URL + '/api/upload'

const translatesData = ref([])
const translatesTotal = ref(0)
const translatesLimit = ref(100)
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
  model: '',
  backup_model: '',
  langs: [],
  lang: '',
  to_lang: null,
  type: [],
  uuid: '',
  prompt:
    '你是一个文档翻译助手，请将以下文本、单词或短语直接翻译成{target_lang}，不返回原文本。如果文本中包含{target_lang}文本、特殊名词（比如邮箱、品牌名、单位名词如mm、px、℃等）、无法翻译等特殊情况，请直接返回原文而无需解释原因。遇到无法翻译的文本直接返回原内容。保留多余空格。',
  threads: 10,
  size: 0,
  scanned: false, // 添加 scanned 字段
  origin_lang: '', // 添加起始语言字段
  comparison_id: '', //术语id
  prompt_id: '', //提示语id,
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
          // 更新翻译任务列表
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

        if (res.data.progress == 100) {
          // 任务完成
          // translating[uuid] = false
          // translated.value = true
          // target_url.value = API_URL + res.data.url
          // target_count.value = res.data.count
          // target_time.value = res.data.time
          // result.value[uuid]['disabled'] = false
          // // 以下演示版存储
          // result.value[uuid]['status'] = 'done'
          // result.value[uuid]['spend_time'] = res.data.time
          // result.value[uuid]['end_at'] = res.data.end_time
          // result.value[uuid]['process'] = 100
          // result.value[uuid]['origin_filename'] = result.value[uuid]['file_name']
          // result.value[uuid]['target_filepath'] = res.data.url

          // 任务完成时，更新翻译任务列表
          ElMessage.success({
            message: '文件翻译成功！',
          })
          getTranslatesData(1)
          
          // 翻译完成后，从form.files中移除已完成的文件
          const completedFileIndex = form.value.files.findIndex(file => file.uuid === uuid)
          if (completedFileIndex !== -1) {
            form.value.files.splice(completedFileIndex, 1)
            console.log('已从文件列表中移除翻译完成的文件:', uuid)
          }
          
          // 翻译完成后，自动启动下一个待翻译的文件
          setTimeout(() => startNextTranslation(), 2000)
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
        // 任务失败时，更新翻译任务列表
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
      // 任务失败时，更新翻译任务列表
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
      model: nextTask.model || 'gpt-3.5-turbo',
      lang: nextTask.lang || '英语',
      uuid: nextTask.uuid,
      prompt: nextTask.prompt || '请将以下内容翻译为{target_lang}',
      threads: nextTask.threads || 10,
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
      doc2x_secret_key: nextTask.doc2x_secret_key || '',
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
      
      // 刷新翻译列表
      getTranslatesData(1)
      
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
      doc2x_secret_key: form.value.doc2x_secret_key
    }
    
    // 先获取当前翻译列表，过滤出需要翻译的文件
    const res = await translates({ page: 1, limit: 100 })
    if (res.code !== 200) {
      ElMessage.error('获取翻译列表失败，无法启动批量翻译')
      return
    }
    
    const translateList = res.data.data
    const filesToTranslate = []
    
    // 过滤出需要翻译的文件（状态为 'none' 且在当前上传列表中）
    for (const file of form.value.files) {
      const existingTask = translateList.find(task => task.uuid === file.uuid)
      if (existingTask && existingTask.status === 'none') {
        filesToTranslate.push({
          ...file,
          existingTask
        })
      } else if (existingTask) {
        console.log(`文件 ${file.file_name} 状态为 ${existingTask.status}，跳过翻译`)
      } else {
        console.log(`文件 ${file.file_name} 未找到对应任务，跳过翻译`)
      }
    }
    
    if (filesToTranslate.length === 0) {
      ElMessage.warning('没有需要翻译的文件，所有文件都已完成或正在处理中')
      return
    }
    
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
    
    // 刷新翻译列表
    getTranslatesData(1)
    
  } catch (error) {
    console.error('批量启动翻译任务时发生错误:', error)
    ElMessage.error({
      message: '批量启动翻译任务失败',
      duration: 3000
    })
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
      // 更新翻译任务列表
      getTranslatesData(1)
      
      // doc2x翻译失败时，从form.files中移除失败的文件
      const failedFileIndex = form.value.files.findIndex(file => file.uuid === data.uuid)
      if (failedFileIndex !== -1) {
        form.value.files.splice(failedFileIndex, 1)
        console.log('已从文件列表中移除doc2x翻译失败的文件:', data.uuid)
      }
      
      return // 直接返回，不再继续查询
    } else if (res.data.status == 'done') {
      // 任务完成时，更新翻译任务列表
      ElMessage.success({
        message: '文件翻译成功！',
      })
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
    // 任务失败时，更新翻译任务列表
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
  if (file_suffix == 'pdf' && translateStore.common.doc2x_flag == 'N') {
    return ElMessage({
      message: '使用pdf翻译请先配置doc2x密钥',
      type: 'error',
    })
  }
  if (
    file_suffix == 'pdf' &&
    translateStore.common.doc2x_flag == 'Y' &&
    translateStore.common.doc2x_secret_key !== ''
  ) {
    form.value.server = 'doc2x'
    form.value.doc2x_flag = translateStore.common.doc2x_flag
    form.value.doc2x_secret_key = translateStore.common.doc2x_secret_key
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

  if (currentServiceType.value == 'ai') {
    // 2.检查翻译设置是否完整
    if (form.value.server === '') {
      ElMessage({
        message: '请选择翻译服务提供商',
        type: 'error',
      })
      return
    }

    if (form.value.type === '') {
      ElMessage({
        message: '请选择翻译类型',
        type: 'error',
      })
      return
    }

    if (form.value.model === '') {
      ElMessage({
        message: '请选择翻译模型',
        type: 'error',
      })
      return
    }

    if (form.value.langs.length < 1) {
      ElMessage({
        message: '请选择目标语言',
        type: 'error',
      })
      return
    }

    if (form.value.prompt === '') {
      ElMessage({
        message: '请输入翻译提示词',
        type: 'error',
      })
      return
    }
    // 翻译服务 检查api密钥是否为空 会员不需要提供key
    if (form.value.api_key === '' && !userStore.isVip) {
      ElMessage({
        message: '请输入API密钥',
        type: 'error',
      })
      return
    }
  } else if (currentServiceType.value == 'baidu') {
    if (form.value.app_key === '' || form.value.app_id === '' || form.value.to_lang === '') {
      ElMessage({
        message: '请填写百度翻译相关信息!',
        type: 'error',
      })
      return
    }
  }

  // 3.提交翻译任务
  // 如果是会员，不需要提供api和key
  form.value.api_key = userStore.isVip ? '' : form.value.api_key
  form.value.api_url = userStore.isVip ? '' : form.value.api_url

  // 设置按钮为加载状态
  translateButtonState.value.isLoading = true
  translateButtonState.value.disabled = true

  try {
    // 检查是否有多个文件需要翻译
    if (form.value.files.length > 1) {
      // 批量启动翻译任务
      await startBatchTranslation()
    } else {
      // 单个文件翻译（保持原有逻辑）
      console.log('翻译表单：', form.value)
      const res = await transalteFile(form.value)
      if (res.code == 200) {
        ElMessage({
          message: '提交翻译任务成功！',
          type: 'success',
        })
        // 刷新翻译列表
        getTranslatesData(1)
        // 启动任务查询
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
    // 刷新翻译列表
    getTranslatesData(1)
    // 启动任务查询
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
        ElMessage({
          message: '文件删除失败，请稍后再试',
          type: 'error',
        })
      }
    })
    .catch((error) => {
      ElMessage({
        message: '文件删除失败，请稍后再试',
        type: 'error',
      })
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
        item.status === 'process' || item.status === 'none'
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
        item.status === 'process' || item.status === 'none'
      )
      
      if (hasProcessingTasks) {
        console.log('🔄 自动刷新翻译进度...')
        getTranslatesData(1)
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
    // 页面变为可见时，立即刷新一次
    if (translatesData.value.length > 0) {
      getTranslatesData(1)
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
      storageTotal.value = (res.data.total_storage / (1024 * 1024)).toFixed(2)
      storageUsed.value = res.data.used_storage
      storagePercentage.value = res.data.percentage
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
    
    // 直接使用fetch下载文件，不使用request工具
    const response = await fetch('/api/api/translate/download/all', {
      headers: {
        'Authorization': 'Bearer ' + userStore.token
      }
    })
    
    if (!response.ok) {
      throw new Error('下载失败')
    }
    
    // 获取文件流并创建下载
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    
    // 创建下载链接
    const a = document.createElement('a')
    a.href = url
    a.download = `translations_${new Date().toISOString().slice(0, 10)}.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('批量下载成功！')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('文件下载失败，请稍后重试')
  }
}

onMounted(() => {
  if (userStore.token) {
    getTranslatesData(1)
    form.value = { ...form.value, ...translateStore.getCurrentServiceForm }
    
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

/* 文件数量提示样式 */
.file-count-tip {
  font-size: 12px;
  color: #666;
  margin-top: 8px;
  text-align: center;
}

/* 当接近限制时显示警告色 */
.file-count-tip.warning {
  color: #e6a23c;
}

/* 当达到限制时显示错误色 */
.file-count-tip.error {
  color: #f56c6c;
}
</style>
