import { ref, watch } from 'vue'

/** 项目标题 */
const systemStore = localStorage.getItem('system-store')
const parsedData = systemStore ? JSON.parse(systemStore) : null

const VITE_APP_TITLE = parsedData?.site_settings.admin_site_title || 'DocTranslator管理后台'

/** 动态标题 */
const dynamicTitle = ref<string>('')

/** 设置标题 */
const setTitle = (title?: string) => {
  dynamicTitle.value = title ? `${VITE_APP_TITLE} | ${title}` : VITE_APP_TITLE
}

/** 监听标题变化 */
watch(dynamicTitle, (value, oldValue) => {
  if (document && value !== oldValue) {
    document.title = value
  }
})

export function useTitle() {
  return { setTitle }
}
