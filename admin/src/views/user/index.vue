<script lang="ts" setup>
import { reactive, ref, watch, computed } from "vue"
import { 
  getUserListApi, 
  createUserApi, 
  updateUserApi, 
  deleteUserApi,
  resetPasswordApi
} from "@/api/user"
import { getTenantListApi } from "@/api/tenant"
import { type FormInstance, type FormRules, ElMessage, ElMessageBox } from "element-plus"
import { Search, Refresh, CirclePlus, Edit, Delete } from "@element-plus/icons-vue"
import { usePagination } from "@/hooks/usePagination"
import { cloneDeep } from "lodash-es"
import { useUserStore } from "@/store/modules/user"
import type { GetUserData, CreateUserRequestData } from "@/api/user/types/user"
import type { TenantData } from "@/api/tenant/types/tenant"
import { formatDateTime } from "@/utils"

defineOptions({
  name: "UserManagement"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()

const userStore = useUserStore()
const isSuperAdmin = computed(() => userStore.isSuperAdmin)
const tenantId = computed(() => userStore.tenantId)

//#region 增
const DEFAULT_FORM_DATA: CreateUserRequestData & { id?: number } = {
  id: undefined,
  name: "",
  email: "",
  password: "",
  tenant_id: undefined
}

const dialogVisible = ref<boolean>(false)
const formRef = ref<FormInstance | null>(null)
const formData = ref<CreateUserRequestData & { id?: number }>(cloneDeep(DEFAULT_FORM_DATA))
const formRules = reactive({
  name: [{ required: true, trigger: "blur", message: "请输入管理员姓名" }],
  email: [{ required: true, trigger: "blur", message: "请输入邮箱" }],
  password: [{ required: true, trigger: "blur", message: "请输入密码" }],
  tenant_id: [{ required: false, message: "请选择租户", trigger: "change" }]
})

const tenantList = ref<TenantData[]>([])
const loadingTenants = ref<boolean>(false)

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

const handleCreateOrUpdate = () => {
  formRef.value?.validate((valid: boolean, fields?: any) => {
    if (!valid) return console.error("表单校验不通过", fields)
    
    // 如果不是超级管理员，自动使用当前租户ID
    if (!isSuperAdmin.value && tenantId.value) {
      formData.value.tenant_id = tenantId.value
    }
    
    loading.value = true
    
    const api = formData.value.id ? updateUserApi(formData.value.id, formData.value) : createUserApi(formData.value)
    
    api
      .then(() => {
        ElMessage.success("操作成功")
        dialogVisible.value = false
        getUserData()
      })
      .finally(() => {
        loading.value = false
      })
  })
}

const resetForm = () => {
  formRef.value?.clearValidate()
  formData.value = cloneDeep(DEFAULT_FORM_DATA)
  dialogVisible.value = false
}

const handleCreate = () => {
  formData.value = cloneDeep(DEFAULT_FORM_DATA)
  console.log('创建管理员 - isSuperAdmin:', isSuperAdmin.value)
  console.log('创建管理员 - tenantId:', tenantId.value)
  if (isSuperAdmin.value) {
    fetchTenantList()
  }
  dialogVisible.value = true
}

const handleUpdate = (row: GetUserData) => {
  formData.value = cloneDeep({
    ...row,
    password: "",
    tenant_id: undefined  // 编辑时不显示租户
  } as any)
  if (isSuperAdmin.value) {
    fetchTenantList()
  }
  dialogVisible.value = true
}
//#endregion

//#region 删
const handleDelete = (row: GetUserData) => {
  // 防止删除ID=1的超级管理员
  if (row.id === 1) {
    ElMessage.error("不能删除超级管理员")
    return
  }
  
  ElMessageBox.confirm(`确定要删除管理员"${row.name}"吗？`, "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning"
  })
    .then(() => {
      loading.value = true
      deleteUserApi(row.id)
        .then(() => {
          ElMessage.success("删除成功")
          getUserData()
        })
        .finally(() => {
          loading.value = false
        })
    })
    .catch(() => {})
}

const handleResetPassword = (row: GetUserData) => {
  // 防止重置ID=1的超级管理员
  if (row.id === 1) {
    ElMessage.error("不能重置超级管理员密码")
    return
  }
  
  ElMessageBox.confirm(`确定要重置管理员"${row.name}"的密码吗？新密码为：ad2025`, "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning"
  })
    .then(() => {
      loading.value = true
      resetPasswordApi(row.id)
        .then((res: any) => {
          ElMessage.success(`密码已重置为：${res.data.new_password}`)
          getUserData()
        })
        .finally(() => {
          loading.value = false
        })
    })
    .catch(() => {})
}
//#endregion

//#region 查
const userData = ref<GetUserData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  search: ""
})

const getUserData = () => {
  loading.value = true
  getUserListApi({
    page: paginationData.currentPage,
    limit: paginationData.pageSize,
    search: searchData.search || undefined
  })
    .then(({ data }) => {
      paginationData.total = data.total
      userData.value = data.data
    })
    .catch(() => {
      userData.value = []
    })
    .finally(() => {
      loading.value = false
    })
}

const handleSearch = () => {
  paginationData.currentPage === 1 ? getUserData() : (paginationData.currentPage = 1)
}

const resetSearch = () => {
  searchData.search = ""
  handleSearch()
}
//#endregion

/** 监听分页参数的变化 */
watch([() => paginationData.currentPage, () => paginationData.pageSize], getUserData, { immediate: true })
</script>

<template>
  <div class="app-container">
    <el-card v-loading="loading" shadow="never">
      <el-form ref="searchFormRef" :inline="true" :model="searchData">
        <el-form-item prop="search" label="" style="width: 320px; max-width: 100%">
          <el-input v-model="searchData.search" placeholder="输入查询" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="CirclePlus" @click="handleCreate">新增管理员</el-button>
        </el-form-item>
      </el-form>

      <div class="table-wrapper">
        <el-table :data="userData">
          <el-table-column prop="id" label="管理员ID" align="left" width="100" />
          <el-table-column prop="name" label="姓名" align="left" />
          <el-table-column prop="email" label="邮箱" align="left" />
          <el-table-column prop="tenant_name" label="所属租户" align="left" />
          <el-table-column prop="created_at" label="创建时间" align="left">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column fixed="right" label="操作" width="180" align="left">
            <template #default="scope">
              <el-button type="primary" text size="small" :icon="Edit" @click="handleUpdate(scope.row)">编辑</el-button>
              <el-button
                v-if="scope.row.role !== 'super_admin'"
                type="warning"
                text
                size="small"
                @click="handleResetPassword(scope.row)"
                >重置密码</el-button
              >
              <el-button
                v-if="scope.row.role !== 'super_admin'"
                type="danger"
                text
                size="small"
                :icon="Delete"
                @click="handleDelete(scope.row)"
                >删除</el-button
              >
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="pager-wrapper">
        <el-pagination
          background
          :layout="paginationData.layout"
          :page-sizes="paginationData.pageSizes"
          :total="paginationData.total"
          :page-size="paginationData.pageSize"
          :currentPage="paginationData.currentPage"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/修改 -->
    <el-dialog modal-class="custom_dialog" v-model="dialogVisible" :show-close="false">
      <template #header>
        <div class="dialog_head">
          <div class="title">{{ formData.id === undefined ? "新增管理员" : "编辑管理员信息" }}</div>
          <el-icon @click="resetForm"><Close /></el-icon>
        </div>
      </template>
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="150px" label-position="left">
        <!-- 超级管理员显示租户选择器 -->
        <el-form-item v-if="isSuperAdmin && !formData.id" prop="tenant_id" label="所属租户" :rules="[{ required: true, message: '请选择租户', trigger: 'change' }]">
          <el-select v-model="formData.tenant_id" placeholder="请选择租户" style="width: 100%" v-loading="loadingTenants">
            <el-option 
              v-for="tenant in tenantList" 
              :key="tenant.id" 
              :label="tenant.name" 
              :value="tenant.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item prop="name" label="姓名">
          <el-input v-model="formData.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item prop="email" label="邮箱">
          <el-input v-model="formData.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item v-if="!formData.id" prop="password" label="密码">
          <el-input type="password" v-model="formData.password" placeholder="请输入密码" />
        </el-form-item>
      </el-form>
      <div class="btn_box">
        <el-button @click="resetForm">取消</el-button>
        <el-button type="primary" @click="handleCreateOrUpdate" :loading="loading">确认</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.search-wrapper {
  margin-bottom: 20px;
  :deep(.el-card__body) {
    padding-bottom: 2px;
  }
}

.table-wrapper {
  margin-bottom: 20px;
}

.pager-wrapper {
  display: flex;
  justify-content: flex-end;
}

:deep(.custom_dialog) {
  .el-dialog {
    padding: 30px 50px;
    width: 90%;
    max-width: 600px;
    .el-form-item__label {
      justify-content: right;
    }
  }
  .btn_box {
    text-align: right;
  }
  .dialog_head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    .title {
      font-weight: bold;
      font-size: 16px;
      color: #333333;
    }
    .el-icon {
      font-size: 20px;
    }
  }
  @media screen and (max-width: 750px) {
    .el-dialog {
      padding: 20px;
    }
  }
}
</style>

