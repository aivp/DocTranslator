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
    <div class="important-notice" v-if="!hasValidSettings && !settingsForm.aiServer.prompt_id">
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
        <!-- 提示词选择 -->
        <el-form-item label="提示词" width="100%">
          <el-select
            v-model="settingsForm.aiServer.prompt_id"
            placeholder="请选择提示词（可选）"
            clearable
            filterable
            @focus="prompt_id_focus"
            @change="prompt_id_change">
            <el-option v-for="prompt in promptData" :key="prompt.id" :label="prompt.title" :value="prompt.id" />
          </el-select>
        </el-form-item>

        <!-- 提示词警告 -->
        <div v-if="settingsForm.aiServer.prompt_id" class="prompt-warning">
          <el-alert
            title="重要提醒"
            type="warning"
            :closable="false"
            show-icon>
            <template #default>
              <p>选择提示词翻译时其他选项不生效，且提示词中必须包含目标语言！</p>
            </template>
          </el-alert>
        </div>

        <!-- 目标语言 -->
        <el-form-item label="目标语言" required width="100%">
          <el-select 
            v-model="settingsForm.aiServer.lang" 
            placeholder="请选择目标语言（可输入筛选）" 
            clearable
            filterable
            :filter-method="filterLanguage"
            :disabled="!!settingsForm.aiServer.prompt_id">
            <el-option v-for="lang in filteredLanguageOptions" :key="lang.value" :label="lang.label" :value="lang.value" />
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
            :disabled="!!settingsForm.aiServer.prompt_id"
            @focus="comparison_id_focus"
            @change="handleTerminologyChange">
            <el-option v-for="term in translateStore.terms" :key="term.id" :label="term.title" :value="term.id" />
          </el-select>
        </el-form-item>

        <!-- 术语库提示 -->
        <div v-if="hasSelectedTerminologies" class="terminology-warning">
          <el-alert
            title="性能提示"
            type="warning"
            :closable="false"
            show-icon>
            <template #default>
              <p>
                <strong>术语数量会较大程度影响翻译速度。</strong>
                <span v-if="selectedTerminologiesCount > 0">
                  当前已选择 {{ selectedTerminologiesCount }} 个术语库，共约 {{ totalTermsCount }} 条术语。
                </span>
                建议您定期<strong>精进术语表</strong>，只保留最常用和最相关的术语，以提高翻译效率。
              </p>
            </template>
          </el-alert>
        </div>

        <!-- PDF翻译方法选择 -->
        <el-form-item label="PDF翻译方法" width="100%">
          <el-radio-group v-model="settingsForm.common.pdf_translate_method" @change="handlePdfMethodToggle">
            <el-radio label="direct">直接翻译（保留PDF格式，速度较慢）</el-radio>
            <el-radio label="doc2x">Doc2x转换后翻译（转word格式翻译，速度较快）</el-radio>
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
import { checkOpenAI, checkDocx, getCustomerSetting, saveCustomerSetting } from '@/api/trans'
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
// qwen-mt-plus 官方支持的语言列表（使用英文名作为value，中文名作为label）
// 参考：https://help.aliyun.com/zh/model-studio/developer-reference/api-details-9
const qwenLanguageList = [
  { value: 'English', label: '英语', code: 'en' },
  { value: 'Chinese', label: '简体中文', code: 'zh' },
  { value: 'Traditional Chinese', label: '繁体中文', code: 'zh_tw' },
  { value: 'Russian', label: '俄语', code: 'ru' },
  { value: 'Japanese', label: '日语', code: 'ja' },
  { value: 'Korean', label: '韩语', code: 'ko' },
  { value: 'Spanish', label: '西班牙语', code: 'es' },
  { value: 'French', label: '法语', code: 'fr' },
  { value: 'Portuguese', label: '葡萄牙语', code: 'pt' },
  { value: 'German', label: '德语', code: 'de' },
  { value: 'Italian', label: '意大利语', code: 'it' },
  { value: 'Thai', label: '泰语', code: 'th' },
  { value: 'Vietnamese', label: '越南语', code: 'vi' },
  { value: 'Indonesian', label: '印度尼西亚语', code: 'id' },
  { value: 'Malay', label: '马来语', code: 'ms' },
  { value: 'Arabic', label: '阿拉伯语', code: 'ar' },
  { value: 'Hindi', label: '印地语', code: 'hi' },
  { value: 'Hebrew', label: '希伯来语', code: 'he' },
  { value: 'Burmese', label: '缅甸语', code: 'my' },
  { value: 'Tamil', label: '泰米尔语', code: 'ta' },
  { value: 'Urdu', label: '乌尔都语', code: 'ur' },
  { value: 'Bengali', label: '孟加拉语', code: 'bn' },
  { value: 'Polish', label: '波兰语', code: 'pl' },
  { value: 'Dutch', label: '荷兰语', code: 'nl' },
  { value: 'Romanian', label: '罗马尼亚语', code: 'ro' },
  { value: 'Turkish', label: '土耳其语', code: 'tr' },
  { value: 'Khmer', label: '高棉语', code: 'km' },
  { value: 'Lao', label: '老挝语', code: 'lo' },
  { value: 'Cantonese', label: '粤语', code: 'yue' },
  { value: 'Czech', label: '捷克语', code: 'cs' },
  { value: 'Greek', label: '希腊语', code: 'el' },
  { value: 'Swedish', label: '瑞典语', code: 'sv' },
  { value: 'Hungarian', label: '匈牙利语', code: 'hu' },
  { value: 'Danish', label: '丹麦语', code: 'da' },
  { value: 'Finnish', label: '芬兰语', code: 'fi' },
  { value: 'Ukrainian', label: '乌克兰语', code: 'uk' },
  { value: 'Bulgarian', label: '保加利亚语', code: 'bg' },
  { value: 'Serbian', label: '塞尔维亚语', code: 'sr' },
  { value: 'Telugu', label: '泰卢固语', code: 'te' },
  { value: 'Afrikaans', label: '南非荷兰语', code: 'af' },
  { value: 'Armenian', label: '亚美尼亚语', code: 'hy' },
  { value: 'Assamese', label: '阿萨姆语', code: 'as' },
  { value: 'Asturian', label: '阿斯图里亚斯语', code: 'ast' },
  { value: 'Basque', label: '巴斯克语', code: 'eu' },
  { value: 'Belarusian', label: '白俄罗斯语', code: 'be' },
  { value: 'Bosnian', label: '波斯尼亚语', code: 'bs' },
  { value: 'Catalan', label: '加泰罗尼亚语', code: 'ca' },
  { value: 'Cebuano', label: '宿务语', code: 'ceb' },
  { value: 'Croatian', label: '克罗地亚语', code: 'hr' },
  { value: 'Egyptian Arabic', label: '埃及阿拉伯语', code: 'arz' },
  { value: 'Estonian', label: '爱沙尼亚语', code: 'et' },
  { value: 'Galician', label: '加利西亚语', code: 'gl' },
  { value: 'Georgian', label: '格鲁吉亚语', code: 'ka' },
  { value: 'Gujarati', label: '古吉拉特语', code: 'gu' },
  { value: 'Icelandic', label: '冰岛语', code: 'is' },
  { value: 'Javanese', label: '爪哇语', code: 'jv' },
  { value: 'Kannada', label: '卡纳达语', code: 'kn' },
  { value: 'Kazakh', label: '哈萨克语', code: 'kk' },
  { value: 'Latvian', label: '拉脱维亚语', code: 'lv' },
  { value: 'Lithuanian', label: '立陶宛语', code: 'lt' },
  { value: 'Luxembourgish', label: '卢森堡语', code: 'lb' },
  { value: 'Macedonian', label: '马其顿语', code: 'mk' },
  { value: 'Maithili', label: '迈蒂利语', code: 'mai' },
  { value: 'Maltese', label: '马耳他语', code: 'mt' },
  { value: 'Marathi', label: '马拉地语', code: 'mr' },
  { value: 'Mesopotamian Arabic', label: '美索不达米亚阿拉伯语', code: 'acm' },
  { value: 'Moroccan Arabic', label: '摩洛哥阿拉伯语', code: 'ary' },
  { value: 'Najdi Arabic', label: '纳吉迪阿拉伯语', code: 'ars' },
  { value: 'Nepali', label: '尼泊尔语', code: 'ne' },
  { value: 'North Azerbaijani', label: '北阿塞拜疆语', code: 'az' },
  { value: 'North Levantine Arabic', label: '北黎凡特阿拉伯语', code: 'apc' },
  { value: 'Northern Uzbek', label: '北乌兹别克语', code: 'uz' },
  { value: 'Norwegian Bokmål', label: '挪威语（博克马尔）', code: 'nb' },
  { value: 'Norwegian Nynorsk', label: '挪威语（尼诺斯克）', code: 'nn' },
  { value: 'Occitan', label: '奥克语', code: 'oc' },
  { value: 'Odia', label: '奥里亚语', code: 'or' },
  { value: 'Pangasinan', label: '邦阿西楠语', code: 'pag' },
  { value: 'Sicilian', label: '西西里语', code: 'scn' },
  { value: 'Sindhi', label: '信德语', code: 'sd' },
  { value: 'Sinhala', label: '僧伽罗语', code: 'si' },
  { value: 'Slovak', label: '斯洛伐克语', code: 'sk' },
  { value: 'Slovenian', label: '斯洛文尼亚语', code: 'sl' },
  { value: 'South Levantine Arabic', label: '南黎凡特阿拉伯语', code: 'ajp' },
  { value: 'Swahili', label: '斯瓦希里语', code: 'sw' },
  { value: 'Tagalog', label: '他加禄语', code: 'tl' },
  { value: "Ta'izzi-Adeni Arabic", label: '塔伊兹-亚丁阿拉伯语', code: 'acq' },
  { value: 'Tosk Albanian', label: '托斯克阿尔巴尼亚语', code: 'sq' },
  { value: 'Tunisian Arabic', label: '突尼斯阿拉伯语', code: 'aeb' },
  { value: 'Venetian', label: '威尼斯语', code: 'vec' },
  { value: 'Waray', label: '瓦瑞语', code: 'war' },
  { value: 'Welsh', label: '威尔士语', code: 'cy' },
  { value: 'Western Persian', label: '西波斯语', code: 'fa' }
]

// 创建语言选项数组（使用英文名作为value，中文名作为label）
const languageOptions = computed(() => {
  return qwenLanguageList.map((lang) => ({
    value: lang.value, // 使用英文名（English Name）作为value，直接传给API
    label: lang.label, // 使用中文名作为显示标签
    code: lang.code // 保留代码，以备后用
  }))
})

// 语言筛选关键词
const languageFilterKeyword = ref('')

// 筛选后的语言选项
const filteredLanguageOptions = computed(() => {
  if (!languageFilterKeyword.value) {
    return languageOptions.value
  }
  const keyword = languageFilterKeyword.value.toLowerCase()
  return languageOptions.value.filter(lang => {
    // 支持按中文名、英文名、代码筛选
    return lang.label.toLowerCase().includes(keyword) || 
           lang.value.toLowerCase().includes(keyword) ||
           lang.code.toLowerCase().includes(keyword)
  })
})

// 语言筛选方法
const filterLanguage = (val) => {
  languageFilterKeyword.value = val
}
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
    // 如果选择了提示词，则不需要验证目标语言
    if (settingsForm.value.aiServer.prompt_id) {
      return true
    }
    // 如果没有选择提示词，则需要验证目标语言
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

// 计算已选择的术语库信息
const hasSelectedTerminologies = computed(() => {
  return Array.isArray(settingsForm.value.aiServer.comparison_id) && 
         settingsForm.value.aiServer.comparison_id.length > 0
})

const selectedTerminologiesCount = computed(() => {
  if (!hasSelectedTerminologies.value) return 0
  return settingsForm.value.aiServer.comparison_id.length
})

const totalTermsCount = computed(() => {
  if (!hasSelectedTerminologies.value) return 0
  const selectedIds = settingsForm.value.aiServer.comparison_id
  const total = translateStore.terms
    .filter(term => selectedIds.includes(term.id))
    .reduce((sum, term) => sum + (term.term_count || 0), 0)
  return total
})

// 处理术语库选择变化
const handleTerminologyChange = () => {
  // 可以在这里添加额外的逻辑，比如记录选择变化
  console.log('术语库选择已更新:', settingsForm.value.aiServer.comparison_id)
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

// 获取提示词数据
const prompt_id_focus = async () => {
  try {
    const res = await prompt_my()
    if (res.code === 200) {
      // promptData.value.push(res.data.data)
      promptData.value = res.data.data
    }
  } catch (error) {
    console.error('获取提示词数据失败:', error)
  }
}

const rules = {
  // 目标语言验证 - AI翻译必选（当没有选择提示词时）
  'aiServer.lang': [
    { 
      required: computed(() => settingsForm.value.currentService === 'ai' && !settingsForm.value.aiServer.prompt_id), 
      message: '请选择目标语言', 
      trigger: 'blur' 
    }
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

// 提示词选择变化
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
      lang: translateStore.aiServer.lang || 'English',  // 只针对语言：使用store中的值，如果没有则默认为English（英文名）
      type: ['trans_text', 'trans_text_only', 'trans_text_only_inherit'],  // 默认译文形式：仅文字+仅译文+继承原版面
      threads: 30,  // 默认线程数：30
      comparison_id: [],  // 术语库多选，默认为空数组
    },
    baidu: { ...translateStore.baidu },
    google: { ...translateStore.google },
    common: { 
      ...translateStore.common,
      langs: translateStore.common.langs || ['', 'English'],  // 只针对langs：使用store中的值，如果没有则默认为['', 'English']
      pdf_translate_method: translateStore.common.pdf_translate_method || 'direct',  // PDF翻译方法，默认为直接翻译
    },
  }
  check_text.value = ''
}

// 保存弹窗翻译设置
const formConfim = (formEl) => {
  if (!formEl) return
  formEl.validate(async (valid) => {
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
          lang: settingsForm.value.aiServer.lang || 'English',
          type: settingsForm.value.aiServer.type || ['trans_text', 'trans_text_only', 'trans_text_only_inherit'],
          threads: settingsForm.value.aiServer.threads || 30,
          // 确保prompt_id被正确保存
          prompt_id: settingsForm.value.aiServer.prompt_id || null,
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
      
      // 优先保存到后端数据库（数据源）
      try {
        const saveData = {
          lang: settingsForm.value.aiServer.lang,
          comparison_id: settingsForm.value.aiServer.comparison_id || [],
          prompt_id: settingsForm.value.aiServer.prompt_id || null,
          pdf_translate_method: settingsForm.value.common.pdf_translate_method || 'direct',
          origin_lang: ''  // 源语言可选，暂时不保存
        }
        
        const saveRes = await saveCustomerSetting(saveData)
        if (saveRes.code === 200) {
          console.log('配置已保存到数据库:', saveRes.data)
          
          // 数据库保存成功后，再更新Store（作为缓存）
          translateStore.updateCommonSettings(settingsForm.value.common)
          ElMessage.success('设置保存成功')
        } else {
          console.error('保存配置到数据库失败:', saveRes.message)
          // 即使数据库保存失败，也更新Store（降级处理）
          translateStore.updateCommonSettings(settingsForm.value.common)
          ElMessage.warning('设置已保存到本地，但保存到数据库失败，请刷新页面重试')
        }
      } catch (error) {
        console.error('保存配置到数据库失败:', error)
        // 即使数据库保存失败，也更新Store（降级处理）
        translateStore.updateCommonSettings(settingsForm.value.common)
        ElMessage.warning('设置已保存到本地，但保存到数据库失败，请刷新页面重试')
      }
      
      formSetShow.value = false
    }
  })
}

// 取消设置
const formCancel = () => {
  formSetShow.value = false
}
const open = async () => {
  formSetShow.value = true
  
  // 从后端获取用户配置（如果没有则自动创建）
  try {
    const settingRes = await getCustomerSetting()
    if (settingRes.code === 200 && settingRes.data) {
      const userSetting = settingRes.data
      console.log('从数据库获取的用户配置:', userSetting)
      
      // 使用数据库配置初始化表单
      settingsForm.value = {
        currentService: 'ai',  // 默认AI翻译
        aiServer: { 
          ...translateStore.aiServer,
          model: 'qwen-mt-plus',  // 固定模型
          backup_model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',  // 固定备用模型
          lang: userSetting.lang || translateStore.aiServer.lang || 'English',  // 从数据库读取
          threads: 30,  // 固定线程数
          comparison_id: userSetting.comparison_id && userSetting.comparison_id.length > 0 
            ? userSetting.comparison_id.map(id => parseInt(id)) 
            : [],  // 从数据库读取，转换为数字数组
          prompt_id: userSetting.prompt_id || null,  // 从数据库读取
        },
        baidu: { ...translateStore.baidu },
        google: { ...translateStore.google },
        common: { 
          ...translateStore.common,
          pdf_translate_method: userSetting.pdf_translate_method || 'direct',  // 从数据库读取
        },
      }
    } else {
      // 如果获取失败，使用默认值
      console.warn('获取用户配置失败，使用默认值')
      settingsForm.value = {
        currentService: 'ai',
        aiServer: { 
          ...translateStore.aiServer,
          model: 'qwen-mt-plus',
          backup_model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',
          lang: translateStore.aiServer.lang || 'English',
          threads: 30,
          comparison_id: [],
          prompt_id: null,
        },
        baidu: { ...translateStore.baidu },
        google: { ...translateStore.google },
        common: { 
          ...translateStore.common,
          pdf_translate_method: 'direct',
        },
      }
    }
  } catch (error) {
    console.error('获取用户配置失败:', error)
    // 使用默认值
    settingsForm.value = {
      currentService: 'ai',
      aiServer: { 
        ...translateStore.aiServer,
        model: 'qwen-mt-plus',
        backup_model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',
        lang: translateStore.aiServer.lang || 'English',
        threads: 30,
        comparison_id: [],
        prompt_id: null,
      },
      baidu: { ...translateStore.baidu },
      google: { ...translateStore.google },
      common: { 
        ...translateStore.common,
        pdf_translate_method: 'direct',
      },
    }
  }
  
  // 预加载提示词数据，确保下拉框显示标题而不是ID
  try {
    const res = await prompt_my()
    if (res.code === 200) {
      promptData.value = res.data.data
      
      // 检查当前选择的prompt_id是否存在于新的提示词列表中
      if (settingsForm.value.aiServer.prompt_id) {
        const promptExists = promptData.value.some(prompt => prompt.id === settingsForm.value.aiServer.prompt_id)
        if (!promptExists) {
          console.log(`提示词ID ${settingsForm.value.aiServer.prompt_id} 不存在于当前用户的提示词列表中，自动置空`)
          settingsForm.value.aiServer.prompt_id = null
        }
      }
    }
  } catch (error) {
    console.error('获取提示词数据失败:', error)
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

.prompt-warning {
  margin-bottom: 20px;
  
  .el-alert {
    border-radius: 8px;
    border-color: #f56c6c;
    
    .el-alert__title {
      font-weight: 600;
      color: #f56c6c;
    }
    
    p {
      margin: 8px 0 0 0;
      color: #f56c6c;
      line-height: 1.5;
      font-weight: 500;
    }
  }
}

.terminology-warning {
  margin-bottom: 20px;
  margin-top: -10px;
  
  .el-alert {
    border-radius: 8px;
    border-color: #e6a23c;
    
    .el-alert__title {
      font-weight: 600;
      color: #e6a23c;
    }
    
    p {
      margin: 8px 0 0 0;
      color: #606266;
      line-height: 1.6;
      
      strong {
        color: #e6a23c;
        font-weight: 600;
      }
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
