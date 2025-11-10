/** 统计响应数据 */
export interface GetStatisticsResponseData {
  code: number
  data: {
    today_tasks: number
    success_rate: number
    active_users: number
    storage_usage: number
  }
  message: string
}

/** 趋势请求数据 */
export interface GetTrendRequestData {
  days?: number
}

/** 趋势响应数据 */
export interface GetTrendResponseData {
  code: number
  data: {
    dates: string[]
    counts: number[]
  }
  message: string
}

/** 状态分布响应数据 */
export interface GetStatusDistributionResponseData {
  code: number
  data: {
    done: number
    process: number
    failed: number
    queued: number
    none: number
  }
  message: string
}

/** 最近任务请求数据 */
export interface GetRecentTasksRequestData {
  limit?: number
}

/** 最近任务响应数据 */
export interface GetRecentTasksResponseData {
  code: number
  data: {
    tasks: Array<{
      id: number
      translate_no: string
      origin_filename: string
      status: string
      created_at: string
      customer_id: number
    }>
  }
  message: string
}

  /** 系统状态响应数据 */
  export interface GetSystemStatusResponseData {
    code: number
    data: {
      queue_count: number
      server_info: {
        cpu_percent: number
        memory_percent: number
        memory_total: number
        memory_used: number
        disk_percent: number
        disk_total: number
        disk_used: number
        uptime: string
      }
      user_storage: {
        percentage: number
        used: number
        total: number
      }
    }
    message: string
  }

