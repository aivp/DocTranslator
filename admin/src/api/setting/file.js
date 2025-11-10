import { request } from "@/utils/service"
// 获取系统存储文件列表
export function getFileList() {
  return request({
    url: "system/storages",
    method: "get"
  })
}
// 删除文件
export function deleteFile(data) {
  return request({
    url: "system/storages",
    method: "delete",
    data
  })
}
