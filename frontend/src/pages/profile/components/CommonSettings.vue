<template>
  <!-- 通用设置已隐藏，不允许用户在此设置 -->
  <div class="hidden-settings-notice">
    <el-alert
      title="通用设置"
      type="info"
      description="通用设置已由系统管理员统一配置，用户无需手动设置。"
      show-icon
      :closable="false"
    />
  </div>
</template>

<script setup>
// 通用设置已隐藏，不需要任何逻辑
</script>

<style scoped>
.el-form-item {
  margin-bottom: 22px;
}
</style>
