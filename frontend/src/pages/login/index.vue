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
            <el-form-item prop="tenant_code" v-if="false">
              <el-input
                v-model="loginForm.tenant_code"
                placeholder="租户代码"
                prefix-icon="el-icon-office-building"
              />
            </el-form-item>
            <el-form-item class="center">
              <el-button type="primary" size="large" class="auth-btn" @click="doLogin" :loading="loginLoading">
                {{ loginLoading ? '登录中...' : '登录' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const router = useRouter()
const activeTab = ref('login')
const loginFormRef = ref(null)
const loginLoading = ref(false)

// 登录表单
const loginForm = reactive({
  email: '',
  password: '',
  tenant_code: 'TENANT_0001' // 用户必须手动输入租户代码
})

// 验证规则：租户代码始终必填
const loginRules = {
  email: [{ required: true, message: '请填写邮箱地址', trigger: 'blur' }],
  password: [{ required: true, message: '请填写密码', trigger: 'blur' }],
  tenant_code: [{ required: true, message: '请填写租户代码', trigger: 'blur' }]
}

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
