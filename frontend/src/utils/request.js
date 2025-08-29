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
  transformRequest: [function(data) {
    if (data instanceof FormData) {
      return data
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
    config.headers['Authorization'] = 'Bearer ' + userStore.token;
    config.headers['credentials']='include'
    config.headers['withCredentials']=true  // 携带凭据（如 Cookies）
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
    const res = response.data
    
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
      // 如果数据部分不包含业务状态码，构造一个标准响应
      return {
        code: 200,
        message: '操作成功',
        data: data
      }
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
          ElMessage.error('用户状态异常或权限不足!')
          break
        default:
          ElMessage.error('请求失败')
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

