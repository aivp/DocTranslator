<template>
  <div
    class="page-center"
    v-loading="pageLoad"
    element-loading-text="loading..."
    element-loading-spinner="el-icon-loading"
    element-loading-background="rgba(255, 255, 255, 0.7)"
  >
    <div class="container">
      <div class="tab_box">
        <div class="tab_li actived">我的</div>
        <div class="tab_li" @click="$router.push('/corpus/square')">广场</div>
      </div>
      <div class="content_box" v-if="true">
        <div class="flex_box flex-between phone_box">
          <el-button-group>
            <el-button
              :class="tab_active == 'terms' ? 'btn_active' : 'my_button'"
              :plain="tab_active == 'terms' ? false : true"
              :type="tab_active == 'terms' ? 'primary' : ''"
              @click="tabSelect('terms')"
            >
              我的术语表
            </el-button>
            <el-button
              :class="tab_active == 'prompt' ? 'btn_active' : 'my_button'"
              :plain="tab_active == 'prompt' ? false : true"
              :type="tab_active == 'prompt' ? 'primary' : ''"
              @click="tabSelect('prompt')"
            >
              我的提示词
            </el-button>
          </el-button-group>

          <div class="btn_box" v-if="tab_active == 'terms'">
            <el-button type="primary" color="#055CF9" @click="openTerms">新建</el-button>
            <el-button type="primary" style="margin: 0 8px" @click="command_terms('down')">
              模板下载
            </el-button>
            <el-upload
              name="file"
              :before-upload="upload_before"
              :action="uploadUrl"
              :headers="{ Authorization: 'Bearer ' + userStore.token }"
              :show-file-list="false"
              :on-success="(response, file, fileList) => upload_success(response)"
              :on-error="(err, file, fileList) => upload_error(err)"
              :disabled="importLoading"
              style="display: inline-block;"
            >
              <el-button 
                type="primary" 
                :loading="importLoading"
                :disabled="importLoading"
              >
                {{ importLoading ? '导入中...' : '导入文件' }}
              </el-button>
            </el-upload>
            <el-button 
              type="" 
              @click="export_terms_all"
              :loading="exportAllLoading"
              :disabled="exportAllLoading"
            >
              {{ exportAllLoading ? '导出中...' : '全部导出' }}
            </el-button>
          </div>

          <div class="btn_box" v-if="tab_active == 'prompt'">
            <el-button type="primary" color="#055CF9" @click="openPrompt">新建</el-button>
          </div>
        </div>
        <!-- 术语列表 -->
        <div class="term_box" v-if="tab_active == 'terms'">
          <el-row :gutter="24" v-if="termsData.length > 0">
            <el-col :xs="24" :sm="8" v-for="(item, index) in termsData" :key="index">
              <div class="term_li">
                <div class="flex_box title_box flex-between">
                  <div class="t" :title="item.title">{{ item.title }}</div>
                  <div class="des">{{ item.origin_lang }}-{{ item.target_lang }}</div>
                </div>
                <div class="term_count">
                  <span class="count_text">共 {{ item.term_count || 0 }} 条术语</span>
                </div>
                <div class="btn_box flex_box flex-between">
                  <div class="left">
                    <el-button type="text" @click="openTerms(item)">编辑</el-button>
                    <el-button type="text" style="color: red" @click="delTerms(item)"
                      >删除</el-button
                    >
                    <el-button 
                      type="text" 
                      @click="export_terms(item)"
                      :loading="exportLoading"
                      :disabled="exportLoading"
                    >
                      {{ exportLoading ? '导出中...' : '导出' }}
                    </el-button>
                  </div>
                  <div class="right">
                    <el-switch
                      v-model="item.share_flag"
                      active-value="Y"
                      inactive-value="N"
                      @change="share_change(item)"
                    />
                  </div>
                </div>
                <div class="table_box" v-if="item.sample_terms && item.sample_terms.length > 0">
                  <el-table
                    :data="item.sample_terms"
                    style="width: 100%"
                    max-height="340"
                    border
                    header-cell-class-name="table_title"
                    tooltip-effect="light"
                  >
                    <el-table-column
                      prop="original"
                      :label="item.origin_lang"
                      show-overflow-tooltip
                    />
                    <el-table-column
                      prop="comparison_text"
                      :label="item.target_lang"
                      show-overflow-tooltip
                    />
                  </el-table>
                  <!-- <div class="more_terms" v-if="item.term_count > 5">
                    <el-button type="text" size="small">查看更多术语...</el-button>
                  </div> -->
                </div>
                <div class="no_terms" v-else>
                  <div class="text">暂无术语数据</div>
                </div>
              </div>
            </el-col>
          </el-row>
          <div v-else class="no_data">
            <img src="@/assets/nodata.png" alt="" />
            <div class="text">暂无数据</div>
          </div>
        </div>
        <!-- 提示词列表 -->
        <div class="prompt_box" v-if="tab_active == 'prompt'">
          <el-row :gutter="24" v-if="promptData.length > 0">
            <el-col :xs="24" :sm="8" v-for="(item, index) in promptData" :key="index">
              <div class="term_li">
                <div class="flex_box title_box flex-between">
                  <div class="t" :title="item.title">{{ item.title }}</div>
                </div>
                <div class="btn_box flex_box flex-between" v-if="!item.undelete">
                  <div class="left">
                    <el-button type="text" @click="openPrompt(item)">编辑</el-button>
                    <el-button type="text" style="color: red" @click="delPrompt(item)"
                      >删除</el-button
                    >
                  </div>
                  <div class="right">
                    <el-switch
                      v-model="item.share_flag"
                      active-value="Y"
                      inactive-value="N"
                      @change="share_change_prompt(item)"
                    />
                  </div>
                </div>
                <div class="btn_box" v-else></div>
                <div class="text_box">
                  <div class="text">{{ item.content }}</div>
                </div>
              </div>
            </el-col>
          </el-row>
          <div v-else class="no_data">
            <img src="@/assets/nodata.png" alt="" />
            <div class="text">暂无数据</div>
          </div>
        </div>
      </div>

      <!-- 备案信息 -->
      <Filing v-if="false"/>
    </div>

    <!-- 术语弹窗 -->
    <TermEdit ref="termEditRef" :langs="langs" :loading="btnLoad" @confirm="handleTermConfirm" @refresh="getTermList" />

    <!-- 提示词弹窗 -->
    <PromptEdit ref="promptEditRef" :loading="btnLoad" @confirm="handlePromptConfirm" />
  </div>
</template>

<script setup>
import Filing from '@/components/filing.vue'
// import { useRouter } from 'vue-router'
import { store } from '@/store/index'
import TermEdit from './components/TermEdit.vue'
import PromptEdit from './components/PromptEdit.vue'
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/store/user'
import {
  comparison_my,
  comparison,
  comparison_edit,
  comparison_del,
  comparison_share,
  prompt_add,
  prompt_edit,
  prompt_my,
  prompt_share,
  prompt_del
} from '@/api/corpus'
const userStore = useUserStore()
const uploadUrl = ref(import.meta.env.VITE_API_URL + '/comparison/import')
const pageLoad = ref(false)
const termsData = ref([])
const promptData = ref([])
const termEditRef = ref(null)
const btnLoad = ref(false)
const promptEditRef = ref(null)
const tab_active = ref('terms')
const importLoading = ref(false) // 导入loading状态
const exportLoading = ref(false) // 导出loading状态
const exportAllLoading = ref(false) // 批量导出loading状态
// const token = localStorage.getItem('token')
// const prompt_id = ref(0)
// watch(
//   () => store.prompt,
//   (n, o) => {
//     if (n) {
//       promptData.value.unshift({
//         title: '默认提示语(无法删除)',
//         content: store.prompt,
//         undelete: true
//       })
//     }
//   }
// )

// 切换tab
function tabSelect(i) {
  tab_active.value = i
}
// 获取术语表数据
const getTermList = async () => {
  pageLoad.value = false
  try {
    const res = await comparison_my()
    if (res.code === 200) {
      termsData.value = res.data.data
      // console.log(111, termsData.value)
      // store.setComparisonList(res.data.data)
    }
  } catch (error) {
    console.error('获取术语表数据失败:', error)
  }
  pageLoad.value = false
}

// 获取提示词数据
const getPromptList = async () => {
  pageLoad.value = false
  try {
    const res = await prompt_my()
    if (res.code === 200) {
      // console.log(6666, res.data)
      promptData.value = JSON.parse(JSON.stringify(res.data.data))
      // 不再添加硬编码的默认提示词
    }
  } catch (error) {
    console.error('获取提示词数据失败:', error)
  }
  pageLoad.value = false
}

//翻译语言
const langs = ['中文', '英语', '日语', '俄语', '阿拉伯语', '西班牙语','韩语','德语']

// 处理提示词弹窗保存逻辑
const handlePromptConfirm = (val) => {
  const formData = val
  btnLoad.value = true
  //是否是编辑
  if (formData.id) {
    prompt_edit(formData.id, formData)
      .then((data) => {
        btnLoad.value = false
        if (data.code == 200) {
          ElMessage({ message: '保存成功', type: 'success' })
          promptEditRef.value.close()
          getPromptList()
        } else {
          ElMessage({ message: data.message, type: 'error' })
        }
      })
      .catch((err) => {
        ElMessage({ message: '接口异常', type: 'error' })
      })
  } else {
    prompt_add(formData)
      .then((data) => {
        btnLoad.value = false
        if (data.code == 200) {
          ElMessage({ message: '保存成功', type: 'success' })
          promptEditRef.value.close()
          getPromptList()
        } else {
          ElMessage({ message: data.message, type: 'error' })
        }
      })
      .catch((err) => {
        ElMessage({ message: '接口异常', type: 'error' })
      })
  }
  promptEditRef.value.close()
  btnLoad.value = false
}
//处理术语表单弹窗保存逻辑
const handleTermConfirm = (val) => {
  const formData = val
  console.log('保存术语表数据:', formData) // 添加调试信息
  btnLoad.value = true
  if (formData.id) {
    // 编辑操作
    console.log('执行编辑操作，ID:', formData.id) // 添加调试信息
    comparison_edit(formData.id, formData)
      .then((data) => {
        console.log('编辑成功响应:', data) // 添加调试信息
        console.log('响应数据类型:', typeof data) // 添加类型信息
        console.log('响应数据键:', Object.keys(data || {})) // 添加键信息
        btnLoad.value = false
        if (data.code == 200) {
          ElMessage({ message: '保存成功', type: 'success' })
          // 先刷新数据，再关闭弹窗
          getTermList()
          // 延迟关闭弹窗，确保数据刷新完成
          setTimeout(() => {
            if (termEditRef.value) {
              termEditRef.value.close()
            }
          }, 100)
        } else {
          ElMessage({ message: data.message || '保存失败', type: 'error' })
        }
      })
      .catch((err) => {
        btnLoad.value = false
        console.error('编辑术语表失败:', err) // 详细的错误信息
        ElMessage({ message: '接口异常', type: 'error' })
      })
  } else {
    // 新建操作
    console.log('执行新建操作') // 添加调试信息
    comparison(formData)
      .then((data) => {
        console.log('新建成功响应:', data) // 添加调试信息
        console.log('响应数据类型:', typeof data) // 添加类型信息
        console.log('响应数据键:', Object.keys(data || {})) // 添加键信息
        btnLoad.value = false
        if (data.code == 200) {
          ElMessage({ message: '保存成功', type: 'success' })
          // 先刷新数据，再关闭弹窗
          getTermList()
          // 延迟关闭弹窗，确保数据刷新完成
          setTimeout(() => {
            if (termEditRef.value) {
              termEditRef.value.close()
            }
          }, 100)
        } else {
          ElMessage({ message: data.message || '保存失败', type: 'error' })
        }
      })
      .catch((err) => {
        btnLoad.value = false
        console.error('新建术语表失败:', err) // 详细的错误信息
        ElMessage({ message: '接口异常', type: 'error' })
      })
  }
}

//打开术语弹窗-编辑
function openTerms(item) {
  if (item) {
    termEditRef.value.open(item) // 传递完整的术语表数据
  } else {
    termEditRef.value.open({
      title: '', // 标题
      share_flag: 'N',
      origin_lang: '',
      target_lang: ''
    })
  }
}
//打开提示词
function openPrompt(item) {
  promptEditRef.value.open()
  if (item) {
    promptEditRef.value.updateForm(JSON.parse(JSON.stringify(item)))
  } else {
    promptEditRef.value.updateForm({
      title: '', //标题
      share_flag: 'N',
      content: ''
    })
  }
}

//删除术语表
function delTerms(item) {
  ElMessageBox.confirm('确定要删除？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    pageLoad.value = true
    comparison_del(item.id).then((data) => {
      if (data.code == 200) {
        ElMessage({ message: '删除成功', type: 'success' })
        getTermList()
      } else {
        ElMessage({ message: data.message, type: 'error' })
      }
    })
  })
}

//术语表 分享状态修改
function share_change(item) {
  pageLoad.value = true
  comparison_share(item.id, { share_flag: item.share_flag })
    .then((data) => {
      pageLoad.value = false
      if (data.code == 200) {
        ElMessage({ message: '分享状态已更新', type: 'success' })
      } else {
        ElMessage({ message: data.message, type: 'error' })
        item.share_flag == 'Y' ? (item.share_flag = 'N') : (item.share_flag = 'Y')
      }
    })
    .catch((err) => {
      ElMessage({ message: '接口异常', type: 'error' })
      item.share_flag == 'Y' ? (item.share_flag = 'N') : (item.share_flag = 'Y')
    })
}

//导出单个术语表
async function export_terms(item) {
  try {
    // 设置loading状态
    exportLoading.value = true
    
    // 发起 fetch 请求
    const response = await fetch(
      `${import.meta.env.VITE_API_URL}/comparison/export/${item.id}`,
      {
        headers: {
          Authorization: `Bearer ${userStore.token}`
        }
      }
    )

    // 检查响应状态
    if (!response.ok) {
      throw new Error('文件下载失败')
    }

    // 获取文件内容
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)

    // 创建 `<a>` 标签并触发下载
    const a = document.createElement('a')
    a.href = url
    a.download = `${item.title}.xlsx` // 设置下载文件名
    document.body.appendChild(a)
    a.click()
    // 清理资源
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url) // 释放 URL 对象
    
    ElMessage({ message: '导出成功', type: 'success' })
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('文件下载失败，请稍后重试')
  } finally {
    // 清除loading状态
    exportLoading.value = false
  }
}

// 导出所有术语表
async function export_terms_all() {
  try {
    // 设置loading状态
    exportAllLoading.value = true
    
    const response = await fetch(import.meta.env.VITE_API_URL + '/comparison/export/all', {
      headers: {
        Authorization: `Bearer ${userStore.token}`
      }
    })

    if (!response.ok) {
      throw new Error('术语表导出失败')
    }

    // 获取文件内容
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)

    // 创建 `<a>` 标签并触发下载
    const a = document.createElement('a')
    a.href = url
    a.download = `all_terms_${new Date().toISOString().slice(0, 10)}.zip` // 设置下载文件名，假设导出的是 Excel 文件
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url) // 释放 URL 对象
    
    ElMessage({ message: '批量导出成功', type: 'success' })
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('术语表导出失败，请稍后重试')
  } finally {
    // 清除loading状态
    exportAllLoading.value = false
  }
}

//术语表模板下载
function command_terms(type) {
  if (type == 'down') {
    window.open(import.meta.env.VITE_API_URL + '/comparison/template')
  }
}

//上传文件
function upload_success(response) {
  console.log("上传成功")
  console.log(response)
  
  // 清除loading状态
  importLoading.value = false
  
  if (response.code == 200) {
    ElMessage({ message: '导入成功', type: 'success' })
    getTermList()
  } else {
    ElMessage({ message: response.message, type: 'error' })
  }
}

function upload_error(error) {
  console.log("上传失败")
  console.log(error)
  
  // 清除loading状态
  importLoading.value = false
  
  let errorMessage = '导入失败'
  
  try {
    // UploadAjaxError的message属性包含JSON字符串
    if (error.message) {
      const errorData = JSON.parse(error.message)
      if (errorData.message) {
        // 确保Unicode编码被正确解码
        errorMessage = decodeURIComponent(JSON.stringify(errorData.message).replace(/\\u/g, '%u'))
      }
    }
  } catch (e) {
    console.error('解析错误响应失败:', e)
    // 如果解析失败，尝试直接使用error.message
    if (error.message && typeof error.message === 'string') {
      errorMessage = error.message
    }
  }
  
  ElMessage({ message: errorMessage, type: 'error' })
}
//上传文件校验
function upload_before(file) {
  const fileType = file.name.substring(file.name.lastIndexOf('.') + 1)
  const isXlsx = fileType === 'xlsx'
  if (!isXlsx) {
    ElMessage({ message: '请上传模板格式的文件', type: 'error' })
    return false
  }
  
  // 文件验证通过，设置loading状态
  importLoading.value = true
  console.log("isXlsx", isXlsx)
  return isXlsx
}

//提示词 分享状态修改
function share_change_prompt(item) {
  pageLoad.value = true
  if (item.id) {
    prompt_share(item.id, { share_flag: item.share_flag })
      .then((data) => {
        pageLoad.value = false
        if (data.code == 200) {
          ElMessage({ message: '分享状态已更新', type: 'success' })
        } else {
          ElMessage({ message: data.message, type: 'error' })
          item.share_flag == 'Y' ? (item.share_flag = 'N') : (item.share_flag = 'Y')
        }
      })
      .catch((err) => {
        ElMessage({ message: '接口异常', type: 'error' })
        item.share_flag == 'Y' ? (item.share_flag = 'N') : (item.share_flag = 'Y')
      })
  }
}

//删除提示词
function delPrompt(item) {
  ElMessageBox.confirm('确定要删除？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    pageLoad.value = true
    prompt_del(item.id).then((data) => {
      if (data.code == 200) {
        ElMessage({ message: '删除成功', type: 'success' })
        getPromptList()
      } else {
        ElMessage({ message: data.message, type: 'error' })
      }
    })
  })
}
onMounted(() => {
  getTermList()
  getPromptList()
})
</script>

<style scoped lang="scss">
.page-center {
  flex: 1;
  overflow-y: auto;
}
.container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 20px;
  padding-bottom: 20px;
}
//tab标签
.tab_box {
  width: 100%;
  height: 68px;
  display: flex;
  align-items: center;
  .tab_li {
    width: 80px;
    height: 36px;
    box-sizing: border-box;
    border-radius: 4px;
    text-align: center;
    line-height: 34px;
    cursor: pointer;
    font-size: 16px;
    color: #284272;
    box-shadow: 0px 2px 4px 0px rgba(5, 92, 249, 0.1);
    border-radius: 4px;
    border: 1px solid #e0e5ed;
    margin-right: 16px;
    background: #fff;
    &.actived {
      background: #055cf9;
      border-color: #055cf9;
      color: #ffffff;
      font-weight: bold;
    }
  }
}
//中间内容区域
.content_box {
  background: #fff;
  padding: 28px;
  padding-bottom: 8px;
  .term_box {
    margin-top: 20px;
  }
  .prompt_box {
    margin-top: 20px;
  }
  .term_li {
    width: 100%;
    background: #ffffff;
    border-radius: 4px;
    border: 1px solid #b8d3ff;
    overflow: hidden;
    margin-bottom: 20px;
    .title_box {
      height: 40px;
      background: #f1f6ff;
      border-bottom: 1px solid #b8d3ff;
      padding: 0 20px;
      .t {
        flex: 1;
        margin-right: 20px;
        font-weight: bold;
        font-size: 14px;
        color: #055cf9;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .des {
        font-size: 14px;
        color: #111111;
      }
    }
    .term_count {
      padding: 0 20px;
      height: 30px;
      line-height: 30px;
      font-size: 14px;
      color: #8b8c9f;
      border-bottom: 1px solid #f0f0f0;
      .count_text {
        font-weight: bold;
        color: #055cf9;
      }
    }
    .btn_box {
      padding: 0 20px;
      height: 50px;
      border-bottom: 1px solid #f0f0f0;
      .left {
        display: flex;
        align-items: center;
      }
      .right {
        display: flex;
        align-items: center;
      }
    }
    .table_box {
      padding: 0 20px;
      padding-top: 20px;
      padding-bottom: 20px;
    }
    .more_terms {
      padding: 0 20px;
      padding-top: 10px;
      text-align: center;
      border-top: 1px solid #f0f0f0;
      .el-button {
        color: #055cf9;
        font-size: 12px;
      }
    }
    .no_terms {
      padding: 0 20px;
      padding-top: 20px;
      padding-bottom: 20px;
      text-align: center;
      .text {
        font-size: 14px;
        color: #8b8c9f;
        font-style: italic;
      }
    }
    .text_box {
      padding: 0 20px;
      padding-bottom: 22px;
      .text {
        box-sizing: border-box;
        height: 340px;
        border: 1px solid #dcdee2;
        padding: 10px 20px;
        font-size: 14px;
        color: #111111;
        line-height: 28px;
        word-break: break-word;
        overflow-y: auto;
        &.disabled {
          color: #284272;
          background: #b8d3ff;
        }
      }
      // 滚动条样式
      .text::-webkit-scrollbar {
        width: 4px;
      }
      .text::-webkit-scrollbar-thumb {
        border-radius: 10px;
        -webkit-box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.2);
        opacity: 0.2;
        background: fade(#d8d8d8, 60%);
      }
      .text::-webkit-scrollbar-track {
        -webkit-box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.2);
        border-radius: 0;
        background: fade(#d8d8d8, 30%);
      }
    }
  }
}

.no_data {
  text-align: center;
  img {
    margin-top: 50px;
    max-width: 100%;
  }
  .text {
    font-size: 16px;
    color: #8b8c9f;
    margin-top: 30px;
    margin-bottom: 120px;
  }
}

::v-deep {
  //弹窗
  .term_dialog {
    padding-top: 20px;
    .el-dialog {
      max-width: 740px;
      padding: 30px 50px;
    }
    .el-dialog__header {
      font-weight: bold;
      font-size: 18px;
      color: #111;
      padding: 0 20px;
      margin-bottom: 16px;
      .title {
        display: inline-block;
        line-height: 32px;
        margin-right: 30px;
      }
      .flag_tips {
        display: inline-block;
        line-height: 32px;
        font-size: 14px;
        color: #111;
        font-weight: normal;
        margin-left: 10px;
      }
    }
    .el-dialog__headerbtn {
      font-size: 20px;
      right: 10px;
      top: 10px;
      i {
        color: #111;
      }
    }
    .el-dialog__body {
      padding: 0px 20px;
      max-height: 450px;
      overflow-y: auto;
    }
    .el-form-item {
      .el-form-item__label {
        justify-content: flex-start;
        color: #111111;
      }
      .el-input-number .el-input__inner {
        text-align: left;
      }
    }
    .btn_box {
      position: relative;
      text-align: center;
    }

    .term_custom {
      width: 100%;
      .label {
        line-height: 22px;
        margin-bottom: 8px;
      }
      .el-button {
        height: auto;
        margin-bottom: 10px;
        padding: 0;
        margin-right: 20px;
      }
      .button_box {
        display: flex;
      }
      .icon_add {
        font-size: 14px;
        color: #ffffff;
        width: 20px;
        height: 20px;
        line-height: 20px;
        background: #055cf9;
        border-radius: 3px;
        text-align: center;
      }
    }
    .term_set_li {
      width: 100%;
      align-items: flex-start;
      .form {
        flex: 1;
        margin-right: 20px;
      }
      .icon_del {
        font-size: 14px;
        color: #ffffff;
        width: 20px;
        height: 20px;
        line-height: 20px;
        background: #ed4014;
        border-radius: 3px;
        text-align: center;
        margin-top: 5px;
      }
    }
    .tips {
      font-size: 14px;
      color: #111111;
      line-height: 24px;
      margin-bottom: 10px;
    }
    .el-switch__core .el-switch__action {
      top: 1px;
    }
  }

  .table_title {
    color: #111111;
  }
  .btn_active {
    background: #eff5ff;
    border-color: #eff5ff;
    color: #055cf9;
  }
  .my_button {
    border-color: #eef3fa;
  }
  tbody {
    outline: none;
  }

  .el-popper {
    max-width: 300px;
  }
}
.btn_box {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .el-button {
    border-radius: 6px;
    font-weight: 500;
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    
    &:active {
      transform: translateY(0);
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
    }
  }
  
  .el-upload {
    .el-button {
      padding: 8px 16px;
    }
  }
}
@media screen and (max-width: 767px) {
  .phone_box {
    flex-direction: column;
    align-items: flex-start;
    .btn_box {
      margin-top: 12px;
    }
  }
  ::v-deep {
    .term_dialog {
      .el-dialog {
        padding: 20px !important;
      }
      .el-dialog__body {
        max-height: 300px;
      }
    }
  }
  .table_box {
    height: auto !important;
    margin-bottom: 20px;
  }
  .no_data {
    .text {
      margin-bottom: 20px;
    }
  }

  /*手机端布局调整*/
  .container {
    padding: 0 16px;
  }
  .content_box {
    padding: 20px 14px;
  }
  .term_box {
    margin-top: 16px;
  }
  .term_li .title_box {
    padding: 0 13px !important;
  }
  .term_li .table_box {
    padding: 0 13px !important;
  }
  .term_li .text_box {
    padding: 0 13px !important;
    padding-bottom: 20px !important;
  }
  .term_li .btn_box {
    padding: 0 13px !important;
  }
  .term_box .el-col:last-child .term_li {
    margin-bottom: 0;
  }
}
</style>
