import router from "@/router"
import { useUserStoreHook } from "@/store/modules/user"
import { usePermissionStoreHook } from "@/store/modules/permission"
import { ElMessage } from "element-plus"
import { setRouteChange } from "@/hooks/useRouteListener"
import { useTitle } from "@/hooks/useTitle"
import { getToken } from "@/utils/cache/cookies"
import routeSettings from "@/config/route"
import isWhiteList from "@/config/white-list"
import NProgress from "nprogress"
import "nprogress/nprogress.css"

const { setTitle } = useTitle()
NProgress.configure({ showSpinner: false })

router.beforeEach(async (to, _from, next) => {
  NProgress.start()
  const userStore = useUserStoreHook()
  const permissionStore = usePermissionStoreHook()
  const token = getToken()
  // 如果没有登陆
  if (!token) {
    // 如果在免登录的白名单中，则直接进入
    if (isWhiteList(to)) return next()
    // 其他没有访问权限的页面将被重定向到登录页面
    return next("/login")
  }

  // 如果已经登录，并准备进入 Login 页面，则重定向到主页
  if (to.path === "/login") {
    return next({ path: "/" })
  }

  // 验证 token 是否有效（防止被其他设备登录顶掉后，刷新页面仍能访问）
  // 如果 roles 不存在（比如刷新页面后），尝试获取用户信息来验证 token
  // 注意：使用 roles 而不是 email，因为 getInfo() 会设置 roles
  // 即使 roles 存在，也需要验证 token（防止被其他设备顶掉）
  // 但是为了避免频繁请求，只在 roles 不存在或路由未设置时验证
  if (token) {
    // 如果 roles 不存在，必须获取用户信息
    // 如果 roles 存在但路由未设置，也需要获取用户信息来设置路由
    const needVerifyToken = userStore.roles.length === 0 || permissionStore.addRoutes.length === 0
    
    if (needVerifyToken) {
      try {
        // 尝试获取用户信息，如果 token 无效会返回 401
        await userStore.getInfo()
        // 如果成功，roles 会被设置
      } catch (error: any) {
        // 处理 401 未授权错误（token 无效或被顶掉）
        const status = error?.response?.status || error?.code
        const isUnauthorized = status === 401
        
        // 特殊处理：如果是 500 错误，检查是否是 token 被撤销导致的
        const isServerError = status === 500
        let isTokenRevoked = false
        if (isServerError) {
          const errorMessage = (error?.response?.data?.message || error?.message || '').toLowerCase()
          isTokenRevoked = errorMessage.includes('revoked') || 
                          (errorMessage.includes('token') && errorMessage.includes('revoked')) ||
                          errorMessage.includes('账号已在其他设备登录') ||
                          errorMessage.includes('已在其他设备登录')
        }
        
        if (isUnauthorized || isTokenRevoked) {
          userStore.resetToken()
          ElMessage.error('账号已在其他设备登录，请重新登录')
          NProgress.done()
          // 使用 window.location 强制跳转，避免路由守卫的缓存问题
          window.location.href = '/login'
          return
        }
        // 其他错误（如 404）不处理，让后续逻辑继续执行
        // 避免因为接口不存在等问题导致无法登录
        console.error('获取用户信息失败:', error)
      }
    }
  }

  // 检查页面是否需要超级管理员权限
  if (to.meta?.requiresSuperAdmin && !userStore.isSuperAdmin) {
    ElMessage.warning("只有超级管理员才能访问此页面")
    NProgress.done()
    return next("/403") // 重定向到403页面
  }

  // 如果用户已经获得其权限角色，且路由已经设置，直接放行
  // 注意：如果 token 被标记为无效，后续的 API 请求会返回 401，响应拦截器会处理跳转
  if (userStore.roles.length !== 0 && permissionStore.addRoutes.length > 0) {
    return next()
  }

  // 如果 roles 存在但路由还没有设置，需要设置路由
  // 或者 roles 不存在，需要重新获取权限角色
  try {
    // 注意：角色必须是一个数组！ 例如: ["admin"] 或 ["developer", "editor"]
    const roles = userStore.roles.length > 0 ? userStore.roles : routeSettings.defaultRoles
    // 生成可访问的 Routes
    routeSettings.dynamic ? permissionStore.setRoutes(roles) : permissionStore.setAllRoutes()
    // 将 "有访问权限的动态路由" 添加到 Router 中
    permissionStore.addRoutes.forEach((route) => router.addRoute(route))
    // 确保添加路由已完成
    // 设置 replace: true, 因此导航将不会留下历史记录
    // next({ ...to, replace: true })
    
    next()
  } catch (err: any) {
    console.log("catch")
    // 过程中发生任何错误，都直接重置 Token，并重定向到登录页面
    userStore.resetToken()
    ElMessage.error(err.message || "路由守卫过程发生错误")
    next("/login")
  }
})

router.afterEach((to) => {
  setRouteChange(to)
  setTitle(to.meta.title)
  NProgress.done()
})
