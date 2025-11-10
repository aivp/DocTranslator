<template>
  <el-form :model="user" ref="userform" label-width="auto" :rules="rules">
    <el-form-item prop="email" label="邮箱">
      <el-input v-model="user.email" placeholder="请输入邮箱" autocomplete="new-password" />
    </el-form-item>
    <!-- 超级管理员显示租户选择器 -->
    <el-form-item v-if="isSuperAdmin" prop="tenant_id" label="所属租户">
      <el-select v-model="user.tenant_id" placeholder="请选择租户" style="width: 100%" v-loading="loadingTenants">
        <el-option 
          v-for="tenant in tenantList" 
          :key="tenant.id" 
          :label="tenant.name" 
          :value="tenant.id" 
        />
      </el-select>
    </el-form-item>
    <el-form-item prop="level" label="用户等级">
      <el-select v-model="user.level" placeholder="" disabled>
        <el-option label="会员用户" value="vip" />
        <!-- 隐藏普通用户选项 -->
      </el-select>
    </el-form-item>
    <el-form-item prop="password" label="密码">
      <el-input type="password" v-model="user.password" placeholder="请输入" autocomplete="new-password" />
    </el-form-item>
    <el-form-item label="" class="center">
      <el-button 
        type="primary" 
        size="large" 
        color="#055CF9" 
        @click="doRegister()" 
        :loading="loading"
        :disabled="loading"
        style="width: 100%"
      >
        {{ loading ? '提交中...' : '提交' }}
      </el-button>
    </el-form-item>
  </el-form>
</template>
<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue"
import { registerCustomer } from "@/api/customer/index"
import { getTenantListApi } from "@/api/tenant"
import { FormInstance, ElMessage } from "element-plus"
import { CreateOrUpdateCustomerRequestData } from "@/api/customer/types/customer"
import { cloneDeep } from "lodash-es"
import { useUserStore } from "@/store/modules/user"
import type { TenantData } from "@/api/tenant/types/tenant"

const emit = defineEmits(["success"])

const userStore = useUserStore()
const isSuperAdmin = computed(() => userStore.isSuperAdmin)
const tenantId = computed(() => userStore.tenantId)

const DEFAULT_FORM_DATA: CreateOrUpdateCustomerRequestData = {
  email: "",
  password: "",
  level: "vip",  // 默认创建为会员用户
  add_storage: 0,
  storage: 0,
  tenant_id: undefined
}

const user = ref<CreateOrUpdateCustomerRequestData>(cloneDeep(DEFAULT_FORM_DATA))

const userform = ref<FormInstance | null>(null)
const loading = ref<boolean>(false)
const loadingTenants = ref<boolean>(false)
const tenantList = ref<TenantData[]>([])

const rules = reactive({
  email: [{ required: true, message: "请填写邮箱地址", trigger: "blur" }],
  level: [{ required: true, message: "请填写用户等级" }],
  password: [{ required: true, message: "请填写密码", trigger: "blur" }],
  tenant_id: [{ required: isSuperAdmin.value, message: "请选择租户", trigger: "change" }]
})

// 获取租户列表
const fetchTenantList = async () => {
  if (!isSuperAdmin.value) return
  
  loadingTenants.value = true
  try {
    const res = await getTenantListApi({ page: 1, limit: 100 })
    if (res.code === 200) {
      tenantList.value = res.data.data
    }
  } catch (error) {
    console.error("获取租户列表失败:", error)
  } finally {
    loadingTenants.value = false
  }
}

onMounted(() => {
  if (isSuperAdmin.value) {
    fetchTenantList()
  }
})

const doRegister = () => {
  userform.value?.validate((valid: boolean, fields?: any) => {
    if (!valid) return console.error("表单校验不通过", fields)
    
    // 如果不是超级管理员，自动使用当前租户ID
    if (!isSuperAdmin.value && tenantId.value) {
      user.value.tenant_id = tenantId.value
    }
    
    loading.value = true
    registerCustomer(user.value)
      .then(() => {
        ElMessage.success("操作成功")
        emit("success")
        user.value = cloneDeep(DEFAULT_FORM_DATA)
      })
      .catch((error) => {
        console.error("注册失败:", error)
        // 错误信息已经由 service.ts 中的拦截器处理，这里不需要重复显示
      })
      .finally(() => {
        loading.value = false
      })
  })
}
</script>
<style scoped lang="scss">
:v-deep {
  .right .el-form-item__content {
    justify-content: end;
  }
  .center .el-form-item__content {
    justify-content: center;
  }
}
</style>
