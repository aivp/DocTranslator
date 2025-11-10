export interface GetTenantRequestData {
  /** 当前页码 */
  page?: number
  /** 查询条数 */
  limit?: number
  /** 关键字 */
  keyword?: string
}

export interface TenantData {
  id: number
  tenant_no: string
  tenant_code: string
  name: string
  company_name: string
  contact_person?: string
  status: string
  storage_quota: number
  total_storage: number
  max_users: number
  created_at: string
  updated_at: string
}

export type GetTenantResponseData = ApiResponseData<{
  data: TenantData[]
  total: number
}>

export interface CreateTenantRequestData {
  tenant_code: string
  name: string
  company_name: string
  contact_person?: string
  status?: string
  storage_quota?: number
  max_users?: number
}

export interface UpdateTenantRequestData {
  tenant_code?: string
  name?: string
  company_name?: string
  contact_person?: string
  status?: string
  storage_quota?: number
  max_users?: number
}

export interface AssignCustomerRequestData {
  customer_id: number
  tenant_id: number
}

export interface AssignUserRequestData {
  user_id: number
  tenant_id: number
}

export interface TenantStorageQuotaData {
  tenant_id: number
  tenant_name: string
  storage_quota: number
  allocated_storage: number
  available_storage: number
  usage_percentage: number
}

export type GetTenantStorageQuotaResponseData = ApiResponseData<TenantStorageQuotaData>
