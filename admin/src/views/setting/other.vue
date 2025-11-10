<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { useUserStore } from '@/store/modules/user'
import { getOtherSettingData, setOtherSettingData } from '@/api/setting'
import { getTenantListApi } from '@/api/tenant'
import type { TenantData } from '@/api/tenant/types/tenant'

const userStore = useUserStore()
const isSuperAdmin = computed(() => userStore.isSuperAdmin)
const tenantId = computed(() => userStore.tenantId)

const loading = ref(false)
const tenants = ref<TenantData[]>([])
const selectedTenantId = ref<number | undefined>(undefined)

const setting = ref({
  email_limit: ""
})

const settingForm = ref<FormInstance | null>(null)

const rules = {
  // 不再需要验证规则，因为email_limit是可选的
}

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
    const res = await getOtherSettingData(targetTenantId ?? undefined)
    
    if (res.data) {
      setting.value = res.data
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

async function onSubmit() {
  try {
    const data: any = {
      ...setting.value
    }
    
    // 如果是超级管理员且选择了租户，传递tenant_id
    if (isSuperAdmin.value && selectedTenantId.value) {
      data.tenant_id = selectedTenantId.value
    }
    
    const res = await setOtherSettingData(data)
    
    if (res.code === 200) {
      ElMessage.success(res.message || '配置保存成功')
      await loadSetting()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
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
      
      <el-form class="settingForm" ref="settingForm" :model="setting" label-position="top">
        <el-form-item label="限定注册邮箱后缀" prop="email_limit">
          <el-input 
            v-model="setting.email_limit" 
            placeholder="请输入允许的邮箱域名，多个用逗号隔开，如: gmail.com,qq.com,163.com"
            clearable
          />
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            <span>匹配规则：邮箱域名必须与配置完全一致。例如：输入 "gmail.com" 只允许 @gmail.com 注册，不允许 @gmail.cc 注册。</span>
          </div>
        </el-form-item>
        <el-form-item class="setting-btns">
          <el-button style="width: 88px" type="primary" @click="onSubmit">保存其他设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.settingForm {
  :deep(.el-form-item__content) {
    max-width: 480px;
    justify-content: left;
  }
}

.form-tip {
  font-size: 12px;
  color: var(--el-color-info);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}
</style>
