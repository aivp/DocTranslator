import { defineStore } from "pinia"
import { ref } from 'vue'
export const useSystemStore = defineStore('system-store', () => {
  const site_settings = ref({})
  const updateSiteSettings = (data) => {
    site_settings.value = { ...site_settings.value, ...data }
  }
  return { site_settings, updateSiteSettings }
},
  {
    persist: true
  })


// import { useSystemStore } from '@/store/modules/system'
// import { getSiteSettingData } from '@/api/setting'
// const systemStore = useSystemStore()
const setting = ref({
  admin_site_title: '',
  site_logo: '',
  site_name: '',
  site_title: '',
  version: '',
  update_time:null // 更新时间-判断是否更新
})