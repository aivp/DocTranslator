import { request } from "@/utils/service"
import type * as Setting from "./types/setting"


/** 列表 */
export function getApiSettingData(tenantId?: number) {
  const params = tenantId ? { tenant_id: tenantId } : {}
  return request<Setting.GetApiSettingResponseData>({
    url: `setting/api`,
    method: "get",
    params
  })
}

/** 设置 */
export function setApiSettingData(data:Setting.ApiSetting & { tenant_id?: number }) {
  return request<Setting.SettingNoResponseData>({
    url: `setting/api`,
    method: "post",
    data
  })
}

/** 列表 */
export function getOtherSettingData(tenantId?: number) {
  const params = tenantId ? { tenant_id: tenantId } : {}
  return request<Setting.GetOtherSettingResponseData>({
    url: `setting/other`,
    method: "get",
    params
  })
}

/** 设置 */
export function setOtherSettingData(data:Setting.OtherSetting & { tenant_id?: number }) {
  return request<Setting.SettingNoResponseData>({
    url: `setting/other`,
    method: "post",
    data
  })
}

/** 列表 */
export function getSiteSettingData(tenantId?: number) {
  const params = tenantId ? { tenant_id: tenantId } : {}
  return request<Setting.GetSiteSettingResponseData>({
    url: `setting/site`,
    method: "get",
    params
  })
}

/** 设置 */
export function setSiteSettingData(data:Setting.SiteSetting & { tenant_id?: number }) {
  return request<Setting.SettingNoResponseData>({
    url: `setting/site`,
    method: "post",
    data
  })
}

