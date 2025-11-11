<template>
  <el-form :model="user" label-width="auto" ref="form" :show-message="false" :rules="rules">
    <el-form-item label="" required prop="email">
      <el-input v-model="user.email" placeholder="邮箱" />
    </el-form-item>
    <el-form-item label="" required prop="password">
      <el-input v-model="user.password" type="password" show-password placeholder="密码" />
    </el-form-item>
    <el-form-item v-if="!hasDefaultTenant" label="" required prop="tenant_code">
      <el-input v-model="user.tenant_code" placeholder="租户代码" />
    </el-form-item>
    <!-- 隐藏忘记密码功能 -->
    <!-- <div class="flex_right">
      <el-text class="forget" @click="doForget">忘记密码?</el-text>
    </div> -->
    <el-form-item label="" class="center">
      <el-button type="primary" size="large" color="#055CF9" @click="doLogin(form)" style="width: 100%">登录</el-button>
    </el-form-item>
  </el-form>
</template>
<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { store } from '@/store/index'

const emit = defineEmits(['forget', 'success'])
const form = ref()

// 从环境变量或运行时配置读取默认租户代码
// 优先使用运行时配置（打包后可通过修改配置文件变更），其次使用构建时环境变量
let defaultTenantCode = ''
try {
  // 尝试从运行时配置文件读取（打包后可通过修改 webConfig.js 变更）
  if (window.__APP_CONFIG__ && window.__APP_CONFIG__.DEFAULT_TENANT_CODE) {
    defaultTenantCode = window.__APP_CONFIG__.DEFAULT_TENANT_CODE
  }
} catch (e) {
  console.warn('无法读取运行时配置:', e)
}
// 如果运行时配置不存在，使用构建时环境变量
if (!defaultTenantCode) {
  defaultTenantCode = import.meta.env.VITE_DEFAULT_TENANT_CODE || ''
}
const hasDefaultTenant = computed(() => !!defaultTenantCode)

const user = reactive({
  email: '',
  password: '',
  tenant_code: defaultTenantCode // 如果有默认值，自动填充
})

// 动态生成验证规则：如果有默认租户代码，则不需要验证tenant_code
const rules = computed(() => {
  const rulesObj = {
    email: [{ required: true, message: '请填写邮箱地址', trigger: 'blur' }],
    password: [{ required: true, message: '请填写密码', trigger: 'blur' }]
  }
  
  // 只有在没有默认租户代码时才需要验证
  if (!hasDefaultTenant.value) {
    rulesObj.tenant_code = [{ required: true, message: '请填写租户代码', trigger: 'blur' }]
  }
  
  return rulesObj
})

// 组件挂载时，如果有默认租户代码，确保表单值已设置
onMounted(() => {
  if (hasDefaultTenant.value) {
    user.tenant_code = defaultTenantCode
  }
})
function doLogin(form) {
  form.validate((valid, fields) => {
    if (valid) {
      login(user)
        .then((data) => {
          if (data.code == 200) {
            store.setToken(data.data.token)
            store.setUsername(data.data.email)
            store.setLevel(data.data.level)
            emit('success')
          } else {
            ElMessage({
              message: data.message,
              type: 'error',
            })
          }
        })
        .catch((data) => {
          console.log(data)
        })
    } else {
      ElMessage({
        message: fields[Object.keys(fields)[0]][0]['message'],
        type: 'error',
      })
    }
  })
}
// 忘记密码功能已隐藏
// function doForget() {
//   emit('forget')
// }
</script>
<style scoped lang="scss">
.forget {
  display: inline-block;
  font-family: 'PingFang SC';
  font-weight: 400;
  font-size: 12px;
  color: #111111;
  cursor: pointer;
  line-height: 14px;
  margin-bottom: 20px;
}
::v-deep {
  .right .el-form-item__content {
    justify-content: end;
  }
  .center .el-form-item__content {
    justify-content: center;
  }
  .flex_right {
    display: flex;
    justify-content: flex-end;
  }
  .el-form-item {
    margin-bottom: 12px;
  }
}
</style>
