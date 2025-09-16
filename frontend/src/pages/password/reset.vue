<template>
  <div class="change-password-page">
    <div class="change-password-container">
      <div class="change-password-header">
        <h1 class="change-password-title">修改密码</h1>
        <p class="change-password-subtitle">请填写以下信息以修改您的密码</p>
      </div>
      <el-form
        ref="form"
        :model="user"
        :show-message="false"
        :rules="rules"
        @keyup.enter="doChangePassword(form)"
      >
        <el-form-item label="" prop="oldpwd">
          <el-input
            v-model="user.oldpwd"
            type="password"
            show-password
            placeholder="原密码"
            prefix-icon="el-icon-lock"
          />
        </el-form-item>
        <el-form-item label="" prop="newpwd">
          <el-input
            v-model="user.newpwd"
            type="password"
            show-password
            placeholder="设置新密码"
            prefix-icon="el-icon-lock"
          />
          <div class="password-tips">
            <div class="tip-item" :class="{ 'valid': user.newpwd.length >= 6 }">
              <i class="el-icon-check" v-if="user.newpwd.length >= 6"></i>
              <i class="el-icon-close" v-else></i>
              至少6位字符
            </div>
            <div class="tip-item" :class="{ 'valid': /[a-zA-Z]/.test(user.newpwd) }">
              <i class="el-icon-check" v-if="/[a-zA-Z]/.test(user.newpwd)"></i>
              <i class="el-icon-close" v-else></i>
              包含字母
            </div>
            <div class="tip-item" :class="{ 'valid': /[0-9]/.test(user.newpwd) }">
              <i class="el-icon-check" v-if="/[0-9]/.test(user.newpwd)"></i>
              <i class="el-icon-close" v-else></i>
              包含数字
            </div>
          </div>
        </el-form-item>
        <el-form-item label="" prop="newpwd_confirmation">
          <el-input
            v-model="user.newpwd_confirmation"
            type="password"
            show-password
            placeholder="确认新密码"
            prefix-icon="el-icon-lock"
          />
        </el-form-item>
        <el-form-item label="" class="center">
          <el-button
            type="primary"
            size="large"
            class="change-password-btn"
            @click="doChangePassword(form)"
            :loading="submitLoading"
          >
            {{ submitLoading ? '提交中...' : '提交' }}
          </el-button>
        </el-form-item>
        <!-- 添加忘记密码链接 -->
        <div class="forgot-password-link">
          <el-link type="primary" @click="$router.push('/forget')">忘记密码？</el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '@/api/account'

const router = useRouter()
const form = ref()
const submitLoading = ref(false)

// 表单数据
const user = reactive({
  oldpwd: '',
  newpwd: '',
  newpwd_confirmation: ''
})

// 密码复杂度验证函数
const validatePasswordComplexity = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请填写新密码'))
  } else if (value.length < 6) {
    callback(new Error('密码至少需要6位'))
  } else if (!/[a-zA-Z]/.test(value) || !/[0-9]/.test(value)) {
    callback(new Error('密码需包含字母和数字'))
  } else {
    callback()
  }
}

// 表单验证规则
const rules = reactive({
  oldpwd: [{ required: true, message: '请填写原密码', trigger: 'blur' }],
  newpwd: [{ validator: validatePasswordComplexity, trigger: 'blur' }],
  newpwd_confirmation: [{ required: true, message: '请填写确认密码', trigger: 'blur' }]
})

// 提交修改密码
const doChangePassword = async (form) => {
  form.validate(async (valid, fields) => {
    if (valid) {
      if (user.newpwd !== user.newpwd_confirmation) {
        ElMessage.error('两次密码输入不一致')
        return
      }
      
      submitLoading.value = true // 开始loading
      
      try {
        const data = await changePassword(user)
        if (data.code === 200) {
          ElMessage.success('密码修改成功')
          // 延迟跳转，让用户看到成功提示
          setTimeout(() => {
            router.push({ name: 'login' })
          }, 1500)
        } else {
          ElMessage.error(data.message)
        }
      } catch (error) {
        ElMessage.error(error.message || '密码修改失败')
      } finally {
        submitLoading.value = false // 结束loading
      }
    } else {
      ElMessage.error(fields[Object.keys(fields)[0]][0].message)
    }
  })
}
</script>

<style scoped lang="scss">
.change-password-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #6a11cb, #2575fc);
  padding: 20px;
}

.change-password-container {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.change-password-header {
  text-align: center;
  margin-bottom: 24px;
}

.change-password-title {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.change-password-subtitle {
  font-size: 14px;
  color: #666;
}

.change-password-btn {
  width: 100%;
  background: linear-gradient(135deg, #6a11cb, #2575fc);
  border: none;
  transition: all 0.3s ease;
  &:hover {
    opacity: 0.9;
  }
}

// 忘记密码链接样式
.forgot-password-link {
  text-align: center;
  margin-top: 16px;
  .el-link {
    font-size: 14px;
  }
}

// 密码提示样式
.password-tips {
  margin-top: 8px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
  border-radius: 8px;
  border: 1px solid #e1e5ff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  
  .tip-item {
    display: flex;
    align-items: center;
    font-size: 13px;
    color: #6c757d;
    margin-bottom: 6px;
    padding: 4px 0;
    transition: all 0.3s ease;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    i {
      margin-right: 8px;
      font-size: 14px;
      width: 16px;
      text-align: center;
    }
    
    .el-icon-check {
      color: #52c41a;
      font-weight: bold;
    }
    
    .el-icon-close {
      color: #ff4d4f;
    }
    
    &.valid {
      color: #52c41a;
      font-weight: 500;
    }
  }
}
</style>
