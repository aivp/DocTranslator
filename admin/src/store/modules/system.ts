import { defineStore } from "pinia"
import { ref } from 'vue'

interface SiteSettings {
  site_logo?: string
  [key: string]: any
}

export const useSystemStore = defineStore('system-store', () => {
  const site_settings = ref<SiteSettings>({})
  
  const updateSiteSettings = (data: Partial<SiteSettings>) => {
    site_settings.value = { ...site_settings.value, ...data }
  }
  
  return { site_settings, updateSiteSettings }
}) 