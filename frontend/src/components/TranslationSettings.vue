<template>
  <el-dialog
    v-model="formSetShow"
    title="翻译设置"
    width="600px"
    modal-class="setting_dialog"
    :close-on-click-modal="false"
    :style="{ minHeight: '400px' }"
    @close="formCancel">
    <!-- 当前服务显示 -->
    <div class="current-service-display">
      <el-tag type="info" size="large">
        <span class="current-service-label">当前翻译服务：</span>
        <span class="current-service-value">{{ getServiceName(settingsForm.currentService) }}</span>
      </el-tag>
    </div>

    <!-- 重要提醒 -->
    <div class="important-notice" v-if="!hasValidSettings">
      <el-alert
        title="重要提醒"
        type="warning"
        :closable="false"
        show-icon>
        <template #default>
          <p>请先选择目标语言，这是翻译的必要设置。术语库为可选设置，可根据需要选择。</p>
        </template>
      </el-alert>
    </div>

    <el-form ref="transformRef" :model="settingsForm" label-width="120px" class="translation-form">
      <el-form-item v-if="!isVIP" label="翻译服务" required width="100%" v-show="false">
        <el-select v-model="settingsForm.currentService" placeholder="请选择翻译服务">
          <el-option value="ai" label="AI翻译"></el-option>
          <el-option value="baidu" label="百度翻译"></el-option>
          <el-option value="google" label="谷歌翻译"></el-option>
        </el-select>
      </el-form-item>

      <!-- AI翻译设置 -->
      <template v-if="settingsForm.currentService === 'ai'">
        <!-- 目标语言 -->
        <el-form-item label="目标语言" required width="100%">
          <el-select v-model="settingsForm.aiServer.lang" placeholder="请选择目标语言" clearable>
            <el-option v-for="lang in languageOptions" :key="lang.value" :label="lang.label" :value="lang.value" />
          </el-select>
        </el-form-item>

        <!-- 术语库 -->
        <el-form-item label="术语库" width="100%">
          <el-select
            v-model="settingsForm.aiServer.comparison_id"
            placeholder="请选择术语（可选，可多选）"
            multiple
            clearable
            filterable
            @focus="comparison_id_focus">
            <el-option v-for="term in translateStore.terms" :key="term.id" :label="term.title" :value="term.id" />
          </el-select>
        </el-form-item>

        <!-- PDF翻译方法选择 -->
        <el-form-item label="PDF翻译方法" width="100%">
          <el-radio-group v-model="settingsForm.common.pdf_translate_method" @change="handlePdfMethodToggle">
            <el-radio label="direct">直接翻译（保留PDF格式）</el-radio>
            <el-radio label="doc2x">Doc2x转换后翻译</el-radio>
          </el-radio-group>
        </el-form-item>
      </template>
    </el-form>

          <template #footer>
        <div class="btn_box">
          <el-button type="primary" color="#055CF9" @click="formConfim(transformRef)" size="large">确认</el-button>
        </div>
      </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useTranslateStore } from '@/store/translate'
import { useSettingsStore } from '@/store/settings'
import { ElMessage } from 'element-plus'
import { prompt_my, comparison_my } from '@/api/corpus'
import { checkOpenAI, checkDocx } from '@/api/trans'
import { useUserStore } from '@/store/user'
const userStore = useUserStore()
const isVIP = computed(() => userStore.isVip)
const translateStore = useTranslateStore()
const settingsStore = useSettingsStore()
const formSetShow = ref(false)
const checking = ref(false)
const check_text = ref('')
const transformRef = ref(null)
const promptData = ref([])
const termsData = ref([])
//检查docx2
const docx2_title = ref('检查')
const docx2_loading = ref(false)
// 本地表单数据
const settingsForm = ref({
  currentService: translateStore.currentService,
  aiServer: { ...translateStore.aiServer },
  baidu: { ...translateStore.baidu },
  google: { ...translateStore.google },
  common: { ...translateStore.common },
})
// 定义语言映射
const languageMap1 = {
  chi_sim: '中文',
  // chi_tra: '中文（繁体）',
  eng: '英语',
  jpn: '日语',
  kor: '韩语',
  fra: '法语',
  spa: '西班牙语',
  rus: '俄语',
  ara: '阿拉伯语',
  deu: '德语',
}
const languageMap = {
  por: '葡萄牙语',
  chi_sim: '中文',
  eng: '英语',
  ara: '阿拉伯语',
  fra: '法语',
  deu: '德语',
  spa: '西班牙语',
  rus: '俄语',
  ita: '意大利语',
  tha: '泰语',
  vie: '越南语',
  ind: '印尼语/马来语',
  tgl: '菲律宾语（他加禄语）',
  mya: '缅甸语',
  khm: '柬埔寨语（高棉语）',
  lao: '老挝语',
  kh: '柬语',
}

// 创建语言选项数组
const languageOptions = computed(() => {
  return Object.values(languageMap).map((label) => ({
    value: label, // key 和 value 都使用中文名称
    label: label,
  }))
})
// 译文形式选项
const typeOptions = [
  {
    value: 'trans_text',
    label: '仅文字部分',
    children: [
      {
        value: 'trans_text_only',
        label: '仅译文',
        children: [
          { value: 'trans_text_only_new', label: '重排版面' },
          { value: 'trans_text_only_inherit', label: '继承原版面' },
        ],
      },
      {
        value: 'trans_text_both',
        label: '原文+译文',
        children: [
          { value: 'trans_text_both_new', label: '重排版面' },
          { value: 'trans_text_both_inherit', label: '继承原版面' },
        ],
      },
    ],
  },
  {
    value: 'trans_all',
    label: '全部内容',
    children: [
      {
        value: 'trans_all_only',
        label: '仅译文',
        children: [
          { value: 'trans_all_only_new', label: '重排版面' },
          { value: 'trans_all_only_inherit', label: '继承原版面' },
        ],
      },
      {
        value: 'trans_all_both',
        label: '原文+译文',
        children: [
          { value: 'trans_all_both_new', label: '重排版面' },
          { value: 'trans_all_both_inherit', label: '继承原版面' },
        ],
      },
    ],
  },
]
// 监听当前服务变化
watch(
  () => settingsForm.value.currentService,
  (newVal) => {
    translateStore.updateCurrentService(newVal)
  }
)

// 检查翻译设置是否完整
const hasValidSettings = computed(() => {
  if (settingsForm.value.currentService === 'ai') {
    return settingsForm.value.aiServer.lang && settingsForm.value.aiServer.lang.trim() !== ''
  }
  // 其他翻译服务已隐藏，默认返回true
  return true
})

// 服务名称映射
const getServiceName = (service) => {
  const names = {
    ai: 'AI翻译',
    baidu: '百度翻译',
    google: '谷歌翻译',
  }
  return names[service] || service
}

// 获取术语库
const comparison_id_focus = async () => {
  try {
    const res = await comparison_my()
    if (res.code === 200) {
      translateStore.terms = res.data.data
    }
  } catch (error) {
    console.error('获取术语库失败:', error)
  }
}

// 处理PDF翻译方法切换
const handlePdfMethodToggle = (value) => {
  // 当选择直接翻译时，自动禁用Doc2x
  if (value === 'direct') {
    settingsForm.value.common.doc2x_flag = 'N'
    settingsForm.value.common.doc2x_secret_key = ''
  }
  // 当选择Doc2x转换时，自动启用Doc2x
  else if (value === 'doc2x') {
    settingsForm.value.common.doc2x_flag = 'Y'
  }
}

// 获取提示语数据
const prompt_id_focus = async () => {
  try {
    const res = await prompt_my()
    if (res.code === 200) {
      // promptData.value.push(res.data.data)
      promptData.value = res.data.data
      // 添加默认提示词
      promptData.value.unshift({
        id: 0,
        title: '默认系统提示语',
        content: settingsStore.system_settings.prompt_template,
      })
    }
  } catch (error) {
    console.error('获取提示语数据失败:', error)
  }
}

const rules = {
  // 目标语言验证 - AI翻译必选
  'aiServer.lang': [
    { required: true, message: '请选择目标语言', trigger: 'blur' }
  ],
  // 其他翻译服务的验证规则（已隐藏，保留以防需要）
  to_lang: [
    {
      required: settingsForm.value.currentService !== 'ai',
      message: '请选择目标语言',
      trigger: 'blur',
    },
  ],
}

// 提示语选择变化
const prompt_id_change = (id) => {
  const selectedPrompt = promptData.value.find((item) => item.id === id)
  if (selectedPrompt) {
    settingsForm.value.aiServer.prompt = selectedPrompt.content
    settingsForm.value.aiServer.prompt_id = id
  }
}
//检查功能实现
function check1() {
  checking.value = true
  check_text.value = ''
  checkOpenAI(form.value)
    .then((data) => {
      checking.value = false
      if (data.code == 200) {
        check_text.value = 'success'
      } else {
        check_text.value = 'fail'
        ElMessage({
          message: data.message,
          type: 'error',
        })
      }
    })
    .catch((err) => {
      checking.value = false
      check_text.value = 'fail'
      ElMessage({
        message: '接口异常',
        type: 'error',
      })
    })
}
// doc2x检查
function docx2_check1() {
  docx2_loading.value = true
  let _prarms = {
    doc2x_secret_key: form.value.doc2x_secret_key,
  }
  checkDocx(_prarms)
    .then((data) => {
      docx2_loading.value = false
      if (data.code == 0) {
        docx2_title.value = '成功'
      } else if (data.code == 1) {
        docx2_title.value = '失败'
        ElMessage({
          message: 'key值无效',
          type: 'error',
        })
      } else {
        docx2_title.value = '失败'
        ElMessage({
          message: data.message,
          type: 'error',
        })
      }
    })
    .catch((err) => {
      docx2_loading.value = false
      docx2_title.value = '失败'
      ElMessage({
        message: '接口异常',
        type: 'error',
      })
    })
}
// 检查连接
const check = async () => {
  checking.value = true
  check_text.value = ''

  try {
    // 根据当前服务调用不同的检查API
    let res
    if (settingsForm.value.currentService === 'ai') {
      res = await checkOpenAI(settingsForm.value.aiServer)
    } else if (settingsForm.value.currentService === 'baidu') {
      alert('百度翻译暂不支持检查')
      return
      // res = await checkBaidu({...})
    } else if (settingsForm.value.currentService === 'google') {
      alert('谷歌翻译暂不支持检查')
      return
      // res = await checkGoogle({...})
    }

    check_text.value = res?.code === 200 ? 'success' : 'fail'
  } catch (error) {
    check_text.value = 'fail'
    ElMessage.error('检查失败: ' + error.message)
  } finally {
    checking.value = false
  }
}

// 重置设置
const formReset = () => {
  settingsForm.value = {
    currentService: 'ai',  // 默认AI翻译
    aiServer: { 
      ...translateStore.aiServer, 
      // 硬编码的默认值
      model: 'qwen-mt-plus',  // 主模型：通义千问
      backup_model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',  // 备用模型：Claude
      lang: translateStore.aiServer.lang || '英语',  // 只针对语言：使用store中的值，如果没有则默认为英语
      type: ['trans_text', 'trans_text_only', 'trans_text_only_inherit'],  // 默认译文形式：仅文字+仅译文+继承原版面
      threads: 30,  // 默认线程数：30
      comparison_id: [],  // 术语库多选，默认为空数组
    },
    baidu: { ...translateStore.baidu },
    google: { ...translateStore.google },
    common: { 
      ...translateStore.common,
      langs: translateStore.common.langs || ['', '英语'],  // 只针对langs：使用store中的值，如果没有则默认为['', '英语']
      pdf_translate_method: translateStore.common.pdf_translate_method || 'direct',  // PDF翻译方法，默认为直接翻译
    },
  }
  check_text.value = ''
}

// 保存弹窗翻译设置
const formConfim = (formEl) => {
  if (!formEl) return
  formEl.validate((valid) => {
    if (valid) {
      // 清理comparison_id数据，确保没有空值
      if (Array.isArray(settingsForm.value.aiServer.comparison_id)) {
        settingsForm.value.aiServer.comparison_id = settingsForm.value.aiServer.comparison_id.filter(
          id => id && id !== '' && id !== null && id !== undefined
        )
      }
      
      // 添加调试信息
      console.log('保存前的表单数据:', settingsForm.value)
      console.log('术语库选择:', settingsForm.value.aiServer.comparison_id)
      
      // 更新store中的数据
      translateStore.updateCurrentService(settingsForm.value.currentService)

      if (settingsForm.value.currentService === 'ai') {
        // 更新AI设置，包括所有硬编码的字段
        translateStore.updateAIServerSettings({
          ...settingsForm.value.aiServer,
          // 确保硬编码的默认值被保存
          model: settingsForm.value.aiServer.model || 'qwen-mt-plus',
          backup_model: settingsForm.value.aiServer.backup_model || 'us.anthropic.claude-sonnet-4-20250514-v1:0',
          lang: settingsForm.value.aiServer.lang || '英语',
          type: settingsForm.value.aiServer.type || ['trans_text', 'trans_text_only', 'trans_text_only_inherit'],
          threads: settingsForm.value.aiServer.threads || 30,
        })
        
        // 同时更新通用设置
        translateStore.updateCommonSettings({
          ...settingsForm.value.common,
          type: settingsForm.value.aiServer.type || ['trans_text', 'trans_text_only', 'trans_text_only_inherit'],
          threads: settingsForm.value.aiServer.threads || 30,
        })
        
        // 添加调试信息
        console.log('保存后的store数据:', translateStore.aiServer)
        console.log('保存后的术语库:', translateStore.aiServer.comparison_id)
      } else if (settingsForm.value.currentService === 'baidu') {
        translateStore.updateBaiduSettings(settingsForm.value.baidu)
      } else if (settingsForm.value.currentService === 'google') {
        translateStore.updateGoogleSettings(settingsForm.value.google)
      }
      
      translateStore.updateCommonSettings(settingsForm.value.common)
      ElMessage.success('设置保存成功')
      formSetShow.value = false
    }
  })
}

// 取消设置
const formCancel = () => {
  formSetShow.value = false
}
const open = () => {
  formSetShow.value = true
  // 初始化表单数据，使用硬编码的默认值
  settingsForm.value = {
    currentService: 'ai',  // 默认AI翻译
    aiServer: { 
      ...translateStore.aiServer, 
      // 硬编码的默认值，覆盖store中的值
      model: 'qwen-mt-plus',  // 主模型：通义千问
      backup_model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',  // 备用模型：Claude
      lang: translateStore.aiServer.lang || '英语',  // 只针对语言：使用store中的值，如果没有则默认为英语
      type: ['trans_text', 'trans_text_only', 'trans_text_only_inherit'],  // 默认译文形式：仅文字+仅译文+继承原版面
      threads: 30,  // 默认线程数：30
      comparison_id: (() => {
        // 清理数据，确保没有空值或无效值
        const storedValue = translateStore.aiServer.comparison_id
        if (Array.isArray(storedValue)) {
          // 过滤掉空值、null、undefined等无效值
          return storedValue.filter(id => id && id !== '' && id !== null && id !== undefined)
        }
        return []
      })(),  // 术语库多选，使用store中的值或默认为空数组
    },
    baidu: { ...translateStore.baidu },
    google: { ...translateStore.google },
    common: { 
      ...translateStore.common,
      langs: translateStore.common.langs || ['', '英语'],  // 只针对langs：使用store中的值，如果没有则默认为['', '英语']
      pdf_translate_method: translateStore.common.pdf_translate_method || 'direct',  // PDF翻译方法，默认为直接翻译
    },
  }
  
  // 添加调试信息
  console.log('打开设置时的数据:', settingsForm.value.aiServer)
}

function docx2_check() {
  docx2_loading.value = true
  let _prarms = {
    doc2x_secret_key: form.value.doc2x_secret_key,
  }
  checkDocx(_prarms)
    .then((data) => {
      docx2_loading.value = false
      if (data.code == 0) {
        docx2_title.value = '成功'
      } else if (data.code == 1) {
        docx2_title.value = '失败'
        ElMessage({
          message: 'key值无效',
          type: 'error',
        })
      } else {
        docx2_title.value = '失败'
        ElMessage({
          message: data.message,
          type: 'error',
        })
      }
    })
    .catch((err) => {
      docx2_loading.value = false
      docx2_title.value = '失败'
      ElMessage({
        message: '接口异常',
        type: 'error',
      })
    })
}
// 暴露方法
defineExpose({
  open,
})
</script>

<style scoped lang="scss">
/* 当前服务显示样式 */
.current-service-display {
  text-align: center;
  margin-bottom: 24px;
  
  .el-tag {
    padding: 12px 20px;
    font-size: 14px;
    border-radius: 8px;
  }
}

.current-service-label {
  font-size: 14px;
  color: #606266;
  margin-right: 8px;
}

.current-service-value {
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
}

/* 原有弹窗样式 */
.setting_dialog {
  .el-dialog {
    max-width: 600px;
    padding: 20px;

    &__title {
      color: #303133;
      font-size: 18px;
      font-weight: 600;
    }

    &__headerbtn {
      font-size: 20px;
      right: 10px;
      top: 10px;

      i {
        color: #111;
      }
    }

    &__body {
      padding: 20px 0;
      /* 确保所有内容可见 */
      overflow: visible !important;
    }
  }

  .el-form-item {
    margin-bottom: 24px;
    
    .el-form-item__label {
      justify-content: flex-start;
      color: #303133;
      font-weight: 500;
    }

    .el-input-number .el-input__inner {
      text-align: left;
    }
    
    .el-select {
      width: 100%;
    }
  }

  .btn_box {
    display: flex;
    justify-content: center;
    gap: 16px;
    padding: 20px 0;
    
    .el-button {
      min-width: 120px;
      border-radius: 8px;
      font-size: 14px;
      
      &.el-button--primary {
        font-weight: 500;
      }
    }
  }
}

/* 确保doc2x功能完全可见 */
h4:contains("Doc2x"),
.el-alert:has(description:contains("doc2x")),
.el-form-item:has(.el-radio-group) {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}

.important-notice {
  margin-bottom: 20px;
  
  .el-alert {
    border-radius: 8px;
    
    .el-alert__title {
      font-weight: 600;
      color: #e6a23c;
    }
    
    p {
      margin: 8px 0 0 0;
      color: #606266;
      line-height: 1.5;
    }
  }
}

.no_label {
  label {
    opacity: 0;
  }

  .flex_box {
    width: 100%;

    .el-input {
      flex: 1;
      margin-right: 10px;
    }
  }
}
</style>

<style lang="scss">
/* 全局样式 - 完全按照原项目写法 */
@media screen and (max-width: 767px) {
  .current-service-display {
    margin-bottom: 15px;
    padding: 6px 0;

    .current-service-label,
    .current-service-value {
      font-size: 13px;
    }
  }

  .setting_dialog {
    .el-dialog {
      padding: 20px !important;

      &__body {
        padding: 0 !important;
        max-height: 600px; /* 增加高度，确保doc2x功能可见 */
        overflow-y: auto;

        .el-form-item {
          display: block !important;
          margin-bottom: 10px;
        }
      }
    }

    .btn_box {
      text-align: right !important;
    }
  }

  .no_label {
    label {
      display: none;
    }
  }
}
.setting_dialog1 {
  .el-dialog {
    padding: 20px !important;
  }
  .el-dialog__body {
    padding: 0 !important;
    max-height: 600px; /* 增加高度，确保doc2x功能可见 */
    overflow-y: auto;
    .el-form-item {
      display: block !important;
      margin-bottom: 10px;
    }
  }
  .btn_box {
    text-align: right !important;
  }
}
</style>
