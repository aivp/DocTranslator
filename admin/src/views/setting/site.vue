<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSiteSettingData, setSiteSettingData } from '@/api/setting'
import { useSystemStore } from '@/store/modules/system'
const systemStore = useSystemStore()
// 表单数据
const setting = ref({
  admin_site_title: '',
  site_logo: '',
  site_name: '',
  site_title: '',
  version: '',
  update_time: null,
})

const settingForm = ref(null)
const isSubmitting = ref(false)

// 标准表单验证规则（不含HTTPS校验）
const rules = {
  version: [{ required: true, message: '请选择版本', trigger: 'blur' }],
  site_title: [{ required: false, message: '请输入站点标题', trigger: 'blur' }],
}

// 获取本地存储站点配置
const getLocalSettings = () => {
  try {
    setting.value = systemStore.site_settings
  } catch (e) {
    ElMessage.error('配置加载失败')
  }
}

// 核心校验函数
const validateHttpsLogo = () => {
  if (!setting.value.site_logo) return true // 允许为空

  if (!setting.value.site_logo.startsWith('https://')) {
    ElMessage.error('LOGO必须使用HTTPS协议，请修改后重试')
    return false
  }

  // 可选：扩展校验图片格式
  const validExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
  const isValid = validExtensions.some((ext) => setting.value.site_logo.toLowerCase().endsWith(ext))

  if (!isValid) {
    ElMessage.error('仅支持JPG/PNG/WEBP/GIF格式的图片链接')
    return false
  }

  return true
}

// 提交表单
const onSubmit = async () => {
  try {
    // 先执行标准表单验证
    await settingForm.value?.validate()

    // 重点：保存前的HTTPS专项校验
    if (!validateHttpsLogo()) return

    isSubmitting.value = true
    setting.value.update_time = Date.now().toString() // 时间戳，判断是否需要更新
    const { code } = await setSiteSettingData(setting.value)

    if (code === 200) {
      // 本地存储更新
      systemStore.updateSiteSettings(setting.value)
      ElMessage.success('配置保存成功')
      setTimeout(() => location.reload(), 800) // 平滑刷新
    }
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    isSubmitting.value = false
  }
}

// 初始化
onMounted(()=>{
  setting.value = systemStore.site_settings
})
</script>

<template>
  <div class="app-container">
    <el-card shadow="never">
      <el-form ref="settingForm" :model="setting" :rules="rules" label-width="120px" label-position="top">
        <!-- Logo URL 输入 -->
        <el-form-item label="站点LOGO地址：" prop="site_logo">
          <el-input v-model="setting.site_logo" placeholder="必须输入HTTPS开头的图片URL" clearable />
          <div class="form-tip">
            <el-icon><Warning /></el-icon>
            <span>必须使用https链接（如：https://example.com/logo.png）</span>
          </div>
        </el-form-item>

        <el-form-item label="用户端站点标题：" prop="site_title">
          <el-input v-model="setting.site_title" placeholder="比如：DocTranslator 开源AI文档翻译" />
        </el-form-item>
        <el-form-item label="站点名称：" prop="site_name">
          <el-input v-model="setting.site_name" placeholder="比如：DocTranslator" />
        </el-form-item>
        <el-form-item label="管理端站点标题：" prop="admin_site_title">
          <el-input v-model="setting.admin_site_title" placeholder="比如：DocTranslator后台管理中心" />
        </el-form-item>
        <el-form-item label="系统版本：" prop="version">
          <el-select v-model="setting.version" placeholder="请选择版本">
            <el-option value="community" label="个人版" />
            <el-option value="business" label="企业版" />
          </el-select>
        </el-form-item>

        <!-- 操作按钮 -->
        <el-form-item>
          <el-button type="primary" @click="onSubmit" :loading="isSubmitting">保存站点设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.form-tip {
  font-size: 12px;
  color: var(--el-color-warning);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}
</style>
