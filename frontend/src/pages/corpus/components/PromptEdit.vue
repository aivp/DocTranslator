<template>
  <el-dialog
    v-model="visible"
    destroy-on-close
    title="提示语编辑器"
    width="90%"
    modal-class="term_dialog"
  >
    <template #header="{ close, titleId, titleClass }">
      <span class="title">提示语编辑器</span>
      <el-switch v-model="localForm.share_flag" active-value="Y" inactive-value="N" />
      <div class="flag_tips">共享{{ localForm.share_flag == 'Y' ? '开启' : '关闭' }}</div>
    </template>
    <el-form
      ref="promptformRef"
      :model="localForm"
      :rules="rules"
      label-position="top"
      hide-required-asterisk="true"
    >
      <el-row :gutter="20">
        <el-col :span="24">
          <el-form-item label="提示语标题" required prop="title" width="100%">
            <el-input
              v-model="localForm.title"
              type="text"
              placeholder="请输入提示语标题"
              maxlength="150"
              show-word-limit
            />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="# 角色" required prop="role_content" width="100%">
            <div class="prompt-section">
              <el-input
                v-model="localForm.role_content"
                type="textarea"
                :rows="4"
                resize="none"
                placeholder="请输入翻译专家的角色描述"
                maxlength="150"
                show-word-limit
              />
              <div class="example-text">
                示例：你是一名专业的法律翻译专家,精通中文和英文,尤其擅长处理商业合同和法律文件。
              </div>
            </div>
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="# 任务" required prop="task_content" width="100%">
            <div class="prompt-section">
              <el-input
                v-model="localForm.task_content"
                type="textarea"
                :rows="4"
                resize="none"
                placeholder="请输入具体的翻译任务"
                maxlength="150"
                show-word-limit
              />
              <div class="example-text">
                示例：我需要你将以下中文法律文本翻译成专业、精准、正式的英文。
              </div>
            </div>
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="# 翻译要求" required prop="requirements_content" width="100%">
            <div class="prompt-section">
              <el-input
                v-model="localForm.requirements_content"
                type="textarea"
                :rows="4"
                resize="none"
                placeholder="请输入翻译的具体要求"
                maxlength="500"
                show-word-limit
              />
              <div class="example-text">
                示例：<br/>
                1. **忠实原文**：严格按照原文的含义和法律意图进行翻译,不得添加或删减信息。<br/>
                2. **术语精准**：使用英美法系(Common law) 通用的标准法律术语。<br/>
                3. **语气正式**：保持法律文件固有的严谨、客观和正式的语体。<br/>
                4. **语句清晰**：译文必须清晰、无歧义,符合英文法律文书的表达习惯。<br/>
                5. **格式保留**：保持原文的段落、编号和基本格式。
              </div>
            </div>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <div class="btn_box">
      <el-button :disabled="loading" @click="close">取消</el-button>
      <el-button
        type="primary"
        color="#055CF9"
        :disabled="loading"
        :loading="loading"
        @click="confirm"
      >
        保存
      </el-button>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  loading: Boolean
})

const rules = {
  title: [{ required: true, message: '请填写提示语标题', trigger: ['blur', 'change'] }],
  role_content: [{ required: true, message: '请填写角色内容', trigger: ['blur', 'change'] }],
  task_content: [{ required: true, message: '请填写任务内容', trigger: ['blur', 'change'] }],
  requirements_content: [{ required: true, message: '请填写翻译要求', trigger: ['blur', 'change'] }]
}

const emit = defineEmits(['confirm', 'close'])

const promptformRef = ref(null)
const visible = ref(false) // 子组件内部控制显示隐藏

// 深拷贝 使用 localForm 管理表单数据
const localForm = ref({
  title: '', //标题
  share_flag: 'N',
  role_content: '', // 角色内容
  task_content: '', // 任务内容
  requirements_content: '', // 翻译要求内容
  content: '' // 拼接后的完整内容（后端自动生成）
})

const open = () => {
  visible.value = true
}
// 关闭弹窗
const close = () => {
  visible.value = false // 隐藏弹窗
}

// 确认保存
const confirm = () => {
  promptformRef.value.validate((valid) => {
    if (valid) {
      emit('confirm', localForm.value) // 将 localForm 传递给父组件
      close()
    }
  })
}
// 更新form
const updateForm = (newForm) => {
  localForm.value = newForm
}
// 暴露方法
defineExpose({
  open,
  close,
  updateForm,
  localForm
})
</script>

<style scoped lang="scss">
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
      margin-bottom: 20px;
      .el-form-item__label {
        justify-content: flex-start;
        color: #111111;
        font-weight: 500;
        margin-bottom: 8px;
      }
      .el-input-number .el-input__inner {
        text-align: left;
      }
      .el-input, .el-textarea {
        width: 100%;
        .el-input__inner, .el-textarea__inner {
          width: 100%;
          border-radius: 6px;
          border: 1px solid #dcdfe6;
          transition: border-color 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
          &:focus {
            border-color: #055cf9;
            outline: none;
          }
        }
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
    
    // 新增的提示语结构化样式
    .prompt-section {
      .section-title {
        font-size: 16px;
        font-weight: bold;
        color: #111;
        margin-bottom: 8px;
        padding: 8px 12px;
        background: #f5f7fa;
        border-radius: 4px;
        border-left: 4px solid #055cf9;
      }
      
      .example-text {
        font-size: 12px;
        color: #666;
        margin-top: 8px;
        padding: 8px 12px;
        background: #fafbfc;
        border-radius: 4px;
        border: 1px solid #e4e7ed;
        line-height: 1.5;
      }
    }
  }
}
</style>
