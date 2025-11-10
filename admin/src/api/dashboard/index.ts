import { request } from "@/utils/service"
import type {
  GetStatisticsResponseData,
  GetTrendRequestData,
  GetTrendResponseData,
  GetStatusDistributionResponseData,
  GetRecentTasksRequestData,
  GetRecentTasksResponseData,
  GetSystemStatusResponseData
} from "./types/dashboard"

/** 获取统计数据 */
export function getDashboardStatisticsApi() {
  return request<GetStatisticsResponseData>({
    url: `dashboard/statistics`,
    method: "get"
  })
}

/** 获取趋势数据 */
export function getDashboardTrendApi(params: GetTrendRequestData) {
  return request<GetTrendResponseData>({
    url: `dashboard/trend`,
    method: "get",
    params
  })
}

/** 获取状态分布 */
export function getDashboardStatusDistributionApi() {
  return request<GetStatusDistributionResponseData>({
    url: `dashboard/status-distribution`,
    method: "get"
  })
}

/** 获取最近任务 */
export function getDashboardRecentTasksApi(params: GetRecentTasksRequestData) {
  return request<GetRecentTasksResponseData>({
    url: `dashboard/recent-tasks`,
    method: "get",
    params
  })
}

/** 获取系统状态 */
export function getDashboardSystemStatusApi() {
  return request<GetSystemStatusResponseData>({
    url: `dashboard/system-status`,
    method: "get"
  })
}

