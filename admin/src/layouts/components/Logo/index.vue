<script lang="ts" setup>
import { useLayoutMode } from '@/hooks/useLayoutMode'
import logo from '@/assets/layouts/logo.png?url'
import logo_text from '@/assets/layouts/logo-text-2.png?url'
import { useSystemStore } from '@/store/modules/system'

const systemStore = useSystemStore()
const logo_url = systemStore.site_settings?.site_logo

interface Props {
  collapse?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  collapse: true,
})

const { isLeft, isTop } = useLayoutMode()
</script>

<template>
  <div class="layout-logo-container" :class="{ collapse: props.collapse, 'layout-mode-top': isTop }">
    <transition name="layout-logo-fade">
      <router-link v-if="props.collapse" key="collapse" to="/">
        <el-avatar :src="logo_url || logo" class="layout-logo" />
      </router-link>
      <router-link v-else key="expand" to="/" class="expanded-logo">
        <el-avatar :src="logo_url || logo_text" class="layout-logo-text" />
        <span class="logo-title">后台管理</span>
      </router-link>
    </transition>
  </div>
</template>

<style lang="scss" scoped>
.layout-logo-container {
  position: relative;
  width: 100%;
  height: var(--v3-header-height);
  line-height: var(--v3-header-height);
  text-align: center;
  overflow: hidden;
  transition: all 0.3s ease;

  .layout-logo {
    display: none;
    height: 32px;
    transition: all 0.3s ease;
  }

  .layout-logo-text {
    vertical-align: middle;
    width: 40px;
    height: 40px;
    transition: all 0.3s ease;
  }

  // 新增展开状态样式
  .expanded-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    text-decoration: none;
    color: inherit;

    .logo-title {
      margin-left: 10px;
      font-size: 16px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      white-space: nowrap;
      transition: all 0.3s ease;
    }
  }
}

.layout-mode-top {
  height: var(--v3-navigationbar-height);
  line-height: var(--v3-navigationbar-height);
}

.collapse {
  .layout-logo {
    width: 32px;
    height: 32px;
    vertical-align: middle;
    display: inline-block;
  }

  .layout-logo-text,
  .logo-title {
    display: none;
  }
}
</style>
