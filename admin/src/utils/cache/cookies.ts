/** 统一处理 Cookie */

import CacheKey from "@/constants/cache-key"
import Cookies from "js-cookie"

export const getToken = () => {
  return Cookies.get(CacheKey.TOKEN)
}
export const setToken = (token: string) => {
  Cookies.set(CacheKey.TOKEN, token)
}
export const removeToken = () => {
  Cookies.remove(CacheKey.TOKEN)
}

export const getIsSuperAdmin = () => {
  return Cookies.get(CacheKey.IS_SUPER_ADMIN) === 'true'
}
export const setIsSuperAdmin = (value: boolean) => {
  Cookies.set(CacheKey.IS_SUPER_ADMIN, value.toString())
}
export const removeIsSuperAdmin = () => {
  Cookies.remove(CacheKey.IS_SUPER_ADMIN)
}

export const getTenantId = () => {
  const value = Cookies.get(CacheKey.TENANT_ID)
  return value ? parseInt(value) : null
}
export const setTenantId = (value: number | null) => {
  if (value !== null) {
    Cookies.set(CacheKey.TENANT_ID, value.toString())
  } else {
    Cookies.remove(CacheKey.TENANT_ID)
  }
}
export const removeTenantId = () => {
  Cookies.remove(CacheKey.TENANT_ID)
}
