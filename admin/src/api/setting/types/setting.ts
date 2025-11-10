
export interface ApiSetting {
  dashscope_key: string
  akool_client_id: string
  akool_client_secret: string
  tenant_id?: number
}

export type GetApiSettingResponseData = ApiResponseData<ApiSetting>


export interface OtherSetting {
  email_limit: string,
  tenant_id?: number
}

export type GetOtherSettingResponseData = ApiResponseData<OtherSetting>


export interface SiteSetting {
  version: string
  site_title: string
  site_name: string
  site_logo: string
  admin_site_title: string
  update_time?: string | null
  tenant_id?: number
}

export type GetSiteSettingResponseData = ApiResponseData<SiteSetting>

export type SettingNoResponseData=ApiResponseData<[]>