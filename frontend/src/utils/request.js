import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/store/user'
import Qs from 'qs'
// import router from '@/router'
// import i18n from '@/lang/index' // i18n 国际化

// create an axios instance
const service = axios.create({
  baseURL: '/api', //  import.meta.env.VITE_API_URL   url = base url + request url
  withCredentials: true, // send cookies when cross-domain requests
  crossDomain: true,
  timeout: 30000, // request timeout
  transformRequest: [function(data, headers) {
    if (data instanceof FormData) {
      return data
    } else if (headers['Content-Type'] === 'application/json' || headers['content-type'] === 'application/json') {
      // JSON请求不进行转换
      return JSON.stringify(data)
    } else {
      data = Qs.stringify(data, { arrayFormat: 'indices' })
      return data
    }
  }],
  paramsSerializer: (params) => {
    for (const param in params) {
      if (params[param] === '' || params[param] == null) {
        delete params[param]
      }
    }
    return Qs.stringify(params)
  }
})

// request interceptor
service.interceptors.request.use(
  config => {
    const userStore = useUserStore()
    console.log('请求token:', userStore.token) // 添加调试信息
    config.headers['Authorization'] = 'Bearer ' + userStore.token;
    config.headers['credentials']='include'
    config.headers['withCredentials']=true  // 携带凭据（如 Cookies）
    
    // 设置Content-Type
    if (config.data && !(config.data instanceof FormData)) {
      // 如果已经指定了Content-Type，使用指定的值
      // 否则默认为application/x-www-form-urlencoded
      if (!config.headers['Content-Type'] && !config.headers['content-type']) {
        config.headers['Content-Type'] = 'application/x-www-form-urlencoded'
      }
    }
    
      // config.headers['language'] = localStorage.getItem('language')||'zh';
      return config
  },
  error => {
    // do something with request error
    console.log(error) // for debug
    return Promise.reject(error)
  }
)

// response interceptor
service.interceptors.response.use(
  response => {
    // 如果是 blob 响应（文件下载），直接返回
    if (response.config.responseType === 'blob' || response.data instanceof Blob) {
      // 检查是否是错误响应（错误响应可能是 JSON 格式的 blob）
      if (response.data.type && response.data.type.includes('application/json')) {
        // 错误响应，需要解析
        return response.data.text().then(text => {
          try {
            const errorData = JSON.parse(text)
            if (errorData.code === 401) {
              ElMessage.error('身份过期，请重新登录')
              router.push('/login')
              return Promise.reject(new Error('Unauthorized'))
            }
            ElMessage.error(errorData.message || '下载失败')
            return Promise.reject(new Error(errorData.message || '下载失败'))
          } catch (e) {
            ElMessage.error('下载失败')
            return Promise.reject(new Error('下载失败'))
          }
        })
      }
      // 正常的文件响应，直接返回 blob
      return response.data
    }
    
    const res = response.data
    console.log('API响应数据:', res) // 添加调试信息
    
    // 检查业务状态码 - 后端返回的是元组格式 (data, code)
    // 如果 res 是数组且第二个元素是状态码，说明是元组格式
    if (Array.isArray(res) && res.length === 2) {
      const [data, statusCode] = res
      // 检查 HTTP 状态码
      if (statusCode === 401) {
        ElMessage.error('身份过期，请重新登录')
        router.push('/login')
        return Promise.reject(new Error('Unauthorized'))
      }
      // 返回数据部分，但保持原有的业务状态码结构
      if (data && typeof data === 'object' && 'code' in data) {
        return data // 如果数据部分包含业务状态码，直接返回
      }
      // 如果数据部分不包含业务状态码，直接返回数据
      return data
    }
    
    // 如果不是元组格式，按原来的逻辑处理
    if (res?.code === 401) {
      ElMessage.error('身份过期，请重新登录')
      router.push('/login')
      return Promise.reject(new Error('Unauthorized'))
    }
    return res
  },
  error => {
    const { response } = error
    if (response) {
      // 尝试从响应中获取具体的错误信息
      let errorMessage = '请求失败'
      
      if (response.data && response.data.message) {
        errorMessage = response.data.message
      } else if (response.data && response.data.error) {
        errorMessage = response.data.error
      }
      
      switch (response.status) {
        case 401:
          ElMessage.error('身份过期，请重新登录')
          router.push('/login')
          break
        case 422:
          ElMessage.error('身份过期，请重新登录')
          router.push('/login')
          break  
        case 403:
          // 优先显示后端返回的具体错误信息
          ElMessage.error(errorMessage || '用户状态异常或权限不足')
          break
        case 400:
          // 优先显示后端返回的具体错误信息
          ElMessage.error(errorMessage || '请求错误')
          break
        case 500:
          ElMessage.error(errorMessage)
          break
        default:
          ElMessage.error(errorMessage)
      }
    } else {
      ElMessage.error('网络连接异常')
    }
    return Promise.reject(error)
  }
)
// service.interceptors.response.use(
//   response => {

//     const res = response.data
  
//       return res
//   },
//   error => {
//     const { response } = error
//      if (response.code == 401) {
//       console.log(401);
//       router.push('/login')
// }
//     console.log('err' + error)
//     ElMessageBox({
//       message: error.message,
//       type: 'error',
//       duration: 5 * 1000
//     })
//     return Promise.reject(error)
//   }
// )

export default service

