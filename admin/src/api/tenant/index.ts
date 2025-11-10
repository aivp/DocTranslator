import { request } from "@/utils/service"
import type * as Tenant from "./types/tenant"

/** 获取租户列表 */
export function getTenantListApi(params: Tenant.GetTenantRequestData) {
  return request<Tenant.GetTenantResponseData>({
    url: "tenants",
    method: "get",
    params
  })
}

/** 获取租户详情 */
export function getTenantDetailApi(id: number) {
  return request<Tenant.TenantData>({
    url: `tenant/${id}`,
    method: "get"
  })
}

/** 创建租户 */
export function createTenantApi(data: Tenant.CreateTenantRequestData) {
  return request({
    url: "tenant",
    method: "post",
    data
  })
}

/** 更新租户 */
export function updateTenantApi(id: number, data: Tenant.UpdateTenantRequestData) {
  return request({
    url: `tenant/${id}`,
    method: "put",
    data
  })
}

/** 删除租户 */
export function deleteTenantApi(id: number) {
  return request({
    url: `tenant/${id}`,
    method: "delete"
  })
}

/** 分配用户到租户 */
export function assignCustomerToTenantApi(data: Tenant.AssignCustomerRequestData) {
  return request({
    url: "tenant/assign-customer",
    method: "post",
    data
  })
}

/** 分配管理员到租户 */
export function assignUserToTenantApi(data: Tenant.AssignUserRequestData) {
  return request({
    url: "tenant/assign-user",
    method: "post",
    data
  })
}

/** 获取租户存储配额使用情况 */
export function getTenantStorageQuotaApi(id: number) {
  return request<Tenant.GetTenantStorageQuotaResponseData>({
    url: `tenant/${id}/storage-quota`,
    method: "get"
  })
}
