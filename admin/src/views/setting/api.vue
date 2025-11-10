<script lang="ts" setup>
import { ref, onMounted, computed } from 'vue'
import { type FormInstance, ElMessage } from 'element-plus'
import { useUserStore } from '@/store/modules/user'
import { getApiSettingData, setApiSettingData } from '@/api/setting'
import { getTenantListApi } from '@/api/tenant'
import type { TenantData } from '@/api/tenant/types/tenant'

defineOptions({
  // 命名当前组件
  name: '接口配置',
})

const userStore = useUserStore()
const isSuperAdmin = computed(() => userStore.isSuperAdmin)
const tenantId = computed(() => userStore.tenantId)

const loading = ref(false)
const tenants = ref<TenantData[]>([])
const selectedTenantId = ref<number | undefined>(undefined)
const setting = ref({
  dashscope_key: '',
  akool_client_id: '',
  akool_client_secret: '',
})

const rules = {
  // 所有字段都是可选的，不需要必填验证
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
    const targetTenantId = isSuperAdmin.value ? selectedTenantId.value : (tenantId.value ?? undefined)
    const data = await getApiSettingData(targetTenantId)
    
    if (data.data) {
      setting.value = {
        dashscope_key: data.data.dashscope_key || '',
        akool_client_id: data.data.akool_client_id || '',
        akool_client_secret: data.data.akool_client_secret || '',
      }
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

// 超级管理员切换租户
const handleTenantChange = async () => {
  await loadSetting()
}

// 已删除 changeModel 函数，不再需要

function onSubmit() {
  const data: any = {
    dashscope_key: setting.value.dashscope_key,
    akool_client_id: setting.value.akool_client_id,
    akool_client_secret: setting.value.akool_client_secret,
  }
  
  // 如果是超级管理员且选择了租户，传递tenant_id
  if (isSuperAdmin.value && selectedTenantId.value) {
    data.tenant_id = selectedTenantId.value
  }
  
  setApiSettingData(data)
    .then((response) => {
      if (response.code == 200) {
        ElMessage.success(response.message || '保存成功')
        // 保存成功后重新加载配置
        loadSetting()
      } else {
        ElMessage.error(response.message || '保存失败')
      }
    })
    .catch((e) => {
      ElMessage.error(e.message || '保存失败')
    })
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
      
      <el-form class="settingForm" :model="setting" label-position="top" :rules="rules">
        <el-form-item label="阿里云 DashScope API 密钥">
          <el-input 
            v-model="setting.dashscope_key" 
            type="password"
            show-password
            placeholder="请输入阿里云 DashScope API 密钥" 
          />
          <div style="font-size: 12px; color: #909399; margin-top: 5px;">
            用于文本翻译功能的 API 密钥
          </div>
        </el-form-item>
        
        <el-form-item label="Akool Client ID">
          <el-input 
            v-model="setting.akool_client_id" 
            placeholder="请输入 Akool Client ID" 
          />
          <div style="font-size: 12px; color: #909399; margin-top: 5px;">
            用于视频翻译功能的 Client ID
          </div>
        </el-form-item>
        
        <el-form-item label="Akool Client Secret">
          <el-input 
            v-model="setting.akool_client_secret" 
            type="password"
            show-password
            placeholder="请输入 Akool Client Secret" 
          />
          <div style="font-size: 12px; color: #909399; margin-top: 5px;">
            用于视频翻译功能的 Client Secret
          </div>
        </el-form-item>
        
        <el-form-item class="setting-btns">
          <el-button type="primary" @click="onSubmit">保存API设置</el-button>
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
</style>
