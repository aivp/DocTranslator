<template>
  <div class="auth-page">
    <div class="auth-container">
      <div class="auth-header">
        <img src="@/assets/logo.png" alt="Logo" class="auth-logo" />
        <h1 class="auth-title">欢迎回来</h1>
        <p class="auth-subtitle">请登录以继续</p>
      </div>
      <el-tabs v-model="activeTab" stretch class="auth-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" ref="loginFormRef" :rules="loginRules" @keyup.enter="doLogin">
            <el-form-item prop="email">
              <el-input
                v-model="loginForm.email"
                placeholder="邮箱"
                prefix-icon="el-icon-message"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                show-password
                placeholder="密码"
                prefix-icon="el-icon-lock"
              />
            </el-form-item>
            <el-form-item v-if="!hasDefaultTenant" prop="tenant_code">
              <el-input
                v-model="loginForm.tenant_code"
                placeholder="租户代码"
                prefix-icon="el-icon-office-building"
              />
            </el-form-item>
            <!-- 隐藏忘记密码功能 -->
            <!-- <div class="auth-actions">
              <el-link type="primary" class="forget-link" @click="goToForgot"> 忘记密码? </el-link>
            </div> -->
            <el-form-item class="center">
              <el-button type="primary" size="large" class="auth-btn" @click="doLogin" :loading="loginLoading">
                {{ loginLoading ? '登录中...' : '登录' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 注册功能已隐藏 -->
        <!-- <el-tab-pane label="注册" name="register">
          <el-form
            :model="registerForm"
            ref="registerFormRef"
            :rules="registerRules"
            @keyup.enter="doRegister"
          >
            <el-form-item prop="email">
              <el-input
                v-model="registerForm.email"
                placeholder="输入邮箱"
                prefix-icon="el-icon-message"
              />
            </el-form-item>
            <el-form-item prop="code">
              <el-input
                v-model="registerForm.code"
                placeholder="邮箱验证码"
                prefix-icon="el-icon-key"
              >
                <template #suffix>
                  <el-button
                    type="text"
                    class="code-btn"
                    @click="sendCode"
                    :disabled="codeDisabled"
                  >
                    {{ codeText }}
                  </el-button>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                show-password
                placeholder="输入密码"
                prefix-icon="el-icon-lock"
              />
            </el-form-item>
            <el-form-item prop="password2">
              <el-input
                v-model="registerForm.password2"
                type="password"
                show-password
                placeholder="确认输入密码"
                prefix-icon="el-icon-lock"
              />
            </el-form-item>
            <el-form-item class="center">
              <el-button type="primary" size="large" class="auth-btn" @click="doRegister" :loading="registerLoading">
                {{ registerLoading ? '提交中...' : '提交' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane> -->
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const router = useRouter()
const activeTab = ref('login')
const loginFormRef = ref(null)
const loginLoading = ref(false)

// 从环境变量读取默认租户代码
const defaultTenantCode = import.meta.env.VITE_DEFAULT_TENANT_CODE || ''
const hasDefaultTenant = computed(() => !!defaultTenantCode)

// 登录表单
const loginForm = reactive({
  email: '',
  password: '',
  tenant_code: defaultTenantCode // 如果有默认值，自动填充
})

// 动态生成验证规则：如果有默认租户代码，则不需要验证tenant_code
const loginRules = computed(() => {
  const rules = {
    email: [{ required: true, message: '请填写邮箱地址', trigger: 'blur' }],
    password: [{ required: true, message: '请填写密码', trigger: 'blur' }]
  }
  
  // 只有在没有默认租户代码时才需要验证
  if (!hasDefaultTenant.value) {
    rules.tenant_code = [{ required: true, message: '请填写租户代码', trigger: 'blur' }]
  }
  
  return rules
})

// 组件挂载时，如果有默认租户代码，确保表单值已设置
onMounted(() => {
  if (hasDefaultTenant.value) {
    loginForm.tenant_code = defaultTenantCode
  }
})

// 注册功能已隐藏
// const registerForm = reactive({
//   email: '',
//   code: '',
//   password: '',
//   password2: ''
// })
// const registerRules = reactive({
//   email: [{ required: true, message: '请填写邮箱地址', trigger: 'blur' }],
//   code: [{ required: true, message: '请填写邮箱验证码', trigger: 'blur' }],
//   password: [{ required: true, message: '请填写密码', trigger: 'blur' }],
//   password2: [{ required: true, message: '请填写确认密码', trigger: 'blur' }]
// })
// const registerFormRef = ref(null)

// // 验证码相关
// const codeText = ref('发送')
// const codeDisabled = ref(false)
// const sendCode = async () => {
//   if (codeDisabled.value) return
//   if (!registerForm.email.trim()) {
//     ElMessage.error('请填写邮箱地址')
//     return
//   }

//   try {
//     await registerSendEmail(registerForm.email)
//     ElMessage.success('验证码已发送')
//     codeDisabled.value = true
//     let count = 60
//     codeText.value = `${count}s`
//     const timer = setInterval(() => {
//       if (count <= 0) {
//         clearInterval(timer)
//         codeDisabled.value = false
//         codeText.value = '发送'
//         return
//       }
//       count--
//       codeText.value = `${count}s`
//     }, 1000)
//   } catch (error) {
//     ElMessage.error(error.message)
//   }
// }

// 登录
const doLogin = async () => {
  loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loginLoading.value = true // 开始loading
      
      try {
        const data = await login(loginForm)
        if (data.code === 200) {
          userStore.updateToken(data.data.token)
          router.push({ name: 'home' })
        } else {
          ElMessage.error(data.message)
        }
      } catch (error) {
        // 错误信息已经在request拦截器中处理了，这里不需要再显示
        console.error('登录失败:', error)
      } finally {
        loginLoading.value = false // 结束loading
      }
    } else {
      ElMessage.error('请正确填写表单')
    }
  })
}

// 注册功能已隐藏
// const doRegister = async () => {
//   if (!registerFormRef.value) return
//   registerFormRef.value.validate(async (valid) => {
//     if (valid) {
//       if (registerForm.password !== registerForm.password2) {
//         ElMessage.error('两次密码输入不一致')
//         return
//       }
      
//       registerLoading.value = true // 开始loading
      
//       try {
//         const data = await register(registerForm)
//         if (data.code === 200) {
//           ElMessage.success('注册成功')
//           activeTab.value = 'login'
//         } else {
//           ElMessage.error(data.message)
//         }
//       } catch (error) {
//         // 错误信息已经在request拦截器中处理了，这里不需要再显示
//         console.error('注册失败:', error)
//       } finally {
//         registerLoading.value = false // 结束loading
//       }
//     } else {
//       ElMessage.error('请正确填写表单')
//     }
//   })
// }

// 跳转到忘记密码页 - 已隐藏
// const goToForgot = () => {
//   router.push({ name: 'forget' })
// }
</script>

<style scoped lang="scss">
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #6a11cb, #2575fc);
  padding: 20px;
}

.auth-container {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.auth-header {
  text-align: center;
  margin-bottom: 24px;
}

.auth-logo {
  width: 80px;
  height: 80px;
  margin-bottom: 16px;
}

.auth-title {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: 14px;
  color: #666;
}

.auth-tabs {
  :deep(.el-tabs__item) {
    font-size: 16px;
    font-weight: 500;
    color: #666;
  }
  :deep(.el-tabs__item.is-active) {
    color: #2575fc;
  }
  :deep(.el-tabs__nav-wrap::after) {
    background-color: transparent;
  }
}

.auth-actions {
  margin-bottom: 20px;
  text-align: right;
}

.forget-link {
  font-size: 12px;
  color: #2575fc;
}

.auth-btn {
  width: 100%;
  background: linear-gradient(135deg, #6a11cb, #2575fc);
  border: none;
  transition: all 0.3s ease;
  &:hover {
    opacity: 0.9;
  }
}

.code-btn {
  font-size: 12px;
  color: #2575fc;
  padding: 0;
}
</style>
