<template>
  <div class="page-center">
    <div class="container">
      <!-- 页面标题 -->
      <div class="page-header">
        <h2>实用工具</h2>
        <p class="subtitle">提供多种实用工具，帮助您更高效地完成工作</p>
      </div>

      <!-- 工具卡片列表 -->
      <div class="tools-grid">
        <!-- 图片翻译工具 -->
        <div class="tool-card">
          <div class="tool-icon">
            <el-icon :size="48" color="#409EFF">
              <Picture />
            </el-icon>
          </div>
          <div class="tool-content">
            <h3>图片翻译</h3>
            <p>使用 Qwen-MT-Image 模型，快速识别并翻译图片中的文字</p>
            <div class="tool-tags">
              <el-tag size="small" type="primary">AI翻译</el-tag>
              <el-tag size="small">图片识别</el-tag>
            </div>
            <div class="tool-actions">
              <el-button type="primary" size="small" @click.stop="openImageTranslate">新建翻译</el-button>
              <el-button size="small" @click.stop="openImageTranslateList">查看任务</el-button>
            </div>
          </div>
          <div class="tool-arrow">
            <el-icon :size="20"><ArrowRight /></el-icon>
          </div>
        </div>

        <!-- PDF转图片工具 -->
        <div class="tool-card">
          <div class="tool-icon">
            <el-icon :size="48" color="#67C23A">
              <Document />
            </el-icon>
          </div>
          <div class="tool-content">
            <h3>PDF转图片</h3>
            <p>将PDF文档的每一页转换为图片，支持PNG、JPG、WEBP等多种格式</p>
            <div class="tool-tags">
              <el-tag size="small" type="success">格式转换</el-tag>
              <el-tag size="small">批量处理</el-tag>
            </div>
            <div class="tool-actions">
              <el-button type="primary" size="small" @click.stop="openPdfToImage">开始转换</el-button>
            </div>
          </div>
          <div class="tool-arrow">
            <el-icon :size="20"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Picture, ArrowRight, Document } from '@element-plus/icons-vue'

const router = useRouter()

function openImageTranslate() {
  router.push('/tools/image-translate')
}

function openImageTranslateList() {
  router.push('/tools/image-translate/list')
}

function openPdfToImage() {
  router.push('/tools/pdf-to-image')
}
</script>

<style scoped lang="scss">
.page-center {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 40px;
}

.container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-header {
  margin-top: 30px;
  margin-bottom: 40px;
  text-align: center;

  h2 {
    font-size: 32px;
    font-weight: bold;
    color: #111111;
    margin-bottom: 12px;
  }

  .subtitle {
    font-size: 16px;
    color: #666666;
  }
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  margin-top: 30px;

  @media screen and (max-width: 768px) {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.tool-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 28px;
  box-shadow: 0px 4px 12px 0px rgba(228, 238, 253, 0.5);
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  position: relative;
  min-height: 200px;

  &:hover {
    box-shadow: 0px 8px 24px 0px rgba(228, 238, 253, 0.8);
    transform: translateY(-4px);
  }

  &.coming-soon {
    opacity: 0.6;
    cursor: not-allowed;

    &:hover {
      transform: none;
    }
  }

  .tool-icon {
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 80px;
    height: 80px;
    background: #f0f7ff;
    border-radius: 12px;
  }

  .tool-content {
    flex: 1;

    h3 {
      font-size: 20px;
      font-weight: bold;
      color: #111111;
      margin-bottom: 12px;
    }

    p {
      font-size: 14px;
      color: #666666;
      line-height: 1.6;
      margin-bottom: 16px;
    }

    .tool-tags {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }

    .tool-actions {
      display: flex;
      gap: 8px;
      margin-top: auto;
    }
  }

  .tool-arrow {
    position: absolute;
    top: 28px;
    right: 28px;
    color: #999999;
    transition: all 0.3s ease;
  }

  &:hover .tool-arrow {
    color: #409EFF;
    transform: translateX(4px);
  }
}

@media screen and (max-width: 767px) {
  .page-header {
    h2 {
      font-size: 24px;
    }

    .subtitle {
      font-size: 14px;
    }
  }

  .tool-card {
    padding: 20px;
    min-height: 180px;

    .tool-icon {
      width: 60px;
      height: 60px;
      margin-bottom: 16px;
    }

    .tool-content {
      h3 {
        font-size: 18px;
      }

      p {
        font-size: 13px;
      }
    }
  }
}
</style>

