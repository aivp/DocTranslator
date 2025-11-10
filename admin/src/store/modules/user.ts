import { ref } from "vue"
import store from "@/store"
import { defineStore } from "pinia"
import { useTagsViewStore } from "./tags-view"
import { useSettingsStore } from "./settings"
import { getToken, removeToken, setToken, getIsSuperAdmin, setIsSuperAdmin, removeIsSuperAdmin, getTenantId, setTenantId, removeTenantId } from "@/utils/cache/cookies"
import { resetRouter } from "@/router"
import { loginApi, getUserInfoApi } from "@/api/login"
import { type LoginRequestData } from "@/api/login/types/login"
import routeSettings from "@/config/route"

export const useUserStore = defineStore("user", () => {
  const token = ref<string>(getToken() || "")
  const roles = ref<string[]>([])
  const email = ref<string>("")
  const isSuperAdmin = ref<boolean>(getIsSuperAdmin())
  const tenantId = ref<number | null>(getTenantId())

  const tagsViewStore = useTagsViewStore()
  const settingsStore = useSettingsStore()

  /** 登录 */
  const login = async (loginData: LoginRequestData) => {
    const { data } = await loginApi(loginData)
    setToken(data.token)
    token.value = data.token
    email.value = data.email
    isSuperAdmin.value = data.is_super_admin || false
    tenantId.value = data.tenant_id || null
    // 持久化保存
    setIsSuperAdmin(isSuperAdmin.value)
    setTenantId(tenantId.value)
  }
  /** 获取用户详情 */
  const getInfo = async () => {
    const { data } = await getUserInfoApi()
    // username.value = data.username
    // 验证返回的 roles 是否为一个非空数组，否则塞入一个没有任何作用的默认角色，防止路由守卫逻辑进入无限循环
    roles.value = data.roles?.length > 0 ? data.roles : routeSettings.defaultRoles
  }
  /** 模拟角色变化 */
  const changeRoles = async (role: string) => {
    const newToken = "token-" + role
    token.value = newToken
    setToken(newToken)
    // 用刷新页面代替重新登录
    window.location.reload()
  }
  /** 登出 */
  const logout = () => {
    removeToken()
    removeIsSuperAdmin()
    removeTenantId()
    token.value = ""
    roles.value = []
    email.value = ""
    isSuperAdmin.value = false
    tenantId.value = null
    resetRouter()
    _resetTagsView()
  }
  /** 重置 Token */
  const resetToken = () => {
    removeToken()
    removeIsSuperAdmin()
    removeTenantId()
    token.value = ""
    roles.value = []
    email.value = ""
    isSuperAdmin.value = false
    tenantId.value = null
  }
  /** 重置 Visited Views 和 Cached Views */
  const _resetTagsView = () => {
    if (!settingsStore.cacheTagsView) {
      tagsViewStore.delAllVisitedViews()
      tagsViewStore.delAllCachedViews()
    }
  }

  return { token, roles, email, isSuperAdmin, tenantId, login, getInfo, changeRoles, logout, resetToken }
})

/** 在 setup 外使用 */
export function useUserStoreHook() {
  return useUserStore(store)
}
