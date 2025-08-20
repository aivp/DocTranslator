<template>
  <el-dialog
    v-model="visible"
    title="术语编辑器"
    width="75%"
    :fullscreen="false"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    destroy-on-close
    class="term_dialog"
  >
    <template #header="{ close, titleId, titleClass }">
      <span class="title">术语编辑器</span>
      <el-switch v-model="localForm.share_flag" active-value="Y" inactive-value="N" />
      <div class="flag_tips">共享{{ localForm.share_flag == 'Y' ? '开启' : '关闭' }}</div>
    </template>
    <el-form
      ref="termformRef"
      :model="localForm"
      :rules="rules"
      label-position="top"
      hide-required-asterisk="true"
    >
      <el-row :gutter="20">
        <el-col :span="24">
          <el-form-item label="术语表标题" required prop="title" width="100%">
            <el-input
              v-model="localForm.title"
              type="text"
              placeholder="请输入术语表标题"
              maxlength="50"
            />
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="源语种" required prop="origin_lang" width="100%">
            <el-select
              v-model="localForm.origin_lang"
              placeholder="请选择"
              filterable
              allow-create
              clearable
            >
              <el-option
                v-for="lang in props.langs"
                :key="lang"
                :name="lang"
                :value="lang"
              ></el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="对照语种" required prop="target_lang" width="100%">
            <el-select
              v-model="localForm.target_lang"
              placeholder="请选择"
              filterable
              allow-create
              clearable
            >
              <el-option
                v-for="lang in props.langs"
                :key="lang"
                :name="lang"
                :value="lang"
              ></el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      
      <!-- 术语列表 -->
      <div class="terms_section">
        <div class="terms_header">
          <h3>术语列表</h3>
          <div class="search_box">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索术语..."
              clearable
              @input="handleSearch"
              style="width: 300px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button
              type="primary"
              @click="addTerm"
              style="margin-left: 12px"
            >
              新增术语
            </el-button>
          </div>
        </div>
        
        <div class="terms_table">
          <el-table
            :data="termsList"
            style="width: 100%"
            v-loading="termsLoading"
            border
            stripe
          >
            <el-table-column
              prop="original"
              :label="localForm.origin_lang || '源语种'"
              min-width="200"
              show-overflow-tooltip
            />
            <el-table-column
              prop="comparison_text"
              :label="localForm.target_lang || '对照语种'"
              min-width="200"
              show-overflow-tooltip
            />
            <el-table-column
              label="操作"
              width="120"
              fixed="right"
              align="center"
            >
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button
                    type="primary"
                    size="small"
                    @click="editTerm(row)"
                    text
                  >
                    编辑
                  </el-button>
                  <el-button
                    type="danger"
                    size="small"
                    @click="deleteTerm(row)"
                    text
                  >
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          
          <!-- 分页 -->
          <div class="pagination_box" v-if="total > 0">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50]"
              :total="total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
      </div>
    </el-form>
    <template #footer>
      <div class="btn_box">
        <el-button
          type="primary"
          color="#055CF9"
          :disabled="props.loading"
          :loading="props.loading"
          @click="confirm"
        >
          保存
        </el-button>
        <el-button @click="close">关闭</el-button>
      </div>
    </template>
  </el-dialog>
  
  <!-- 编辑/新增术语弹窗 -->
  <el-dialog
    v-model="editTermVisible"
    :title="editTermForm.id ? '编辑术语' : '新增术语'"
    width="600px"
    destroy-on-close
  >
    <el-form
      ref="editTermFormRef"
      :model="editTermForm"
      :rules="editTermRules"
      label-width="80px"
    >
      <el-form-item label="原文" prop="original">
        <el-input
          v-model="editTermForm.original"
          type="textarea"
          :rows="3"
          placeholder="请输入原文"
        />
      </el-form-item>
      <el-form-item label="对应术语" prop="comparison_text">
        <el-input
          v-model="editTermForm.comparison_text"
          type="textarea"
          :rows="3"
          placeholder="请输入对应术语"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="btn_box">
        <el-button @click="editTermVisible = false">取消</el-button>
        <el-button
          type="primary"
          color="#055CF9"
          :loading="editTermLoading"
          @click="confirmEditTerm"
        >
          {{ editTermForm.id ? '确认' : '保存' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import request from '@/utils/request'

const termformRef = ref(null)

// 术语列表相关
const termsList = ref([])
const termsLoading = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 编辑术语相关
const editTermVisible = ref(false)
const editTermLoading = ref(false)
const editTermFormRef = ref(null)
const editTermForm = ref({
  id: '',
  original: '',
  comparison_text: ''
})

// 编辑术语验证规则
const editTermRules = {
  original: [
    { required: true, message: '请输入原文', trigger: 'blur' }
  ],
  comparison_text: [
    { required: true, message: '请输入对应术语', trigger: 'blur' }
  ]
}

// 搜索防抖
let searchTimer = null
const handleSearch = () => {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchTermsList()
  }, 500)
}

// 分页处理
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTermsList()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  fetchTermsList()
}

// 获取术语列表
const fetchTermsList = async () => {
  console.log('fetchTermsList 被调用，ID:', localForm.value.id)
  if (!localForm.value.id) {
    console.log('没有ID，退出获取术语列表')
    return
  }
  
  termsLoading.value = true
  try {
    const params = {
      page: currentPage.value,
      limit: pageSize.value
    }
    
    if (searchKeyword.value.trim()) {
      params.search = searchKeyword.value.trim()
    }
    
    const url = `/api/comparison/${localForm.value.id}/terms?${new URLSearchParams(params)}`
    console.log('请求URL:', url)
    
    const response = await request({
      url: `/api/comparison/${localForm.value.id}/terms`,
      method: 'get',
      params: params
    })
    
    console.log('响应状态:', response.code)
    
    if (response.code === 200) {
      termsList.value = response.data.data
      total.value = response.data.total
      console.log('术语列表设置成功，数量:', termsList.value.length, '总数:', total.value)
    } else {
      ElMessage.error(response.message || '获取术语列表失败')
    }
  } catch (error) {
    console.error('获取术语列表失败:', error)
    ElMessage.error('获取术语列表失败')
  } finally {
    termsLoading.value = false
  }
}

const validatePass = (rule, value, callback) => {
  termformRef.value.clearValidate(['origin_lang', 'target_lang'])
  if (
    localForm.value.origin_lang != '' &&
    localForm.value.target_lang != '' &&
    localForm.value.origin_lang == localForm.value.target_lang
  ) {
    callback(new Error('源语种与对照语种不能一样'))
  } else {
    callback()
  }
}

const rules = {
  title: [{ required: true, message: '请填写术语标题', trigger: ['blur', 'change'] }],
  origin_lang: [
    { required: true, message: '请选择源语种', trigger: ['blur', 'change'] },
    { validator: validatePass, trigger: ['blur', 'change'] }
  ],
  target_lang: [
    { required: true, message: '请选择对照语种', trigger: ['blur', 'change'] },
    { validator: validatePass, trigger: ['blur', 'change'] }
  ]
}

const props = defineProps({
  langs: Array,
  loading: Boolean
})

// 内部管理 visible 状态
const visible = ref(false)

const localForm = ref({
  id: '',
  title: '',
  origin_lang: '',
  target_lang: '',
  share_flag: 'N'
})

// 监听 visible 变化，打开时获取术语列表
watch(visible, (newVal) => {
  console.log('visible 变化:', newVal, 'localForm.id:', localForm.value.id)
  if (newVal && localForm.value.id) {
    console.log('准备获取术语列表，ID:', localForm.value.id)
    nextTick(() => {
      fetchTermsList()
    })
  } else {
    console.log('不满足获取术语列表的条件')
  }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'refresh'])

// 打开编辑弹窗
const open = (data) => {
  console.log('TermEdit open 被调用，接收到的数据:', data)
  localForm.value = { ...data }
  console.log('localForm 设置后的值:', localForm.value)
  visible.value = true
}

// 关闭弹窗
const close = () => {
  visible.value = false
  // 重置数据
  termsList.value = []
  searchKeyword.value = ''
  currentPage.value = 1
  total.value = 0
  // 通知父组件刷新数据
  emit('refresh')
}

// 确认保存
const confirm = async () => {
  try {
    await termformRef.value.validate()
    emit('confirm', localForm.value)
    close()
  } catch (error) {
    console.error('表单验证失败:', error)
  }
}

// 暴露方法给父组件
defineExpose({
  open
})

// 编辑术语
const editTerm = (row) => {
  editTermForm.value = {
    id: row.id,
    original: row.original,
    comparison_text: row.comparison_text
  }
  editTermVisible.value = true
}

// 新增术语
const addTerm = () => {
  editTermForm.value = {
    id: '', // 新增时ID为空
    original: '',
    comparison_text: ''
  }
  editTermVisible.value = true
}

// 确认编辑/新增术语
const confirmEditTerm = async () => {
  try {
    await editTermFormRef.value.validate()
    editTermLoading.value = true
    
    if (editTermForm.value.id) {
      // 编辑操作
      const response = await request({
        url: `/api/comparison/term/${editTermForm.value.id}`,
        method: 'put',
        data: {
          original: editTermForm.value.original,
          comparison_text: editTermForm.value.comparison_text
        }
      })
      
      if (response.code === 200) {
        ElMessage.success('编辑成功')
        editTermVisible.value = false
        // 重新获取当前页数据
        fetchTermsList()
        // 通知父组件刷新数据
        emit('refresh')
      } else {
        ElMessage.error(response.message || '编辑失败')
      }
    } else {
      // 新增操作
      const response = await request({
        url: `/api/comparison/${localForm.value.id}/terms`,
        method: 'post',
        data: {
          original: editTermForm.value.original,
          comparison_text: editTermForm.value.comparison_text
        }
      })
      
      if (response.code === 200) {
        ElMessage.success('新增成功')
        editTermVisible.value = false
        // 重新获取当前页数据
        fetchTermsList()
        // 通知父组件刷新数据
        emit('refresh')
      } else {
        ElMessage.error(response.message || '新增失败')
      }
    }
  } catch (error) {
    console.error('操作术语失败:', error)
    ElMessage.error('操作术语失败')
  } finally {
    editTermLoading.value = false
  }
}

// 删除术语
const deleteTerm = (row) => {
  ElMessageBox.confirm(
    `确定要删除这条术语记录吗？\n原文：${row.original}\n对应术语：${row.comparison_text}`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false
    }
  ).then(async () => {
    try {
      const response = await request({
        url: `/api/comparison/term/${row.id}`,
        method: 'delete'
      })
      
      if (response.code === 200) {
        ElMessage.success('删除成功')
        // 重新获取当前页数据
        fetchTermsList()
        // 通知父组件刷新数据
        emit('refresh')
      } else {
        ElMessage.error(response.message || '删除失败')
      }
    } catch (error) {
      console.error('删除术语失败:', error)
      ElMessage.error('删除术语失败')
    }
  }).catch(() => {
    // 用户取消删除
  })
}
</script>

<style lang="scss" scoped>
.term_dialog {
  .el-dialog {
    max-width: 1200px;
    margin: 3vh auto !important;
    
    .el-dialog__body {
      max-height: 80vh;
      overflow-y: auto;
      padding: 20px;
    }
    
    .el-dialog__footer {
      padding: 15px 20px;
      border-top: 1px solid #e4e7ed;
    }
  }
  
  .terms_section {
    margin-top: 20px;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    overflow: hidden;
    
    .terms_header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 15px 20px;
      background-color: #f5f7fa;
      border-bottom: 1px solid #e4e7ed;
      
      h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #303133;
      }
      
      .search_box {
        display: flex;
        align-items: center;
      }
    }
    
    .terms_table {
      padding: 0;
      
      .el-table {
        .el-table__header-wrapper {
          .el-table__header {
            th {
              background-color: #f5f7fa;
              color: #606266;
              font-weight: 600;
            }
          }
        }
        
        .el-table__body-wrapper {
          max-height: 400px;
          overflow-y: auto;
        }
      }
      
      .action-buttons {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        
        .el-button {
          margin: 0;
          padding: 4px 8px;
          min-width: 40px;
          height: 28px;
          font-size: 12px;
          
          &.el-button--primary {
            color: #409eff;
            &:hover {
              color: #66b1ff;
              background-color: #ecf5ff;
            }
          }
          
          &.el-button--danger {
            color: #f56c6c;
            &:hover {
              color: #f78989;
              background-color: #fef0f0;
            }
          }
        }
      }
    }
    
    .pagination_box {
      padding: 15px 20px;
      background-color: #f5f7fa;
      border-top: 1px solid #e4e7ed;
      display: flex;
      justify-content: center;
      align-items: center;
      
      .el-pagination {
        .el-pagination__total {
          margin-right: 15px;
        }
        
        .el-pagination__sizes {
          margin-right: 15px;
        }
        
        .el-pager {
          .el-pager__item {
            margin: 0 2px;
          }
        }
        
        .el-pagination__jump {
          margin-left: 15px;
        }
      }
    }
  }
}

.title {
  font-size: 18px;
  font-weight: bold;
  color: #111111;
}

.flag_tips {
  font-size: 12px;
  color: #8b8c9f;
  margin-top: 5px;
}

.btn_box {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 响应式设计
@media screen and (max-width: 768px) {
  .terms_header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch !important;
    
    .search_box {
      .el-input {
        width: 100% !important;
      }
    }
  }
  
  .terms_table {
    padding: 15px;
    
    .el-table {
      font-size: 12px;
    }
  }
}
</style>
