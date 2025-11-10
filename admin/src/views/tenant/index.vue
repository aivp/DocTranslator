<script lang="ts" setup>
import { reactive, ref, watch } from "vue"
import { 
  getTenantListApi, 
  createTenantApi, 
  updateTenantApi, 
  deleteTenantApi 
} from "@/api/tenant"
import { type FormInstance, type FormRules, ElMessage, ElMessageBox } from "element-plus"
import { Search, Refresh, CirclePlus, Edit, Delete } from "@element-plus/icons-vue"
import { usePagination } from "@/hooks/usePagination"
import { cloneDeep } from "lodash-es"
import type { TenantData, CreateTenantRequestData } from "@/api/tenant/types/tenant"
import { computed } from "vue"

defineOptions({
  name: "TenantManagement"
})

const loading = ref<boolean>(false)
const { paginationData, handleCurrentChange, handleSizeChange } = usePagination()

//#region 增
const DEFAULT_FORM_DATA: CreateTenantRequestData & { id?: number } = {
  id: undefined,
  tenant_code: "",
  name: "",
  company_name: "",
  contact_person: "",
  status: "active",
  storage_quota: 10737418240, // 10GB
  max_users: 100
}

const dialogVisible = ref<boolean>(false)
const formRef = ref<FormInstance | null>(null)
const formData = ref<CreateTenantRequestData & { id?: number }>(cloneDeep(DEFAULT_FORM_DATA))
const formRules = computed<FormRules<CreateTenantRequestData>>(() => ({
  tenant_code: [{ required: true, trigger: "blur", message: "请输入租户代码" }],
  name: [{ required: true, trigger: "blur", message: "请输入租户名称" }],
  company_name: [{ required: true, trigger: "blur", message: "请输入公司名称" }]
}))

const handleCreateOrUpdate = () => {
  formRef.value?.validate((valid: boolean, fields?: any) => {
    if (!valid) return console.error("表单校验不通过", fields)
    loading.value = true
    
    const api = formData.value.id ? updateTenantApi(formData.value.id, formData.value) : createTenantApi(formData.value)
    
    api
      .then(() => {
        ElMessage.success("操作成功")
        dialogVisible.value = false
        getTenantData()
      })
      .catch(() => {
        // 错误信息已由全局拦截器统一处理，不需要在这里重复显示
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
  dialogVisible.value = true
}

const handleUpdate = (row: TenantData) => {
  formData.value = cloneDeep(row as any)
  dialogVisible.value = true
}

const storageQuotaGB = computed({
  get: () => Math.floor((formData.value.storage_quota || 0) / (1024 * 1024 * 1024)),
  set: (val: number) => {
    formData.value.storage_quota = val * 1024 * 1024 * 1024
  }
})
//#endregion

//#region 删
const handleDelete = (row: TenantData) => {
  ElMessageBox.confirm(`确定要删除租户"${row.name}"吗？`, "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning"
  })
    .then(() => {
      loading.value = true
      deleteTenantApi(row.id)
        .then(() => {
          ElMessage.success("删除成功")
          getTenantData()
        })
        .finally(() => {
          loading.value = false
        })
    })
    .catch(() => {})
}
//#endregion

//#region 查
const tenantData = ref<TenantData[]>([])
const searchFormRef = ref<FormInstance | null>(null)
const searchData = reactive({
  keyword: ""
})

const getTenantData = () => {
  loading.value = true
  getTenantListApi({
    page: paginationData.currentPage,
    limit: paginationData.pageSize,
    keyword: searchData.keyword || undefined
  })
    .then(({ data }) => {
      paginationData.total = data.total
      tenantData.value = data.data
    })
    .catch(() => {
      tenantData.value = []
    })
    .finally(() => {
      loading.value = false
    })
}

const handleSearch = () => {
  paginationData.currentPage === 1 ? getTenantData() : (paginationData.currentPage = 1)
}

const resetSearch = () => {
  searchData.keyword = ""
  handleSearch()
}
//#endregion

/** 监听分页参数的变化 */
watch([() => paginationData.currentPage, () => paginationData.pageSize], getTenantData, { immediate: true })
</script>

<template>
  <div class="app-container">
    <el-card v-loading="loading" shadow="never">
      <el-form ref="searchFormRef" :inline="true" :model="searchData">
        <el-form-item prop="keyword" label="" style="width: 320px; max-width: 100%">
          <el-input v-model="searchData.keyword" placeholder="输入查询" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="CirclePlus" @click="handleCreate">新增租户</el-button>
        </el-form-item>
      </el-form>

      <div class="table-wrapper">
        <el-table :data="tenantData">
          <el-table-column prop="id" label="租户ID" align="left" width="80" />
          <el-table-column prop="tenant_code" label="租户代码" align="left" />
          <el-table-column prop="name" label="租户名称" align="left" />
          <el-table-column prop="company_name" label="公司名称" align="left" />
          <el-table-column prop="contact_person" label="联系人" align="left" />
          <el-table-column prop="status" label="状态" align="left" width="100">
            <template #default="scope">
              <el-tag v-if="scope.row.status === 'active'" type="success" effect="plain">启用</el-tag>
              <el-tag v-else type="danger" effect="plain">禁用</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="storage_quota" label="存储配额" align="left">
            <template #default="{ row }"> {{ (row.storage_quota / (1024 * 1024 * 1024)).toFixed(2) }} GB </template>
          </el-table-column>
          <el-table-column label="已分配/剩余" align="left" width="180">
            <template #default="{ row }">
              <div>
                <span style="color: #409eff;">{{ (row.total_storage / (1024 * 1024 * 1024)).toFixed(2) }}GB</span>
                /
                <span style="color: #67c23a;">{{ ((row.storage_quota - row.total_storage) / (1024 * 1024 * 1024)).toFixed(2) }}GB</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="max_users" label="最大用户数" align="left" />
          <el-table-column fixed="right" label="操作" width="120" align="left">
            <template #default="scope">
              <el-button type="primary" text size="small" :icon="Edit" @click="handleUpdate(scope.row)">编辑</el-button>
              <el-button
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
          <div class="title">{{ formData.id === undefined ? "新增租户" : "编辑租户信息" }}</div>
          <el-icon @click="resetForm"><Close /></el-icon>
        </div>
      </template>
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="150px" label-position="left">
        <el-form-item prop="tenant_code" label="租户代码">
          <el-input v-model="formData.tenant_code" placeholder="请输入租户代码（唯一，用于区分租户）" />
        </el-form-item>
        <el-form-item prop="name" label="租户名称">
          <el-input v-model="formData.name" placeholder="请输入租户名称" />
        </el-form-item>
        <el-form-item prop="company_name" label="公司名称">
          <el-input v-model="formData.company_name" placeholder="请输入公司名称" />
        </el-form-item>
        <el-form-item prop="contact_person" label="联系人">
          <el-input v-model="formData.contact_person" placeholder="请输入联系人" />
        </el-form-item>
        <el-form-item prop="status" label="状态">
          <el-select v-model="formData.status" placeholder="请选择状态">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item prop="storage_quota" label="存储配额(GB)">
          <el-input-number
            style="width: 80%"
            :precision="0"
            v-model="storageQuotaGB"
            :step="1"
            :min="1"
            placeholder="请输入存储配额"
          />
          <span class="ml-2">GB</span>
        </el-form-item>
        <el-form-item prop="max_users" label="最大用户数">
          <el-input-number
            style="width: 80%"
            :precision="0"
            v-model="formData.max_users"
            :step="10"
            :min="1"
            placeholder="请输入最大用户数"
          />
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

