import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { useUserStoreHook } from '@/store/modules/user'
import { ElMessage } from 'element-plus'
import { get, merge } from 'lodash-es'
import { getToken } from './cache/cookies'

/** 退出登录并跳转到登录页 */
function logout() {
  // 先清除 token 和用户信息
  useUserStoreHook().logout()
  // 使用 window.location.href 强制跳转，确保页面刷新并触发路由守卫
  // 这样可以避免路由守卫的缓存问题
  window.location.href = '/login'
}

/** 创建请求实例 */
function createService() {
  // 创建一个 axios 实例命名为 service
  const service = axios.create({
    timeout: 10000,
    baseURL: '/api',
  })
  // 请求拦截
  service.interceptors.request.use(
    (config) => config,
    // 发送失败
    (error) => Promise.reject(error)
  )
  // 响应拦截（可根据具体业务作出相应的调整）
  service.interceptors.response.use(
    (response) => {
      // apiData 是 api 返回的数据
      const apiData = response.data
      // 二进制数据则直接返回
      const responseType = response.request?.responseType
      if (responseType === 'blob' || responseType === 'arraybuffer') return apiData
      // 这个 code 是和后端约定的业务 code
      const code = apiData.code
      // 如果没有 code, 代表这不是项目后端开发的 api
      if (code === undefined) {
        ElMessage.error('非本系统的接口')
        return Promise.reject(new Error('非本系统的接口'))
      }
      switch (code) {
        case 200:
          // 本系统采用 code === 0 来表示没有业务错误
          return apiData
        case 401:
          // Token 过期时
          ElMessage.error('身份过期，请重新登录')
          logout()
          return Promise.reject(new Error('Unauthorized'))
        default:
          // 不是正确的 code，直接返回错误数据，由全局错误处理
          return Promise.reject({
            ...apiData,
            isHandled: true  // 标记为已处理
          })
      }
    },
    (error) => {
      // status 是 HTTP 状态码
      const status = get(error, 'response.status')
      
      // 检查是否已经由响应拦截器处理过
      if (error.isHandled) {
        // 业务错误，显示错误信息
        ElMessage.error(error.message || 'Error')
        return Promise.reject(error)
      }
      
      switch (status) {
        case 400:
          // 优先显示后端返回的具体错误信息
          const backendMessage = get(error, 'response.data.message')
          error.message = backendMessage || '请求错误'
          break
        case 401:
          // Token 过期时
          ElMessage.error('身份过期，请重新登录')
          logout()
          break
        case 403:
          // 优先显示后端返回的具体错误信息
          const backendMessage403 = get(error, 'response.data.message')
          error.message = backendMessage403 || '拒绝访问'
          break
        case 404:
          error.message = '请求地址出错'
          break
        case 408:
          error.message = '请求超时'
          break
        case 500:
          // 优先显示后端返回的具体错误信息
          const backendMessage500 = get(error, 'response.data.message')
          error.message = backendMessage500 || '服务器内部错误'
          // 特殊处理：如果是 token 被撤销导致的 500 错误，跳转到登录页
          const errorMessage = (backendMessage500 || '').toLowerCase()
          const isTokenRevoked = errorMessage.includes('revoked') || 
                                errorMessage.includes('token') && errorMessage.includes('revoked') ||
                                errorMessage.includes('账号已在其他设备登录') ||
                                errorMessage.includes('已在其他设备登录')
          if (isTokenRevoked) {
            ElMessage.error('账号已在其他设备登录，请重新登录')
            logout()
            return Promise.reject(error)
          }
          break
        case 501:
          error.message = '服务未实现'
          break
        case 502:
          error.message = '网关错误'
          break
        case 503:
          error.message = '服务不可用'
          break
        case 504:
          error.message = '网关超时'
          break
        case 505:
          error.message = 'HTTP 版本不受支持'
          break
        default:
          break
      }
      ElMessage.error(error.message)
      return Promise.reject(error)
    }
  )
  return service
}
const globalApi = window.ipConfig
console.log(globalApi)
/** 创建请求方法 */
function createRequest(service: AxiosInstance) {
  return function <T>(config: AxiosRequestConfig): Promise<T> {
    const token = getToken()
    const defaultConfig = {
      headers: {
        // 携带 Token - 使用标准的Bearer格式
        Authorization: token ? `Bearer ${token}` : undefined,
        'Content-Type': 'application/json',
      },
      timeout: 10000,
      //本地开发环境开发，接口配置修改.env.development 正式环境读取动态变量
      baseURL: '/api/admin',
      // baseURL: (import.meta.env.MODE != "production" ? import.meta.env.VITE_BASE_API : globalApi) + "/api/admin",
      data: {},
    }
    // 将默认配置 defaultConfig 和传入的自定义配置 config 进行合并成为 mergeConfig
    const mergeConfig = merge(defaultConfig, config)
    return service(mergeConfig)
  }
}


/** 用于网络请求的实例 */
const service = createService()
/** 用于网络请求的方法 */
export const request = createRequest(service)
