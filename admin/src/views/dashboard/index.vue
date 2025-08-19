<script setup>
import { onMounted } from 'vue'
import { useUserStore } from '@/store/modules/user'
import Admin from './components/Admin.vue'
import Editor from './components/Editor.vue'
import { ElMessage } from 'element-plus'
import { useSystemStore } from '@/store/modules/system'
import { getSiteSettingData } from '@/api/setting'
const systemStore = useSystemStore()
const userStore = useUserStore()
// 请求获取站点配置
const getSiteSettings = async () => {
  try {
    const res = await getSiteSettingData()
    if (res.code == 200 && res.data.update_time !== systemStore.site_settings.update_time) {
      systemStore.updateSiteSettings(res.data)
    }
  } catch (e) {
    console.log(e);
    
    ElMessage.error('系统加载失败~')
  }
}
const isAdmin = userStore.roles.includes('admin')
onMounted(() => {
  getSiteSettings()
})
</script>

<template>
  <component :is="isAdmin ? Admin : Editor" />
</template>
