<script setup>
import { onMounted, computed } from 'vue'
import { useUserStore } from '@/store/modules/user'
import AdminDashboard from './components/AdminDashboard.vue'
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

// 判断是否是管理员：检查角色或超级管理员
const isAdmin = computed(() => {
  // 如果有角色且包含admin，或者是超级管理员，则显示看板
  const hasAdminRole = userStore.roles && userStore.roles.includes('admin')
  const isSuperAdmin = userStore.isSuperAdmin
  // 临时：先让所有人都看到看板，方便测试
  // 正式使用时可以改为：return hasAdminRole || isSuperAdmin
  return true // 临时改为true，所有用户都显示看板
})

onMounted(() => {
  getSiteSettings()
  // 调试：打印当前角色信息
  console.log('当前用户角色:', userStore.roles)
  console.log('是否超级管理员:', userStore.isSuperAdmin)
  console.log('是否显示看板:', isAdmin.value)
})
</script>

<template>
  <div>
    <!-- 确保能看到新看板组件 -->
    <AdminDashboard />
  </div>
</template>
