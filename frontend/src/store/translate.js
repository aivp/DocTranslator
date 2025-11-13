
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useSettingsStore } from './settings';
export const useTranslateStore = defineStore('translate-settings', () => {
  // 当前翻译服务
  const currentService = ref('ai') // ai/baidu/google
  const settingsStore = useSettingsStore();
  // console.log('settingsStore', settingsStore.system_settings);

  // AI翻译设置
  const aiServer = ref({
    api_url: settingsStore.system_settings.api_url || '',
    api_key: '',
    // 使用硬编码的默认值，优先级高于后端配置
    model: 'qwen-mt-plus',  // 硬编码：通义千问
    backup_model: 'us.anthropic.claude-sonnet-4-20250514-v1:0',  // 硬编码：Claude
    prompt: settingsStore.system_settings.prompt_template || '你是一个文档翻译助手，请将以下文本、单词或短语直接翻译成{target_lang}，不返回原文本。如果文本中包含{target_lang}文本、特殊名词（比如邮箱、品牌名、单位名词如mm、px、℃等）、无法翻译等特殊情况，请直接返回原文而无需解释原因。遇到无法翻译的文本直接返回原内容。保留多余空格。',
    prompt_id: null,
    threads: 30,  // 硬编码：30线程
    comparison_id: [], // 改为数组类型，支持多选术语库，默认为空数组
    lang: 'English', // 硬编码：默认目标语言为英语（使用英文名，直接传给API）
    doc2x_flag: 'N',  // 硬编码：不使用Doc2x
    doc2x_secret_key: 'sk-6jr7hx69652pzdd4o4poj3hp5mauana0'
  })

  // 百度翻译设置
  const baidu = ref({
    app_id: '',
    app_key: '',
    from_lang: 'auto',
    to_lang: 'zh',
    needIntervene: false // 是否使用术语库
  })

  // 谷歌翻译设置
  const google = ref({
    app_key: '',
    project_id: '',
    from_lang: 'auto',
    to_lang: 'zh'
  })
  // 其他设置
  const otherSettings = ref({
    langs: ['', 'English'],
    comparison_id: '',
    threads: 30,
    doc2x_flag: 'N', // 是否使用doc2x
    doc2x_secret_key: ''
  })
  // 通用设置
  const common = ref({
    langs: ['', 'English'],  // 硬编码：默认语言数组
    type: ['trans_text', 'trans_text_only', 'trans_text_only_inherit'],  // 硬编码：默认译文形式
    doc2x_flag: 'N',  // 硬编码：不使用Doc2x
    doc2x_secret_key: 'sk-6jr7hx69652pzdd4o4poj3hp5mauana0',
    pdf_translate_method: 'direct'  // PDF翻译方法：direct(直接翻译) 或 doc2x(转换后翻译)
  })

  // 模型和语言选项
  const models = ref(['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo'])
  const langOptions = ref([
    { value: 'auto', label: '自动检测' },
    { value: 'zh', label: '中文' },
    { value: 'en', label: '英语' },
    // 其他语言...
  ])

  const terms = ref([])

  // 更新当前服务
  const updateCurrentService = (service) => {
    currentService.value = service
  }

  // 更新AI设置
  const updateAIServerSettings = (settings) => {
    aiServer.value = { ...aiServer.value, ...settings }
  }

  // 更新百度翻译设置
  const updateBaiduSettings = (settings) => {
    baidu.value = { ...baidu.value, ...settings }
  }

  // 更新谷歌翻译设置
  const updateGoogleSettings = (settings) => {
    google.value = { ...google.value, ...settings }
  }

  // 更新通用设置
  const updateCommonSettings = (settings) => {
    common.value = { ...common.value, ...settings }
  }
  // 更新其他设置
  const updateOtherSettings = (settings) => {
    otherSettings.value = { ...otherSettings.value, ...settings }
  }
  // 更新AI翻译表单其中某一个字段
  const updateAISettingsField = (field, value) => {
    aiServer.value[field] = value
    // if (currentService.value === 'ai') {
    //   aiServer.value[field] = value
    // } else if (currentService.value === 'baidu') {
    //   baidu.value[field] = value
    // } else if (currentService.value === 'google') {
    //   google.value[field] = value
    // }
  }
  // 获取当前服务的全部表单数据
  const getCurrentServiceForm = computed(() => {
    switch (currentService.value) {
      case 'ai':
        return { ...aiServer.value, ...common.value, server: 'openai' };
      case 'baidu':
        return { ...baidu.value, ...common.value, server: 'baidu' };
      case 'google':
        return { ...google.value, ...common.value, server: 'google' };
      default:
        return {}; // 默认返回空对象
    }
  });
  // 保存所有设置
  const saveAllSettings = (settings) => {
    if (settings.currentService) {
      currentService.value = settings.currentService
    }
    if (settings.aiServer) updateAIServerSettings(settings.aiServer)
    if (settings.baidu) updateBaiduSettings(settings.baidu)
    if (settings.google) updateGoogleSettings(settings.google)
    if (settings.common) updateCommonSettings(settings.common)
    if (settings.otherSettings) updateOtherSettings(settings.otherSettings)
  }

  // 重置当前服务设置
  const resetCurrentService = () => {
    if (currentService.value === 'ai') {
      aiServer.value = {
        api_url: 'https://api.openai.com',
        api_key: '',
        model: 'gpt-3.5-turbo',
        backup_model: '',
        prompt: '你是一个文档翻译助手...',
        prompt_id: 0
      }
    } else if (currentService.value === 'baidu') {
      baidu.value = {
        app_id: '',
        app_key: '',
        from_lang: 'auto',
        to_lang: 'zh'
      }
    } else if (currentService.value === 'google') {
      google.value = {
        api_key: '',
        project_id: '',
        from_lang: 'auto',
        to_lang: 'zh'
      }
    }
  }

  return {
    currentService,
    aiServer,
    baidu,
    google,
    common,
    models,
    langOptions,
    terms,
    otherSettings,
    updateCurrentService,
    updateAIServerSettings,
    updateBaiduSettings,
    updateGoogleSettings,
    updateCommonSettings,
    updateOtherSettings,
    saveAllSettings,
    resetCurrentService,
    updateAISettingsField,
    getCurrentServiceForm
  }
}, {
  persist: true, // 启用持久化
});
