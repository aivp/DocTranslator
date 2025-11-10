<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/modules/user'
import { getSiteSettingData, setSiteSettingData } from '@/api/setting'
import { getTenantListApi } from '@/api/tenant'
import type { TenantData } from '@/api/tenant/types/tenant'

const userStore = useUserStore()
const isSuperAdmin = computed(() => userStore.isSuperAdmin)
const tenantId = computed(() => userStore.tenantId)

const loading = ref(false)
const tenants = ref<TenantData[]>([])
const selectedTenantId = ref<number | undefined>(undefined)

// 表单数据
const setting = ref({
  admin_site_title: '',
  site_logo: '',
  site_name: '',
  site_title: '',
  version: '',
  update_time: null as string | null,
})

const settingForm = ref<any>(null)
const isSubmitting = ref(false)

// 标准表单验证规则（不含HTTPS校验）
const rules = {
  version: [{ required: true, message: '请选择版本', trigger: 'blur' }],
  site_title: [{ required: false, message: '请输入站点标题', trigger: 'blur' }],
}

// 移除旧的本地存储逻辑，现在从API加载

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
    
    const data: any = {
      ...setting.value,
      update_time: Date.now().toString() // 时间戳，判断是否需要更新
    }
    
    // 如果是超级管理员且选择了租户，传递tenant_id
    if (isSuperAdmin.value && selectedTenantId.value) {
      data.tenant_id = selectedTenantId.value
    }
    
    const { code, message } = await setSiteSettingData(data)

    if (code === 200) {
      ElMessage.success(message || '站点设置保存成功')
      // 保存成功后重新加载配置
      await loadSetting()
    }
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  } finally {
    isSubmitting.value = false
  }
}

// 初始化
onMounted(async () => {
  loading.value = true
  
  // 如果是超级管理员，加载租户列表
  if (isSuperAdmin.value) {
    try {
      const tenantData = await getTenantListApi({ page: 1, limit: 100 })
      if (tenantData.data && tenantData.data.data) {
        tenants.value = tenantData.data.data
      }
    } catch (error) {
      console.error('加载租户列表失败:', error)
    }
  }
  
  // 加载配置
  await loadSetting()
  loading.value = false
})

// 加载配置
const loadSetting = async () => {
  try {
    const targetTenantId = isSuperAdmin.value ? selectedTenantId.value : tenantId.value
    const res = await getSiteSettingData(targetTenantId ?? undefined)
    
    if (res.data) {
      // 兼容类型转换
      setting.value = {
        ...res.data,
        update_time: res.data.update_time ?? null
      } as any
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败')
  }
}

// 超级管理员切换租户
const handleTenantChange = async () => {
  await loadSetting()
}
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" v-loading="loading" :element-loading-text="'加载中...'">
      <!-- 超级管理员显示租户选择 -->
      <div v-if="isSuperAdmin" style="margin-bottom: 20px;">
        <el-alert
          type="info"
          title="全局配置"
          description="请选择租户来查看或编辑其配置。不选择租户则查看/编辑全局默认配置。"
          :closable="false"
          show-icon
        />
        <el-select 
          v-model="selectedTenantId" 
          placeholder="选择租户（不选择则为全局配置）"
          clearable
          @change="handleTenantChange"
          style="width: 300px; margin-top: 10px;"
        >
          <el-option
            label="全局配置"
            :value="undefined as any"
          />
          <el-option
            v-for="tenant in tenants"
            :key="tenant.id"
            :label="tenant.name"
            :value="tenant.id"
          />
        </el-select>
      </div>
      
      <!-- 租户管理员显示提示 -->
      <div v-else style="margin-bottom: 20px;">
        <el-alert
          type="warning"
          title="租户配置"
          description="此为租户级别配置，仅对本租户生效。如未配置，将使用全局配置。"
          :closable="false"
          show-icon
        />
      </div>
      
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
