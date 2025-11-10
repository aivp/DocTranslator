import { request } from "@/utils/service"
import type * as User from "./types/user"

/** 获取管理员列表 */
export function getUserListApi(params: User.GetUserRequestData) {
  return request<User.GetUserResponseData>({
    url: "users",
    method: "get",
    params
  })
}

/** 获取管理员详情 */
export function getUserDetailApi(id: number) {
  return request<User.GetUserData>({
    url: `user/${id}`,
    method: "get"
  })
}

/** 创建管理员 */
export function createUserApi(data: User.CreateUserRequestData) {
  return request({
    url: "user",
    method: "put",
    data
  })
}

/** 更新管理员 */
export function updateUserApi(id: number, data: User.UpdateUserRequestData) {
  return request({
    url: `user/${id}`,
    method: "post",
    data
  })
}

/** 删除管理员 */
export function deleteUserApi(id: number) {
  return request({
    url: `user/${id}`,
    method: "delete"
  })
}

/** 重置密码 */
export function resetPasswordApi(id: number) {
  return request({
    url: `user/${id}/reset-password`,
    method: "post"
  })
}

