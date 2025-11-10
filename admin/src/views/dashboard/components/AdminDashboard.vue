<template>
  <div class="dashboard-container">
    <!-- 统计卡片区域 -->
    <el-row :gutter="20" class="statistics-row">
      <el-col :xs="24" :sm="12" :md="6" v-for="(item, index) in statistics" :key="index">
        <div class="statistics-card" :class="`card-${index}`">
          <div class="card-icon">
            <el-icon :size="40">
              <component :is="item.icon" />
            </el-icon>
          </div>
          <div class="card-content">
            <div class="card-value">{{ item.value }}</div>
            <div class="card-label">{{ item.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :xs="24" :md="14">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>翻译量趋势（最近7天）</span>
            </div>
          </template>
          <div class="chart-container" ref="trendChartRef"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="10">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>任务状态分布</span>
            </div>
          </template>
          <div class="chart-container" ref="statusChartRef"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据区域 -->
    <el-row :gutter="20" class="data-row">
      <el-col :xs="24" :md="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近任务</span>
              <el-button type="primary" link @click="handleViewAll">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentTasks" stripe :default-sort="{prop: 'created_at', order: 'descending'}">
            <el-table-column type="index" label="序号" width="80" :index="(index) => index + 1" />
            <el-table-column prop="origin_filename" label="文件名" width="280" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" sortable>
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统状态</span>
            </div>
          </template>
          <div class="status-list">
            <div class="status-item">
              <span class="status-label">队列任务:</span>
              <span class="status-value">{{ systemStatus.queue_count }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">CPU使用率:</span>
              <div class="progress-info">
                <span class="progress-text">{{ systemStatus.server_info.cpu_percent }}%</span>
                <el-progress 
                  :percentage="systemStatus.server_info.cpu_percent" 
                  :status="getCpuStatus(systemStatus.server_info.cpu_percent)"
                  :stroke-width="8"
                />
              </div>
            </div>
            <div class="status-item">
              <span class="status-label">内存使用:</span>
              <div class="progress-info">
                <span class="progress-text">
                  {{ formatStorage(systemStatus.server_info.memory_used) }} / {{ formatStorage(systemStatus.server_info.memory_total) }}
                  ({{ systemStatus.server_info.memory_percent }}%)
                </span>
                <el-progress 
                  :percentage="systemStatus.server_info.memory_percent" 
                  :status="getMemoryStatus(systemStatus.server_info.memory_percent)"
                  :stroke-width="8"
                />
              </div>
            </div>
            <div class="status-item">
              <span class="status-label">系统磁盘:</span>
              <div class="progress-info">
                <span class="progress-text">
                  {{ formatStorage(systemStatus.server_info.disk_used) }} / {{ formatStorage(systemStatus.server_info.disk_total) }}
                  ({{ systemStatus.server_info.disk_percent }}%)
                </span>
                <el-progress 
                  :percentage="systemStatus.server_info.disk_percent" 
                  :status="getDiskStatus(systemStatus.server_info.disk_percent)"
                  :stroke-width="8"
                />
              </div>
            </div>
            <div class="status-item">
              <span class="status-label">运行时间:</span>
              <span class="status-value">{{ systemStatus.server_info.uptime }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">用户存储:</span>
              <div class="storage-info">
                <div class="storage-text">
                  {{ formatStorage(systemStatus.user_storage.used) }} / {{ formatStorage(systemStatus.user_storage.total) }}
                </div>
                <el-progress 
                  :percentage="systemStatus.user_storage.percentage" 
                  :status="getDiskStatus(systemStatus.user_storage.percentage)"
                  :stroke-width="8"
                />
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  Document,
  CircleCheck,
  User,
  DataLine
} from '@element-plus/icons-vue'
import {
  getDashboardStatisticsApi,
  getDashboardTrendApi,
  getDashboardStatusDistributionApi,
  getDashboardRecentTasksApi,
  getDashboardSystemStatusApi
} from '@/api/dashboard'
import { formatDateTime } from '@/utils'

const router = useRouter()

// 统计卡片数据
const statistics = ref([
  { label: '今日任务', value: 0, icon: Document },
  { label: '成功率', value: '0%', icon: CircleCheck },
  { label: '活跃用户', value: 0, icon: User },
  { label: '存储使用', value: '0%', icon: DataLine }
])

// 图表引用
const trendChartRef = ref<HTMLElement>()
const statusChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null
let statusChart: echarts.ECharts | null = null

// 数据
const trendData = ref<{ dates: string[], counts: number[] }>({ dates: [], counts: [] })
const distributionData = ref<{ done: number, process: number, failed: number, queued: number, none: number }>({ done: 0, process: 0, failed: 0, queued: 0, none: 0 })
const recentTasks = ref<any[]>([])
const systemStatus = ref({
  queue_count: 0,
  server_info: {
    cpu_percent: 0,
    memory_percent: 0,
    memory_total: 0,
    memory_used: 0,
    disk_percent: 0,
    disk_total: 0,
    disk_used: 0,
    uptime: '未知'
  },
  user_storage: {
    percentage: 0,
    used: 0,
    total: 0
  }
})

// 定时器
let timer1: ReturnType<typeof setInterval> | null = null
let timer2: ReturnType<typeof setInterval> | null = null

// 加载统计数据
const loadStatistics = async () => {
  try {
    const res = await getDashboardStatisticsApi()
    if (res.code === 200) {
      statistics.value[0].value = res.data.today_tasks
      statistics.value[1].value = `${res.data.success_rate}%`
      statistics.value[2].value = res.data.active_users
      statistics.value[3].value = `${res.data.storage_usage}%`
    }
  } catch (e) {
    console.error('获取统计数据失败:', e)
  }
}

// 加载趋势数据
const loadTrend = async () => {
  try {
    const res = await getDashboardTrendApi({ days: 7 })
    if (res.code === 200) {
      trendData.value = res.data
      initTrendChart()
    }
  } catch (e) {
    console.error('获取趋势数据失败:', e)
  }
}

// 加载状态分布
const loadStatusDistribution = async () => {
  try {
    const res = await getDashboardStatusDistributionApi()
    if (res.code === 200) {
      distributionData.value = res.data
      initStatusChart()
    }
  } catch (e) {
    console.error('获取状态分布失败:', e)
  }
}

// 加载最近任务
const loadRecentTasks = async () => {
  try {
    const res = await getDashboardRecentTasksApi({ limit: 10 })
    if (res.code === 200) {
      recentTasks.value = res.data.tasks
    }
  } catch (e) {
    console.error('获取最近任务失败:', e)
  }
}

// 加载系统状态
const loadSystemStatus = async () => {
  try {
    const res = await getDashboardSystemStatusApi()
    if (res.code === 200) {
      systemStatus.value = res.data
    }
  } catch (e) {
    console.error('获取系统状态失败:', e)
  }
}

// 初始化趋势图
const initTrendChart = () => {
  if (!trendChartRef.value) return
  
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trendData.value.dates
    },
    yAxis: {
      type: 'value'
    },
    series: [{
      name: '任务数',
      type: 'line',
      smooth: true,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
          ]
        }
      },
      itemStyle: {
        color: '#409EFF'
      },
      data: trendData.value.counts
    }]
  }
  
  trendChart.setOption(option)
}

// 初始化状态饼图
const initStatusChart = () => {
  if (!statusChartRef.value) return
  
  if (!statusChart) {
    statusChart = echarts.init(statusChartRef.value)
  }
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [{
      name: '任务状态',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        formatter: '{b}: {c}'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold'
        }
      },
      data: [
        { value: distributionData.value.done, name: '已完成', itemStyle: { color: '#67C23A' } },
        { value: distributionData.value.process, name: '处理中', itemStyle: { color: '#409EFF' } },
        { value: distributionData.value.failed, name: '失败', itemStyle: { color: '#F56C6C' } },
        { value: distributionData.value.queued, name: '排队中', itemStyle: { color: '#E6A23C' } },
        { value: distributionData.value.none, name: '待处理', itemStyle: { color: '#909399' } }
      ]
    }]
  }
  
  statusChart.setOption(option)
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'done': '已完成',
    'process': '处理中',
    'failed': '失败',
    'queued': '排队中',
    'none': '待处理'
  }
  return statusMap[status] || status
}

// 获取状态类型
const getStatusType = (status: string): 'success' | 'warning' | 'info' | 'primary' | 'danger' => {
  const typeMap: Record<string, 'success' | 'warning' | 'info' | 'primary' | 'danger'> = {
    'done': 'success',
    'process': 'primary',
    'failed': 'danger',
    'queued': 'warning',
    'none': 'info'
  }
  return typeMap[status] || 'info'
}

// 获取磁盘状态
const getDiskStatus = (usage: number) => {
  if (usage >= 90) return 'exception'
  if (usage >= 80) return 'warning'
  return 'success'
}

// 获取CPU状态
const getCpuStatus = (usage: number) => {
  if (usage >= 90) return 'exception'
  if (usage >= 70) return 'warning'
  return 'success'
}

// 获取内存状态
const getMemoryStatus = (usage: number) => {
  if (usage >= 90) return 'exception'
  if (usage >= 80) return 'warning'
  return 'success'
}

// 格式化存储大小
const formatStorage = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

// 查看全部任务
const handleViewAll = () => {
  router.push('/translate')
}

// 窗口resize处理
const handleResize = () => {
  trendChart?.resize()
  statusChart?.resize()
}

onMounted(() => {
  // 加载初始数据
  loadStatistics()
  loadTrend()
  loadStatusDistribution()
  loadRecentTasks()
  loadSystemStatus()
  
  // 设置定时刷新
  timer1 = setInterval(() => {
    loadStatistics()
    loadRecentTasks()
    loadSystemStatus()
  }, 30000) // 30秒刷新一次
  
  timer2 = setInterval(() => {
    loadTrend()
    loadStatusDistribution()
  }, 300000) // 5分钟刷新一次
  
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (timer1) clearInterval(timer1)
  if (timer2) clearInterval(timer2)
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  statusChart?.dispose()
})
</script>

<style lang="scss" scoped>
.dashboard-container {
  padding: 20px;
  
  .statistics-row {
    margin-bottom: 20px;
    
    .statistics-card {
      height: 120px;
      border-radius: 8px;
      padding: 20px;
      display: flex;
      align-items: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
      transition: transform 0.3s;
      
      &:hover {
        transform: translateY(-5px);
      }
      
      &.card-0 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      }
      
      &.card-1 {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      }
      
      &.card-2 {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      }
      
      &.card-3 {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
      }
      
      .card-icon {
        margin-right: 20px;
        
        :deep(svg) {
          width: 50px;
          height: 50px;
        }
      }
      
      .card-content {
        flex: 1;
        
        .card-value {
          font-size: 32px;
          font-weight: bold;
          margin-bottom: 8px;
        }
        
        .card-label {
          font-size: 14px;
          opacity: 0.9;
        }
      }
    }
  }
  
  .chart-row {
    margin-bottom: 20px;
    
    .chart-card {
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: bold;
      }
      
      .chart-container {
        height: 300px;
        width: 100%;
      }
    }
  }
  
  .data-row {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: bold;
    }
    
    .status-list {
      .status-item {
        margin-bottom: 20px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .status-label {
          font-weight: 500;
          margin-bottom: 8px;
          display: block;
        }
        
        .status-value {
          font-size: 18px;
          font-weight: bold;
          color: #409EFF;
        }
        
        .storage-info,
        .progress-info {
          width: 100%;
          
          .storage-text,
          .progress-text {
            font-size: 13px;
            color: #606266;
            margin-bottom: 6px;
            display: block;
          }
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 10px;
    
    .statistics-row .statistics-card {
      margin-bottom: 10px;
    }
    
    .chart-row .chart-card .chart-container {
      height: 250px;
    }
  }
}
</style>

