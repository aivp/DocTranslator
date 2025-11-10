export interface GetUserRequestData {
  /** 当前页码 */
  page?: number
  /** 查询条数 */
  limit?: number
  /** 关键字 */
  search?: string
}

export interface GetUserData {
  id: number
  name: string
  email: string
  role?: string  // 'super_admin' or 'tenant_admin'
  created_at: string
}

export type GetUserResponseData = ApiResponseData<{
  data: GetUserData[]
  total: number
}>

export interface CreateUserRequestData {
  name: string
  email: string
  password: string
  tenant_id?: number  // 超级管理员必须指定，租户管理员自动关联
}

export interface UpdateUserRequestData {
  name?: string
  email?: string
}


