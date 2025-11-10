export interface LoginRequestData {
  /** admin 或 editor */
  email: string,
  /** 密码 */
  password: string
  /** 租户代码（tenant_admin角色必填） */
  tenant_code?: string
  /** 验证码 */
  // code: string
}

export type LoginCodeResponseData = ApiResponseData<string>

export type LoginResponseData = ApiResponseData<{ 
  token: string
  email: string
  name: string
  is_super_admin: boolean
  tenant_id: number | null
}>

export type UserInfoResponseData = ApiResponseData<{ username: string; roles: string[] }>
